"""
03_prepare_negative.py
Negative 샘플 수집 및 가공

현재 기준:
  - AI Hub 자유대화 음성(일반남여)
  - MUSAN
  - FSD50K

공통 출력 스펙:
  - WAV (PCM_16)
  - 16kHz
  - mono
  - 3.0초 고정 클립

현재 구현 범위:
  - MUSAN 전처리 완료
  - FSD50K / AI Hub는 추후 추가 예정
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")

import librosa
import numpy as np
import soundfile as sf
from tqdm import tqdm

# ── 설정 ──────────────────────────────────────────────────────────────────────
SEED = 42
TARGET_SR = 16000
CLIP_DURATION = 3.0
MIN_DURATION = 0.5
CLIP_SAMPLES = int(TARGET_SR * CLIP_DURATION)

POSITIVE_COUNT = 11_250
RATIO = 10
TOTAL_NEGATIVE = POSITIVE_COUNT * RATIO

QUOTA = {
    "aihub_free_conversation": 72_500,
    "musan": 20_000,
    "fsd50k": 20_000,
}

BASE_DIR = Path(__file__).parent.parent / "data" / "hi_popo"
NEG_DIR = BASE_DIR / "negative"
TMP_DIR = BASE_DIR / "_tmp_download"

MUSAN_DIR = TMP_DIR / "musan"
FSD50K_DIR = TMP_DIR / "fsd50k"
AIHUB_DIR = TMP_DIR / "aihub_free_conversation"
AIHUB_ARCHIVE_DIR = TMP_DIR / "AI-Hub_자유대화_음성(일반남녀)" / "Training"

random.seed(SEED)
np.random.seed(SEED)


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def save_wav(y: np.ndarray, path: Path) -> None:
    """
    기능:
    - 오디오 배열을 공통 스펙 WAV 파일로 저장한다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    - `path`: 처리할 파일 경로.
    
    반환:
    - 없음.
    """
    sf.write(str(path), y, TARGET_SR, subtype="PCM_16")


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    """
    기능:
    - 오디오 파일을 읽어 mono 16kHz 기준 배열로 정리한다.
    
    입력:
    - `path`: 처리할 파일 경로.
    
    반환:
    - 읽어 온 데이터 또는 객체를 반환한다.
    """
    y, sr = sf.read(str(path), always_2d=False)
    y = np.asarray(y, dtype=np.float32)

    if y.ndim == 2:
        y = y.mean(axis=1)

    if sr != TARGET_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR

    return y, sr


def iter_fixed_chunks(y: np.ndarray) -> list[np.ndarray]:
    """
    기능:
    - 입력 오디오를 3초 고정 길이 청크 목록으로 나눈다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    chunks: list[np.ndarray] = []
    for start in range(0, len(y), CLIP_SAMPLES):
        chunk = y[start:start + CLIP_SAMPLES]
        duration = len(chunk) / TARGET_SR
        if duration < MIN_DURATION:
            continue
        if len(chunk) < CLIP_SAMPLES:
            padded = np.zeros(CLIP_SAMPLES, dtype=np.float32)
            padded[:len(chunk)] = chunk
            chunk = padded
        chunks.append(chunk.astype(np.float32, copy=False))
    return chunks


def sample_indices(total: int, count: int) -> list[int]:
    """
    기능:
    - 전체 인덱스 중에서 필요한 개수만 무작위로 고른다.
    
    입력:
    - `total`: 전체 개수.
    - `count`: 선택하거나 저장할 개수.
    
    반환:
    - 계산된 결과 목록 또는 배열을 반환한다.
    """
    if total <= count:
        return list(range(total))
    return random.sample(range(total), count)


def ensure_dir(path: Path) -> None:
    """
    기능:
    - 대상 디렉토리가 없으면 생성한다.
    
    입력:
    - `path`: 처리할 파일 경로.
    
    반환:
    - 없음.
    """
    path.mkdir(parents=True, exist_ok=True)


# ── MUSAN ─────────────────────────────────────────────────────────────────────
def collect_musan_chunk_refs(limit_input_files: int | None = None) -> list[tuple[Path, int]]:
    """
    기능:
    - MUSAN 원본에서 저장 가능한 청크 위치 정보를 수집한다.
    
    입력:
    - `limit_input_files`: 입력 파일 개수 제한값.
    
    반환:
    - 수집한 목록 또는 그룹 정보를 반환한다.
    """
    if not MUSAN_DIR.exists():
        raise FileNotFoundError(
            f"MUSAN 디렉토리가 없습니다: {MUSAN_DIR}\n"
            "먼저 MUSAN 다운로드와 압축 해제를 완료하세요."
        )

    src_files = sorted(MUSAN_DIR.rglob("*.wav"))
    if limit_input_files is not None:
        src_files = src_files[:limit_input_files]
    print(f"[MUSAN] 원본 파일 수: {len(src_files):,}")

    chunk_refs: list[tuple[Path, int]] = []
    for src in tqdm(src_files, desc="[MUSAN] 청킹"):
        try:
            y, _ = load_audio(src)
            for idx, _chunk in enumerate(iter_fixed_chunks(y)):
                chunk_refs.append((src, idx))
        except Exception as exc:
            print(f"[MUSAN] 스킵: {src} ({exc})")
            continue

    print(f"[MUSAN] 생성된 후보 청크 수: {len(chunk_refs):,}")
    return chunk_refs


def prepare_musan(
    cleanup_source: bool = False,
    limit_input_files: int | None = None,
    limit_output_count: int | None = None,
) -> list[Path]:
    """
    기능:
    - MUSAN 원본을 읽어 negative 학습용 WAV 샘플로 저장한다.
    
    입력:
    - `cleanup_source`: 전처리 후 원본 폴더를 삭제할지 여부.
    - `limit_input_files`: 입력 파일 개수 제한값.
    - `limit_output_count`: 출력 샘플 개수 제한값.
    
    반환:
    - 준비해 저장한 결과 파일 목록을 반환한다.
    """
    out_dir = NEG_DIR / "musan"
    ensure_dir(out_dir)

    existing = sorted(out_dir.glob("*.wav"))
    if len(existing) >= QUOTA["musan"]:
        print(f"[MUSAN] 이미 {len(existing):,}개 존재, skip")
        return existing

    chunk_refs = collect_musan_chunk_refs(limit_input_files=limit_input_files)
    quota = QUOTA["musan"] if limit_output_count is None else limit_output_count
    target_count = min(quota, len(chunk_refs))
    selected = sample_indices(len(chunk_refs), target_count)
    selected_refs = [chunk_refs[idx] for idx in selected]

    saved: list[Path] = []
    for i, (src, chunk_idx) in enumerate(tqdm(selected_refs, desc="[MUSAN] 저장")):
        y, _ = load_audio(src)
        chunks = iter_fixed_chunks(y)
        if chunk_idx >= len(chunks):
            continue
        chunk = chunks[chunk_idx]
        out_path = out_dir / f"musan_{i:05d}.wav"
        if not out_path.exists():
            save_wav(chunk, out_path)
        saved.append(out_path)

    print(f"[MUSAN] 저장 완료: {len(saved):,}개 → {out_dir}")

    if cleanup_source:
        print(f"[MUSAN] 원본 폴더 삭제: {MUSAN_DIR}")
        shutil.rmtree(MUSAN_DIR)

    return saved


# ── 자리만 잡아두는 소스들 ───────────────────────────────────────────────────
def prepare_fsd50k() -> list[Path]:
    """
    기능:
    - FSD50K 원본을 읽어 negative 학습용 WAV 샘플로 저장한다.
    
    입력:
    - 없음.
    
    반환:
    - 준비해 저장한 결과 파일 목록을 반환한다.
    """
    audio_dir = FSD50K_DIR / "FSD50K.dev_audio"
    if not audio_dir.exists():
        raise FileNotFoundError(
            f"FSD50K dev 오디오 디렉토리가 없습니다: {audio_dir}\n"
            "먼저 FSD50K dev 압축 해제를 완료하세요."
        )

    out_dir = NEG_DIR / "fsd50k"
    ensure_dir(out_dir)

    existing = sorted(out_dir.glob("*.wav"))
    if len(existing) >= QUOTA["fsd50k"]:
        print(f"[FSD50K] 이미 {len(existing):,}개 존재, skip")
        return existing

    src_files = sorted(audio_dir.glob("*.wav"))
    print(f"[FSD50K] 원본 파일 수: {len(src_files):,}")

    # 각 파일을 개별 샘플 단위로 취급하되, 3초보다 긴 경우는 고정 길이 청크로 확장
    chunk_refs: list[tuple[Path, int]] = []
    for src in tqdm(src_files, desc="[FSD50K] 청킹"):
        try:
            y, _ = load_audio(src)
            chunks = iter_fixed_chunks(y)
            for idx, _chunk in enumerate(chunks):
                chunk_refs.append((src, idx))
        except Exception as exc:
            print(f"[FSD50K] 스킵: {src} ({exc})")
            continue

    print(f"[FSD50K] 생성된 후보 청크 수: {len(chunk_refs):,}")

    target_count = min(QUOTA["fsd50k"], len(chunk_refs))
    selected = sample_indices(len(chunk_refs), target_count)
    selected_refs = [chunk_refs[idx] for idx in selected]

    saved: list[Path] = []
    for i, (src, chunk_idx) in enumerate(tqdm(selected_refs, desc="[FSD50K] 저장")):
        y, _ = load_audio(src)
        chunks = iter_fixed_chunks(y)
        if chunk_idx >= len(chunks):
            continue
        out_path = out_dir / f"fsd50k_{i:05d}.wav"
        if not out_path.exists():
            save_wav(chunks[chunk_idx], out_path)
        saved.append(out_path)

    print(f"[FSD50K] 저장 완료: {len(saved):,}개 → {out_dir}")
    return saved


def prepare_aihub() -> list[Path]:
    """
    기능:
    - AI Hub 자유대화 음성을 풀고 negative 학습용 WAV 샘플로 저장한다.
    
    입력:
    - 없음.
    
    반환:
    - 준비해 저장한 결과 파일 목록을 반환한다.
    """
    if not AIHUB_ARCHIVE_DIR.exists():
        raise FileNotFoundError(
            f"AI Hub Training 디렉토리가 없습니다: {AIHUB_ARCHIVE_DIR}\n"
            "원천 zip 파일 경로를 확인하세요."
        )

    out_dir = NEG_DIR / "aihub_free_conversation"
    ensure_dir(out_dir)

    existing = sorted(out_dir.glob("*.wav"))
    if len(existing) >= QUOTA["aihub_free_conversation"]:
        print(f"[AIHub] 이미 {len(existing):,}개 존재, skip")
        return existing

    ensure_dir(AIHUB_DIR)
    source_archives = sorted(AIHUB_ARCHIVE_DIR.glob("[[]원천]*.zip"))
    print(f"[AIHub] 원천 zip 수: {len(source_archives):,}")

    # 원천 zip만 압축 해제
    extracted_marker = AIHUB_DIR / ".extracted_complete"
    if not extracted_marker.exists():
        for archive in source_archives:
            print(f"[AIHub] 압축 해제: {archive.name}")
            subprocess.run(["unzip", "-q", "-o", str(archive), "-d", str(AIHUB_DIR)], check=True)
        extracted_marker.touch()

    src_files = sorted(AIHUB_DIR.rglob("*.wav"))
    print(f"[AIHub] 원본 파일 수: {len(src_files):,}")

    chunk_refs: list[tuple[Path, int]] = []
    for src in tqdm(src_files, desc="[AIHub] 청킹"):
        try:
            y, _ = load_audio(src)
            chunks = iter_fixed_chunks(y)
            for idx, _chunk in enumerate(chunks):
                chunk_refs.append((src, idx))
        except Exception as exc:
            print(f"[AIHub] 스킵: {src} ({exc})")
            continue

    print(f"[AIHub] 생성된 후보 청크 수: {len(chunk_refs):,}")

    target_count = min(QUOTA["aihub_free_conversation"], len(chunk_refs))
    selected = sample_indices(len(chunk_refs), target_count)
    selected_refs = [chunk_refs[idx] for idx in selected]

    saved: list[Path] = []
    for i, (src, chunk_idx) in enumerate(tqdm(selected_refs, desc="[AIHub] 저장")):
        y, _ = load_audio(src)
        chunks = iter_fixed_chunks(y)
        if chunk_idx >= len(chunks):
            continue
        out_path = out_dir / f"aihub_{i:05d}.wav"
        if not out_path.exists():
            save_wav(chunks[chunk_idx], out_path)
        saved.append(out_path)

    print(f"[AIHub] 저장 완료: {len(saved):,}개 → {out_dir}")
    return saved


# ── 메인 ──────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    """
    기능:
    - 명령행 인자를 정의하고 파싱한다.
    
    입력:
    - 없음.
    
    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["musan"],
        choices=["musan", "fsd50k", "aihub"],
        help="처리할 negative 데이터 소스",
    )
    parser.add_argument(
        "--cleanup-source",
        action="store_true",
        help="전처리 후 선택한 원본 다운로드 폴더를 삭제",
    )
    parser.add_argument(
        "--limit-input-files",
        type=int,
        default=None,
        help="테스트용: 소스 파일 앞에서 N개만 사용",
    )
    parser.add_argument(
        "--limit-output-count",
        type=int,
        default=None,
        help="테스트용: 저장 개수를 N개로 제한",
    )
    return parser.parse_args()


def main() -> None:
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    args = parse_args()

    print(f"Negative 목표: {TOTAL_NEGATIVE:,}개 (Positive {POSITIVE_COUNT:,} × {RATIO})")
    print("공통 출력 스펙:")
    print(f"  - sample rate: {TARGET_SR}")
    print("  - channels: mono")
    print("  - format: wav (PCM_16)")
    print(f"  - clip duration: {CLIP_DURATION:.1f}s")
    print(f"  - seed: {SEED}")
    print()

    prepared: dict[str, int] = {}
    for source in args.sources:
        if source == "musan":
            prepared[source] = len(
                prepare_musan(
                    cleanup_source=args.cleanup_source,
                    limit_input_files=args.limit_input_files,
                    limit_output_count=args.limit_output_count,
                )
            )
        elif source == "fsd50k":
            prepared[source] = len(prepare_fsd50k())
        elif source == "aihub":
            prepared[source] = len(prepare_aihub())

    print()
    print("=== 요약 ===")
    for source, count in prepared.items():
        print(f"  {source}: {count:,}개")


if __name__ == "__main__":
    main()
