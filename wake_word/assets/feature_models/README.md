# Wake Word Feature Backbone Models

이 디렉토리는 wake word feature backbone ONNX 파일을 프로젝트 안에서 직접 관리하는 위치다.

현재 포함 파일:

- `melspectrogram.onnx`
- `embedding_model.onnx`

출처:

- `melspectrogram.onnx`
  - https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx
- `embedding_model.onnx`
  - https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx

운영 원칙:

- wake word 추론과 학습 feature extraction은 이제 이 디렉토리의 ONNX 파일만 사용한다.
- `wake_word/openWakeWord/` 로컬 clone은 더 이상 실행 의존성으로 사용하지 않는다.
- 어떤 원본 파일을 참고했고, 현재 무엇을 로컬 구현으로 옮겼는지는 `wake_word/docs/조사/260316_1231_OpenWakeWord_레퍼런스_조사.md`에 기록한다.
