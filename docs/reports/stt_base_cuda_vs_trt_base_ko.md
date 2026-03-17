# STT `base(cuda)` vs `WhisperTRT base(ko)` 비교

## 기준

- 이 문서는 사람이 임의 계산한 값이 아니라, 아래 두 code-generated 원본에서 값을 그대로 옮겨 비교한 표다.
- 기존 `base(cuda)` 출처:
  - `stt/eval_results/korean_eval_50/overview.md`
- 새 `WhisperTRT base(ko)` 출처:
  - `results/stt_trt_eval_results/korean_eval_50/20260317_112711/summary.json`

## 비교 표

| 항목 | `base (cuda)` | `WhisperTRT base (ko)` |
|---|---:|---:|
| sample_count | 50 | 50 |
| load_time_sec | 5.2179 | 3.3325 |
| mean_stt_sec | 0.7428 | 0.2115 |
| p95_stt_sec | 0.9637 | 0.2946 |
| mean_rtf | 0.1526 | 0.0435 |
| normalized_exact_match_rate | 0.1800 | 0.1600 |
| mean_normalized_cer | 0.1653 | 0.1759 |

## 해석 메모

- 현재 표는 원본 수치를 그대로 나란히 둔 비교 기록이다.
- 현 시점 기본 STT 경로는 `Whisper base (PyTorch + CUDA)`로 유지한다.
- 이유는 `WhisperTRT base (ko)`가 속도는 더 빠르지만, 현재 코드가 계산한 정확도 지표는 약간 불리하기 때문이다.
