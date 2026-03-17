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


def load_model_for_trt_build(wm, whisper, model_name):
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
    model = wm.load_model(model_name, device="cpu").half()
    for module in model.modules():
        if isinstance(module, whisper.model.LayerNorm):
            module.float()
    return model.cuda().eval()


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
        ):
            super().__init__()
            self.engines = torch.nn.ModuleList(engines)
            self.token_embedding = token_embedding
            self.positional_embedding = positional_embedding
            self.ln = ln
            self.register_buffer("mask", mask, persistent=False)

        @torch.no_grad()
        def forward(self, x, xa):
            offset = 0
            x = (
                self.token_embedding(x)
                + self.positional_embedding[offset : offset + x.shape[-1]]
            )
            x = x.to(xa.dtype)

            for engine in self.engines:
                x = engine(x, xa, self.mask)

            x = self.ln(x)
            logits = (
                x @ torch.transpose(self.token_embedding.weight.to(x.dtype), 0, 1)
            ).float()
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


def prepare_builder(
    wm,
    whisper,
    model_name,
    language,
    workspace_mb,
    max_text_ctx,
    verbose,
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
    builder.fp16_mode = True
    builder.max_workspace_size = int(workspace_mb) * (1 << 20)
    builder.max_text_ctx = int(max_text_ctx)

    @classmethod
    @wm.torch.no_grad()
    def build_text_decoder_engine(cls, block_start=0, block_end=None):
        model = load_model_for_trt_build(wm, whisper, cls.model)
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

        engine = build_torch2trt_with_lowmem_export(
            wm,
            decoder_blocks_module,
            [x, xa, mask],
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

        return engine

    builder.build_text_decoder_engine = build_text_decoder_engine

    @classmethod
    @wm.torch.no_grad()
    def build_audio_encoder_engine(cls, block_start=0, block_end=None):
        model = load_model_for_trt_build(wm, whisper, cls.model)
        dims = model.dims
        total_blocks = len(model.encoder.blocks)
        block_start = max(0, int(block_start))
        block_end = total_blocks if block_end is None else min(int(block_end), total_blocks)
        if block_end <= block_start:
            raise ValueError(
                f"encoder block 범위가 잘못되었습니다: {block_start}..{block_end}"
            )

        class AudioEncoderFirstChunkEngine(wm.nn.Module):
            def __init__(self, conv1, conv2, blocks):
                super().__init__()
                self.conv1 = conv1
                self.conv2 = conv2
                self.blocks = blocks

            @wm.torch.no_grad()
            def forward(self, x, positional_embedding):
                x = wm.F.gelu(self.conv1(x))
                x = wm.F.gelu(self.conv2(x))
                x = x.permute(0, 2, 1)
                x = (x + positional_embedding).to(x.dtype)
                for block in self.blocks:
                    x = block(x)
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
            )
        else:
            encoder_module = AudioEncoderLaterChunkEngine(
                encoder_blocks,
                model.encoder.ln_post if is_last else None,
            )

        n_frames = dims.n_audio_ctx * 2
        if is_first:
            x = wm.torch.randn(1, dims.n_mels, n_frames).cuda()
            positional_embedding = model.encoder.positional_embedding.cuda().detach()
            engine = build_torch2trt_with_lowmem_export(
                wm,
                encoder_module,
                [x, positional_embedding],
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
        else:
            x = wm.torch.randn(1, dims.n_audio_ctx, dims.n_audio_state).cuda()
            engine = build_torch2trt_with_lowmem_export(
                wm,
                encoder_module,
                [x],
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

    builder = prepare_builder(
        wm=wm,
        whisper=whisper,
        model_name=model_name,
        language=language,
        workspace_mb=workspace_mb,
        max_text_ctx=max_text_ctx,
        verbose=verbose,
    )

    checkpoint = torch.load(str(checkpoint_path), map_location="cpu")
    dims = wm.ModelDimensions(**checkpoint["dims"])

    aes = checkpoint["audio_encoder_extra_state"]
    if "audio_encoder_engines" in checkpoint:
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

    if "text_decoder_engines" in checkpoint:
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
        )
    else:
        text_decoder_engine = wm.torch2trt.TRTModule()
        text_decoder_engine.load_state_dict(checkpoint["text_decoder_engine"])
        decoder = wm.TextDecoderTRT(
            text_decoder_engine,
            token_embedding,
            positional_embedding,
            text_ln,
            text_mask,
        )

    model = wm.WhisperTRT(dims, encoder, decoder, builder.get_tokenizer())
    model = model.cuda().eval()
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
):
    """
    기능:
    - decoder 엔진과 decoder extra state를 별도 파일로 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: WhisperTRT 모델 이름.
    - `workspace_mb`: TensorRT workspace 크기(MB).
    - `verbose`: verbose 로그 사용 여부.

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
    )
    write_dims(paths, model_name, max_text_ctx)

    base_model = whisper.load_model(model_name, device="cpu")
    chunk_ranges = get_decoder_chunk_ranges(
        total_blocks=len(base_model.decoder.blocks),
        chunk_size=decoder_chunk_size,
    )
    del base_model

    paths["decoder_engines_dir"].mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    saved_chunk_paths = []
    for chunk_index, (block_start, block_end) in enumerate(chunk_ranges):
        engine = builder.build_text_decoder_engine(block_start, block_end)
        if len(chunk_ranges) == 1:
            chunk_path = paths["decoder_engine"]
        else:
            chunk_path = (
                paths["decoder_engines_dir"] / f"decoder_engine_{chunk_index:02d}.pt"
            )
        torch.save(engine.state_dict(), chunk_path)
        saved_chunk_paths.append(chunk_path.name)
        del engine
        cleanup_cuda(torch)

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
):
    """
    기능:
    - encoder 엔진과 encoder extra state를 별도 파일로 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: WhisperTRT 모델 이름.
    - `workspace_mb`: TensorRT workspace 크기(MB).
    - `verbose`: verbose 로그 사용 여부.

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
    )
    write_dims(paths, model_name, max_text_ctx)

    base_model = whisper.load_model(model_name, device="cpu")
    chunk_ranges = get_decoder_chunk_ranges(
        total_blocks=len(base_model.encoder.blocks),
        chunk_size=encoder_chunk_size,
    )
    del base_model

    paths["encoder_engines_dir"].mkdir(parents=True, exist_ok=True)

    started_at = time.perf_counter()
    saved_chunk_paths = []
    for chunk_index, (block_start, block_end) in enumerate(chunk_ranges):
        engine = builder.build_audio_encoder_engine(block_start, block_end)
        if len(chunk_ranges) == 1:
            chunk_path = paths["encoder_engine"]
        else:
            chunk_path = (
                paths["encoder_engines_dir"] / f"encoder_engine_{chunk_index:02d}.pt"
            )
        torch.save(engine.state_dict(), chunk_path)
        saved_chunk_paths.append(chunk_path.name)
        del engine
        cleanup_cuda(torch)

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
