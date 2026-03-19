"""
한국어 text-only corpus를 준비한다.
"""

import argparse
import csv
import json
import random
import re
import unicodedata
from pathlib import Path


def parse_args():
    """
    기능:
    - corpus builder 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse namespace를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data2/iena/260318_ondevice-voice-agent/results/tts_custom/corpora/ko_text_corpus_v1"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-char-count", type=int, default=6)
    parser.add_argument("--max-char-count", type=int, default=90)
    parser.add_argument("--pilot-target-sec", type=float, default=7200.0)
    parser.add_argument("--pilot-max-items", type=int, default=2200)
    parser.add_argument("--kss-limit", type=int, default=5000)
    parser.add_argument("--zeroth-limit", type=int, default=5000)
    return parser.parse_args()


def normalize_text(text):
    """
    기능:
    - corpus dedupe와 저장에 사용할 한국어 문장 정규화를 수행한다.

    입력:
    - `text`: 원본 문장 문자열.

    반환:
    - 정리된 문자열을 반환한다.
    """
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def classify_text(text):
    """
    기능:
    - 문장 특성을 단순 category 문자열로 분류한다.

    입력:
    - `text`: 정규화된 문장 문자열.

    반환:
    - category 문자열을 반환한다.
    """
    has_digit = bool(re.search(r"\d", text))
    has_english = bool(re.search(r"[A-Za-z]", text))
    if has_digit and has_english:
        return "mixed_numeric_en"
    if has_digit:
        return "numeric"
    if has_english:
        return "english_mixed"
    if "?" in text:
        return "question"
    if any(text.endswith(suffix) for suffix in ("하세요.", "하십시오.", "해 주세요.", "해주세요.", "해라.")):
        return "command"
    if any(text.endswith(suffix) for suffix in ("요.", "니다.", "입니다.", "합니다.", "습니다.")):
        return "polite"
    return "statement"


def estimate_duration_sec(text):
    """
    기능:
    - pilot subset 선정을 위해 발화 길이를 대략 추정한다.

    입력:
    - `text`: 정규화된 문장 문자열.

    반환:
    - 초 단위 추정 길이를 float로 반환한다.
    """
    dense_char_count = len(re.sub(r"\s+", "", text))
    return round(max(1.5, dense_char_count * 0.14), 2)


def iter_kss_rows(limit):
    """
    기능:
    - KSS streaming dataset에서 텍스트만 꺼낸다.

    입력:
    - `limit`: 최대 샘플 수.

    반환:
    - row dict iterable을 반환한다.
    """
    from datasets import load_dataset

    dataset = load_dataset("Bingsu/KSS_Dataset", split="train", streaming=True)
    dataset = dataset.remove_columns("audio")
    for index, row in zip(range(limit), dataset):
        text = row.get("expanded_script") or row.get("original_script") or ""
        yield {
            "source_corpus": "kss",
            "source_split": "train",
            "source_index": index,
            "source_text": text,
        }


def iter_zeroth_rows(limit):
    """
    기능:
    - Zeroth-Korean streaming dataset에서 텍스트만 꺼낸다.

    입력:
    - `limit`: 최대 샘플 수.

    반환:
    - row dict iterable을 반환한다.
    """
    from datasets import load_dataset

    dataset = load_dataset("Bingsu/zeroth-korean", split="train", streaming=True)
    dataset = dataset.remove_columns("audio")
    for index, row in zip(range(limit), dataset):
        yield {
            "source_corpus": "zeroth_korean",
            "source_split": "train",
            "source_index": index,
            "source_text": row.get("text") or "",
        }


def build_records(args):
    """
    기능:
    - KSS와 Zeroth 텍스트를 읽어 dedupe된 corpus record 목록을 만든다.

    입력:
    - `args`: 실행 인자 namespace.

    반환:
    - record list를 반환한다.
    """
    seen = set()
    records = []

    for source_iter in (iter_kss_rows(args.kss_limit), iter_zeroth_rows(args.zeroth_limit)):
        for row in source_iter:
            text = normalize_text(row["source_text"])
            dense_char_count = len(re.sub(r"\s+", "", text))
            if dense_char_count < args.min_char_count:
                continue
            if dense_char_count > args.max_char_count:
                continue
            if text in seen:
                continue
            seen.add(text)
            record = {
                "text_id": f"ko_{len(records)+1:06d}",
                "text": text,
                "source_corpus": row["source_corpus"],
                "source_split": row["source_split"],
                "source_index": row["source_index"],
                "category": classify_text(text),
                "language": "ko",
                "normalization_version": "ko_text_corpus_v1",
                "char_count": len(text),
                "dense_char_count": dense_char_count,
                "word_count": len(text.split()),
                "estimated_sec": estimate_duration_sec(text),
            }
            records.append(record)

    return records


def build_pilot_subset(records, seed, pilot_target_sec, pilot_max_items):
    """
    기능:
    - full corpus에서 pilot generation용 subset을 고른다.

    입력:
    - `records`: full corpus record list.
    - `seed`: shuffle seed.
    - `pilot_target_sec`: 목표 추정 초.
    - `pilot_max_items`: 최대 utterance 수.

    반환:
    - pilot record list를 반환한다.
    """
    rng = random.Random(seed)
    by_source = {}
    for row in records:
        by_source.setdefault(row["source_corpus"], []).append(dict(row))

    for rows in by_source.values():
        rng.shuffle(rows)

    source_names = sorted(by_source.keys())
    selected = []
    total_estimated_sec = 0.0
    while len(selected) < pilot_max_items and total_estimated_sec < pilot_target_sec:
        progressed = False
        for source_name in source_names:
            rows = by_source[source_name]
            if not rows:
                continue
            row = rows.pop()
            row["pilot_selected"] = True
            selected.append(row)
            total_estimated_sec += float(row["estimated_sec"])
            progressed = True
            if len(selected) >= pilot_max_items or total_estimated_sec >= pilot_target_sec:
                break
        if not progressed:
            break

    return selected


def write_jsonl(path, records):
    """
    기능:
    - record list를 JSONL로 저장한다.

    입력:
    - `path`: 출력 경로.
    - `records`: record list.

    반환:
    - 없음.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as output_file:
        for row in records:
            output_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_tsv(path, records):
    """
    기능:
    - record list를 TSV로 저장한다.

    입력:
    - `path`: 출력 경로.
    - `records`: record list.

    반환:
    - 없음.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(records)


def summarize(records, pilot_records):
    """
    기능:
    - corpus build 결과 요약 dict를 만든다.

    입력:
    - `records`: full record list.
    - `pilot_records`: pilot record list.

    반환:
    - summary dict를 반환한다.
    """
    by_source = {}
    by_category = {}
    for row in records:
        by_source[row["source_corpus"]] = by_source.get(row["source_corpus"], 0) + 1
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1

    return {
        "run_name": "ko_text_corpus_v1",
        "full_count": len(records),
        "pilot_count": len(pilot_records),
        "pilot_estimated_sec": round(sum(float(row["estimated_sec"]) for row in pilot_records), 2),
        "pilot_estimated_hour": round(sum(float(row["estimated_sec"]) for row in pilot_records) / 3600.0, 3),
        "source_counts": by_source,
        "category_counts": by_category,
    }


def main():
    """
    기능:
    - 한국어 text-only corpus와 pilot subset을 생성한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = build_records(args)
    pilot_records = build_pilot_subset(
        records=records,
        seed=args.seed,
        pilot_target_sec=args.pilot_target_sec,
        pilot_max_items=args.pilot_max_items,
    )
    summary = summarize(records, pilot_records)

    write_jsonl(args.output_dir / "corpus_full.jsonl", records)
    write_tsv(args.output_dir / "corpus_full.tsv", records)
    write_jsonl(args.output_dir / "pilot_seed.jsonl", pilot_records)
    write_tsv(args.output_dir / "pilot_seed.tsv", pilot_records)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
