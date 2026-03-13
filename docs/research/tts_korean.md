# 한국어 TTS 기술 조사 (Wake Word 학습 데이터 생성용)

> 작성일: 2026-03-12
> 목적: "하이 포포" Positive 샘플 생성

---

## 결론

- **PoC 데이터 생성**: Edge TTS (목소리 다양성 최대)
- **제품화 시 대체**: MeloTTS (MIT, 오프라인, 라이선스 안전)

---

## 비교표

| 도구 | 오프라인 | 한국어 목소리 수 | 속도 조절 | 피치 조절 | 라이선스 | 상업적 사용 |
|------|---------|----------------|---------|---------|---------|-----------|
| **Edge TTS** | ❌ 인터넷 필요 | **10개** | ✅ `--rate` | ✅ `--pitch` | Microsoft 약관 | ⚠️ 회색지대 |
| **MeloTTS** | ✅ | 1개 | ✅ `speed=` | 후처리 필요 | **MIT** | ✅ |
| Coqui XTTS v2 | ✅ | 1개 (다국어) | ✅ | 후처리 필요 | Coqui Public License | ❌ (회사 폐업) |
| Meta MMS TTS | ✅ | 1개 | ❌ | ❌ | CC BY-NC 4.0 | ❌ |
| Kokoro-82M | ✅ | 한국어 미확인 | ✅ | 후처리 필요 | Apache 2.0 | ✅ |

---

## Edge TTS 상세

```python
import asyncio, edge_tts

KO_VOICES = [
    "ko-KR-SunHiNeural",       # 여성
    "ko-KR-InJoonNeural",      # 남성
    "ko-KR-BongJinNeural",     # 남성
    "ko-KR-GookMinNeural",     # 남성
    "ko-KR-HyunsuNeural",      # 남성
    "ko-KR-JiMinNeural",       # 여성
    "ko-KR-SeoHyeonNeural",    # 여성
    "ko-KR-SoonBokNeural",     # 여성
    "ko-KR-YuJinNeural",       # 여성
    "ko-KR-HyunsuMultilingualNeural",
]

# 10 voices × 5 rates × 3 pitches = 150개
RATES  = ["-20%", "-10%", "+0%", "+10%", "+20%"]
PITCHES = ["-5Hz", "+0Hz", "+5Hz"]
```

---

## librosa 증강 (공통 후처리)

```python
import librosa, soundfile as sf

def augment(y, sr):
    # 피치 시프트: -3 ~ +3 반음
    for n in [-3, -2, -1, 1, 2, 3]:
        yield librosa.effects.pitch_shift(y, sr=sr, n_steps=n)
    # 타임 스트레치
    for rate in [0.85, 0.92, 1.08, 1.15]:
        yield librosa.effects.time_stretch(y, rate=rate)
    # 화이트 노이즈
    import numpy as np
    yield y + np.random.normal(0, 0.005, len(y))
```

---

## 설치

```bash
# Edge TTS
pip install edge-tts

# MeloTTS
pip install melotts

# 증강용
pip install librosa soundfile
```
