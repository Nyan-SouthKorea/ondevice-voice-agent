"""
02_augment.py
Positive 샘플 증강 (TTS + recorded 모두 처리)
입력: data/hi_popo/positive/tts/*.wav
      data/hi_popo/positive/recorded/*.wav  (있을 경우)
출력: data/hi_popo/positive_aug/clean/*.wav

증강 종류:
  - 원본 변환:    24kHz → 16kHz 모노 (feature backbone 입력 포맷)
  - 피치 시프트:  -3, -2, +2, +3 반음 (4종)
  - 화이트 노이즈: SNR 5, 15, 25 dB (3종)
  - 볼륨 스케일:  0.5×, 0.8× (2종)

총: 원본 1 + 증강 9 = 10종 × 945 TTS = 9,450개
"""

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from tqdm import tqdm

TARGET_SR = 16000

BASE_DIR   = Path(__file__).parent.parent / "data" / "hi_popo"
INPUT_DIRS = [
    BASE_DIR / "positive" / "tts",
    BASE_DIR / "positive" / "recorded",
]
OUTPUT_DIR = BASE_DIR / "positive_aug" / "clean"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_16k_mono(path: Path) -> np.ndarray:
    """
    기능:
    - 오디오 파일을 16kHz 모노 신호로 읽는다.
    
    입력:
    - `path`: 처리할 파일 경로.
    
    반환:
    - 읽어 온 데이터 또는 객체를 반환한다.
    """
    y, sr = librosa.load(str(path), sr=TARGET_SR, mono=True)
    return y


def add_white_noise(y: np.ndarray, snr_db: float) -> np.ndarray:
    """
    기능:
    - 지정한 SNR에 맞춰 화이트 노이즈를 섞는다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    - `snr_db`: 혼합 시 적용할 SNR 값(dB).
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    signal_power = np.mean(y ** 2)
    noise_power  = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), len(y))
    return np.clip(y + noise, -1.0, 1.0)


def save(y: np.ndarray, path: Path):
    """
    기능:
    - 증강된 오디오를 WAV 파일로 저장한다.
    
    입력:
    - `y`: 처리할 오디오 파형 배열.
    - `path`: 처리할 파일 경로.
    
    반환:
    - 없음.
    """
    sf.write(str(path), y, TARGET_SR, subtype="PCM_16")


def augment_file(src: Path):
    """
    기능:
    - 원본 positive 파일 하나에 대해 clean 증강본들을 생성한다.
    
    입력:
    - `src`: 원본 입력 파일 경로.
    
    반환:
    - 없음.
    """
    stem = src.stem
    y = load_16k_mono(src)

    # 원본 변환 (16kHz 모노)
    out = OUTPUT_DIR / f"{stem}__orig.wav"
    if not out.exists():
        save(y, out)

    # 피치 시프트
    for n in [-3, -2, 2, 3]:
        tag = f"pitch_{'neg' if n < 0 else 'pos'}{abs(n)}"
        out = OUTPUT_DIR / f"{stem}__{tag}.wav"
        if not out.exists():
            save(librosa.effects.pitch_shift(y, sr=TARGET_SR, n_steps=n), out)

    # 화이트 노이즈
    for snr in [5, 15, 25]:
        out = OUTPUT_DIR / f"{stem}__noise_snr{snr}.wav"
        if not out.exists():
            save(add_white_noise(y, snr), out)

    # 볼륨 스케일
    for scale in [0.5, 0.8]:
        tag = f"vol_{int(scale * 10)}"
        out = OUTPUT_DIR / f"{stem}__{tag}.wav"
        if not out.exists():
            save(np.clip(y * scale, -1.0, 1.0), out)


def main():
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    src_files = []
    for d in INPUT_DIRS:
        if d.exists():
            src_files.extend(sorted(d.glob("*.wav")))

    if not src_files:
        print("입력 파일 없음. data/hi_popo/positive/tts/ 또는 recorded/ 를 확인하세요.")
        return

    print(f"입력 파일: {len(src_files)}개 → 증강 10종 → 목표 {len(src_files) * 10}개")
    for src in tqdm(src_files, desc="증강 중"):
        augment_file(src)

    total = len(list(OUTPUT_DIR.glob("*.wav")))
    print(f"완료: {total}개 → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
