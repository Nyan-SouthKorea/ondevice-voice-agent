"""
기존 STT benchmark summary 산출물을 읽어 통합 요약표를 만든다.
"""

from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path


DEFAULT_EXPECTS = [
    "whisper:tiny:cuda",
    "whisper:base:cuda",
    "whisper:small:cuda",
    "whisper:tiny:cpu",
    "whisper:base:cpu",
    "whisper:small:cpu",
    "api:gpt-4o-mini-transcribe:auto",
]


def parse_args():
    """
    통합 요약표 생성에 필요한 실행 인자를 읽는다.

    입력 인자 설명
    - `--results-dir`: summary.json들이 모여 있는 평가 결과 루트 디렉토리.
    - `--output`: 생성할 overview markdown 파일 경로.
    - `--expect`: 기대하는 평가 조합 목록. 없으면 기본 조합을 사용한다.

    return 관련 설명
    - 파싱된 argparse 네임스페이스를 반환한다.
    """

    parser = ArgumentParser(description="STT benchmark summary를 통합해 overview 표를 생성한다.")
    parser.add_argument(
        "--results-dir",
        default=Path(__file__).resolve().parent / "eval_results" / "korean_eval_50",
        type=Path,
        help="summary.json이 들어 있는 평가 결과 루트 디렉토리",
    )
    parser.add_argument(
        "--output",
        default=None,
        type=Path,
        help="생성할 overview markdown 경로",
    )
    parser.add_argument(
        "--expect",
        action="append",
        default=[],
        help="기대하는 평가 조합. 형식은 model:model_name:device",
    )
    return parser.parse_args()


def load_summary_rows(results_dir):
    """
    결과 디렉토리 아래의 summary.json 파일들을 읽어 행 목록으로 펼친다.

    입력 인자 설명
    - `results_dir`: 여러 run 디렉토리를 포함하는 상위 평가 결과 디렉토리.

    return 관련 설명
    - summary.json에서 읽어낸 각 summary 행에 source 정보가 추가된 리스트를 반환한다.
    """

    rows = []
    for summary_path in sorted(results_dir.glob("*/summary.json")):
        payload = json.loads(summary_path.read_text())
        for row in payload.get("summaries", []):
            copied = dict(row)
            copied["source_dir"] = summary_path.parent.name
            copied["source_path"] = str(summary_path.relative_to(results_dir.parent.parent))
            rows.append(copied)
    return rows


def build_expected_rows(summary_rows, expect_specs):
    """
    기대 조합 목록과 실제 summary 행을 합쳐 최종 overview 행을 만든다.

    입력 인자 설명
    - `summary_rows`: summary.json에서 읽은 실제 결과 행 목록.
    - `expect_specs`: model:model_name:device 형식의 기대 평가 조합 목록.

    return 관련 설명
    - 각 기대 조합별로 status와 수치가 정리된 리스트를 반환한다.
    """

    indexed = {}
    for row in summary_rows:
        key = (row["model"], row["model_name"], row["device"])
        indexed[key] = row

    rows = []
    for spec in expect_specs:
        model, model_name, device = spec.split(":", 2)
        found = indexed.get((model, model_name, device))
        label = f"{model_name} ({device})" if model == "whisper" else f"{model_name} (api)"
        if found:
            rows.append(
                {
                    "status": "ok",
                    "label": label,
                    "model": model,
                    "model_name": model_name,
                    "device": device,
                    "sample_count": found["sample_count"],
                    "load_time_sec": found["load_time_sec"],
                    "mean_stt_sec": found["mean_stt_sec"],
                    "p95_stt_sec": found["p95_stt_sec"],
                    "mean_rtf": found["mean_rtf"],
                    "normalized_exact_match_rate": found["normalized_exact_match_rate"],
                    "mean_normalized_cer": found["mean_normalized_cer"],
                    "source_dir": found["source_dir"],
                    "source_path": found["source_path"],
                }
            )
            continue

        rows.append(
            {
                "status": "missing_summary",
                "label": label,
                "model": model,
                "model_name": model_name,
                "device": device,
                "sample_count": None,
                "load_time_sec": None,
                "mean_stt_sec": None,
                "p95_stt_sec": None,
                "mean_rtf": None,
                "normalized_exact_match_rate": None,
                "mean_normalized_cer": None,
                "source_dir": "-",
                "source_path": "-",
            }
        )
    return rows


def pick_rule_winners(rows):
    """
    규칙 기반으로 정확도/오류율/속도 1위 행을 뽑는다.

    입력 인자 설명
    - `rows`: status와 주요 지표가 정리된 overview 행 목록.

    return 관련 설명
    - 항목별 1위를 담은 딕셔너리를 반환한다.
    """

    usable = [row for row in rows if row["status"] == "ok"]
    if not usable:
        return {}

    return {
        "accuracy_best": sorted(
            usable,
            key=lambda row: (
                -row["normalized_exact_match_rate"],
                row["mean_normalized_cer"],
                row["mean_stt_sec"],
                row["label"],
            ),
        )[0],
        "cer_best": sorted(
            usable,
            key=lambda row: (
                row["mean_normalized_cer"],
                -row["normalized_exact_match_rate"],
                row["mean_stt_sec"],
                row["label"],
            ),
        )[0],
        "latency_best": sorted(
            usable,
            key=lambda row: (
                row["mean_stt_sec"],
                row["p95_stt_sec"],
                row["mean_rtf"],
                row["label"],
            ),
        )[0],
    }


def format_number(value):
    """
    숫자와 결측값을 markdown 표에 넣기 좋은 문자열로 바꾼다.

    입력 인자 설명
    - `value`: 표에 표시할 숫자 또는 None.

    return 관련 설명
    - None이면 `-`, 숫자면 소수점 네 자리 문자열을 반환한다.
    """

    if value is None:
        return "-"
    return f"{value:.4f}"


def format_status(value):
    """
    내부 status 값을 한국어 표기 문자열로 바꾼다.

    입력 인자 설명
    - `value`: 내부에서 사용하는 status 문자열.

    return 관련 설명
    - 보고 문서에 넣을 한국어 상태 문자열을 반환한다.
    """

    return {
        "ok": "완료",
        "missing_summary": "summary 없음",
    }.get(value, value)


def format_metric_label(value):
    """
    규칙 기반 1위 항목 이름을 한국어 표시명으로 바꾼다.

    입력 인자 설명
    - `value`: accuracy_best 같은 내부 metric 이름.

    return 관련 설명
    - 보고 문서용 한국어 metric 이름을 반환한다.
    """

    return {
        "accuracy_best": "정확도 우선",
        "cer_best": "오류율 우선",
        "latency_best": "지연 우선",
    }.get(value, value)


def render_markdown(results_dir, rows, winners):
    """
    overview markdown 전체 본문을 만든다.

    입력 인자 설명
    - `results_dir`: 요약표 대상이 되는 평가 결과 루트 디렉토리.
    - `rows`: 통합 overview 행 목록.
    - `winners`: 규칙 기반 1위 결과 딕셔너리.

    return 관련 설명
    - markdown 문자열 전체를 반환한다.
    """

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# STT 평가 개요",
        "",
        f"- 결과 디렉토리: `{results_dir}`",
        f"- 생성 시각: `{generated_at}`",
        "- 원본 산출물: 각 run 디렉토리의 `summary.json`",
        "- 자동 선택 규칙:",
        "  - 정확도 우선: `Normalized Exact Match` 내림차순, `Normalized CER` 오름차순, `Mean STT (s)` 오름차순",
        "  - 오류율 우선: `Normalized CER` 오름차순, `Normalized Exact Match` 내림차순, `Mean STT (s)` 오름차순",
        "  - 지연 우선: `Mean STT (s)` 오름차순, `P95 STT (s)` 오름차순, `Mean RTF` 오름차순",
        "",
        "## 지표 설명",
        "",
        "- `상태 (Status)`: 해당 모델 조합에 대해 summary 산출물이 존재하는지 나타낸다.",
        "- `모델 (Label)`: 평가한 모델 이름과 실행 장치 조합이다.",
        "- `샘플 수 (Samples)`: 실제 평가에 사용된 문장 수다.",
        "- `Load (s)`: 모델을 메모리에 올리는 데 걸린 시간이다. warm-up 이전 1회 비용이다.",
        "- `Mean STT (s)`: warm-up을 제외한 문장별 STT 처리 시간 평균이다.",
        "- `P95 STT (s)`: warm-up을 제외한 문장별 STT 처리 시간의 95퍼센타일이다. 느린 구간 체감에 가깝다.",
        "- `Mean RTF`: 평균 실시간비다. `처리 시간 / 오디오 길이`로 계산하며, 1.0 이하면 오디오 길이보다 빠르게 처리한 것이다.",
        "- `Normalized Exact Match`: 정규화 후 기준 문장과 예측 문장이 완전히 같은 비율이다. 공백, 일부 기호 차이를 줄인 뒤 비교한다.",
        "- `Normalized CER`: 정규화 후 문자 오류율이다. 낮을수록 좋다.",
        "- `원본 run (Source)`: 수치를 읽어온 run 디렉토리 이름이다.",
        "",
        "## 질문 기반 추가 설명",
        "",
        "### Normalized Exact Match는 어떻게 정규화하나",
        "",
        "- 현재 평가는 `stt_benchmark.py`의 `normalize_text()` 기준을 그대로 사용한다.",
        "- 정규화 순서는 다음과 같다.",
        "  - 문자열 앞뒤 공백 제거",
        "  - 영문 소문자 변환",
        "  - 일반 문장부호와 `“ ” ‘ ’ … ·` 제거",
        "  - 남아 있는 모든 공백 제거",
        "- 즉, 띄어쓰기나 문장부호 차이는 무시하고 핵심 글자열이 완전히 같으면 `Normalized Exact Match = 1`로 본다.",
        "",
        "예시:",
        "- 기준: `안녕하세요, 오늘 음성 인식 테스트를 시작하겠습니다.`",
        "- 예측: `안녕하세요 오늘 음성 인식 테스트를 시작하겠습니다`",
        "- 정규화 후 둘 다 `안녕하세요오늘음성인식테스트를시작하겠습니다`가 되므로 일치로 처리된다.",
        "",
        "반대로 다음은 불일치다.",
        "- 기준: `오늘 서울 날씨는 맑고 바람이 조금 붑니다.`",
        "- 예측: `오늘 서울 날씨는 맑고 바람이 많이 붑니다`",
        "- 정규화 후에도 `조금`과 `많이` 차이가 남기 때문에 불일치로 처리된다.",
        "",
        "### CER은 무엇인가",
        "",
        "- `CER`은 `Character Error Rate`로, 문자 단위 오류율이다.",
        "- 계산식은 `편집거리 / 기준 문자열 길이`다.",
        "- 편집거리는 삽입, 삭제, 치환 횟수를 합친 Levenshtein distance를 사용한다.",
        "- 값이 낮을수록 좋고, `0.0`이면 완전 일치다.",
        "",
        "예시:",
        "- 기준: `하이포포`",
        "- 예측: `하이보보`",
        "- `포 -> 보` 치환이 두 번 필요하므로 편집거리는 2다.",
        "- 기준 문자열 길이가 4면 `CER = 2 / 4 = 0.5`다.",
        "",
        "- 이 문서의 `Normalized CER`은 위에서 설명한 정규화 이후에 계산한 CER이다.",
        "- 그래서 문장부호나 띄어쓰기 차이만 있는 경우에는 CER이 낮아지거나 0이 될 수 있다.",
        "",
    ]

    if winners:
        lines.extend(
            [
                "## 규칙 기반 자동 선택",
                "",
                "| 항목 | 모델 | 원본 run | Normalized Exact Match | Normalized CER | Mean STT (s) | Mean RTF |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for metric_name in ["accuracy_best", "cer_best", "latency_best"]:
            row = winners[metric_name]
            lines.append(
                f"| {format_metric_label(metric_name)} | {row['label']} | `{row['source_dir']}` | "
                f"{format_number(row['normalized_exact_match_rate'])} | "
                f"{format_number(row['mean_normalized_cer'])} | "
                f"{format_number(row['mean_stt_sec'])} | "
                f"{format_number(row['mean_rtf'])} |"
            )
        lines.append("")

    lines.extend(
        [
            "## 전체 평가 표",
            "",
            "| 상태 | 모델 | 샘플 수 | Load (s) | Mean STT (s) | P95 STT (s) | Mean RTF | Normalized Exact Match | Normalized CER | 원본 run |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for row in rows:
        lines.append(
            f"| {format_status(row['status'])} | {row['label']} | {row['sample_count'] or '-'} | "
            f"{format_number(row['load_time_sec'])} | "
            f"{format_number(row['mean_stt_sec'])} | "
            f"{format_number(row['p95_stt_sec'])} | "
            f"{format_number(row['mean_rtf'])} | "
            f"{format_number(row['normalized_exact_match_rate'])} | "
            f"{format_number(row['mean_normalized_cer'])} | "
            f"`{row['source_dir']}` |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    """
    실행 인자를 읽고 STT 평가 overview markdown 파일을 생성한다.

    입력 인자 설명
    - 별도 함수 호출 없이 CLI 인자를 직접 사용한다.

    return 관련 설명
    - 파일을 저장한 뒤 경로를 표준 출력으로 알리고 종료한다.
    """

    args = parse_args()
    expect_specs = args.expect or list(DEFAULT_EXPECTS)
    output_path = args.output or (args.results_dir / "overview.md")

    summary_rows = load_summary_rows(args.results_dir)
    rows = build_expected_rows(summary_rows, expect_specs)
    winners = pick_rule_winners(rows)
    markdown = render_markdown(args.results_dir, rows, winners)

    output_path.write_text(markdown)
    print(output_path)


if __name__ == "__main__":
    main()
