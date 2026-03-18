"""
A100 기준 6-backend TTS benchmark orchestrator.
"""

import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber


class ProcessMonitor:
    def __init__(self, pid, interval_sec=0.2):
        self.pid = int(pid)
        self.interval_sec = float(interval_sec)
        self.peak_ram_mb = 0.0
        self.peak_vram_mb = 0.0
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=2.0)

    def _run(self):
        proc_path = Path("/proc") / str(self.pid)
        while not self._stop_event.is_set():
            if not proc_path.exists():
                break
            self.peak_ram_mb = max(self.peak_ram_mb, self._read_rss_mb())
            self.peak_vram_mb = max(self.peak_vram_mb, self._read_vram_mb())
            time.sleep(self.interval_sec)

    def _read_rss_mb(self):
        status_path = Path("/proc") / str(self.pid) / "status"
        try:
            for line in status_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
        except Exception:
            return 0.0
        return 0.0

    def _read_vram_mb(self):
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,used_memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return 0.0

        peak = 0.0
        for line in result.stdout.splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) != 2:
                continue
            try:
                line_pid = int(fields[0])
                used_mb = float(fields[1])
            except ValueError:
                continue
            if line_pid == self.pid:
                peak = max(peak, used_mb)
        return peak


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        type=Path,
        default=REPO_ROOT / "tts" / "evaluation" / "benchmark_registry_v1.json",
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        default=REPO_ROOT
        / "tts"
        / "evaluation"
        / "prompts"
        / "tts_benchmark_prompts_v1.tsv",
    )
    parser.add_argument(
        "--listening-prompts",
        type=Path,
        default=REPO_ROOT
        / "tts"
        / "evaluation"
        / "prompts"
        / "tts_listening_subset_v1.tsv",
    )
    parser.add_argument(
        "--run-name",
        default=time.strftime("%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--entries",
        default=None,
        help="쉼표로 구분된 entry id 목록. 비우면 registry 전체를 사용한다.",
    )
    parser.add_argument(
        "--prompt-limit-per-language",
        type=int,
        default=0,
        help="0이면 전체, 양수면 언어별 앞에서부터 일부 prompt만 사용한다.",
    )
    parser.add_argument(
        "--skip-stt",
        action="store_true",
        help="역전사 scorer를 건너뛴다.",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="reference backend 중 network 성격인 Edge/OpenAI API를 제외한다.",
    )
    return parser.parse_args()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_prompts(path):
    with path.open("r", encoding="utf-8") as prompt_file:
        return list(csv.DictReader(prompt_file, delimiter="\t"))


def load_listening_ids(path):
    with path.open("r", encoding="utf-8") as prompt_file:
        rows = list(csv.DictReader(prompt_file, delimiter="\t"))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["language"], []).append(row["prompt_id"])
    return grouped


def resolve_workspace_path(value):
    if value is None:
        return None
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    return WORKSPACE_ROOT / candidate


def select_entries(registry, args):
    entries = list(registry["entries"])
    if args.entries:
        requested = {item.strip() for item in args.entries.split(",") if item.strip()}
        entries = [entry for entry in entries if entry["id"] in requested]
    if args.skip_network:
        entries = [
            entry
            for entry in entries
            if entry["backend"] not in {"edge_tts", "openai_api", "chatgpt_api", "api"}
        ]
    if not entries:
        raise ValueError("실행할 benchmark entry가 없습니다.")
    return entries


def select_prompts(all_prompts, language, limit_per_language):
    selected = [row for row in all_prompts if row["language"] == language]
    if limit_per_language > 0:
        selected = selected[:limit_per_language]
    return selected


def run_worker(entry, prompts, run_root):
    env_python = resolve_workspace_path(entry["env_python"])
    if not env_python.is_file():
        raise FileNotFoundError(f"env python을 찾지 못했습니다: {env_python}")

    output_dir = run_root / "audio" / entry["id"]
    job_prompts = []
    for prompt in prompts:
        job_prompts.append(
            {
                "prompt_id": prompt["prompt_id"],
                "language": prompt["language"],
                "text": prompt["text"],
                "output_path": str(output_dir / f"{prompt['prompt_id']}.wav"),
            }
        )

    backend_kwargs = dict(entry["synth_kwargs"])
    for key, value in list(backend_kwargs.items()):
        if key.endswith("_path") or key.endswith("_root"):
            backend_kwargs[key] = str(resolve_workspace_path(value))

    worker_script = REPO_ROOT / "tts" / "tools" / "tts_benchmark_worker.py"
    job_dir = run_root / "jobs"
    job_dir.mkdir(parents=True, exist_ok=True)
    output_json = job_dir / f"{entry['id']}_summary.json"
    stdout_path = run_root / "logs" / f"{entry['id']}.stdout.log"
    stderr_path = run_root / "logs" / f"{entry['id']}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    job_path = job_dir / f"{entry['id']}.job.json"
    job_payload = {
        "entry_id": entry["id"],
        "display_name": entry["display_name"],
        "backend": entry["backend"],
        "family": entry["family"],
        "prompt_language": entry["prompt_language"],
        "backend_kwargs": backend_kwargs,
        "prompts": job_prompts,
    }
    job_path.write_text(
        json.dumps(job_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_file:
        process = subprocess.Popen(
            [str(env_python), str(worker_script), "--job", str(job_path), "--output-json", str(output_json)],
            stdout=stdout_file,
            stderr=stderr_file,
        )
        monitor = ProcessMonitor(process.pid)
        monitor.start()
        return_code = process.wait()
        monitor.stop()

    if return_code != 0:
        raise RuntimeError(
            f"benchmark worker가 실패했습니다: {entry['id']} stderr={stderr_path}"
        )
    summary = load_json(output_json)
    summary["peak_ram_mb"] = round(monitor.peak_ram_mb, 3)
    summary["peak_vram_mb"] = round(monitor.peak_vram_mb, 3)
    summary["stdout_log"] = str(stdout_path)
    summary["stderr_log"] = str(stderr_path)
    return summary


def require_binary(name):
    binary = shutil.which(name)
    if not binary:
        raise RuntimeError(f"{name} 실행 파일을 찾지 못했습니다.")
    return binary


def probe_audio(audio_path):
    ffprobe_path = require_binary("ffprobe")
    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,sample_rate,channels",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    stream = {}
    if payload.get("streams"):
        stream = payload["streams"][0]
    return {
        "codec_name": stream.get("codec_name", ""),
        "sample_rate": int(stream.get("sample_rate", 0) or 0),
        "channels": int(stream.get("channels", 0) or 0),
        "audio_duration_sec": float(payload.get("format", {}).get("duration", 0.0) or 0.0),
    }


def resample_to_16k(audio_path, output_path):
    ffmpeg_path = require_binary("ffmpeg")
    subprocess.run(
        [
            ffmpeg_path,
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(output_path),
        ],
        check=True,
    )


def normalize_text(text, language):
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = normalized.replace("’", "'").replace("‘", "'")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.lower()
    if language == "ko":
        normalized = re.sub(r"[^0-9a-z가-힣\s]", " ", normalized)
    else:
        normalized = re.sub(r"[^0-9a-z\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def levenshtein_distance(left, right):
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def compute_cer(reference_text, hypothesis_text):
    ref = reference_text.replace(" ", "")
    hyp = hypothesis_text.replace(" ", "")
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein_distance(ref, hyp) / len(ref)


def mean_or_nan(values):
    if not values:
        return math.nan
    return sum(values) / len(values)


def write_tsv(rows, path, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def build_stt_scorer():
    return STTTranscriber(
        model="whisper",
        model_name="large-v3",
        language="ko",
        device="cuda",
    )


def score_prompt(scorer, audio_path, prompt, temp_dir):
    normalized_audio = temp_dir / f"{prompt['prompt_id']}_16k.wav"
    resample_to_16k(audio_path, normalized_audio)
    scorer.backend.language = prompt["language"]
    transcribed = scorer.transcribe(normalized_audio)
    normalized_reference = normalize_text(prompt["text"], prompt["language"])
    normalized_transcription = normalize_text(transcribed, prompt["language"])
    return {
        "stt_back_transcription": transcribed,
        "stt_duration_sec": float(scorer.last_duration_sec),
        "normalized_reference": normalized_reference,
        "normalized_transcription": normalized_transcription,
        "stt_back_transcription_cer": compute_cer(
            normalized_reference,
            normalized_transcription,
        ),
        "stt_back_transcription_exact_match": int(
            normalized_reference == normalized_transcription
        ),
    }


def materialize_listening_samples(per_prompt_rows, listening_ids, run_root):
    listening_rows = []
    prompt_order = {}
    for language, prompt_id_list in listening_ids.items():
        prompt_order.update(
            {(language, prompt_id): index + 1 for index, prompt_id in enumerate(prompt_id_list)}
        )

    for row in per_prompt_rows:
        key = (row["language"], row["prompt_id"])
        if key not in prompt_order:
            continue
        if not row["success"]:
            continue
        order = prompt_order[key]
        source_path = Path(row["output_path"])
        destination = (
            run_root
            / "listening"
            / row["language"]
            / row["entry_id"]
            / f"{order:02d}_{row['prompt_id']}.wav"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        listening_rows.append(
            {
                "entry_id": row["entry_id"],
                "display_name": row["display_name"],
                "language": row["language"],
                "prompt_id": row["prompt_id"],
                "order": order,
                "category": row["category"],
                "text": row["text"],
                "audio_path": str(destination),
                "overall_impression_10": "",
                "naturalness_10": "",
                "voice_appeal_10": "",
                "pronunciation_10": "",
                "notes": "",
            }
        )
    return listening_rows


def main():
    args = parse_args()
    registry = load_json(args.registry)
    all_prompts = load_prompts(args.prompts)
    listening_ids = load_listening_ids(args.listening_prompts)
    entries = select_entries(registry, args)

    run_root = (
        args.output_root
        if args.output_root is not None
        else WORKSPACE_ROOT / "results" / "tts" / f"benchmark_{args.run_name}"
    )
    run_root.mkdir(parents=True, exist_ok=True)

    scorer = None
    if not args.skip_stt:
        scorer = build_stt_scorer()

    per_prompt_rows = []
    summary_rows = []

    try:
        for entry in entries:
            prompts = select_prompts(
                all_prompts,
                language=entry["prompt_language"],
                limit_per_language=args.prompt_limit_per_language,
            )
            worker_summary = run_worker(entry, prompts, run_root)

            for result_row, prompt in zip(worker_summary["results"], prompts):
                row = {
                    "entry_id": entry["id"],
                    "display_name": entry["display_name"],
                    "family": entry["family"],
                    "backend": entry["backend"],
                    "language": prompt["language"],
                    "prompt_id": prompt["prompt_id"],
                    "category": prompt["category"],
                    "track": prompt["track"],
                    "paired_group": prompt["paired_group"],
                    "text": prompt["text"],
                    "output_path": result_row["output_path"],
                    "success": int(bool(result_row["success"])),
                    "error": result_row["error"],
                    "model_load_sec": float(worker_summary["model_load_sec"]),
                    "elapsed_sec": result_row["elapsed_sec"]
                    if result_row["elapsed_sec"] is not None
                    else math.nan,
                    "peak_ram_mb": float(worker_summary["peak_ram_mb"]),
                    "peak_vram_mb": float(worker_summary["peak_vram_mb"]),
                    "codec_name": "",
                    "sample_rate": 0,
                    "channels": 0,
                    "audio_duration_sec": math.nan,
                    "real_time_factor": math.nan,
                    "stt_back_transcription": "",
                    "stt_duration_sec": math.nan,
                    "normalized_reference": "",
                    "normalized_transcription": "",
                    "stt_back_transcription_cer": math.nan,
                    "stt_back_transcription_exact_match": 0,
                }

                if result_row["success"]:
                    audio_meta = probe_audio(result_row["output_path"])
                    row.update(audio_meta)
                    if audio_meta["audio_duration_sec"] > 0.0:
                        row["real_time_factor"] = (
                            float(result_row["elapsed_sec"]) / audio_meta["audio_duration_sec"]
                        )
                    if scorer is not None:
                        with tempfile.TemporaryDirectory(prefix="tts_benchmark_stt_") as tmp_dir:
                            score = score_prompt(
                                scorer,
                                Path(result_row["output_path"]),
                                prompt,
                                Path(tmp_dir),
                            )
                        row.update(score)

                per_prompt_rows.append(row)

            successful_rows = [
                row
                for row in per_prompt_rows
                if row["entry_id"] == entry["id"] and row["success"] == 1
            ]
            summary_rows.append(
                {
                    "entry_id": entry["id"],
                    "display_name": entry["display_name"],
                    "family": entry["family"],
                    "backend": entry["backend"],
                    "language": entry["prompt_language"],
                    "prompt_count": len(prompts),
                    "success_count": len(successful_rows),
                    "success_rate": len(successful_rows) / len(prompts) if prompts else math.nan,
                    "model_load_sec": float(worker_summary["model_load_sec"]),
                    "mean_elapsed_sec": mean_or_nan(
                        [row["elapsed_sec"] for row in successful_rows if not math.isnan(row["elapsed_sec"])]
                    ),
                    "mean_audio_duration_sec": mean_or_nan(
                        [row["audio_duration_sec"] for row in successful_rows if not math.isnan(row["audio_duration_sec"])]
                    ),
                    "mean_real_time_factor": mean_or_nan(
                        [row["real_time_factor"] for row in successful_rows if not math.isnan(row["real_time_factor"])]
                    ),
                    "peak_ram_mb": float(worker_summary["peak_ram_mb"]),
                    "peak_vram_mb": float(worker_summary["peak_vram_mb"]),
                    "mean_stt_duration_sec": mean_or_nan(
                        [row["stt_duration_sec"] for row in successful_rows if not math.isnan(row["stt_duration_sec"])]
                    ),
                    "mean_stt_back_transcription_cer": mean_or_nan(
                        [
                            row["stt_back_transcription_cer"]
                            for row in successful_rows
                            if not math.isnan(row["stt_back_transcription_cer"])
                        ]
                    ),
                    "stt_back_transcription_exact_match_rate": mean_or_nan(
                        [row["stt_back_transcription_exact_match"] for row in successful_rows]
                    ),
                }
            )
    finally:
        if scorer is not None:
            scorer.close()

    write_tsv(
        per_prompt_rows,
        run_root / "per_prompt.tsv",
        [
            "entry_id",
            "display_name",
            "family",
            "backend",
            "language",
            "prompt_id",
            "category",
            "track",
            "paired_group",
            "text",
            "output_path",
            "success",
            "error",
            "model_load_sec",
            "elapsed_sec",
            "peak_ram_mb",
            "peak_vram_mb",
            "codec_name",
            "sample_rate",
            "channels",
            "audio_duration_sec",
            "real_time_factor",
            "stt_back_transcription",
            "stt_duration_sec",
            "normalized_reference",
            "normalized_transcription",
            "stt_back_transcription_cer",
            "stt_back_transcription_exact_match",
        ],
    )
    write_tsv(
        summary_rows,
        run_root / "per_entry_summary.tsv",
        [
            "entry_id",
            "display_name",
            "family",
            "backend",
            "language",
            "prompt_count",
            "success_count",
            "success_rate",
            "model_load_sec",
            "mean_elapsed_sec",
            "mean_audio_duration_sec",
            "mean_real_time_factor",
            "peak_ram_mb",
            "peak_vram_mb",
            "mean_stt_duration_sec",
            "mean_stt_back_transcription_cer",
            "stt_back_transcription_exact_match_rate",
        ],
    )

    listening_rows = materialize_listening_samples(per_prompt_rows, listening_ids, run_root)
    write_tsv(
        listening_rows,
        run_root / "listening_scores_template.tsv",
        [
            "entry_id",
            "display_name",
            "language",
            "prompt_id",
            "order",
            "category",
            "text",
            "audio_path",
            "overall_impression_10",
            "naturalness_10",
            "voice_appeal_10",
            "pronunciation_10",
            "notes",
        ],
    )

    manifest = {
        "run_name": args.run_name,
        "registry_path": str(args.registry),
        "prompts_path": str(args.prompts),
        "listening_prompts_path": str(args.listening_prompts),
        "entries": [entry["id"] for entry in entries],
        "prompt_limit_per_language": args.prompt_limit_per_language,
        "skip_stt": bool(args.skip_stt),
        "skip_network": bool(args.skip_network),
        "output_root": str(run_root),
    }
    (run_root / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
