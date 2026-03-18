# Edge TTS Experiment

목표:

- wake word positive 생성에 사용했던 `edge_tts` 경로를 공통 SDK형 TTS backend로 다시 연결한다.
- 한국어 voice baseline과 다국어 voice 빠른 생성 경로를 reference backend로 유지한다.

현재 상태:

- A100 env `../env/tts_edge_tts` 생성 완료
- `TTSSynthesizer(model="edge_tts", ...)` backend 연결 완료
- 한국어 voice 기준 SDK/CLI smoke 완료

현재 smoke 메모:

- wake word 생성 스크립트:
  - `wake_word/train/01_generate_positive.py`
- 현재 smoke voice:
  - `ko-KR-InJoonNeural`
- SDK smoke:
  - output: `../results/tts/20260318_edge_tts_smoke/sdk_import.wav`
  - `model_load_sec 0.000`
  - `elapsed_sec 0.915`
- CLI smoke:
  - output: `../results/tts/20260318_edge_tts_smoke/demo_cli.wav`
  - `model_load_sec 0.000`
  - `elapsed_sec 0.849`

구현 메모:

- wake word 생성 스크립트는 `.wav` 이름으로 저장하지만 실제 포맷은 MP3였다.
- 현재 SDK backend는 `ffmpeg`를 사용해 `.wav` 요청 시 실제 RIFF WAV로 변환한다.
- `.mp3` 출력도 그대로 지원한다.
- `rate`, `pitch`를 그대로 받아 wake word positive 생성 조건을 재현할 수 있다.

현재 판단:

- 제품 최종 후보라기보다, wake word 데이터 생성과 reference 청취 baseline 용도로 유용하다.
- A100 4개 로컬 후보 비교와 별도로 유지한다.
