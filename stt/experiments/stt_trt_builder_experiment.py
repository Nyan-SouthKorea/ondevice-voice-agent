"""
WhisperTRT 분리 빌드 실험 스크립트.
"""

import argparse
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def parse_args():
    """
    기능:
    - 분리 빌드 실험용 CLI 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스를 반환한다.
    """
    parser = argparse.ArgumentParser(
        description="WhisperTRT encoder/decoder 분리 빌드 실험 스크립트"
    )
    parser.add_argument(
        "--step",
        choices=["run", "decoder", "encoder", "combine", "load-check"],
        default="run",
        help="실행 단계",
    )
    parser.add_argument(
        "--model-name",
        default="base.en",
        help="Whisper 모델 이름. 예: tiny.en, base.en, base, small",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="다국어 모델일 때 사용할 language 코드. 예: ko, en",
    )
    parser.add_argument(
        "--work-dir",
        required=True,
        help="중간 산출물과 최종 checkpoint를 저장할 작업 디렉토리",
    )
    parser.add_argument(
        "--workspace-mb",
        type=int,
        default=256,
        help="TensorRT workspace 크기(MB)",
    )
    parser.add_argument(
        "--max-text-ctx",
        type=int,
        default=448,
        help="decoder 엔진 빌드 시 사용할 최대 text context 길이",
    )
    parser.add_argument(
        "--decoder-chunk-size",
        type=int,
        default=0,
        help="decoder block을 나눠 빌드할 chunk 크기. 0이면 전체 block을 한 번에 빌드",
    )
    parser.add_argument(
        "--encoder-chunk-size",
        type=int,
        default=0,
        help="encoder block을 나눠 빌드할 chunk 크기. 0이면 전체 block을 한 번에 빌드",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="TensorRT verbose 로그 사용 여부",
    )
    parser.add_argument(
        "--disable-lowmem-export",
        action="store_true",
        help="low-memory ONNX export 우회를 끄고 기본 torch2trt 경로를 사용한다.",
    )
    parser.add_argument(
        "--disable-fp16",
        action="store_true",
        help="fp16 대신 fp32로 빌드한다.",
    )
    parser.add_argument(
        "--keep-fp32-weights",
        action="store_true",
        help="빌드용 Whisper 가중치를 half로 줄이지 않고 fp32 상태로 유지한다.",
    )
    return parser.parse_args()


def prepare_dirs(work_dir):
    """
    기능:
    - 작업 디렉토리를 만들고 주요 경로를 반환한다.

    입력:
    - `work_dir`: 작업 디렉토리 문자열 경로.

    반환:
    - 주요 경로 딕셔너리를 반환한다.
    """
    root = Path(work_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": root,
        "cache_dir": cache_dir,
        "decoder_engines_dir": root / "decoder_engines",
        "decoder_chunk_meta": root / "decoder_chunk_meta.json",
        "encoder_engines_dir": root / "encoder_engines",
        "encoder_chunk_meta": root / "encoder_chunk_meta.json",
        "decoder_engine": root / "decoder_engine.pt",
        "decoder_extra": root / "decoder_extra.pt",
        "encoder_engine": root / "encoder_engine.pt",
        "encoder_extra": root / "encoder_extra.pt",
        "dims": root / "dims.json",
        "checkpoint": root / "whisper_trt_split.pth",
        "lowmem_runtime_flag": root / "lowmem_runtime.txt",
    }


def load_runtime_modules():
    """
    기능:
    - 분리 빌드에 필요한 런타임 모듈을 로드한다.

    입력:
    - 없음.

    반환:
    - torch, whisper, whisper_trt.model 모듈을 반환한다.
    """
    import torch
    import whisper
    import whisper_trt.model as wm

    return torch, whisper, wm


def load_model_for_trt_build(wm, whisper, model_name, use_half_weights):
    """
    기능:
    - TRT 빌드용 Whisper 모델을 CPU에서 half로 줄인 뒤 GPU에 올린다.

    입력:
    - `wm`: whisper_trt.model 모듈.
    - `whisper`: whisper 모듈.
    - `model_name`: Whisper 모델 이름.

    반환:
    - GPU에 적재된 fp16 Whisper 모델을 반환한다.
    """
    model = wm.load_model(model_name, device="cpu")
    if use_half_weights:
        model = model.half()
        for module in model.modules():
            if isinstance(module, whisper.model.LayerNorm):
                module.float()
    return model.cuda().eval()


def prepare_module_for_trt_build(module, whisper, use_half_weights):
    """
    기능:
    - 빌드 대상 모듈 조각만 dtype을 정리한 뒤 CUDA로 올린다.

    입력:
    - `module`: CUDA로 올릴 torch 모듈 조각.
    - `whisper`: whisper 모듈.
    - `use_half_weights`: half 가중치 사용 여부.

    반환:
    - CUDA에 올라간 eval 모드를 반환한다.
    """
    if use_half_weights:
        module = module.half()
        for child in module.modules():
            if isinstance(child, whisper.model.LayerNorm):
                child.float()
    return module.cuda().eval()


def get_decoder_chunk_ranges(total_blocks, chunk_size):
    """
    기능:
    - decoder block 수와 chunk 크기를 받아 빌드 범위를 계산한다.

    입력:
    - `total_blocks`: decoder block 총 개수.
    - `chunk_size`: 한 chunk에 넣을 block 개수. 0이면 전체 block을 한 번에 사용한다.

    반환:
    - `(start, end)` 튜플 목록을 반환한다.
    """
    if int(chunk_size) <= 0 or int(chunk_size) >= int(total_blocks):
        return [(0, int(total_blocks))]

    ranges = []
    start = 0
    total_blocks = int(total_blocks)
    chunk_size = int(chunk_size)
    while start < total_blocks:
        end = min(start + chunk_size, total_blocks)
        ranges.append((start, end))
        start = end
    return ranges


def build_chunked_text_decoder_class(torch, wm):
    """
    기능:
    - 여러 TRT decoder 엔진을 순차 실행하는 decoder 클래스를 만든다.

    입력:
    - `torch`: torch 모듈.
    - `wm`: whisper_trt.model 모듈.

    반환:
    - chunked decoder 클래스 객체를 반환한다.
    """

    class ChunkedTextDecoderTRT(torch.nn.Module):
        def __init__(
            self,
            engines,
            token_embedding,
            positional_embedding,
            ln,
            mask,
            input_dtype=None,
        ):
            super().__init__()
            self.engines = torch.nn.ModuleList(engines)
            self.token_embedding = token_embedding
            self.positional_embedding = positional_embedding
            self.ln = ln
            self.register_buffer("mask", mask, persistent=False)
            self.input_dtype = input_dtype

        @torch.no_grad()
        def forward(self, x, xa):
            offset = 0
            token_device = self.token_embedding.weight.device
            pos = self.positional_embedding[offset : offset + x.shape[-1]]
            if pos.device != token_device:
                pos = pos.to(token_device)
            x = self.token_embedding(x.to(token_device)) + pos
            if self.input_dtype is not None:
                x = x.to(device=xa.device, dtype=self.input_dtype)
                xa = xa.to(self.input_dtype)
            else:
                x = x.to(device=xa.device, dtype=xa.dtype)

            mask = self.mask
            if mask.device != x.device:
                mask = mask.to(x.device)
            for engine in self.engines:
                x = engine(x, xa, mask)

            ln_device = self.ln.weight.device
            if x.device != ln_device:
                x = x.to(ln_device)
            x = self.ln(x)
            logits = project_logits_with_embedding(x, self.token_embedding)
            return logits

    return ChunkedTextDecoderTRT


def build_audio_encoder_chunk_runtime_class(torch, wm):
    """
    기능:
    - 여러 TRT encoder 엔진을 순차 실행하는 encoder 클래스를 만든다.

    입력:
    - `torch`: torch 모듈.
    - `wm`: whisper_trt.model 모듈.

    반환:
    - chunked audio encoder 클래스 객체를 반환한다.
    """

    class ChunkedAudioEncoderTRT(torch.nn.Module):
        def __init__(self, first_engine, later_engines, positional_embedding):
            super().__init__()
            self.first_engine = first_engine
            self.later_engines = torch.nn.ModuleList(later_engines)
            self.register_buffer("positional_embedding", positional_embedding)

        @torch.no_grad()
        def forward(self, x):
            n_audio_ctx = int(x.shape[2] // 2)
            pos_embed = self.positional_embedding[-n_audio_ctx:, :]
            x = self.first_engine(x, pos_embed)
            for engine in self.later_engines:
                x = engine(x)
            return x

    return ChunkedAudioEncoderTRT


def project_logits_with_embedding(x, token_embedding):
    """
    기능:
    - token embedding weight의 현재 dtype/device를 기준으로 logits를 계산한다.

    입력:
    - `x`: decoder 출력 텐서.
    - `token_embedding`: token embedding 모듈.

    반환:
    - float32 logits를 반환한다.
    """
    import torch

    weight = token_embedding.weight
    if weight.device != x.device:
        weight = weight.to(x.device)
    if x.dtype != weight.dtype:
        x = x.to(weight.dtype)
    return (x @ torch.transpose(weight, 0, 1)).float()


def prepare_builder(
    wm,
    whisper,
    model_name,
    language,
    workspace_mb,
    max_text_ctx,
    verbose,
    use_lowmem_export,
    use_fp16,
    use_half_weights,
):
    """
    기능:
    - 선택한 모델의 WhisperTRT builder 설정을 준비한다.

    입력:
    - `wm`: whisper_trt.model 모듈.
    - `whisper`: whisper 모듈.
    - `model_name`: WhisperTRT 모델 이름.
        - `language`: tokenizer에 사용할 언어 코드.
        - `workspace_mb`: TensorRT workspace 크기(MB).
        - `max_text_ctx`: decoder 엔진 빌드 시 최대 text context 길이.
        - `verbose`: verbose 로그 사용 여부.
        - `use_lowmem_export`: low-memory ONNX export 우회 사용 여부.
        - `use_fp16`: fp16 빌드 사용 여부.

    반환:
    - 준비된 builder 클래스를 반환한다.
    """
    whisper.model.MultiHeadAttention.use_sdpa = False
    if model_name in wm.MODEL_BUILDERS:
        builder = wm.MODEL_BUILDERS[model_name]
    else:
        model = whisper.load_model(model_name, device="cpu")
        is_multilingual = bool(model.is_multilingual)
        num_languages = int(model.num_languages)
        del model

        class CustomBuilder(wm.WhisperTRTBuilder):
            pass

        @classmethod
        def get_tokenizer(cls):
            return whisper.tokenizer.get_tokenizer(
                is_multilingual,
                num_languages=num_languages,
                language=language,
                task="transcribe",
            )

        CustomBuilder.model = model_name
        CustomBuilder.get_tokenizer = get_tokenizer
        builder = CustomBuilder

    builder.verbose = verbose
    builder.fp16_mode = bool(use_fp16)
    builder.max_workspace_size = int(workspace_mb) * (1 << 20)
    builder.max_text_ctx = int(max_text_ctx)
    builder.use_lowmem_export = bool(use_lowmem_export)
    builder.use_half_weights = bool(use_half_weights)

    @classmethod
    @wm.torch.no_grad()
    def build_text_decoder_engine(cls, block_start=0, block_end=None):
        model = load_model_for_trt_build(
            wm, whisper, cls.model, cls.use_half_weights
        )
        dims = model.dims

        capped_text_ctx = max(
            8,
            min(int(getattr(cls, "max_text_ctx", dims.n_text_ctx)), dims.n_text_ctx),
        )
        total_blocks = len(model.decoder.blocks)
        block_start = max(0, int(block_start))
        block_end = total_blocks if block_end is None else min(int(block_end), total_blocks)
        if block_end <= block_start:
            raise ValueError(
                f"decoder block 범위가 잘못되었습니다: {block_start}..{block_end}"
            )

        decoder_blocks_module = wm._TextDecoderEngine(
            model.decoder.blocks[block_start:block_end]
        )

        x = wm.torch.randn(1, 1, dims.n_text_state).cuda()
        xa = wm.torch.randn(1, dims.n_audio_ctx, dims.n_audio_state).cuda()
        mask = wm.torch.randn(capped_text_ctx, capped_text_ctx).cuda()

        trt_kwargs = dict(
            use_onnx=True,
            min_shapes=[
                (1, 1, dims.n_text_state),
                (1, 1, dims.n_audio_state),
                (8, 8),
            ],
            opt_shapes=[
                (1, min(capped_text_ctx, 32), dims.n_text_state),
                (1, dims.n_audio_ctx, dims.n_audio_state),
                (min(capped_text_ctx, 32), min(capped_text_ctx, 32)),
            ],
            max_shapes=[
                (1, capped_text_ctx, dims.n_text_state),
                (1, dims.n_audio_ctx, dims.n_audio_state),
                (capped_text_ctx, capped_text_ctx),
            ],
            input_names=["x", "xa", "mask"],
            output_names=["output"],
            max_workspace_size=cls.max_workspace_size,
            fp16_mode=cls.fp16_mode,
            log_level=wm.tensorrt.Logger.VERBOSE if cls.verbose else wm.tensorrt.Logger.ERROR,
        )
        if cls.use_lowmem_export:
            engine = build_torch2trt_with_lowmem_export(
                wm,
                decoder_blocks_module,
                [x, xa, mask],
                **trt_kwargs,
            )
        else:
            engine = wm.torch2trt.torch2trt(
                decoder_blocks_module,
                [x, xa, mask],
                **trt_kwargs,
            )

        return engine

    builder.build_text_decoder_engine = build_text_decoder_engine

    @classmethod
    @wm.torch.no_grad()
    def build_audio_encoder_engine(cls, block_start=0, block_end=None):
        model = wm.load_model(cls.model, device="cpu").eval()
        dims = model.dims
        total_blocks = len(model.encoder.blocks)
        block_start = max(0, int(block_start))
        block_end = total_blocks if block_end is None else min(int(block_end), total_blocks)
        if block_end <= block_start:
            raise ValueError(
                f"encoder block 범위가 잘못되었습니다: {block_start}..{block_end}"
            )

        class AudioEncoderFirstChunkEngine(wm.nn.Module):
            def __init__(self, conv1, conv2, blocks, ln_post=None):
                super().__init__()
                self.conv1 = conv1
                self.conv2 = conv2
                self.blocks = blocks
                self.ln_post = ln_post

            @wm.torch.no_grad()
            def forward(self, x, positional_embedding):
                x = wm.F.gelu(self.conv1(x))
                x = wm.F.gelu(self.conv2(x))
                x = x.permute(0, 2, 1)
                x = (x + positional_embedding).to(x.dtype)
                for block in self.blocks:
                    x = block(x)
                if self.ln_post is not None:
                    x = self.ln_post(x)
                return x

        class AudioEncoderLaterChunkEngine(wm.nn.Module):
            def __init__(self, blocks, ln_post=None):
                super().__init__()
                self.blocks = blocks
                self.ln_post = ln_post

            @wm.torch.no_grad()
            def forward(self, x):
                for block in self.blocks:
                    x = block(x)
                if self.ln_post is not None:
                    x = self.ln_post(x)
                return x

        is_first = block_start == 0
        is_last = block_end >= total_blocks
        encoder_blocks = model.encoder.blocks[block_start:block_end]
        if is_first:
            encoder_module = AudioEncoderFirstChunkEngine(
                model.encoder.conv1,
                model.encoder.conv2,
                encoder_blocks,
                model.encoder.ln_post if is_last else None,
            )
        else:
            encoder_module = AudioEncoderLaterChunkEngine(
                encoder_blocks,
                model.encoder.ln_post if is_last else None,
            )
        encoder_module = prepare_module_for_trt_build(
            encoder_module,
            whisper,
            cls.use_half_weights,
        )

        n_frames = dims.n_audio_ctx * 2
        if is_first:
            x = wm.torch.randn(1, dims.n_mels, n_frames).cuda()
            positional_embedding = model.encoder.positional_embedding.detach()
            if cls.use_half_weights:
                positional_embedding = positional_embedding.half()
            positional_embedding = positional_embedding.cuda()
            trt_kwargs = dict(
                use_onnx=True,
                min_shapes=[
                    (1, dims.n_mels, 1),
                    (1, dims.n_audio_state),
                ],
                opt_shapes=[
                    (1, dims.n_mels, n_frames),
                    (dims.n_audio_ctx, dims.n_audio_state),
                ],
                max_shapes=[
                    (1, dims.n_mels, n_frames),
                    (dims.n_audio_ctx, dims.n_audio_state),
                ],
                input_names=["x", "positional_embedding"],
                output_names=["output"],
                max_workspace_size=cls.max_workspace_size,
                fp16_mode=cls.fp16_mode,
                log_level=wm.tensorrt.Logger.VERBOSE if cls.verbose else wm.tensorrt.Logger.ERROR,
            )
            if cls.use_lowmem_export:
                engine = build_torch2trt_with_lowmem_export(
                    wm,
                    encoder_module,
                    [x, positional_embedding],
                    **trt_kwargs,
                )
            else:
                engine = wm.torch2trt.torch2trt(
                    encoder_module,
                    [x, positional_embedding],
                    **trt_kwargs,
                )
        else:
            x = wm.torch.randn(1, dims.n_audio_ctx, dims.n_audio_state).cuda()
            trt_kwargs = dict(
                use_onnx=True,
                min_shapes=[
                    (1, dims.n_audio_ctx, dims.n_audio_state),
                ],
                opt_shapes=[
                    (1, dims.n_audio_ctx, dims.n_audio_state),
                ],
                max_shapes=[
                    (1, dims.n_audio_ctx, dims.n_audio_state),
                ],
                input_names=["x"],
                output_names=["output"],
                max_workspace_size=cls.max_workspace_size,
                fp16_mode=cls.fp16_mode,
                log_level=wm.tensorrt.Logger.VERBOSE if cls.verbose else wm.tensorrt.Logger.ERROR,
            )
            if cls.use_lowmem_export:
                engine = build_torch2trt_with_lowmem_export(
                    wm,
                    encoder_module,
                    [x],
                    **trt_kwargs,
                )
            else:
                engine = wm.torch2trt.torch2trt(
                    encoder_module,
                    [x],
                    **trt_kwargs,
                )

        del model
        return engine

    builder.build_audio_encoder_engine = build_audio_encoder_engine
    return builder


def load_checkpoint_model(
    checkpoint_path,
    model_name,
    language,
    workspace_mb,
    max_text_ctx,
    verbose=False,
):
    """
    기능:
    - single-engine 또는 chunked WhisperTRT checkpoint를 로드한다.

    입력:
    - `checkpoint_path`: WhisperTRT checkpoint 파일 경로.
    - `model_name`: tokenizer 생성을 위한 Whisper 모델 이름.
    - `language`: tokenizer 언어 코드.
    - `workspace_mb`: builder 기록용 workspace 크기(MB).
    - `max_text_ctx`: checkpoint 빌드 시 사용한 최대 text context 길이.
    - `verbose`: verbose 로그 사용 여부.

    반환:
    - 로드된 WhisperTRT 모델 객체를 반환한다.
    """
    torch, whisper, wm = load_runtime_modules()
    import torch.nn as nn

    dtype_map = {
        "float16": torch.float16,
        "float32": torch.float32,
    }

    builder = prepare_builder(
        wm=wm,
        whisper=whisper,
        model_name=model_name,
        language=language,
        workspace_mb=workspace_mb,
        max_text_ctx=max_text_ctx,
        verbose=verbose,
        use_lowmem_export=True,
        use_fp16=True,
        use_half_weights=True,
    )

    checkpoint_path = Path(checkpoint_path)
    work_dir_mode = checkpoint_path.is_dir()

    if work_dir_mode:
        paths = prepare_dirs(str(checkpoint_path))
        with paths["dims"].open("r", encoding="utf-8") as file:
            dims_dict = json.load(file)
        checkpoint = {"dims": dims_dict}
        if paths["decoder_chunk_meta"].exists():
            with paths["decoder_chunk_meta"].open("r", encoding="utf-8") as file:
                checkpoint["text_decoder_chunk_ranges"] = json.load(file)["chunk_ranges"]
        if paths["encoder_chunk_meta"].exists():
            with paths["encoder_chunk_meta"].open("r", encoding="utf-8") as file:
                checkpoint["audio_encoder_chunk_ranges"] = json.load(file)["chunk_ranges"]
        if paths["decoder_extra"].exists():
            checkpoint["text_decoder_extra_state"] = torch.load(
                paths["decoder_extra"], map_location="cpu"
            )
        if paths["encoder_extra"].exists():
            checkpoint["audio_encoder_extra_state"] = torch.load(
                paths["encoder_extra"], map_location="cpu"
            )
        decoder_dtype_path = checkpoint_path / "text_decoder_input_dtype.txt"
        if decoder_dtype_path.exists():
            checkpoint["text_decoder_input_dtype"] = (
                decoder_dtype_path.read_text(encoding="utf-8").strip()
            )
        if paths["lowmem_runtime_flag"].exists():
            checkpoint["lowmem_runtime"] = (
                paths["lowmem_runtime_flag"].read_text(encoding="utf-8").strip().lower()
                in {"1", "true", "yes", "on"}
            )
    else:
        checkpoint = torch.load(str(checkpoint_path), map_location="cpu")

    dims = wm.ModelDimensions(**checkpoint["dims"])
    decoder_input_dtype = dtype_map.get(checkpoint.get("text_decoder_input_dtype"))
    lowmem_runtime = bool(checkpoint.get("lowmem_runtime", False))

    aes = checkpoint["audio_encoder_extra_state"]
    if work_dir_mode:
        if paths["encoder_chunk_meta"].exists():
            with paths["encoder_chunk_meta"].open("r", encoding="utf-8") as file:
                encoder_chunk_meta = json.load(file)
            if len(encoder_chunk_meta.get("files", [])) > 1:
                chunked_audio_cls = build_audio_encoder_chunk_runtime_class(torch, wm)
                first_engine = wm.torch2trt.TRTModule()
                first_engine.load_state_dict(
                    torch.load(
                        paths["encoder_engines_dir"] / encoder_chunk_meta["files"][0],
                        map_location="cpu",
                    )
                )
                later_engines = []
                for file_name in encoder_chunk_meta["files"][1:]:
                    engine = wm.torch2trt.TRTModule()
                    engine.load_state_dict(
                        torch.load(
                            paths["encoder_engines_dir"] / file_name,
                            map_location="cpu",
                        )
                    )
                    later_engines.append(engine)
                encoder = chunked_audio_cls(
                    first_engine,
                    later_engines,
                    aes["positional_embedding"],
                )
            else:
                audio_encoder_engine = wm.torch2trt.TRTModule()
                audio_encoder_engine.load_state_dict(
                    torch.load(paths["encoder_engine"], map_location="cpu")
                )
                encoder = wm.AudioEncoderTRT(
                    audio_encoder_engine, aes["positional_embedding"]
                )
        else:
            audio_encoder_engine = wm.torch2trt.TRTModule()
            audio_encoder_engine.load_state_dict(
                torch.load(paths["encoder_engine"], map_location="cpu")
            )
            encoder = wm.AudioEncoderTRT(audio_encoder_engine, aes["positional_embedding"])
    elif "audio_encoder_engines" in checkpoint:
        chunked_audio_cls = build_audio_encoder_chunk_runtime_class(torch, wm)
        first_engine = wm.torch2trt.TRTModule()
        first_engine.load_state_dict(checkpoint["audio_encoder_engines"][0])
        later_engines = []
        for engine_state in checkpoint["audio_encoder_engines"][1:]:
            engine = wm.torch2trt.TRTModule()
            engine.load_state_dict(engine_state)
            later_engines.append(engine)
        encoder = chunked_audio_cls(
            first_engine,
            later_engines,
            aes["positional_embedding"],
        )
    else:
        audio_encoder_engine = wm.torch2trt.TRTModule()
        audio_encoder_engine.load_state_dict(checkpoint["audio_encoder_engine"])
        encoder = wm.AudioEncoderTRT(audio_encoder_engine, aes["positional_embedding"])

    tes = checkpoint["text_decoder_extra_state"]
    token_embedding = nn.Embedding(dims.n_vocab, dims.n_text_state)
    token_embedding.load_state_dict(tes["token_embedding"])
    positional_embedding = nn.Parameter(tes["positional_embedding"])
    text_ln = wm.LayerNorm(dims.n_text_state)
    text_ln.load_state_dict(tes["ln"])
    text_mask = tes["mask"]

    if work_dir_mode:
        if paths["decoder_chunk_meta"].exists():
            with paths["decoder_chunk_meta"].open("r", encoding="utf-8") as file:
                decoder_chunk_meta = json.load(file)
            if len(decoder_chunk_meta.get("files", [])) > 1:
                chunked_cls = build_chunked_text_decoder_class(torch, wm)
                decoder_engines = []
                for file_name in decoder_chunk_meta["files"]:
                    engine = wm.torch2trt.TRTModule()
                    engine.load_state_dict(
                        torch.load(
                            paths["decoder_engines_dir"] / file_name,
                            map_location="cpu",
                        )
                    )
                    decoder_engines.append(engine)
                decoder = chunked_cls(
                    decoder_engines,
                    token_embedding,
                    positional_embedding,
                    text_ln,
                    text_mask,
                    decoder_input_dtype,
                )
            else:
                class TextDecoderTRTWithDType(nn.Module):
                    def __init__(
                        self,
                        engine,
                        token_embedding,
                        positional_embedding,
                        ln,
                        mask,
                        input_dtype=None,
                    ):
                        super().__init__()
                        self.engine = engine
                        self.token_embedding = token_embedding
                        self.positional_embedding = positional_embedding
                        self.ln = ln
                        self.register_buffer("mask", mask, persistent=False)
                        self.input_dtype = input_dtype

                    @torch.no_grad()
                    def forward(self, x, xa):
                        offset = 0
                        token_device = self.token_embedding.weight.device
                        pos = self.positional_embedding[offset : offset + x.shape[-1]]
                        if pos.device != token_device:
                            pos = pos.to(token_device)
                        x = self.token_embedding(x.to(token_device)) + pos
                        if self.input_dtype is not None:
                            x = x.to(device=xa.device, dtype=self.input_dtype)
                            xa = xa.to(self.input_dtype)
                        else:
                            x = x.to(device=xa.device, dtype=xa.dtype)
                        mask = self.mask
                        if mask.device != x.device:
                            mask = mask.to(x.device)
                        x = self.engine(x, xa, mask)
                        ln_device = self.ln.weight.device
                        if x.device != ln_device:
                            x = x.to(ln_device)
                        x = self.ln(x)
                        logits = project_logits_with_embedding(x, self.token_embedding)
                        return logits

                text_decoder_engine = wm.torch2trt.TRTModule()
                text_decoder_engine.load_state_dict(
                    torch.load(paths["decoder_engine"], map_location="cpu")
                )
                decoder = TextDecoderTRTWithDType(
                    text_decoder_engine,
                    token_embedding,
                    positional_embedding,
                    text_ln,
                    text_mask,
                    decoder_input_dtype,
                )
        else:
            text_decoder_engine = wm.torch2trt.TRTModule()
            text_decoder_engine.load_state_dict(
                torch.load(paths["decoder_engine"], map_location="cpu")
            )
            decoder = wm.TextDecoderTRT(
                text_decoder_engine,
                token_embedding,
                positional_embedding,
                text_ln,
                text_mask,
            )
    elif "text_decoder_engines" in checkpoint:
        chunked_cls = build_chunked_text_decoder_class(torch, wm)
        decoder_engines = []
        for engine_state in checkpoint["text_decoder_engines"]:
            engine = wm.torch2trt.TRTModule()
            engine.load_state_dict(engine_state)
            decoder_engines.append(engine)
        decoder = chunked_cls(
            decoder_engines,
            token_embedding,
            positional_embedding,
            text_ln,
            text_mask,
            decoder_input_dtype,
        )
    else:
        class TextDecoderTRTWithDType(nn.Module):
            def __init__(
                self,
                engine,
                token_embedding,
                positional_embedding,
                ln,
                mask,
                input_dtype=None,
            ):
                super().__init__()
                self.engine = engine
                self.token_embedding = token_embedding
                self.positional_embedding = positional_embedding
                self.ln = ln
                self.register_buffer("mask", mask, persistent=False)
                self.input_dtype = input_dtype

            @torch.no_grad()
            def forward(self, x, xa):
                offset = 0
                token_device = self.token_embedding.weight.device
                pos = self.positional_embedding[offset : offset + x.shape[-1]]
                if pos.device != token_device:
                    pos = pos.to(token_device)
                x = self.token_embedding(x.to(token_device)) + pos
                if self.input_dtype is not None:
                    x = x.to(device=xa.device, dtype=self.input_dtype)
                    xa = xa.to(self.input_dtype)
                else:
                    x = x.to(device=xa.device, dtype=xa.dtype)

                mask = self.mask
                if mask.device != x.device:
                    mask = mask.to(x.device)
                x = self.engine(x, xa, mask)
                ln_device = self.ln.weight.device
                if x.device != ln_device:
                    x = x.to(ln_device)
                x = self.ln(x)
                logits = project_logits_with_embedding(x, self.token_embedding)
                return logits

        text_decoder_engine = wm.torch2trt.TRTModule()
        text_decoder_engine.load_state_dict(checkpoint["text_decoder_engine"])
        decoder = TextDecoderTRTWithDType(
            text_decoder_engine,
            token_embedding,
            positional_embedding,
            text_ln,
            text_mask,
            decoder_input_dtype,
        )

    def move_runtime_modules_to_cuda(trt_model):
        """
        기능:
        - TRT engine은 그대로 두고, runtime에 필요한 작은 모듈과 버퍼만 CUDA로 옮긴다.

        입력:
        - `trt_model`: 생성된 WhisperTRT 모델.

        반환:
        - CUDA 준비가 끝난 WhisperTRT 모델을 반환한다.
        """

        if hasattr(trt_model.encoder, "positional_embedding"):
            trt_model.encoder.positional_embedding = (
                trt_model.encoder.positional_embedding.cuda()
            )

        if lowmem_runtime:
            trt_model.decoder.token_embedding = trt_model.decoder.token_embedding.cpu().half()
            trt_model.decoder.ln = trt_model.decoder.ln.cpu()
            if isinstance(trt_model.decoder.positional_embedding, torch.nn.Parameter):
                trt_model.decoder.positional_embedding = torch.nn.Parameter(
                    trt_model.decoder.positional_embedding.detach().cpu().half(),
                    requires_grad=False,
                )
            else:
                trt_model.decoder.positional_embedding = (
                    trt_model.decoder.positional_embedding.cpu().half()
                )
            trt_model.decoder.mask = trt_model.decoder.mask.cuda()
        else:
            trt_model.decoder.token_embedding = trt_model.decoder.token_embedding.cuda()
            trt_model.decoder.ln = trt_model.decoder.ln.cuda()
            if isinstance(trt_model.decoder.positional_embedding, torch.nn.Parameter):
                trt_model.decoder.positional_embedding = torch.nn.Parameter(
                    trt_model.decoder.positional_embedding.detach().cuda(),
                    requires_grad=False,
                )
            else:
                trt_model.decoder.positional_embedding = (
                    trt_model.decoder.positional_embedding.cuda()
                )
            trt_model.decoder.mask = trt_model.decoder.mask.cuda()
        return trt_model.eval()

    model = wm.WhisperTRT(dims, encoder, decoder, builder.get_tokenizer())
    model = move_runtime_modules_to_cuda(model)
    return model


def build_torch2trt_with_lowmem_export(wm, module, inputs, **kwargs):
    """
    기능:
    - ONNX export와 graph folding의 메모리 피크를 낮춘 상태로 torch2trt를 호출한다.

    입력:
    - `wm`: whisper_trt.model 모듈.
    - `module`: TRT로 변환할 torch 모듈.
    - `inputs`: 예시 입력 목록.
    - `kwargs`: torch2trt 호출 인자.

    반환:
    - 생성된 TRT engine을 반환한다.
    """
    import onnx_graphsurgeon as gs

    original_export = wm.torch.onnx.export
    original_fold_constants = gs.Graph.fold_constants

    def export_without_constant_folding(*args, **export_kwargs):
        export_kwargs.setdefault("do_constant_folding", False)
        return original_export(*args, **export_kwargs)

    def fold_constants_noop(self, *args, **kwargs):
        return self

    wm.torch.onnx.export = export_without_constant_folding
    gs.Graph.fold_constants = fold_constants_noop
    try:
        return wm.torch2trt.torch2trt(module, inputs, **kwargs)
    finally:
        wm.torch.onnx.export = original_export
        gs.Graph.fold_constants = original_fold_constants


def write_dims(paths, model_name, max_text_ctx):
    """
    기능:
    - 최종 checkpoint에 필요한 dims 메타데이터를 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: Whisper 모델 이름.
    - `max_text_ctx`: 저장할 최대 text context 길이.

    반환:
    - 없음.
    """
    _, whisper, _ = load_runtime_modules()
    model = whisper.load_model(model_name, device="cpu")
    dims = vars(model.dims)
    dims["n_text_ctx"] = max(8, min(int(max_text_ctx), int(dims["n_text_ctx"])))
    with paths["dims"].open("w", encoding="utf-8") as file:
        json.dump(dims, file, ensure_ascii=False, indent=2)
    del model


def cleanup_cuda(torch):
    """
    기능:
    - 현재 프로세스의 CUDA 캐시를 최대한 정리한다.

    입력:
    - `torch`: torch 모듈.

    반환:
    - 없음.
    """
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def build_decoder(
    paths,
    model_name,
    language,
    workspace_mb,
    max_text_ctx,
    decoder_chunk_size,
    verbose,
    use_lowmem_export,
    use_fp16,
    use_half_weights,
):
    """
    기능:
    - decoder 엔진과 decoder extra state를 별도 파일로 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: WhisperTRT 모델 이름.
    - `workspace_mb`: TensorRT workspace 크기(MB).
    - `verbose`: verbose 로그 사용 여부.
    - `use_lowmem_export`: low-memory ONNX export 우회 사용 여부.
    - `use_fp16`: fp16 빌드 사용 여부.
    - `use_half_weights`: 빌드용 가중치를 half로 줄일지 여부.

    반환:
    - 없음.
    """
    torch, whisper, wm = load_runtime_modules()
    builder = prepare_builder(
        wm,
        whisper,
        model_name,
        language,
        workspace_mb,
        max_text_ctx,
        verbose,
        use_lowmem_export,
        use_fp16,
        use_half_weights,
    )
    write_dims(paths, model_name, max_text_ctx)

    base_model = whisper.load_model(model_name, device="cpu")
    chunk_ranges = get_decoder_chunk_ranges(
        total_blocks=len(base_model.decoder.blocks),
        chunk_size=decoder_chunk_size,
    )
    del base_model

    paths["decoder_engines_dir"].mkdir(parents=True, exist_ok=True)

    saved_chunk_paths = []
    for chunk_index in range(len(chunk_ranges)):
        if len(chunk_ranges) == 1:
            chunk_path = paths["decoder_engine"]
        else:
            chunk_path = (
                paths["decoder_engines_dir"] / f"decoder_engine_{chunk_index:02d}.pt"
            )
        saved_chunk_paths.append(chunk_path.name)

    with paths["decoder_chunk_meta"].open("w", encoding="utf-8") as file:
        json.dump(
            {
                "chunk_ranges": chunk_ranges,
                "chunk_size": int(decoder_chunk_size),
                "files": saved_chunk_paths,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    started_at = time.perf_counter()
    for chunk_index, (block_start, block_end) in enumerate(chunk_ranges):
        if len(chunk_ranges) == 1:
            chunk_path = paths["decoder_engine"]
        else:
            chunk_path = (
                paths["decoder_engines_dir"] / f"decoder_engine_{chunk_index:02d}.pt"
            )
        if chunk_path.exists():
            continue

        engine = builder.build_text_decoder_engine(block_start, block_end)
        torch.save(engine.state_dict(), chunk_path)
        del engine
        cleanup_cuda(torch)

    capped_text_ctx = max(8, min(int(max_text_ctx), int(builder.max_text_ctx)))
    model = whisper.load_model(model_name, device="cpu").eval()
    extra_state = {
        "token_embedding": model.decoder.token_embedding.state_dict(),
        "positional_embedding": model.decoder.positional_embedding[:capped_text_ctx]
        .detach()
        .cpu(),
        "ln": model.decoder.ln.state_dict(),
        "mask": model.decoder.mask[:capped_text_ctx, :capped_text_ctx].detach().cpu(),
    }
    torch.save(extra_state, paths["decoder_extra"])

    print("STEP=decoder", flush=True)
    print(f"ELAPSED_SEC={time.perf_counter() - started_at:.3f}", flush=True)

    del model
    cleanup_cuda(torch)


def build_encoder(
    paths,
    model_name,
    language,
    workspace_mb,
    max_text_ctx,
    encoder_chunk_size,
    verbose,
    use_lowmem_export,
    use_fp16,
    use_half_weights,
):
    """
    기능:
    - encoder 엔진과 encoder extra state를 별도 파일로 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: WhisperTRT 모델 이름.
    - `workspace_mb`: TensorRT workspace 크기(MB).
    - `verbose`: verbose 로그 사용 여부.
    - `use_lowmem_export`: low-memory ONNX export 우회 사용 여부.
    - `use_fp16`: fp16 빌드 사용 여부.
    - `use_half_weights`: 빌드용 가중치를 half로 줄일지 여부.

    반환:
    - 없음.
    """
    torch, whisper, wm = load_runtime_modules()
    builder = prepare_builder(
        wm,
        whisper,
        model_name,
        language,
        workspace_mb,
        max_text_ctx,
        verbose,
        use_lowmem_export,
        use_fp16,
        use_half_weights,
    )
    write_dims(paths, model_name, max_text_ctx)

    base_model = whisper.load_model(model_name, device="cpu")
    chunk_ranges = get_decoder_chunk_ranges(
        total_blocks=len(base_model.encoder.blocks),
        chunk_size=encoder_chunk_size,
    )
    del base_model

    paths["encoder_engines_dir"].mkdir(parents=True, exist_ok=True)

    saved_chunk_paths = []
    for chunk_index in range(len(chunk_ranges)):
        if len(chunk_ranges) == 1:
            chunk_path = paths["encoder_engine"]
        else:
            chunk_path = (
                paths["encoder_engines_dir"] / f"encoder_engine_{chunk_index:02d}.pt"
            )
        saved_chunk_paths.append(chunk_path.name)

    with paths["encoder_chunk_meta"].open("w", encoding="utf-8") as file:
        json.dump(
            {
                "chunk_ranges": chunk_ranges,
                "chunk_size": int(encoder_chunk_size),
                "files": saved_chunk_paths,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    started_at = time.perf_counter()
    for chunk_index, (block_start, block_end) in enumerate(chunk_ranges):
        if len(chunk_ranges) == 1:
            chunk_path = paths["encoder_engine"]
        else:
            chunk_path = (
                paths["encoder_engines_dir"] / f"encoder_engine_{chunk_index:02d}.pt"
            )
        if chunk_path.exists():
            continue

        engine = builder.build_audio_encoder_engine(block_start, block_end)
        torch.save(engine.state_dict(), chunk_path)
        del engine
        cleanup_cuda(torch)

    model = whisper.load_model(model_name, device="cpu").eval()
    extra_state = {
        "positional_embedding": model.encoder.positional_embedding.detach().cpu(),
    }
    torch.save(extra_state, paths["encoder_extra"])

    print("STEP=encoder", flush=True)
    print(f"ELAPSED_SEC={time.perf_counter() - started_at:.3f}", flush=True)

    del model
    cleanup_cuda(torch)


def combine_checkpoint(paths):
    """
    기능:
    - 분리 저장한 중간 산출물을 WhisperTRT 최종 checkpoint로 합친다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.

    반환:
    - 없음.
    """
    import torch
    import whisper_trt

    with paths["dims"].open("r", encoding="utf-8") as file:
        dims = json.load(file)

    chunk_meta = None
    if paths["decoder_chunk_meta"].exists():
        with paths["decoder_chunk_meta"].open("r", encoding="utf-8") as file:
            chunk_meta = json.load(file)
    encoder_chunk_meta = None
    if paths["encoder_chunk_meta"].exists():
        with paths["encoder_chunk_meta"].open("r", encoding="utf-8") as file:
            encoder_chunk_meta = json.load(file)

    text_decoder_engines = None
    text_decoder_engine = None
    if chunk_meta and len(chunk_meta.get("files", [])) > 1:
        text_decoder_engines = []
        for file_name in chunk_meta["files"]:
            text_decoder_engines.append(
                torch.load(paths["decoder_engines_dir"] / file_name, map_location="cpu")
            )
    else:
        text_decoder_engine = torch.load(paths["decoder_engine"], map_location="cpu")

    audio_encoder_engines = None
    audio_encoder_engine = None
    if encoder_chunk_meta and len(encoder_chunk_meta.get("files", [])) > 1:
        audio_encoder_engines = []
        for file_name in encoder_chunk_meta["files"]:
            audio_encoder_engines.append(
                torch.load(paths["encoder_engines_dir"] / file_name, map_location="cpu")
            )
    else:
        audio_encoder_engine = torch.load(paths["encoder_engine"], map_location="cpu")

    checkpoint = {
        "whisper_trt_version": whisper_trt.__version__,
        "dims": dims,
        "text_decoder_extra_state": torch.load(
            paths["decoder_extra"], map_location="cpu"
        ),
        "audio_encoder_extra_state": torch.load(
            paths["encoder_extra"], map_location="cpu"
        ),
    }
    if text_decoder_engines is not None:
        checkpoint["text_decoder_engines"] = text_decoder_engines
        checkpoint["text_decoder_chunk_ranges"] = chunk_meta["chunk_ranges"]
    else:
        checkpoint["text_decoder_engine"] = text_decoder_engine
    if audio_encoder_engines is not None:
        checkpoint["audio_encoder_engines"] = audio_encoder_engines
        checkpoint["audio_encoder_chunk_ranges"] = encoder_chunk_meta["chunk_ranges"]
    else:
        checkpoint["audio_encoder_engine"] = audio_encoder_engine
    torch.save(checkpoint, paths["checkpoint"])
    print("STEP=combine", flush=True)
    print(f"CHECKPOINT={paths['checkpoint']}", flush=True)


def load_check(paths, model_name, language, workspace_mb, max_text_ctx, verbose):
    """
    기능:
    - 합쳐진 checkpoint가 실제로 load 가능한지 확인한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: WhisperTRT 모델 이름.
    - `workspace_mb`: TensorRT workspace 크기(MB).
    - `verbose`: verbose 로그 사용 여부.

    반환:
    - 없음.
    """
    torch, _, _ = load_runtime_modules()
    started_at = time.perf_counter()
    model = load_checkpoint_model(
        checkpoint_path=paths["checkpoint"],
        model_name=model_name,
        language=language,
        workspace_mb=workspace_mb,
        max_text_ctx=max_text_ctx,
        verbose=verbose,
    )
    print("STEP=load-check", flush=True)
    print(f"MODEL={type(model).__name__}", flush=True)
    print(f"ELAPSED_SEC={time.perf_counter() - started_at:.3f}", flush=True)
    del model
    cleanup_cuda(torch)


def run_subprocess(step, args):
    """
    기능:
    - 현재 스크립트를 별도 프로세스로 다시 호출한다.

    입력:
    - `step`: 실행할 하위 단계 이름.
    - `args`: 상위 CLI 인자 네임스페이스.

    반환:
    - 없음.
    """
    command = [
        sys.executable,
        __file__,
        "--step",
        step,
        "--model-name",
        args.model_name,
        "--language",
        args.language,
        "--work-dir",
        args.work_dir,
        "--workspace-mb",
        str(args.workspace_mb),
        "--max-text-ctx",
        str(args.max_text_ctx),
        "--decoder-chunk-size",
        str(args.decoder_chunk_size),
        "--encoder-chunk-size",
        str(args.encoder_chunk_size),
    ]
    if args.verbose:
        command.append("--verbose")
    if args.disable_lowmem_export:
        command.append("--disable-lowmem-export")
    if args.disable_fp16:
        command.append("--disable-fp16")
    if args.keep_fp32_weights:
        command.append("--keep-fp32-weights")

    subprocess.run(command, check=True)


def main():
    """
    기능:
    - 선택한 단계에 따라 분리 빌드 실험을 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    paths = prepare_dirs(args.work_dir)

    if args.step == "decoder":
        build_decoder(
            paths,
            args.model_name,
            args.language,
            args.workspace_mb,
            args.max_text_ctx,
            args.decoder_chunk_size,
            args.verbose,
            not args.disable_lowmem_export,
            not args.disable_fp16,
            not args.keep_fp32_weights,
        )
        return

    if args.step == "encoder":
        build_encoder(
            paths,
            args.model_name,
            args.language,
            args.workspace_mb,
            args.max_text_ctx,
            args.encoder_chunk_size,
            args.verbose,
            not args.disable_lowmem_export,
            not args.disable_fp16,
            not args.keep_fp32_weights,
        )
        return

    if args.step == "combine":
        combine_checkpoint(paths)
        return

    if args.step == "load-check":
        load_check(
            paths,
            args.model_name,
            args.language,
            args.workspace_mb,
            args.max_text_ctx,
            args.verbose,
        )
        return

    run_subprocess("decoder", args)
    run_subprocess("encoder", args)
    run_subprocess("combine", args)
    run_subprocess("load-check", args)


if __name__ == "__main__":
    main()
