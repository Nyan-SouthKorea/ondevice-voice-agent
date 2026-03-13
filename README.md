# On-Device Voice Agent

온디바이스 음성 에이전트 개발용 리포지토리다.  
현재는 `wake_word` 학습 파이프라인이 가장 먼저 진행되고 있으며, 이후 `VAD`, `STT`, `LLM`, `TTS`를 포함한 전체 음성 에이전트 스택으로 확장하는 것을 목표로 한다.

## 현재 범위

- `wake_word`
  - `하이 포포` 한국어 wake word 데이터 준비
  - feature extraction
  - baseline 학습
  - 하이퍼파라미터 탐색
  - ONNX export 예정
- `vad`, `stt`, `llm`, `tts`
  - 상위 음성 에이전트 구조용 모듈 자리 확보

## 목표

- Linux 서버(A100)에서 wake word 모델을 학습하고 평가한다
- 성능이 충분하면 Jetson Orin Nano Developer Kit으로 이관한다
- 이후에는 ONNX 기반 추론 중심으로 전체 음성 에이전트를 구성한다

## 현재 진행 상태

- negative 데이터셋 준비 완료
  - `AI Hub + MUSAN + FSD50K`
- positive clean/mixed 증강 완료
- feature extraction 완료
- baseline 학습 및 grid search 준비 완료
- 다음 단계: best trial 선정 후 전체 데이터 학습, ONNX export, 평가

자세한 최신 상태는 [docs/status.md](/data2/iena/260312_WakeWord-train/docs/status.md)를 본다.

## 프로젝트 구조

```text
.
├── wake_word/     # wake word 데이터, 학습, 추론 모듈
├── vad/           # voice activity detection
├── stt/           # speech-to-text
├── llm/           # language model orchestration
├── tts/           # text-to-speech
├── docs/          # 문서 허브, 상태, 결정, 작업 로그
└── examples/      # 공개용 소량 샘플
```

## 문서 안내

- 문서 허브: [docs/README.md](/data2/iena/260312_WakeWord-train/docs/README.md)
- 개발 원칙: [docs/개발방침.md](/data2/iena/260312_WakeWord-train/docs/개발방침.md)
- 최신 상태: [docs/status.md](/data2/iena/260312_WakeWord-train/docs/status.md)
- 의사결정 기록: [docs/decisions.md](/data2/iena/260312_WakeWord-train/docs/decisions.md)
- 작업 로그: [docs/logbook.md](/data2/iena/260312_WakeWord-train/docs/logbook.md)

## 리포지토리 운영 원칙

- 대용량 데이터와 학습 산출물은 리포에 포함하지 않는다
- 공개용 샘플은 `examples/audio_samples/`에만 소량 유지한다
- 코드 변경과 문서 변경은 가능한 한 같은 흐름으로 관리한다
