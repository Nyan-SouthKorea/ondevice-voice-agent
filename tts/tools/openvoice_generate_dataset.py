"""
OpenVoice로 synthetic dataset을 생성하고 선택적으로 STT filter를 수행한다.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import librosa
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber
from tts import TTSSynthesizer
from tts.tools.tts_benchmark import compute_cer, normalize_text


def parse_args():
    """
    기능:
    - synthetic dataset generation 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse namespace를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-tsv", type=Path, required=True)
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--reference-audio-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="KR")
    parser.add_argument("--voice", default="KR")
    parser.add_argument("--speed", type=float, default=1.1)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--max-items", type=int, default=32)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--enable-stt-filter", action="store_true")
    parser.add_argument("--stt-model-name", default="large-v3")
    parser.add_argument("--stt-device", default="cuda")
    parser.add_argument("--accept-max-normalized-cer", type=float, default=0.15)
    return parser.parse_args()


def load_rows(path):
    """
    기능:
    - TSV corpus를 읽는다.

    입력:
    - `path`: corpus TSV 경로.

    반환:
    - row dict list를 반환한다.
    """
    with open(path, "r", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file, delimiter="\t"))


def select_shard_rows(rows, shard_index, shard_count, max_items):
    """
    기능:
    - 전체 row 중 현재 shard가 담당할 항목만 고른다.

    입력:
    - `rows`: 전체 corpus row list.
    - `shard_index`: 현재 shard 인덱스.
    - `shard_count`: 전체 shard 개수.
    - `max_items`: shard 적용 뒤 최대 항목 수.

    반환:
    - 현재 shard row list를 반환한다.
    """
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must satisfy 0 <= shard_index < shard_count")
    shard_rows = [row for row_index, row in enumerate(rows) if row_index % shard_count == shard_index]
    return shard_rows[:max_items]


def load_audio_for_stt(audio_path):
    """
    기능:
    - STT filter용으로 wav를 16k mono float32 배열로 변환한다.

    입력:
    - `audio_path`: 생성된 wav 경로.

    반환:
    - 16k mono numpy 배열을 반환한다.
    """
    audio, sample_rate = sf.read(str(audio_path))
    if getattr(audio, "ndim", 1) == 2:
        audio = audio.mean(axis=1)
    if sample_rate != 16000:
        audio = librosa.resample(audio.astype("float32"), orig_sr=sample_rate, target_sr=16000)
    return audio.astype("float32")


def main():
    """
    기능:
    - OpenVoice synthetic dataset과 메타데이터를 생성한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    rows = select_shard_rows(
        load_rows(args.corpus_tsv),
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        max_items=args.max_items,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = args.output_dir / "wavs"
    wav_dir.mkdir(parents=True, exist_ok=True)

    synthesizer = TTSSynthesizer(
        model="openvoice_v2",
        model_name=args.model_name,
        voice=args.voice,
        speed=args.speed,
        device=args.device,
        reference_audio_path=args.reference_audio_path,
    )
    transcriber = None
    if args.enable_stt_filter:
        transcriber = STTTranscriber(
            model="whisper",
            model_name=args.stt_model_name,
            language="ko",
            device=args.stt_device,
        )

    result_rows = []
    try:
        for index, row in enumerate(rows, start=1):
            output_path = wav_dir / f"{row['text_id']}.wav"
            result = {
                "utterance_id": f"{args.reference_id}_{index:06d}",
                "text_id": row["text_id"],
                "text": row["text"],
                "source_corpus": row.get("source_corpus", ""),
                "category": row.get("category", ""),
                "reference_id": args.reference_id,
                "reference_audio_path": str(args.reference_audio_path),
                "speed": args.speed,
                "output_path": str(output_path),
                "success": False,
                "generation_sec": None,
                "audio_sec": None,
                "stt_prediction": "",
                "normalized_exact_match": "",
                "normalized_cer": "",
                "accepted": "",
                "error": "",
            }
            try:
                saved_path = synthesizer.synthesize_to_file(row["text"], output_path)
                info = sf.info(str(saved_path))
                result["success"] = True
                result["generation_sec"] = round(float(synthesizer.last_duration_sec), 3)
                result["audio_sec"] = round(float(info.frames / info.samplerate), 3)
                if transcriber is not None:
                    prediction = transcriber.transcribe(load_audio_for_stt(saved_path))
                    norm_ref = normalize_text(row["text"], "ko")
                    norm_pred = normalize_text(prediction, "ko")
                    normalized_cer = round(float(compute_cer(norm_ref, norm_pred)), 4)
                    normalized_exact = int(norm_ref == norm_pred)
                    accepted = int(normalized_exact == 1 or normalized_cer <= args.accept_max_normalized_cer)
                    result["stt_prediction"] = prediction
                    result["normalized_exact_match"] = normalized_exact
                    result["normalized_cer"] = normalized_cer
                    result["accepted"] = accepted
            except Exception as exc:
                result["error"] = f"{type(exc).__name__}: {exc}"
            result_rows.append(result)
    finally:
        if transcriber is not None:
            transcriber.close()

    manifest_path = args.output_dir / "manifest.tsv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(result_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(result_rows)

    summary = {
        "reference_id": args.reference_id,
        "speed": args.speed,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "item_count": len(result_rows),
        "success_count": sum(1 for row in result_rows if row["success"]),
        "accepted_count": sum(int(row["accepted"]) for row in result_rows if str(row["accepted"]).isdigit()),
        "manifest": str(manifest_path),
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
