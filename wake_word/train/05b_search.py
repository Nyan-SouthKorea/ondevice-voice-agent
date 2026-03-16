"""
05b_search.py
baseline 구조에서 핵심 하이퍼파라미터만 좁게 탐색하고, 최적 조합을 고른다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAIN_SCRIPT = REPO_ROOT / "wake_word" / "train" / "05_train.py"
MODEL_DIR = REPO_ROOT / "wake_word" / "models" / "hi_popo"
SEARCH_DIR = MODEL_DIR / "searches"
SEARCH_DIR.mkdir(parents=True, exist_ok=True)


def parse_int_list(value: str) -> list[int]:
    """
    기능:
    - 쉼표로 구분된 정수 문자열을 리스트로 변환한다.
    
    입력:
    - `value`: 게이지에 표시할 현재 값.
    
    반환:
    - 파싱된 값 또는 리스트를 반환한다.
    """
    return [int(v.strip()) for v in value.split(",") if v.strip()]


def parse_float_list(value: str) -> list[float]:
    """
    기능:
    - 쉼표로 구분된 실수 문자열을 리스트로 변환한다.
    
    입력:
    - `value`: 게이지에 표시할 현재 값.
    
    반환:
    - 파싱된 값 또는 리스트를 반환한다.
    """
    return [float(v.strip()) for v in value.split(",") if v.strip()]


def parse_args() -> argparse.Namespace:
    """
    기능:
    - 명령행 인자를 정의하고 파싱한다.
    
    입력:
    - 없음.
    
    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cpu", "gpu"], default="gpu")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--search-name", type=str, default=None)
    parser.add_argument("--lr-grid", type=parse_float_list, default=[1e-4, 3e-4, 5e-4])
    parser.add_argument("--negative-weight-grid", type=parse_float_list, default=[3.0, 5.0, 8.0, 12.0])
    parser.add_argument("--layer-dim-grid", type=parse_int_list, default=[32, 64])
    parser.add_argument("--n-blocks-grid", type=parse_int_list, default=[1, 2])
    parser.add_argument("--limit-train-positive", type=int, default=10631)
    parser.add_argument("--limit-train-negative", type=int, default=40000)
    parser.add_argument("--limit-val-positive", type=int, default=1181)
    parser.add_argument("--limit-val-negative", type=int, default=5000)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def score_run(metadata: dict) -> float:
    """
    기능:
    - run metadata에서 검색용 종합 점수를 계산한다.
    
    입력:
    - `metadata`: 함수에서 사용할 `metadata` 값.
    
    반환:
    - 계산된 점수 하나를 반환한다.
    """
    best = metadata["best_metrics"]
    return float(best["recall"]) - 0.25 * float(best["false_positive_rate"])


def build_command(args: argparse.Namespace, run_name: str, lr: float, negative_weight: float, layer_dim: int, n_blocks: int) -> list[str]:
    """
    기능:
    - 주어진 하이퍼파라미터 조합으로 학습 실행 명령을 만든다.
    
    입력:
    - `args`: 명령행에서 파싱된 실행 인자 객체.
    - `run_name`: 실험 run 이름.
    - `lr`: 학습률 값.
    - `negative_weight`: negative 샘플 loss 가중치.
    - `layer_dim`: 은닉층 차원 크기.
    - `n_blocks`: FCN block 개수.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    return [
        sys.executable,
        str(TRAIN_SCRIPT),
        "--device",
        args.device,
        "--epochs",
        str(args.epochs),
        "--batch-size",
        str(args.batch_size),
        "--seed",
        str(args.seed),
        "--run-name",
        run_name,
        "--lr",
        str(lr),
        "--negative-weight",
        str(negative_weight),
        "--layer-dim",
        str(layer_dim),
        "--n-blocks",
        str(n_blocks),
        "--limit-train-positive",
        str(args.limit_train_positive),
        "--limit-train-negative",
        str(args.limit_train_negative),
        "--limit-val-positive",
        str(args.limit_val_positive),
        "--limit-val-negative",
        str(args.limit_val_negative),
    ]


def main() -> None:
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    args = parse_args()
    if args.search_name is None:
        args.search_name = f"{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_grid_search"

    search_run_dir = SEARCH_DIR / args.search_name
    search_run_dir.mkdir(parents=True, exist_ok=True)

    combos = list(itertools.product(args.lr_grid, args.negative_weight_grid, args.layer_dim_grid, args.n_blocks_grid))
    summary: list[dict] = []

    print(f"Search dir: {search_run_dir}", flush=True)
    print(f"Total trials: {len(combos)}", flush=True)

    for index, (lr, negative_weight, layer_dim, n_blocks) in enumerate(combos, start=1):
        run_name = f"{args.search_name}_trial{index:02d}"
        print(
            f"[trial] {index}/{len(combos)} | run={run_name} | "
            f"lr={lr} | neg_w={negative_weight} | layer_dim={layer_dim} | n_blocks={n_blocks}",
            flush=True,
        )
        cmd = build_command(args, run_name, lr, negative_weight, layer_dim, n_blocks)
        completed = subprocess.run(cmd, cwd=REPO_ROOT)
        if completed.returncode != 0:
            raise RuntimeError(f"trial failed: {run_name}")

        metadata_path = MODEL_DIR / "runs" / run_name / "run_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        trial_result = {
            "run_name": run_name,
            "lr": lr,
            "negative_weight": negative_weight,
            "layer_dim": layer_dim,
            "n_blocks": n_blocks,
            "score": score_run(metadata),
            "best_metrics": metadata["best_metrics"],
            "threshold": metadata["threshold"],
            "artifacts": metadata["artifacts"],
        }
        summary.append(trial_result)

    summary.sort(key=lambda item: item["score"], reverse=True)

    ranking_path = search_run_dir / "ranking.json"
    best_path = search_run_dir / "best_trial.json"
    ranking_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    best_path.write_text(json.dumps(summary[0], indent=2), encoding="utf-8")

    top_k = summary[: args.top_k]
    print("[search] top results", flush=True)
    for item in top_k:
        metrics = item["best_metrics"]
        print(
            f"  {item['run_name']} | score={item['score']:.6f} | "
            f"recall={metrics['recall']:.4f} | fp_rate={metrics['false_positive_rate']:.4f} | "
            f"acc={metrics['accuracy']:.4f} | threshold={item['threshold']:.2f} | "
            f"lr={item['lr']} | neg_w={item['negative_weight']} | "
            f"layer_dim={item['layer_dim']} | n_blocks={item['n_blocks']}",
            flush=True,
        )

    print(f"Saved ranking: {ranking_path}", flush=True)
    print(f"Saved best trial: {best_path}", flush=True)


if __name__ == "__main__":
    main()
