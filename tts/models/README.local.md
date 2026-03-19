# TTS Local Model Cache

이 디렉토리는 TTS 런타임 모델을 로컬에 보관하는 자리다.

운영 원칙:

- `repo/tts/models/` 아래 파일은 기본적으로 Git에 올리지 않는다.
- 이 디렉토리 안에서는 `.gitignore`, `README.local.md`만 추적한다.
- 실제 ONNX, checkpoint, metadata 파일은 장비 로컬에서만 유지한다.
- 코드에서 기본 모델 경로를 찾을 때는 이 디렉토리를 먼저 보고, 없으면 `results/` 아래 export 산출물을 fallback으로 본다.

현재 메모:

- `Piper` 한국어 공식 파인튜닝 ONNX는 필요 시 아래처럼 둔다.
  - `tts/models/piper_ko_260319_공식파인튜닝/`
