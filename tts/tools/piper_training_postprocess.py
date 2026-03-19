"""
Piper 학습 완료 후 checkpoint export와 benchmark를 자동으로 이어준다.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent


def parse_args():
    """
    기능:
    - Piper 학습 후처리 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - argparse namespace.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--wait-for-file", type=Path, default=None)
    parser.add_argument("--poll-sec", type=float, default=20.0)
    parser.add_argument("--prompt-limit-per-language", type=int, default=20)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--tts-python-bin",
        type=Path,
        default=WORKSPACE_ROOT / "env" / "tts_piper" / "bin" / "python",
    )
    parser.add_argument(
        "--export-python-bin",
        type=Path,
        default=WORKSPACE_ROOT / "env" / "tts_piper_train" / "bin" / "python",
    )
    parser.add_argument(
        "--benchmark-python-bin",
        type=Path,
        default=WORKSPACE_ROOT / "env" / "tts_eval_stt" / "bin" / "python",
    )
    parser.add_argument(
        "--benchmark-prompts",
        type=Path,
        default=REPO_ROOT / "tts" / "evaluation" / "prompts" / "tts_benchmark_prompts_v1.tsv",
    )
    return parser.parse_args()


def checkpoint_epoch(path: Path) -> int:
    """
    기능:
    - checkpoint 파일명에서 epoch를 추출한다.

    입력:
    - `path`: checkpoint 경로.

    반환:
    - epoch 정수. 없으면 -1.
    """
    match = re.search(r"epoch=(\d+)", path.name)
    return int(match.group(1)) if match else -1


def checkpoint_step(path: Path) -> int:
    """
    기능:
    - checkpoint 파일명에서 step을 추출한다.

    입력:
    - `path`: checkpoint 경로.

    반환:
    - step 정수. 없으면 -1.
    """
    match = re.search(r"step=(\d+)", path.name)
    return int(match.group(1)) if match else -1


def sort_checkpoints(paths: List[Path]) -> List[Path]:
    """
    기능:
    - checkpoint 목록을 epoch, step 기준으로 정렬한다.

    입력:
    - `paths`: checkpoint 경로 리스트.

    반환:
    - 정렬된 리스트.
    """
    return sorted(paths, key=lambda path: (checkpoint_epoch(path), checkpoint_step(path), path.name))


def write_status(path: Path, stage: str, lines: List[str]) -> None:
    """
    기능:
    - 후처리 상태를 로컬 문서로 기록한다.

    입력:
    - `path`: 상태 파일 경로.
    - `stage`: 현재 단계 문자열.
    - `lines`: 추가 줄 목록.

    반환:
    - 없음.
    """
    content = [
        "# Piper Training Postprocess Status",
        "",
        f"- stage: {stage}",
        f"- updated_at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
    ]
    content.extend(lines)
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def wait_for_file(path: Path, poll_sec: float, status_path: Path) -> None:
    """
    기능:
    - 지정 파일이 생길 때까지 대기한다.

    입력:
    - `path`: 대기할 파일.
    - `poll_sec`: polling 간격.
    - `status_path`: 상태 파일 경로.

    반환:
    - 없음.
    """
    while not path.exists():
        write_status(
            status_path,
            "waiting_for_training_done",
            [
                f"- wait_for_file: {path}",
                f"- poll_sec: {poll_sec}",
            ],
        )
        time.sleep(poll_sec)


def collect_target_checkpoints(run_root: Path) -> List[Path]:
    """
    기능:
    - export와 benchmark 대상으로 쓸 checkpoint 목록을 모은다.

    입력:
    - `run_root`: 학습 실행 루트.

    반환:
    - checkpoint 경로 리스트.
    """
    important_dir = run_root / "checkpoint_review" / "important_checkpoints"
    important = sort_checkpoints(list(important_dir.glob("*.ckpt")))
    latest_all = sort_checkpoints(list((run_root / "train_root" / "lightning_logs").rglob("*.ckpt")))
    targets = list(important)
    if latest_all:
        latest = latest_all[-1]
        if latest not in targets:
            targets.append(latest)
    return sort_checkpoints(targets)


def export_checkpoint(
    checkpoint_path: Path,
    export_root: Path,
    config_src: Path,
    export_python_bin: Path,
) -> Dict[str, str]:
    """
    기능:
    - checkpoint를 ONNX로 export하고 Piper runtime config를 함께 복사한다.

    입력:
    - `checkpoint_path`: source checkpoint.
    - `export_root`: export 상위 디렉토리.
    - `config_src`: preprocessed config.json 경로.
    - `python_bin`: export에 쓸 python 실행 파일.

    반환:
    - export metadata dict.
    """
    export_dir = export_root / checkpoint_path.stem
    export_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = export_dir / f"{checkpoint_path.stem}.onnx"
    config_dst = Path(f"{onnx_path}.json")
    if not onnx_path.exists():
        subprocess.run(
            [
                str(export_python_bin),
                "-m",
                "piper_train.export_onnx",
                str(checkpoint_path),
                str(onnx_path),
            ],
            check=True,
        )
    shutil.copy2(config_src, config_dst)

    metadata = {
        "checkpoint_path": str(checkpoint_path),
        "onnx_path": str(onnx_path),
        "config_path": str(config_dst),
        "epoch": checkpoint_epoch(checkpoint_path),
        "step": checkpoint_step(checkpoint_path),
    }
    (export_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (export_dir / "README.local.md").write_text(
        "\n".join(
            [
                f"# {checkpoint_path.stem}",
                "",
                f"- checkpoint_path: {checkpoint_path}",
                f"- onnx_path: {onnx_path}",
                f"- config_path: {config_dst}",
                f"- epoch: {metadata['epoch']}",
                f"- step: {metadata['step']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return metadata


def build_registry(entries: List[Dict[str, str]], tts_python_bin: Path, device: str) -> Dict[str, object]:
    """
    기능:
    - exported Piper ONNX들을 위한 benchmark registry payload를 만든다.

    입력:
    - `entries`: export metadata 리스트.
    - `tts_python_bin`: TTS worker env python.
    - `device`: Piper runtime 장치 문자열.

    반환:
    - registry dict.
    """
    registry_entries = []
    for item in entries:
        stem = Path(item["onnx_path"]).stem
        entry_id = re.sub(r"[^0-9a-zA-Z_]+", "_", f"piper_train_{stem}")
        registry_entries.append(
            {
                "id": entry_id,
                "display_name": f"Piper Train {stem}",
                "family": "custom_training_pilot",
                "backend": "piper",
                "prompt_language": "ko",
                "env_python": str(tts_python_bin),
                "synth_kwargs": {
                    "model": "piper",
                    "model_name": item["onnx_path"],
                    "device": device,
                },
            }
        )
    return {"entries": registry_entries}


def run_benchmark(
    benchmark_python_bin: Path,
    registry_path: Path,
    prompts_path: Path,
    run_root: Path,
    prompt_limit_per_language: int,
) -> None:
    """
    기능:
    - exported checkpoint들을 기존 benchmark harness로 평가한다.

    입력:
    - `benchmark_python_bin`: benchmark 실행 python.
    - `registry_path`: custom registry 경로.
    - `prompts_path`: prompt TSV 경로.
    - `run_root`: benchmark output root.
    - `prompt_limit_per_language`: 언어별 prompt 수 제한.

    반환:
    - 없음.
    """
    subprocess.run(
        [
            str(benchmark_python_bin),
            str(REPO_ROOT / "tts" / "tools" / "tts_benchmark.py"),
            "--registry",
            str(registry_path),
            "--prompts",
            str(prompts_path),
            "--run-name",
            run_root.name,
            "--output-root",
            str(run_root),
            "--prompt-limit-per-language",
            str(prompt_limit_per_language),
        ],
        check=True,
    )


def main():
    """
    기능:
    - Piper pilot 학습 완료 후 export와 benchmark를 자동 수행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    run_root = args.run_root.resolve()
    status_path = run_root / "postprocess_status.local.md"
    export_root = run_root / "exported_onnx"
    benchmark_root = run_root / "benchmark_postprocess"
    config_src = run_root / "preprocessed" / "config.json"

    try:
        if args.wait_for_file:
            wait_for_file(args.wait_for_file.resolve(), args.poll_sec, status_path)

        write_status(status_path, "collecting_checkpoints", [f"- run_root: {run_root}"])
        checkpoints = collect_target_checkpoints(run_root)
        if not checkpoints:
            raise RuntimeError("export 대상 checkpoint를 찾지 못했습니다.")

        exported = []
        write_status(
            status_path,
            "exporting_onnx",
            [
                f"- checkpoint_count: {len(checkpoints)}",
                *[f"- checkpoint: {path}" for path in checkpoints],
            ],
        )
        for checkpoint_path in checkpoints:
            exported.append(
                export_checkpoint(
                    checkpoint_path=checkpoint_path,
                    export_root=export_root,
                    config_src=config_src,
                    export_python_bin=args.export_python_bin,
                )
            )

        registry_payload = build_registry(exported, args.tts_python_bin, args.device)
        benchmark_root.mkdir(parents=True, exist_ok=True)
        registry_path = benchmark_root / "registry.json"
        registry_path.write_text(
            json.dumps(registry_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        benchmark_run_root = benchmark_root / time.strftime("%Y%m%d_%H%M%S")
        write_status(
            status_path,
            "running_benchmark",
            [
                f"- export_count: {len(exported)}",
                f"- benchmark_root: {benchmark_run_root}",
                f"- prompt_limit_per_language: {args.prompt_limit_per_language}",
            ],
        )
        run_benchmark(
            benchmark_python_bin=args.benchmark_python_bin,
            registry_path=registry_path,
            prompts_path=args.benchmark_prompts,
            run_root=benchmark_run_root,
            prompt_limit_per_language=args.prompt_limit_per_language,
        )

        manifest = {
            "run_root": str(run_root),
            "export_root": str(export_root),
            "benchmark_root": str(benchmark_run_root),
            "exported_count": len(exported),
            "prompt_limit_per_language": args.prompt_limit_per_language,
        }
        (run_root / "postprocess_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_status(
            status_path,
            "completed",
            [
                f"- export_root: {export_root}",
                f"- benchmark_root: {benchmark_run_root}",
                f"- exported_count: {len(exported)}",
            ],
        )
    except Exception as exc:
        write_status(
            status_path,
            "failed",
            [
                f"- error_type: {type(exc).__name__}",
                f"- error: {exc}",
            ],
        )
        raise


if __name__ == "__main__":
    main()
