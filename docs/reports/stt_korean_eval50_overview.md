# STT Evaluation Overview

- results_dir: `/home/everybot/workspace/ondevice-voice-agent/project/repo/stt/eval_results/korean_eval_50`
- generated_at: `2026-03-17 08:55:49`
- summary source: 각 run 디렉토리의 `summary.json`
- selection rule:
  - accuracy_best: normalized_exact_match_rate 내림차순, mean_normalized_cer 오름차순, mean_stt_sec 오름차순
  - cer_best: mean_normalized_cer 오름차순, normalized_exact_match_rate 내림차순, mean_stt_sec 오름차순
  - latency_best: mean_stt_sec 오름차순, p95_stt_sec 오름차순, mean_rtf 오름차순

## Rule-Based Winners

| Metric | Label | Source | Normalized Exact Match | Normalized CER | Mean STT (s) | Mean RTF |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| accuracy_best | gpt-4o-mini-transcribe (api) | `20260316_180115` | 0.7000 | 0.0669 | 0.8874 | 0.1824 |
| cer_best | gpt-4o-mini-transcribe (api) | `20260316_180115` | 0.7000 | 0.0669 | 0.8874 | 0.1824 |
| latency_best | tiny (cuda) | `20260316_180025` | 0.0400 | 0.4753 | 0.6355 | 0.1306 |

## Full Table

| Status | Label | Samples | Load (s) | Mean STT (s) | P95 STT (s) | Mean RTF | Normalized Exact Match | Normalized CER | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ok | tiny (cuda) | 50 | 6.2438 | 0.6355 | 0.8203 | 0.1306 | 0.0400 | 0.4753 | `20260316_180025` |
| ok | base (cuda) | 50 | 5.2179 | 0.7428 | 0.9637 | 0.1526 | 0.1800 | 0.1653 | `20260316_172552` |
| missing_summary | small (cuda) | - | - | - | - | - | - | - | `-` |
| ok | tiny (cpu) | 50 | 5.3554 | 4.6160 | 5.7325 | 0.9487 | 0.0400 | 0.4740 | `20260316_172715` |
| ok | base (cpu) | 50 | 1.3013 | 9.3706 | 11.6535 | 1.9258 | 0.1800 | 0.1661 | `20260316_172715` |
| ok | small (cpu) | 50 | 7.7633 | 24.6712 | 31.1793 | 5.0702 | 0.4200 | 0.0901 | `20260316_172715` |
| ok | gpt-4o-mini-transcribe (api) | 50 | 1.4875 | 0.8874 | 1.6442 | 0.1824 | 0.7000 | 0.0669 | `20260316_180115` |
