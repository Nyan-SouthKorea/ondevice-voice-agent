"""
고정 문장 데이터셋 기준 STT 비교 평가 스크립트.
"""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import string
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
STT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber


def parse_args():
    """
    기능:
    - STT 비교 평가 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=STT_ROOT / "datasets" / "korean_eval_50",
        help="기준 txt와 wav가 같이 들어 있는 데이터셋 디렉토리",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=[],
        help="비교할 설정. 예: whisper:tiny, whisper:base, api:gpt-4o-mini-transcribe",
    )
    parser.add_argument(
        "--language",
        default="ko",
        help="기본 언어 코드",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Whisper 실행 장치(cpu 또는 cuda)",
    )
    parser.add_argument(
        "--download-root",
        type=Path,
        default=None,
        help="Whisper 모델 다운로드 경로",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="공통 STT 힌트 프롬프트",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API STT용 키",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=STT_ROOT / "eval_results",
        help="평가 결과를 저장할 상위 디렉토리",
    )
    parser.add_argument(
        "--usage-purpose",
        default=None,
        help="API STT 사용 목적 기록용 문자열",
    )
    parser.add_argument(
        "--disable-warmup",
        action="store_true",
        help="로컬 모델 warm-up 1회를 생략한다",
    )
    return parser.parse_args()


def list_dataset_entries(dataset_dir):
    """
    기능:
    - 데이터셋 디렉토리에서 평가 가능한 txt/wav 쌍을 읽는다.

    입력:
    - `dataset_dir`: 기준 txt와 wav가 함께 들어 있는 디렉토리.

    반환:
    - 평가 대상 엔트리 목록을 반환한다.
    """
    entries = []
    for text_path in sorted(dataset_dir.glob("*.txt")):
        if not text_path.stem.isdigit():
            continue
        wav_path = text_path.with_suffix(".wav")
        if not wav_path.exists():
            continue
        entries.append(
            {
                "id": text_path.stem,
                "text_path": text_path,
                "wav_path": wav_path,
            }
        )

    if not entries:
        raise RuntimeError("평가 가능한 txt/wav 쌍이 없습니다.")
    return entries


def read_text_file(text_path):
    """
    기능:
    - 기준 문장 txt 내용을 읽는다.

    입력:
    - `text_path`: 읽을 txt 파일 경로.

    반환:
    - 기준 문장 문자열을 반환한다.
    """
    return text_path.read_text(encoding="utf-8").strip()


def normalize_text(text):
    """
    기능:
    - 비교용으로 텍스트를 소문자와 무구두점 기준으로 단순 정규화한다.

    입력:
    - `text`: 정규화할 원본 문자열.

    반환:
    - 비교용 정규화 문자열을 반환한다.
    """
    lowered = str(text).strip().lower()
    table = str.maketrans("", "", string.punctuation + "“”‘’…·")
    collapsed = lowered.translate(table)
    return "".join(collapsed.split())


def levenshtein_distance(source, target):
    """
    기능:
    - 두 문자열의 Levenshtein 거리를 계산한다.

    입력:
    - `source`: 기준 문자열.
    - `target`: 비교 문자열.

    반환:
    - 편집 거리 정수를 반환한다.
    """
    if source == target:
        return 0
    if not source:
        return len(target)
    if not target:
        return len(source)

    previous_row = list(range(len(target) + 1))
    for source_index, source_char in enumerate(source, start=1):
        current_row = [source_index]
        for target_index, target_char in enumerate(target, start=1):
            insert_cost = current_row[target_index - 1] + 1
            delete_cost = previous_row[target_index] + 1
            replace_cost = previous_row[target_index - 1] + (source_char != target_char)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row
    return previous_row[-1]


def compute_cer(reference, prediction):
    """
    기능:
    - 기준 문자열 대비 문자 오류율을 계산한다.

    입력:
    - `reference`: 기준 문자열.
    - `prediction`: 예측 문자열.

    반환:
    - 문자 오류율 실수를 반환한다.
    """
    if not reference:
        return 0.0 if not prediction else 1.0
    distance = levenshtein_distance(reference, prediction)
    return float(distance) / float(len(reference))


def parse_config(config_value):
    """
    기능:
    - `backend:model_name` 형식의 설정 문자열을 분리한다.

    입력:
    - `config_value`: 사용자가 전달한 설정 문자열.

    반환:
    - backend와 model_name을 담은 사전을 반환한다.
    """
    if ":" in config_value:
        model, model_name = config_value.split(":", 1)
    else:
        model = config_value
        model_name = None
    return {
        "model": model.strip(),
        "model_name": model_name.strip() if model_name else None,
    }


def build_run_name(config):
    """
    기능:
    - 결과 저장과 출력에 사용할 간단한 실행 이름을 만든다.

    입력:
    - `config`: backend와 model_name이 들어 있는 사전.

    반환:
    - 실행 이름 문자열을 반환한다.
    """
    model = config["model"]
    model_name = config["model_name"] or "default"
    return f"{model}_{model_name}".replace("/", "_").replace(":", "_")


def compute_percentile(values, percentile):
    """
    기능:
    - 숫자 목록에서 선형 보간 방식 percentile 값을 계산한다.

    입력:
    - `values`: 숫자 목록.
    - `percentile`: 계산할 percentile 값.

    반환:
    - percentile 실수를 반환한다.
    """
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    position = (len(sorted_values) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    lower_value = float(sorted_values[lower_index])
    upper_value = float(sorted_values[upper_index])
    return lower_value + (upper_value - lower_value) * fraction


def ensure_output_dir(base_dir, dataset_name):
    """
    기능:
    - 결과 저장용 타임스탬프 디렉토리를 만든다.

    입력:
    - `base_dir`: 결과를 저장할 상위 디렉토리.
    - `dataset_name`: 데이터셋 이름.

    반환:
    - 생성된 실행 디렉토리 경로를 반환한다.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / dataset_name / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def evaluate_config(entries, config, args):
    """
    기능:
    - 하나의 STT 설정으로 전체 데이터셋을 평가한다.

    입력:
    - `entries`: 평가 대상 txt/wav 엔트리 목록.
    - `config`: backend와 model_name 설정.
    - `args`: 공통 실행 인자 객체.

    반환:
    - 요약 정보와 샘플별 결과를 담은 사전을 반환한다.
    """
    run_name = build_run_name(config)
    load_started_at = time.perf_counter()
    transcriber = STTTranscriber(
        model=config["model"],
        model_name=config["model_name"],
        language=args.language,
        device=args.device,
        download_root=args.download_root,
        api_key=args.api_key,
        prompt=args.prompt,
        usage_purpose=args.usage_purpose or f"stt_benchmark:{args.dataset_dir.name}:{run_name}",
    )
    load_time_sec = time.perf_counter() - load_started_at

    warmup_enabled = (config["model"] != "api") and (not args.disable_warmup)
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
        "model": config["model"],
        "model_name": config["model_name"] or "default",
        "device": args.device or "auto",
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


def write_rows_csv(output_path, rows):
    """
    기능:
    - 샘플별 평가 결과를 CSV 파일로 저장한다.

    입력:
    - `output_path`: 저장할 CSV 경로.
    - `rows`: 샘플별 결과 목록.

    반환:
    - 없음.
    """
    fieldnames = [
        "run_name",
        "id",
        "audio_sec",
        "stt_sec",
        "rtf",
        "exact_match",
        "normalized_exact_match",
        "cer",
        "normalized_cer",
        "warmup_excluded",
        "reference",
        "prediction",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_csv(output_path, summaries):
    """
    기능:
    - 설정별 요약 결과를 CSV 파일로 저장한다.

    입력:
    - `output_path`: 저장할 CSV 경로.
    - `summaries`: 요약 결과 목록.

    반환:
    - 없음.
    """
    fieldnames = [
        "run_name",
        "model",
        "model_name",
        "device",
        "sample_count",
        "load_time_sec",
        "warmup_enabled",
        "warmup_sample_id",
        "warmup_time_sec",
        "total_audio_sec",
        "total_stt_sec",
        "mean_stt_sec",
        "p50_stt_sec",
        "p95_stt_sec",
        "max_stt_sec",
        "mean_rtf",
        "p50_rtf",
        "p95_rtf",
        "max_rtf",
        "exact_match_rate",
        "normalized_exact_match_rate",
        "mean_cer",
        "mean_normalized_cer",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)


def write_summary_json(output_path, dataset_dir, summaries):
    """
    기능:
    - 전체 평가 요약을 JSON 파일로 저장한다.

    입력:
    - `output_path`: 저장할 JSON 경로.
    - `dataset_dir`: 사용한 데이터셋 디렉토리.
    - `summaries`: 요약 결과 목록.

    반환:
    - 없음.
    """
    payload = {
        "dataset_dir": str(dataset_dir),
        "summaries": summaries,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_summary_markdown(output_path, summaries):
    """
    기능:
    - 코드가 계산한 summary 값을 그대로 Markdown 표로 저장한다.

    입력:
    - `output_path`: 저장할 Markdown 경로.
    - `summaries`: 요약 결과 목록.

    반환:
    - 없음.
    """
    lines = [
        "# STT Summary Table",
        "",
        "| run_name | model | device | sample_count | load_time_sec | warmup_time_sec | mean_stt_sec | p50_stt_sec | p95_stt_sec | max_stt_sec | mean_rtf | p95_rtf | norm_match | norm_cer |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in summaries:
        lines.append(
            "| "
            f"{summary['run_name']} | "
            f"{summary['model_name']} | "
            f"{summary['device']} | "
            f"{summary['sample_count']} | "
            f"{summary['load_time_sec']} | "
            f"{summary['warmup_time_sec']} | "
            f"{summary['mean_stt_sec']} | "
            f"{summary['p50_stt_sec']} | "
            f"{summary['p95_stt_sec']} | "
            f"{summary['max_stt_sec']} | "
            f"{summary['mean_rtf']} | "
            f"{summary['p95_rtf']} | "
            f"{summary['normalized_exact_match_rate']} | "
            f"{summary['mean_normalized_cer']} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readable_markdown(output_path, summary, rows):
    """
    기능:
    - GT와 예측을 사람이 바로 비교할 수 있는 Markdown 리포트를 저장한다.

    입력:
    - `output_path`: 저장할 Markdown 경로.
    - `summary`: 실행 요약 사전.
    - `rows`: 샘플별 결과 목록.

    반환:
    - 없음.
    """
    lines = [
        f"# {summary['run_name']}",
        "",
        "## Summary",
        "",
        f"- model: {summary['model']}",
        f"- model_name: {summary['model_name']}",
        f"- device: {summary['device']}",
        f"- sample_count: {summary['sample_count']}",
        f"- load_time_sec: {summary['load_time_sec']}",
        f"- warmup_enabled: {summary['warmup_enabled']}",
        f"- warmup_sample_id: {summary['warmup_sample_id'] or '-'}",
        f"- warmup_time_sec: {summary['warmup_time_sec']}",
        f"- mean_stt_sec: {summary['mean_stt_sec']}",
        f"- p50_stt_sec: {summary['p50_stt_sec']}",
        f"- p95_stt_sec: {summary['p95_stt_sec']}",
        f"- max_stt_sec: {summary['max_stt_sec']}",
        f"- mean_rtf: {summary['mean_rtf']}",
        f"- p50_rtf: {summary['p50_rtf']}",
        f"- p95_rtf: {summary['p95_rtf']}",
        f"- max_rtf: {summary['max_rtf']}",
        f"- exact_match_rate: {summary['exact_match_rate']}",
        f"- normalized_exact_match_rate: {summary['normalized_exact_match_rate']}",
        f"- mean_cer: {summary['mean_cer']}",
        f"- mean_normalized_cer: {summary['mean_normalized_cer']}",
        "",
        "## Per Sample",
        "",
    ]

    for row in rows:
        lines.extend(
            [
                f"### {row['id']}",
                f"- stt_sec: {row['stt_sec']}",
                f"- rtf: {row['rtf']}",
                f"- exact_match: {row['exact_match']}",
                f"- normalized_exact_match: {row['normalized_exact_match']}",
                f"- cer: {row['cer']}",
                f"- normalized_cer: {row['normalized_cer']}",
                f"- GT: {row['reference']}",
                f"- Pred: {row['prediction']}",
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def print_summary_table(summaries):
    """
    기능:
    - 설정별 요약 결과를 터미널에 보기 좋게 출력한다.

    입력:
    - `summaries`: 요약 결과 목록.

    반환:
    - 없음.
    """
    print("")
    print("STT 비교 요약")
    print("-" * 92)
    for summary in summaries:
        print(
            f"{summary['run_name']:<28} "
            f"load={summary['load_time_sec']:<6} "
            f"samples={summary['sample_count']:<3} "
            f"mean_stt={summary['mean_stt_sec']:<6} "
            f"p95_stt={summary['p95_stt_sec']:<6} "
            f"mean_rtf={summary['mean_rtf']:<6} "
            f"norm_match={summary['normalized_exact_match_rate']:<6} "
            f"norm_cer={summary['mean_normalized_cer']:<6}"
        )


def main():
    """
    기능:
    - 고정 문장 데이터셋 기준으로 여러 STT 설정을 순차 평가한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    dataset_dir = args.dataset_dir.resolve()
    entries = list_dataset_entries(dataset_dir)
    configs = args.config or ["whisper:tiny"]
    parsed_configs = [parse_config(config_value) for config_value in configs]
    run_dir = ensure_output_dir(args.output_dir.resolve(), dataset_dir.name)

    summaries = []
    for config in parsed_configs:
        result = evaluate_config(entries, config, args)
        summary = result["summary"]
        rows = result["rows"]
        run_name = summary["run_name"]
        summaries.append(summary)
        write_rows_csv(run_dir / f"{run_name}_per_sample.csv", rows)
        write_readable_markdown(run_dir / f"{run_name}_readable.md", summary, rows)

    write_summary_csv(run_dir / "summary.csv", summaries)
    write_summary_json(run_dir / "summary.json", dataset_dir, summaries)
    write_summary_markdown(run_dir / "summary.md", summaries)
    print_summary_table(summaries)
    print("")
    print(f"결과 저장 위치: {run_dir}")


if __name__ == "__main__":
    main()
