"""
02b_mix_background.py
원본 positive(TTS/recorded) 기반 background mixing 증강

출력:
  - data/hi_popo/positive_aug/mixed_noise/*.wav
  - data/hi_popo/positive_aug/mixed_speech/*.wav
  - data/hi_popo/positive_aug/_manifests/mixed_background_manifest.jsonl

기본 정책:
  - 입력은 원본 positive만 사용
  - 전체 원본의 50%만 mixed 증강 대상으로 선택
  - mixed 대상 중 50%는 noise 계열, 50%는 speech 계열
  - background 소스 비율:
      MUSAN 50 / FSD50K 30 / AI Hub 20
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")

import librosa
import numpy as np
import soundfile as sf
from tqdm import tqdm

SEED = 42
TARGET_SR = 16000
CLIP_DURATION = 3.0
CLIP_SAMPLES = int(TARGET_SR * CLIP_DURATION)

MIX_RATIO = 0.5
SNR_NOISE = [5, 10, 15, 20]
SNR_SPEECH = [10, 15, 20]

BASE_DIR = Path(__file__).parent.parent / "data" / "hi_popo"
POSITIVE_DIRS = [
    BASE_DIR / "positive" / "tts",
    BASE_DIR / "positive" / "recorded",
]
NEGATIVE_DIR = BASE_DIR / "negative"

OUT_NOISE = BASE_DIR / "positive_aug" / "mixed_noise"
OUT_SPEECH = BASE_DIR / "positive_aug" / "mixed_speech"
MANIFEST_DIR = BASE_DIR / "positive_aug" / "_manifests"
MANIFEST_PATH = MANIFEST_DIR / "mixed_background_manifest.jsonl"

OUT_NOISE.mkdir(parents=True, exist_ok=True)
OUT_SPEECH.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

random.seed(SEED)
np.random.seed(SEED)


def load_audio(path: Path) -> np.ndarray:
    """
    기능:
    - 오디오 파일을 읽어 현재 파이프라인에서 쓸 배열로 변환한다.
    
    입력:
    - `path`: 처리할 파일 경로.
    
    반환:
    - 읽어 온 데이터 또는 객체를 반환한다.
    """
    y, _ = librosa.load(str(path), sr=TARGET_SR, mono=True)
    return y.astype(np.float32, copy=False)


def fit_to_3s(y: np.ndarray) -> np.ndarray:
    """
    기능:
    - 오디오를 3초 길이에 맞게 자르거나 zero-padding 한다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    if len(y) >= CLIP_SAMPLES:
        return y[:CLIP_SAMPLES]
    out = np.zeros(CLIP_SAMPLES, dtype=np.float32)
    out[:len(y)] = y
    return out


def sample_background(bg_files: list[Path]) -> np.ndarray:
    """
    기능:
    - 배경 파일 목록에서 무작위 3초 구간 하나를 뽑는다.
    
    입력:
    - `bg_files`: 함수에서 사용할 `bg_files` 값.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    path = random.choice(bg_files)
    y = load_audio(path)
    if len(y) <= CLIP_SAMPLES:
        return fit_to_3s(y)
    start = random.randint(0, len(y) - CLIP_SAMPLES)
    return y[start:start + CLIP_SAMPLES]


def mix_with_snr(fg: np.ndarray, bg: np.ndarray, snr_db: float) -> np.ndarray:
    """
    기능:
    - 전경 음성과 배경 음성을 원하는 SNR로 혼합한다.
    
    입력:
    - `fg`: 전경 음성 신호.
    - `bg`: 배경 오디오 신호.
    - `snr_db`: 혼합 시 적용할 SNR 값(dB).
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    fg = fit_to_3s(fg)
    bg = fit_to_3s(bg)
    fg_power = np.mean(np.square(fg)) + 1e-12
    bg_power = np.mean(np.square(bg)) + 1e-12
    desired_bg_power = fg_power / (10 ** (snr_db / 10))
    scale = np.sqrt(desired_bg_power / bg_power)
    mixed = np.clip(fg + bg * scale, -1.0, 1.0)
    return mixed.astype(np.float32, copy=False)


def save_audio(y: np.ndarray, path: Path) -> None:
    """
    기능:
    - 오디오 배열을 PCM_16 WAV로 저장한다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    - `path`: 처리할 파일 경로.
    
    반환:
    - 없음.
    """
    sf.write(str(path), y, TARGET_SR, subtype="PCM_16")


def collect_positive_files() -> list[Path]:
    """
    기능:
    - mixed 증강 대상이 될 positive 원본 파일 목록을 모은다.
    
    입력:
    - 없음.
    
    반환:
    - 수집한 목록 또는 그룹 정보를 반환한다.
    """
    files: list[Path] = []
    for d in POSITIVE_DIRS:
        if d.exists():
            files.extend(sorted(d.glob("*.wav")))
    return files


def collect_background_groups() -> dict[str, list[Path]]:
    """
    기능:
    - mixed 증강에 사용할 배경 파일들을 소스별로 모은다.
    
    입력:
    - 없음.
    
    반환:
    - 수집한 목록 또는 그룹 정보를 반환한다.
    """
    groups = {
        "musan_noise": sorted((NEGATIVE_DIR / "musan").glob("*.wav")),
        "fsd50k": sorted((NEGATIVE_DIR / "fsd50k").glob("*.wav")),
        "aihub": sorted((NEGATIVE_DIR / "aihub_free_conversation").glob("*.wav")),
    }
    return groups


def choose_background_source() -> str:
    # MUSAN 50 / FSD50K 30 / AI Hub 20
    """
    기능:
    - 정해진 비율에 따라 배경 소스를 무작위 선택한다.
    
    입력:
    - 없음.
    
    반환:
    - 문자열 결과를 반환한다.
    """
    r = random.random()
    if r < 0.5:
        return "musan_noise"
    if r < 0.8:
        return "fsd50k"
    return "aihub"


def main() -> None:
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    positives = collect_positive_files()
    backgrounds = collect_background_groups()

    if not positives:
        raise RuntimeError("원본 positive 파일이 없습니다.")

    if not backgrounds["musan_noise"] or not backgrounds["fsd50k"] or not backgrounds["aihub"]:
        raise RuntimeError("mixed 증강에 필요한 negative 배경 데이터가 준비되지 않았습니다.")

    selected_count = int(len(positives) * MIX_RATIO)
    selected = random.sample(positives, selected_count)
    half = selected_count // 2
    noise_targets = selected[:half]
    speech_targets = selected[half:]

    with MANIFEST_PATH.open("a", encoding="utf-8") as manifest:
        for src in tqdm(noise_targets, desc="mixed_noise 생성"):
            fg = load_audio(src)
            source_name = choose_background_source()
            bg = sample_background(backgrounds[source_name])
            snr = random.choice(SNR_NOISE)
            mixed = mix_with_snr(fg, bg, snr)
            out = OUT_NOISE / f"{src.stem}__{source_name}__snr{snr}.wav"
            if not out.exists():
                save_audio(mixed, out)
            manifest.write(json.dumps({
                "type": "mixed_noise",
                "src": str(src),
                "background_source": source_name,
                "snr": snr,
                "out": str(out),
            }, ensure_ascii=False) + "\n")

        speech_pool = backgrounds["aihub"] + backgrounds["musan_noise"]
        for src in tqdm(speech_targets, desc="mixed_speech 생성"):
            fg = load_audio(src)
            bg = sample_background(speech_pool)
            snr = random.choice(SNR_SPEECH)
            mixed = mix_with_snr(fg, bg, snr)
            out = OUT_SPEECH / f"{src.stem}__speechbg__snr{snr}.wav"
            if not out.exists():
                save_audio(mixed, out)
            manifest.write(json.dumps({
                "type": "mixed_speech",
                "src": str(src),
                "background_source": "aihub_or_musan",
                "snr": snr,
                "out": str(out),
            }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
