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
        model = whisper.load_model(model_name)
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
    def build_text_decoder_engine(cls):
        model = wm.load_model(cls.model).cuda().eval()
        dims = model.dims

        decoder_blocks_module = wm._TextDecoderEngine(model.decoder.blocks)

        x = wm.torch.randn(1, 1, dims.n_text_state).cuda()
        xa = wm.torch.randn(1, dims.n_audio_ctx, dims.n_audio_state).cuda()
        mask = wm.torch.randn(dims.n_text_ctx, dims.n_text_ctx).cuda()

        capped_text_ctx = max(8, min(int(getattr(cls, "max_text_ctx", dims.n_text_ctx)), dims.n_text_ctx))

        engine = wm.torch2trt.torch2trt(
            decoder_blocks_module,
            [x, xa, mask],
            use_onnx=True,
            min_shapes=[
                (1, 1, dims.n_text_state),
                (1, 1, dims.n_audio_state),
                (dims.n_text_ctx, dims.n_text_ctx),
            ],
            opt_shapes=[
                (1, min(capped_text_ctx, 32), dims.n_text_state),
                (1, dims.n_audio_ctx, dims.n_audio_state),
                (dims.n_text_ctx, dims.n_text_ctx),
            ],
            max_shapes=[
                (1, capped_text_ctx, dims.n_text_state),
                (1, dims.n_audio_ctx, dims.n_audio_state),
                (dims.n_text_ctx, dims.n_text_ctx),
            ],
            input_names=["x", "xa", "mask"],
            output_names=["output"],
            max_workspace_size=cls.max_workspace_size,
            fp16_mode=cls.fp16_mode,
            log_level=wm.tensorrt.Logger.VERBOSE if cls.verbose else wm.tensorrt.Logger.ERROR,
        )

        return engine

    builder.build_text_decoder_engine = build_text_decoder_engine
    return builder


def write_dims(paths, model_name):
    """
    기능:
    - 최종 checkpoint에 필요한 dims 메타데이터를 저장한다.

    입력:
    - `paths`: prepare_dirs가 만든 경로 딕셔너리.
    - `model_name`: Whisper 모델 이름.

    반환:
    - 없음.
    """
    _, whisper, _ = load_runtime_modules()
    model = whisper.load_model(model_name)
    dims = vars(model.dims)
    with paths["dims"].open("w", encoding="utf-8") as file:
        json.dump(dims, file, ensure_ascii=False, indent=2)


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


def build_decoder(paths, model_name, language, workspace_mb, max_text_ctx, verbose):
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
    write_dims(paths, model_name)

    started_at = time.perf_counter()
    engine = builder.build_text_decoder_engine()
    torch.save(engine.state_dict(), paths["decoder_engine"])

    model = whisper.load_model(model_name).cuda().eval()
    extra_state = {
        "token_embedding": model.decoder.token_embedding.state_dict(),
        "positional_embedding": model.decoder.positional_embedding.detach().cpu(),
        "ln": model.decoder.ln.state_dict(),
        "mask": model.decoder.mask.detach().cpu(),
    }
    torch.save(extra_state, paths["decoder_extra"])

    print("STEP=decoder", flush=True)
    print(f"ELAPSED_SEC={time.perf_counter() - started_at:.3f}", flush=True)

    del model
    del engine
    cleanup_cuda(torch)


def build_encoder(paths, model_name, language, workspace_mb, max_text_ctx, verbose):
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
    write_dims(paths, model_name)

    started_at = time.perf_counter()
    engine = builder.build_audio_encoder_engine()
    torch.save(engine.state_dict(), paths["encoder_engine"])

    model = whisper.load_model(model_name).cuda().eval()
    extra_state = {
        "positional_embedding": model.encoder.positional_embedding.detach().cpu(),
    }
    torch.save(extra_state, paths["encoder_extra"])

    print("STEP=encoder", flush=True)
    print(f"ELAPSED_SEC={time.perf_counter() - started_at:.3f}", flush=True)

    del model
    del engine
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

    checkpoint = {
        "whisper_trt_version": whisper_trt.__version__,
        "dims": dims,
        "text_decoder_engine": torch.load(paths["decoder_engine"], map_location="cpu"),
        "text_decoder_extra_state": torch.load(
            paths["decoder_extra"], map_location="cpu"
        ),
        "audio_encoder_engine": torch.load(paths["encoder_engine"], map_location="cpu"),
        "audio_encoder_extra_state": torch.load(
            paths["encoder_extra"], map_location="cpu"
        ),
    }
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
    started_at = time.perf_counter()
    model = builder.load(str(paths["checkpoint"]))
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
