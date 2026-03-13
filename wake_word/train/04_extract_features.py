"""
04_extract_features.py
openWakeWord AudioFeatures 기반 feature 추출

입력:
  - positive_aug/clean
  - positive_aug/mixed_noise
  - positive_aug/mixed_speech
  - negative/musan
  - negative/fsd50k
  - negative/aihub_free_conversation

출력:
  - data/hi_popo/features/positive_features_train.npy
  - data/hi_popo/features/positive_features_test.npy
  - data/hi_popo/features/negative_features_train.npy
  - data/hi_popo/features/negative_features_test.npy
  - data/hi_popo/features/manifests/*.jsonl

비고:
  - openWakeWord 레포의 AudioFeatures를 직접 사용
  - trim_mmap 경로를 타지 않도록 자체 memmap 저장 루프 구현
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from numpy.lib.format import open_memmap
from tqdm import tqdm

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")

REPO_ROOT = Path(__file__).resolve().parents[1]
OPENWAKEWORD_ROOT = REPO_ROOT / "openWakeWord"
if str(OPENWAKEWORD_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENWAKEWORD_ROOT))

from openwakeword.utils import AudioFeatures, download_models  # noqa: E402

SEED = 42
TARGET_SR = 16000
CLIP_SAMPLES = TARGET_SR * 3
TEST_RATIO = 0.1
BATCH_SIZE = 128
PROGRESS_INTERVAL_SEC = 60

BASE_DIR = REPO_ROOT / "data" / "hi_popo"
FEATURE_DIR = BASE_DIR / "features"
MANIFEST_DIR = FEATURE_DIR / "manifests"
OWW_MODEL_DIR = OPENWAKEWORD_ROOT / "openwakeword" / "resources" / "models"

FEATURE_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

POSITIVE_SOURCES = [
    BASE_DIR / "positive_aug" / "clean",
    BASE_DIR / "positive_aug" / "mixed_noise",
    BASE_DIR / "positive_aug" / "mixed_speech",
]
NEGATIVE_SOURCES = [
    BASE_DIR / "negative" / "musan",
    BASE_DIR / "negative" / "fsd50k",
    BASE_DIR / "negative" / "aihub_free_conversation",
]

random.seed(SEED)
np.random.seed(SEED)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cpu", choices=["cpu", "gpu"])
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--test-ratio", type=float, default=TEST_RATIO)
    parser.add_argument("--limit-positive", type=int, default=None)
    parser.add_argument("--limit-negative", type=int, default=None)
    parser.add_argument(
        "--groups",
        nargs="+",
        choices=["positive_train", "positive_test", "negative_train", "negative_test"],
        default=["positive_train", "positive_test", "negative_train", "negative_test"],
    )
    parser.add_argument("--progress-interval-sec", type=int, default=PROGRESS_INTERVAL_SEC)
    return parser.parse_args()


def collect_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.exists():
            files.extend(sorted(path.glob("*.wav")))
    return files


def split_files(files: list[Path], test_ratio: float) -> tuple[list[Path], list[Path]]:
    files = list(files)
    random.shuffle(files)
    n_test = max(1, int(len(files) * test_ratio))
    test_files = files[:n_test]
    train_files = files[n_test:]
    return train_files, test_files


def write_manifest(name: str, files: list[Path]) -> None:
    out = MANIFEST_DIR / f"{name}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for path in files:
            f.write(json.dumps({"path": str(path)}, ensure_ascii=False) + "\n")


def load_pcm16(path: Path) -> np.ndarray:
    audio, sr = sf.read(str(path), always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if sr != TARGET_SR:
        raise ValueError(f"입력 샘플레이트가 16kHz가 아닙니다: {path} ({sr})")
    if len(audio) < CLIP_SAMPLES:
        padded = np.zeros(CLIP_SAMPLES, dtype=np.float32)
        padded[:len(audio)] = audio
        audio = padded
    elif len(audio) > CLIP_SAMPLES:
        audio = audio[:CLIP_SAMPLES]
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767.0).astype(np.int16)


def ensure_openwakeword_models() -> tuple[str, str]:
    OWW_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    melspec_path = OWW_MODEL_DIR / "melspectrogram.onnx"
    embedding_path = OWW_MODEL_DIR / "embedding_model.onnx"
    if not melspec_path.exists() or not embedding_path.exists():
        download_models(target_directory=str(OWW_MODEL_DIR), inference_framework="onnx")
    return str(melspec_path), str(embedding_path)


def extract_features(
    files: list[Path],
    output_file: Path,
    device: str,
    batch_size: int,
    progress_interval_sec: int,
) -> None:
    if output_file.exists():
        output_file.unlink()

    melspec_path, embedding_path = ensure_openwakeword_models()
    feature_extractor = AudioFeatures(
        device=device,
        melspec_model_path=melspec_path,
        embedding_model_path=embedding_path,
    )
    sample_shape = feature_extractor.get_embedding_shape(CLIP_SAMPLES / TARGET_SR)
    fp = open_memmap(
        str(output_file),
        mode="w+",
        dtype=np.float32,
        shape=(len(files), sample_shape[0], sample_shape[1]),
    )

    row = 0
    batch: list[np.ndarray] = []
    start_time = time.monotonic()
    last_report_time = start_time

    def maybe_report_progress(force: bool = False) -> None:
        nonlocal last_report_time
        now = time.monotonic()
        if not force and now - last_report_time < progress_interval_sec:
            return

        elapsed = now - start_time
        rate = row / elapsed if elapsed > 0 else 0.0
        percent = (row / len(files) * 100.0) if files else 100.0
        remaining = max(len(files) - row, 0)
        eta_sec = int(remaining / rate) if rate > 0 else -1
        eta_text = f"{eta_sec // 60}m{eta_sec % 60}s" if eta_sec >= 0 else "unknown"
        print(
            f"[progress] {output_file.stem}: {row}/{len(files)} "
            f"({percent:.1f}%) | {rate:.2f} clips/s | eta {eta_text}",
            flush=True,
        )
        last_report_time = now

    for path in tqdm(files, desc=f"features:{output_file.stem}"):
        batch.append(load_pcm16(path))
        if len(batch) >= batch_size:
            if device == "cpu":
                embedded = np.stack([feature_extractor._get_embeddings(x) for x in batch]).astype(np.float32)
            else:
                embedded = feature_extractor.embed_clips(np.stack(batch), batch_size=len(batch), ncpu=1)
            fp[row:row + embedded.shape[0], :, :] = embedded
            row += embedded.shape[0]
            fp.flush()
            batch = []
            maybe_report_progress()

    if batch:
        if device == "cpu":
            embedded = np.stack([feature_extractor._get_embeddings(x) for x in batch]).astype(np.float32)
        else:
            embedded = feature_extractor.embed_clips(np.stack(batch), batch_size=len(batch), ncpu=1)
        fp[row:row + embedded.shape[0], :, :] = embedded
        row += embedded.shape[0]
        fp.flush()
        maybe_report_progress()

    if row < len(files):
        trimmed = np.array(fp[:row], dtype=np.float32)
        del fp
        output_file.unlink()
        np.save(str(output_file), trimmed)

    maybe_report_progress(force=True)


def main() -> None:
    args = parse_args()

    positive_files = collect_files(POSITIVE_SOURCES)
    negative_files = collect_files(NEGATIVE_SOURCES)

    if args.limit_positive is not None:
        positive_files = positive_files[:args.limit_positive]
    if args.limit_negative is not None:
        negative_files = negative_files[:args.limit_negative]

    if not positive_files or not negative_files:
        raise RuntimeError("positive 또는 negative 입력 파일이 부족합니다.")

    pos_train, pos_test = split_files(positive_files, args.test_ratio)
    neg_train, neg_test = split_files(negative_files, args.test_ratio)

    write_manifest("positive_train", pos_train)
    write_manifest("positive_test", pos_test)
    write_manifest("negative_train", neg_train)
    write_manifest("negative_test", neg_test)

    print(f"Positive: train={len(pos_train):,}, test={len(pos_test):,}")
    print(f"Negative: train={len(neg_train):,}, test={len(neg_test):,}")

    group_map = {
        "positive_train": (pos_train, FEATURE_DIR / "positive_features_train.npy"),
        "positive_test": (pos_test, FEATURE_DIR / "positive_features_test.npy"),
        "negative_train": (neg_train, FEATURE_DIR / "negative_features_train.npy"),
        "negative_test": (neg_test, FEATURE_DIR / "negative_features_test.npy"),
    }

    for group_name in args.groups:
        files, output_file = group_map[group_name]
        extract_features(
            files,
            output_file,
            args.device,
            args.batch_size,
            args.progress_interval_sec,
        )


if __name__ == "__main__":
    main()
