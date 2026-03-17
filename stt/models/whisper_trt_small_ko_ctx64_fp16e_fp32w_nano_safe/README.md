# WhisperTRT Small KO ctx64 fp16e fp32w nano safe

이 디렉토리는 Jetson Orin Nano에서 직접 생성 검증한 한국어 `WhisperTRT small` safe 자산 경로다.

핵심:

- 엔진 dtype: `fp16`
- 빌드 가중치 dtype: `fp32`
- 장비: `Jetson Orin Nano`
- 목적: Nano에서 GPU 메모리 부족을 피하면서 안전하게 재현 가능한 main checkpoint

안전 빌드 기준:

- decoder chunk: `2`
- encoder chunk: `1`
- workspace: `64MB`
- max text context: `64`

포함 파일:

- `whisper_trt_split.pth`
  - Nano에서 직접 생성한 main checkpoint
  - 로컬 생성 대상, git 비추적

설명:

- 이 모델은 decoder와 encoder를 chunk 단위로 나눠 빌드한 safe 모델이다.
- 목적은 Orin Nano 8GB에서 메모리 피크를 낮추면서 실제 한국어 전사를 유지하는 것이다.

