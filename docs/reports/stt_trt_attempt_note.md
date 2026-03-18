# STT TRT 시도 메모

## 목적

- 현재 로컬 STT 기본 후보인 `whisper base (cuda)`보다 더 빠른 CUDA/TensorRT 경로가 가능한지 확인한다.
- PyTorch 경로에서 `small (cuda)`가 GPU 로드 단계에서 실패했기 때문에, TensorRT 경로에서는 메모리 사용과 실행 경로가 더 유리할 수 있는지 탐색한다.
- 탐색 결과가 유효하면 `base`와 `small`을 같은 한국어 50문장 세트로 다시 비교할 계획이었다.

## 시도 범위

- NVIDIA `whisper_trt` 기반으로 `base`, `small` 한국어 실험을 별도 임시 경로에서만 시도했다.
- 기존 STT 공식 평가 문서와 기존 benchmark 결과는 변경하지 않았다.
- 이번 시도는 정식 비교 평가가 아니라, TensorRT 경로가 실제로 성립하는지 확인하는 탐색 실험이었다.

## 초기 실패 원인

- 1차 시도
  - `onnx_graphsurgeon` 모듈 누락으로 `base` 경로가 중단됐다.
  - `small` 경로는 GPU 메모리/allocator 계열 오류와 함께 중단됐다.
- 2차 시도
  - 임시 패키지 경로 충돌로 `Numpy is not available` 오류가 발생했다.
- 3차 시도
  - `onnx.helper.float32_to_bfloat16` 속성 누락으로 엔진 준비 단계가 중단됐다.
- 별도 확인
  - PyTorch `small (cuda)`는 메모리 정리 후 fresh process로 다시 시도했지만, `NVML_SUCCESS == r` / `CUDACachingAllocator` / `NvMapMemAlloc ... error 12` 계열 오류로 다시 실패했다.

## 이후 정리와 최종 상태

- split builder로 경로를 바꾼 뒤 `base.en`은 checkpoint 생성과 로드까지 성공했다.
- 이후 split builder 내부 메모리 점유를 더 줄이고 `max_text_ctx 64`로 좁힌 뒤, 한국어 다국어 `base`도 checkpoint 생성과 load-check까지 성공했다.
- 한국어 다국어 `base`는 custom 시작 토큰(`sot_sequence_including_notimestamps`)을 쓰는 transcribe 경로로 1~3번 smoke와 50문장 benchmark까지 통과했다.

최종 benchmark 경로:

- `/home/everybot/workspace/ondevice-voice-agent/results/stt_trt_eval_results/korean_eval_50/20260317_112711`

code-generated summary 기준:

- `mean_stt_sec 0.2115`
- `p95_stt_sec 0.2946`
- `mean_rtf 0.0435`
- `normalized_exact_match_rate 0.1600`
- `mean_normalized_cer 0.1759`

## 최종 결론

- WhisperTRT 경로는 이제 Jetson에서 실제 한국어 `base` checkpoint 생성과 평가까지 가능한 상태다.
- 다만 현재 수치 기준으로는 속도는 크게 좋아졌지만, 정확도는 PyTorch `base(cuda)`보다 약간 불리하다.
- 따라서 현 시점 기본 STT 후보는 계속 `whisper base (cuda)`로 유지한다.
- WhisperTRT는 실패 탐색 단계는 지났고, 이제는 성능/정확도 균형을 더 다듬을 수 있는 실험 경로로 본다.

## 정리 원칙

- TRT 관련 임시 코드와 TRT 실험 산출물은 정리했다.
- 기존 STT 평가 문서와 기존 benchmark 결과는 그대로 유지한다.
- 이번 내용은 실패 탐색 기록으로만 남기고, 정식 성능 비교 표에는 포함하지 않는다.
