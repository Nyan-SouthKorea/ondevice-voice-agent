# WhisperTRT Base KO ctx64

이 디렉토리는 현재 승격된 한국어 `WhisperTRT base` 자산 경로다.

중요:

- `whisper_trt_split.pth`는 로컬 생성 대상이다.
- 파일 크기 때문에 git에는 올리지 않고, `.gitignore`로 제외한다.
- 즉 다른 개발 환경에서는 아래 절차로 다시 생성해야 한다.

포함 파일:

- `whisper_trt_split.pth`
  - 현재 메인 후보 checkpoint
  - 로컬 생성 대상, git 비추적
- `benchmark_summary.json`
  - 50문장 평가의 code-generated summary 스냅샷
- `smoke_test_001_003_custom_ko.json`
  - 1~3번 smoke 결과 스냅샷

현재 기준:

- 모델: `WhisperTRT base`
- 언어: `ko`
- 최대 text context: `64`

참고:

- 이 모델은 속도 면에서는 매우 유리하지만, 현재 정확도 지표는 `Whisper base (PyTorch + CUDA)`보다 약간 불리하다.
- 따라서 현재는 승격 저장만 한 상태이고, 기본 STT 경로는 아직 PyTorch `base(cuda)`를 유지한다.

재현 절차:

1. `stt/experiments/stt_trt_builder_experiment.py`로 split build 수행
2. 생성된 `whisper_trt_split.pth`를 이 디렉토리로 복사
3. `stt/experiments/stt_trt_benchmark_experiment.py`로 benchmark 재실행
