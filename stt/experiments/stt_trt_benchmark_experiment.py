"""
WhisperTRT 한국어 분리 빌드 checkpoint 평가 스크립트.
"""

import argparse
from pathlib import Path
import sys
import time
import wave

import numpy as np
import torch
import whisper
import whisper_trt.model as wm

REPO_ROOT = Path(__file__).resolve().parents[2]
STT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt.tools.stt_benchmark import compute_cer
from stt.tools.stt_benchmark import compute_percentile
from stt.tools.stt_benchmark import ensure_output_dir
from stt.tools.stt_benchmark import list_dataset_entries
from stt.tools.stt_benchmark import normalize_text
from stt.tools.stt_benchmark import read_text_file
from stt.tools.stt_benchmark import write_readable_markdown
from stt.tools.stt_benchmark import write_rows_csv
from stt.tools.stt_benchmark import write_summary_csv
from stt.tools.stt_benchmark import write_summary_json
from stt.tools.stt_benchmark import write_summary_markdown
from stt.experiments.stt_trt_builder_experiment import prepare_builder


def parse_args():
    """
    기능:
    - WhisperTRT 평가 실행용 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=STT_ROOT / "datasets" / "korean_eval_50",
        help="평가용 txt/wav 쌍이 들어 있는 디렉토리",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="WhisperTRT 분리 빌드 checkpoint 경로",
    )
    parser.add_argument(
        "--model-name",
        default="base",
        help="기록용 Whisper 모델 이름",
    )
    parser.add_argument(
        "--language",
        default="ko",
        help="Tokenizer 언어 코드",
    )
    parser.add_argument(
        "--workspace-mb",
        type=int,
        default=128,
        help="checkpoint 로드 시 사용할 기록용 workspace 크기(MB)",
    )
    parser.add_argument(
        "--max-text-ctx",
        type=int,
        default=64,
        help="checkpoint 빌드 시 사용한 최대 text context 길이",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT.parent / "results" / "stt_trt_eval_results",
        help="평가 결과 저장 상위 디렉토리",
    )
    parser.add_argument(
        "--disable-warmup",
        action="store_true",
        help="warm-up 1회를 생략한다",
    )
    return parser.parse_args()


class WhisperTRTTranscriber:
    """
    기능:
    - WhisperTRT checkpoint를 로드하고 한국어 transcribe를 수행한다.

    입력:
    - `checkpoint_path`: WhisperTRT checkpoint 경로.
    - `model_name`: 기록용 모델 이름.
    - `language`: tokenizer 언어 코드.
    - `workspace_mb`: builder 설정 기록용 workspace 크기(MB).
    - `max_text_ctx`: builder 설정 기록용 최대 text context 길이.

    반환:
    - 없음.
    """

    def __init__(self, checkpoint_path, model_name, language, workspace_mb, max_text_ctx):
        self.last_duration_sec = 0.0
        builder = prepare_builder(
            wm=wm,
            whisper=whisper,
            model_name=model_name,
            language=language,
            workspace_mb=workspace_mb,
            max_text_ctx=max_text_ctx,
            verbose=False,
        )
        self.model = builder.load(str(checkpoint_path))

    def load_audio(self, wav_path):
        """
        기능:
        - 16kHz mono PCM16 wav를 float32 배열로 읽는다.

        입력:
        - `wav_path`: wav 파일 경로.

        반환:
        - 정규화된 float32 mono 오디오 배열을 반환한다.
        """
        with wave.open(str(wav_path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            pcm = wav_file.readframes(frame_count)

        if channels != 1:
            raise ValueError(f"mono only: {channels}")
        if sample_width != 2:
            raise ValueError(f"pcm16 only: {sample_width}")
        if sample_rate != 16000:
            raise ValueError(f"16k only: {sample_rate}")

        return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

    @torch.no_grad()
    def transcribe(self, audio):
        """
        기능:
        - 한국어 다국어 WhisperTRT checkpoint로 오디오를 전사한다.

        입력:
        - `audio`: 16kHz mono float32 오디오 배열.

        반환:
        - 전사 텍스트 문자열을 반환한다.
        """
        started_at = time.perf_counter()

        mel = whisper.audio.log_mel_spectrogram(
            audio,
            padding=whisper.audio.N_SAMPLES,
        )[None, ...].cuda()
        if int(mel.shape[2]) > whisper.audio.N_FRAMES:
            mel = mel[:, :, :whisper.audio.N_FRAMES]

        audio_features = self.model.embed_audio(mel)
        prompt = list(self.model.tokenizer.sot_sequence_including_notimestamps)
        tokens = torch.LongTensor(prompt).cuda()[None, ...]

        for _ in range(self.model.dims.n_text_ctx - len(prompt)):
            logits = self.model.logits(tokens, audio_features)
            next_tokens = logits.argmax(dim=-1)
            tokens = torch.cat([tokens, next_tokens[:, -1:]], dim=-1)
            if tokens[0, -1] == self.model.tokenizer.eot:
                break

        generated = tokens[:, len(prompt):]
        if generated.shape[1] > 0 and generated[0, -1] == self.model.tokenizer.eot:
            generated = generated[:, :-1]

        text = self.model.tokenizer.decode([int(x) for x in generated.flatten()])
        self.last_duration_sec = time.perf_counter() - started_at
        return str(text).strip()


def evaluate(entries, args):
    """
    기능:
    - WhisperTRT checkpoint 하나로 전체 데이터셋을 평가한다.

    입력:
    - `entries`: 평가 대상 txt/wav 엔트리 목록.
    - `args`: 공통 실행 인자 객체.

    반환:
    - summary와 rows를 담은 사전을 반환한다.
    """
    run_name = f"whisper_trt_{args.model_name}_{args.language}_ctx{args.max_text_ctx}"
    load_started_at = time.perf_counter()
    transcriber = WhisperTRTTranscriber(
        checkpoint_path=args.checkpoint,
        model_name=args.model_name,
        language=args.language,
        workspace_mb=args.workspace_mb,
        max_text_ctx=args.max_text_ctx,
    )
    load_time_sec = time.perf_counter() - load_started_at

    warmup_enabled = not args.disable_warmup
    warmup_time_sec = 0.0
    warmup_sample_id = ""
    if warmup_enabled and entries:
        warmup_entry = entries[0]
        warmup_audio = transcriber.load_audio(warmup_entry["wav_path"])
        warmup_started_at = time.perf_counter()
        transcriber.transcribe(warmup_audio)
        warmup_time_sec = time.perf_counter() - warmup_started_at
        warmup_sample_id = warmup_entry["id"]

    rows = []
    total_audio_sec = 0.0
    total_stt_sec = 0.0
    total_exact_match = 0
    total_normalized_exact_match = 0
    total_cer = 0.0
    total_normalized_cer = 0.0
    stt_times = []
    rtf_values = []

    for entry in entries:
        reference = read_text_file(entry["text_path"])
        audio = transcriber.load_audio(entry["wav_path"])
        audio_sec = float(len(audio)) / 16000.0
        prediction = transcriber.transcribe(audio)
        stt_sec = float(transcriber.last_duration_sec)

        normalized_reference = normalize_text(reference)
        normalized_prediction = normalize_text(prediction)

        exact_match = int(reference == prediction)
        normalized_exact_match = int(normalized_reference == normalized_prediction)
        cer = compute_cer(reference, prediction)
        normalized_cer = compute_cer(normalized_reference, normalized_prediction)
        rtf = stt_sec / audio_sec if audio_sec > 0 else 0.0

        rows.append(
            {
                "run_name": run_name,
                "id": entry["id"],
                "audio_sec": round(audio_sec, 4),
                "stt_sec": round(stt_sec, 4),
                "rtf": round(rtf, 4),
                "exact_match": exact_match,
                "normalized_exact_match": normalized_exact_match,
                "cer": round(cer, 4),
                "normalized_cer": round(normalized_cer, 4),
                "warmup_excluded": 1,
                "reference": reference,
                "prediction": prediction,
            }
        )

        total_audio_sec += audio_sec
        total_stt_sec += stt_sec
        total_exact_match += exact_match
        total_normalized_exact_match += normalized_exact_match
        total_cer += cer
        total_normalized_cer += normalized_cer
        stt_times.append(stt_sec)
        rtf_values.append(rtf)

    sample_count = len(rows)
    summary = {
        "run_name": run_name,
        "model": "whisper_trt",
        "model_name": args.model_name,
        "device": "cuda_trt",
        "sample_count": sample_count,
        "load_time_sec": round(load_time_sec, 4),
        "warmup_enabled": int(warmup_enabled),
        "warmup_sample_id": warmup_sample_id,
        "warmup_time_sec": round(warmup_time_sec, 4),
        "total_audio_sec": round(total_audio_sec, 4),
        "total_stt_sec": round(total_stt_sec, 4),
        "mean_stt_sec": round(total_stt_sec / sample_count, 4),
        "p50_stt_sec": round(compute_percentile(stt_times, 0.50), 4),
        "p95_stt_sec": round(compute_percentile(stt_times, 0.95), 4),
        "max_stt_sec": round(max(stt_times), 4) if stt_times else 0.0,
        "mean_rtf": round(total_stt_sec / total_audio_sec, 4) if total_audio_sec > 0 else 0.0,
        "p50_rtf": round(compute_percentile(rtf_values, 0.50), 4),
        "p95_rtf": round(compute_percentile(rtf_values, 0.95), 4),
        "max_rtf": round(max(rtf_values), 4) if rtf_values else 0.0,
        "exact_match_rate": round(total_exact_match / sample_count, 4),
        "normalized_exact_match_rate": round(total_normalized_exact_match / sample_count, 4),
        "mean_cer": round(total_cer / sample_count, 4),
        "mean_normalized_cer": round(total_normalized_cer / sample_count, 4),
    }
    return {"summary": summary, "rows": rows}


def main():
    """
    기능:
    - WhisperTRT 한국어 checkpoint를 고정 문장 데이터셋으로 평가한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    entries = list_dataset_entries(dataset_dir)
    run_dir = ensure_output_dir(args.output_dir.resolve(), dataset_dir.name)

    result = evaluate(entries, args)
    summary = result["summary"]
    rows = result["rows"]
    run_name = summary["run_name"]

    write_rows_csv(run_dir / f"{run_name}_per_sample.csv", rows)
    write_readable_markdown(run_dir / f"{run_name}_readable.md", summary, rows)
    write_summary_csv(run_dir / "summary.csv", [summary])
    write_summary_json(run_dir / "summary.json", dataset_dir, [summary])
    write_summary_markdown(run_dir / "summary.md", [summary])

    print(f"run_name={run_name}")
    print(f"result_dir={run_dir}")
    print(f"mean_stt_sec={summary['mean_stt_sec']}")
    print(f"p95_stt_sec={summary['p95_stt_sec']}")
    print(f"mean_rtf={summary['mean_rtf']}")
    print(f"normalized_exact_match_rate={summary['normalized_exact_match_rate']}")
    print(f"mean_normalized_cer={summary['mean_normalized_cer']}")


if __name__ == "__main__":
    main()
