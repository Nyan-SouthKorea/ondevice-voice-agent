"""
01_generate_positive.py
Edge TTS로 "하이 포포" positive 샘플 생성
15 voices × 9 rates × 7 pitches = 945개 → data/hi_popo/positive/tts/

목소리 구성 (2026-03 기준):
- 한국어 4개: SunHiNeural, InJoonNeural, HyunsuNeural, HyunsuMultilingualNeural
- 다국어 11개: 영어/프랑스어/독일어/이탈리아어/포르투갈어 (한국어 발음 가능 확인)

Rate/Pitch 범위:
- Rate: -30% ~ +30% (9단계) — 그 이상은 발음 부자연스러워 학습에 역효과
- Pitch: -15Hz ~ +15Hz (7단계) — 그 이상은 음성 품질 저하
"""

import asyncio
import itertools
from pathlib import Path

import edge_tts

TARGET_PHRASE = "하이 포포"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "hi_popo" / "positive" / "tts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KO_VOICES = [
    # 한국어 (2026-03 기준 사용 가능)
    "ko-KR-SunHiNeural",               # 여성
    "ko-KR-InJoonNeural",              # 남성
    "ko-KR-HyunsuNeural",              # 남성
    "ko-KR-HyunsuMultilingualNeural",  # 남성 (다국어)
    # 다국어 (한국어 발음 가능 확인됨)
    "en-US-AvaMultilingualNeural",     # 여성
    "en-US-EmmaMultilingualNeural",    # 여성
    "en-US-AndrewMultilingualNeural",  # 남성
    "en-US-BrianMultilingualNeural",   # 남성
    "en-AU-WilliamMultilingualNeural", # 남성
    "fr-FR-VivienneMultilingualNeural",# 여성
    "fr-FR-RemyMultilingualNeural",    # 남성
    "de-DE-SeraphinaMultilingualNeural",# 여성
    "de-DE-FlorianMultilingualNeural", # 남성
    "it-IT-GiuseppeMultilingualNeural",# 남성
    "pt-BR-ThalitaMultilingualNeural", # 여성
]

RATES  = ["-30%", "-22%", "-15%", "-8%", "+0%", "+8%", "+15%", "+22%", "+30%"]
PITCHES = ["-15Hz", "-10Hz", "-5Hz", "+0Hz", "+5Hz", "+10Hz", "+15Hz"]


async def generate_one(voice: str, rate: str, pitch: str) -> Path:
    rate_tag = rate.replace("%", "p").replace("+", "pos").replace("-", "neg")
    pitch_tag = pitch.replace("Hz", "hz").replace("+", "pos").replace("-", "neg")
    filename = f"{voice}__{rate_tag}__{pitch_tag}.wav"
    out_path = OUTPUT_DIR / filename

    if out_path.exists():
        return out_path

    communicate = edge_tts.Communicate(
        text=TARGET_PHRASE,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    await communicate.save(str(out_path))
    return out_path


async def main():
    combos = list(itertools.product(KO_VOICES, RATES, PITCHES))
    print(f"생성 목표: {len(combos)}개 → data/positive/tts/")

    tasks = [generate_one(v, r, p) for v, r, p in combos]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = sum(1 for r in results if isinstance(r, Path))
    failed = [(combos[i], r) for i, r in enumerate(results) if isinstance(r, Exception)]

    print(f"완료: {success}/{len(combos)}")
    if failed:
        print(f"실패 {len(failed)}건:")
        for combo, err in failed:
            print(f"  {combo}: {err}")


if __name__ == "__main__":
    asyncio.run(main())
