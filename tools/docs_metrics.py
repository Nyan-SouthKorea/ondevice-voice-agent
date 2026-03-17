#!/usr/bin/env python3
"""문서량을 측정하고 전후 비교 리포트를 생성한다."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


ARCHIVE_PREFIX = "docs/archive/"
GENERATED_PREFIX = "stt/eval_results/"
PRIVATE_PREFIX = "secrets/"


@dataclass
class FileMetric:
    path: str
    chars: int
    lines: int


def normalize(path: Path, repo_root: Path) -> str:
    """기능: 저장용 상대 경로를 POSIX 형식으로 만든다.
    입력: path(Path), repo_root(Path)
    반환: str
    """

    return path.relative_to(repo_root).as_posix()


def collect_markdown_files(repo_root: Path) -> list[Path]:
    """기능: 레포 안의 마크다운 파일 목록을 모은다.
    입력: repo_root(Path)
    반환: list[Path]
    """

    files = []
    for path in repo_root.rglob("*.md"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(repo_root)
        if any(part.startswith(".") for part in rel_path.parts):
            continue
        files.append(path)
    return sorted(files)


def classify(rel_path: str) -> str:
    """기능: 문서를 active/archive/generated 범주로 분류한다.
    입력: rel_path(str)
    반환: str
    """

    if rel_path.startswith(ARCHIVE_PREFIX):
        return "archive_docs"
    if rel_path.startswith(GENERATED_PREFIX):
        return "generated_artifacts"
    if rel_path.startswith(PRIVATE_PREFIX):
        return "local_private_docs"
    return "active_docs"


def measure_file(path: Path, repo_root: Path) -> FileMetric:
    """기능: 개별 문서의 문자 수와 줄 수를 센다.
    입력: path(Path), repo_root(Path)
    반환: FileMetric
    """

    text = path.read_text(encoding="utf-8")
    return FileMetric(
        path=normalize(path, repo_root),
        chars=len(text),
        lines=text.count("\n") + (0 if not text else 1),
    )


def summarize(metrics: list[FileMetric]) -> dict:
    """기능: 파일 목록의 총계와 상위 파일 정보를 만든다.
    입력: metrics(list[FileMetric])
    반환: dict
    """

    sorted_metrics = sorted(metrics, key=lambda item: (-item.chars, item.path))
    return {
        "file_count": len(metrics),
        "chars": sum(item.chars for item in metrics),
        "lines": sum(item.lines for item in metrics),
        "top_files_by_chars": [
            {
                "path": item.path,
                "chars": item.chars,
                "lines": item.lines,
            }
            for item in sorted_metrics[:10]
        ],
    }


def build_snapshot(repo_root: Path, label: str, commit: str) -> dict:
    """기능: 전체 문서량 스냅샷을 만든다.
    입력: repo_root(Path), label(str), commit(str)
    반환: dict
    """

    all_files = collect_markdown_files(repo_root)
    bucketed = {
        "active_docs": [],
        "archive_docs": [],
        "generated_artifacts": [],
        "local_private_docs": [],
    }
    per_file = []

    for path in all_files:
        metric = measure_file(path, repo_root)
        bucket = classify(metric.path)
        bucketed[bucket].append(metric)
        per_file.append(
            {
                "path": metric.path,
                "group": bucket,
                "chars": metric.chars,
                "lines": metric.lines,
            }
        )

    all_summary = summarize([metric for group in bucketed.values() for metric in group])
    group_summaries = {name: summarize(metrics) for name, metrics in bucketed.items()}

    return {
        "label": label,
        "commit": commit,
        "repo_root": repo_root.as_posix(),
        "group_rules": {
            "active_docs": "all *.md except docs/archive/**, stt/eval_results/**, and secrets/**",
            "archive_docs": "docs/archive/**/*.md",
            "generated_artifacts": "stt/eval_results/**/*.md",
            "local_private_docs": "secrets/**/*.md",
        },
        "totals": all_summary,
        "groups": group_summaries,
        "files": sorted(per_file, key=lambda item: item["path"]),
    }


def diff_counts(after: int, before: int) -> dict:
    """기능: 두 수치의 차이와 증감률을 계산한다.
    입력: after(int), before(int)
    반환: dict
    """

    delta = after - before
    if before == 0:
        delta_pct = None
    else:
        delta_pct = round((delta / before) * 100, 2)
    return {
        "before": before,
        "after": after,
        "delta": delta,
        "delta_pct": delta_pct,
    }


def build_comparison(before: dict, after: dict) -> dict:
    """기능: 스냅샷 두 개를 비교한 결과를 만든다.
    입력: before(dict), after(dict)
    반환: dict
    """

    comparison = {
        "before_label": before["label"],
        "after_label": after["label"],
        "before_commit": before["commit"],
        "after_commit": after["commit"],
        "totals": {
            "chars": diff_counts(after["totals"]["chars"], before["totals"]["chars"]),
            "lines": diff_counts(after["totals"]["lines"], before["totals"]["lines"]),
            "file_count": diff_counts(
                after["totals"]["file_count"], before["totals"]["file_count"]
            ),
        },
        "groups": {},
    }

    for group_name in (
        "active_docs",
        "archive_docs",
        "generated_artifacts",
        "local_private_docs",
    ):
        comparison["groups"][group_name] = {
            "chars": diff_counts(
                after["groups"][group_name]["chars"],
                before["groups"][group_name]["chars"],
            ),
            "lines": diff_counts(
                after["groups"][group_name]["lines"],
                before["groups"][group_name]["lines"],
            ),
            "file_count": diff_counts(
                after["groups"][group_name]["file_count"],
                before["groups"][group_name]["file_count"],
            ),
        }

    before_files = {item["path"]: item for item in before["files"]}
    after_files = {item["path"]: item for item in after["files"]}
    changed_files = []

    for path in sorted(set(before_files) | set(after_files)):
        before_item = before_files.get(path)
        after_item = after_files.get(path)
        before_chars = 0 if before_item is None else before_item["chars"]
        after_chars = 0 if after_item is None else after_item["chars"]
        before_lines = 0 if before_item is None else before_item["lines"]
        after_lines = 0 if after_item is None else after_item["lines"]
        if before_chars == after_chars and before_lines == after_lines:
            continue
        changed_files.append(
            {
                "path": path,
                "before_group": None if before_item is None else before_item["group"],
                "after_group": None if after_item is None else after_item["group"],
                "chars": diff_counts(after_chars, before_chars),
                "lines": diff_counts(after_lines, before_lines),
            }
        )

    comparison["changed_files"] = sorted(
        changed_files,
        key=lambda item: (item["chars"]["delta"], item["lines"]["delta"], item["path"]),
    )
    return comparison


def format_pct(value: float | None) -> str:
    """기능: 퍼센트 값을 보기 좋게 포맷한다.
    입력: value(float | None)
    반환: str
    """

    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def write_json(path: Path, payload: dict) -> None:
    """기능: JSON 파일을 기록한다.
    입력: path(Path), payload(dict)
    반환: 없음
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_snapshot_markdown(snapshot: dict) -> str:
    """기능: 스냅샷 결과를 마크다운 표로 렌더링한다.
    입력: snapshot(dict)
    반환: str
    """

    lines = [
        f"# Documentation Metrics Snapshot: {snapshot['label']}",
        "",
        f"- commit: `{snapshot['commit']}`",
        f"- repo: `{snapshot['repo_root']}`",
        "",
            "## Totals",
        "",
        "| Scope | Files | Lines | Characters |",
        "|---|---:|---:|---:|",
        (
            f"| all_markdown | {snapshot['totals']['file_count']} | "
            f"{snapshot['totals']['lines']} | {snapshot['totals']['chars']} |"
        ),
    ]

    for group_name in (
        "active_docs",
        "archive_docs",
        "generated_artifacts",
        "local_private_docs",
    ):
        group = snapshot["groups"][group_name]
        lines.append(
            f"| {group_name} | {group['file_count']} | {group['lines']} | {group['chars']} |"
        )

    lines.extend(
        [
            "",
            "## Top Files By Characters",
            "",
            "| Path | Group | Lines | Characters |",
            "|---|---|---:|---:|",
        ]
    )

    for item in sorted(snapshot["files"], key=lambda row: (-row["chars"], row["path"]))[:15]:
        lines.append(
            f"| `{item['path']}` | {item['group']} | {item['lines']} | {item['chars']} |"
        )

    return "\n".join(lines) + "\n"


def render_comparison_markdown(comparison: dict) -> str:
    """기능: 전후 비교 결과를 마크다운으로 렌더링한다.
    입력: comparison(dict)
    반환: str
    """

    lines = [
        f"# Documentation Metrics Comparison: {comparison['before_label']} -> {comparison['after_label']}",
        "",
        f"- before commit: `{comparison['before_commit']}`",
        f"- after commit: `{comparison['after_commit']}`",
        "",
        "## Total Change",
        "",
        "| Scope | Metric | Before | After | Delta | Delta % |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for metric_name in ("chars", "lines", "file_count"):
        metric = comparison["totals"][metric_name]
        lines.append(
            f"| all_markdown | {metric_name} | {metric['before']} | {metric['after']} | "
            f"{metric['delta']} | {format_pct(metric['delta_pct'])} |"
        )

    for group_name in (
        "active_docs",
        "archive_docs",
        "generated_artifacts",
        "local_private_docs",
    ):
        for metric_name in ("chars", "lines", "file_count"):
            metric = comparison["groups"][group_name][metric_name]
            lines.append(
                f"| {group_name} | {metric_name} | {metric['before']} | {metric['after']} | "
                f"{metric['delta']} | {format_pct(metric['delta_pct'])} |"
            )

    lines.extend(
        [
            "",
            "## Largest File Changes By Characters",
            "",
            "| Path | Before Group | After Group | Before Chars | After Chars | Delta |",
            "|---|---|---|---:|---:|---:|",
        ]
    )

    sorted_changes = sorted(
        comparison["changed_files"],
        key=lambda item: (abs(item["chars"]["delta"]), item["path"]),
        reverse=True,
    )

    for item in sorted_changes[:20]:
        lines.append(
            f"| `{item['path']}` | {item['before_group'] or '-'} | {item['after_group'] or '-'} | "
            f"{item['chars']['before']} | {item['chars']['after']} | {item['chars']['delta']} |"
        )

    return "\n".join(lines) + "\n"


def write_markdown(path: Path, content: str) -> None:
    """기능: 마크다운 파일을 기록한다.
    입력: path(Path), content(str)
    반환: 없음
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """기능: CLI 인자를 파싱한다.
    입력: 없음
    반환: argparse.Namespace
    """

    parser = argparse.ArgumentParser(description="Measure markdown documentation volume.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--repo-root", required=True)
    snapshot_parser.add_argument("--label", required=True)
    snapshot_parser.add_argument("--commit", required=True)
    snapshot_parser.add_argument("--output-json", required=True)
    snapshot_parser.add_argument("--output-md", required=True)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--before-json", required=True)
    compare_parser.add_argument("--after-json", required=True)
    compare_parser.add_argument("--output-json", required=True)
    compare_parser.add_argument("--output-md", required=True)

    return parser.parse_args()


def main() -> None:
    """기능: CLI 명령을 실행한다.
    입력: 없음
    반환: 없음
    """

    args = parse_args()

    if args.command == "snapshot":
        repo_root = Path(args.repo_root).resolve()
        snapshot = build_snapshot(repo_root, args.label, args.commit)
        write_json(Path(args.output_json), snapshot)
        write_markdown(Path(args.output_md), render_snapshot_markdown(snapshot))
        return

    before = json.loads(Path(args.before_json).read_text(encoding="utf-8"))
    after = json.loads(Path(args.after_json).read_text(encoding="utf-8"))
    comparison = build_comparison(before, after)
    write_json(Path(args.output_json), comparison)
    write_markdown(Path(args.output_md), render_comparison_markdown(comparison))


if __name__ == "__main__":
    main()
