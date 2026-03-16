# STT 기술 조사

> 목적: Jetson Orin Nano에서 동작 가능한 온디바이스 STT v1 선택 기준 정리

## 현재 선택

- 기본 온디바이스 경로: OpenAI Whisper Python
- 백업/API 경로: OpenAI Audio Transcriptions API
- v1 구현 목표:
- `짧은 utterance -> text`
  - wake word + VAD 뒤에 붙을 공통 STT 래퍼 확보
- 기본 모델값 확정 기준:
  - 사용자가 직접 녹음한 고정 문장 50개 데이터셋으로 속도와 정확도를 비교한 뒤 결정

## 선택 이유

- 현재 문서 기준으로 STT는 `온디바이스 + API`를 같은 사용법으로 묶는 구조가 먼저 필요하다.
- VAD 뒤에서 들어오는 입력은 길지 않은 utterance이므로, 먼저 Python 경로로 빠르게 붙여 기본 흐름을 보는 것이 맞다.
- Whisper는 공식 모델/코드 기준이 분명하고, 한국어 다국어 모델 경로가 바로 있다.
- 이후 Jetson 실기 속도가 부족하면 `whisper_trt` 같은 가속 경로를 별도 단계로 검토하면 된다.

## v1 구조

- `stt/transcriber.py`
  - 공통 진입점
- `stt/stt_whisper.py`
  - 온디바이스 Whisper
- `stt/stt_api.py`
  - API STT
- `stt/stt_demo.py`
  - wav 또는 짧은 마이크 녹음 기준 최소 데모
- `stt/stt_dataset_recorder.py`
  - 고정 문장 50개 녹음 GUI
- `stt/stt_benchmark.py`
  - 같은 데이터셋 기준 다중 STT 비교
- `stt/datasets/korean_eval_50/`
  - txt/wav 같은 파일명 기준 평가 세트

## 공식 참고 자료

- OpenAI Whisper 공식 저장소
  - https://github.com/openai/whisper
- OpenAI Audio Transcriptions API
  - https://platform.openai.com/docs/guides/speech-to-text
- NVIDIA WhisperTRT 공식 저장소
  - https://github.com/NVIDIA-AI-IOT/whisper_trt

## 현재 판단

- v1 기본값은 `whisper`로 두는 것이 맞다.
- 다만 기본 Whisper 모델값은 비교 전까지 잠정값으로만 둔다.
- 이유:
  - 다국어 한국어 경로가 바로 있다.
  - Python에서 VAD 뒤 numpy 배열을 바로 넘기기 쉽다.
  - API 경로와 같은 인터페이스로 묶기 쉽다.
- 현재 Jetson smoke에서는 `tiny` + `cuda` 기준으로 예시 샘플 전사가 먼저 확인됐다.
- 현재 Jetson smoke 기준 측정:
  - sample: 짧은 `하이 포포` 예시 샘플
  - result: `하이포포`
  - elapsed: 약 `3.031 sec`
- 단, 이 값만으로 최종 모델을 정하지 않는다.
- 다음 단계에서는 직접 녹음한 고정 문장 50개 세트로 `tiny / base / small`과 필요 시 API 경로를 같은 조건으로 비교한다.
- 실기 속도와 메모리가 부족하면 다음 단계에서 `whisper_trt` 또는 ONNX 기반 경로를 다시 검토한다.
