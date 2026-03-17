# STT TRT 시도 메모

## 목적

- 현재 로컬 STT 기본 후보인 `whisper base (cuda)`보다 더 빠른 CUDA/TensorRT 경로가 가능한지 확인한다.
- PyTorch 경로에서 `small (cuda)`가 GPU 로드 단계에서 실패했기 때문에, TensorRT 경로에서는 메모리 사용과 실행 경로가 더 유리할 수 있는지 탐색한다.
- 탐색 결과가 유효하면 `base`와 `small`을 같은 한국어 50문장 세트로 다시 비교할 계획이었다.

## 시도 범위

- NVIDIA `whisper_trt` 기반으로 `base`, `small` 한국어 실험을 별도 임시 경로에서만 시도했다.
- 기존 STT 공식 평가 문서와 기존 benchmark 결과는 변경하지 않았다.
- 이번 시도는 정식 비교 평가가 아니라, TensorRT 경로가 실제로 성립하는지 확인하는 탐색 실험이었다.

## 확인된 실패 원인

- 1차 시도
  - `onnx_graphsurgeon` 모듈 누락으로 `base` 경로가 중단됐다.
  - `small` 경로는 GPU 메모리/allocator 계열 오류와 함께 중단됐다.
- 2차 시도
  - 임시 패키지 경로 충돌로 `Numpy is not available` 오류가 발생했다.
- 3차 시도
  - `onnx.helper.float32_to_bfloat16` 속성 누락으로 엔진 준비 단계가 중단됐다.
- 별도 확인
  - PyTorch `small (cuda)`는 메모리 정리 후 fresh process로 다시 시도했지만, `NVML_SUCCESS == r` / `CUDACachingAllocator` / `NvMapMemAlloc ... error 12` 계열 오류로 다시 실패했다.

## 결론

- 이번 사이클에서는 WhisperTRT 경로로 유효한 속도/정확도 수치를 만들지 못했다.
- 따라서 현재 로컬 기본 STT 후보는 기존 비교 결과가 이미 확보된 `whisper base (cuda)`로 유지한다.
- `small`은 정확도 개선 가능성은 남아 있지만, 현재 Jetson 환경에서는 GPU 로드 안정성이 확보되지 않았다.
- WhisperTRT는 향후 전용 임시 환경과 의존성 버전 고정 조건에서 다시 검토할 수 있지만, 이번 결정에는 반영하지 않는다.

## 정리 원칙

- TRT 관련 임시 코드와 TRT 실험 산출물은 정리했다.
- 기존 STT 평가 문서와 기존 benchmark 결과는 그대로 유지한다.
- 이번 내용은 실패 탐색 기록으로만 남기고, 정식 성능 비교 표에는 포함하지 않는다.
