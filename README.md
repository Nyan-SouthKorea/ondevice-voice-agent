# On-Device Voice Agent

온디바이스 로봇 음성 에이전트를 단계적으로 구축하는 리포지토리다.  
현재는 `하이 포포` wake word 시스템을 먼저 완성하고 있으며, 이후 `VAD`, `STT`, `LLM`, `TTS`를 결합해 Jetson Orin Nano에서 실시간으로 동작하는 전체 음성 에이전트 스택으로 확장하는 것이 목표다.

## 프로젝트 목표

- Linux 서버(A100)에서 데이터 준비, 학습, 평가를 수행한다.
- Jetson Orin Nano Developer Kit에서 ONNX 기반 실시간 추론을 검증한다.
- wake word를 시작점으로 음성 파이프라인 전체를 순차적으로 확장한다.
- 최종적으로는 Jetson 안에서 재사용 가능한 음성 에이전트 SDK/플랫폼 형태로 정리한다.
- 공개 리포에는 코드와 문서 중심으로 남기고, 대용량 데이터와 민감 운영 정보는 분리 관리한다.

## 장기 제품 방향

이 프로젝트의 장기 목표는 단순히 wake word 데모를 만드는 것이 아니라,  
Jetson 내부에서 다른 프론트엔드, 백엔드, 동료 개발자가 쉽게 붙여 쓸 수 있는 음성 에이전트 SDK를 만드는 것이다.

이 SDK가 제공해야 하는 핵심 가치는 다음과 같다.

- 음성 입력부터 응답 출력까지의 공통 파이프라인 제공
- wake word, VAD, STT, LLM, TTS를 일관된 인터페이스로 추상화
- 다른 시스템이 음성 에이전트를 이벤트/콜백/명령 형태로 쉽게 사용 가능
- 로봇의 다른 기능과 자연스럽게 연결 가능한 오케스트레이션 레이어 제공

예상 통합 대상:

- 안면 인식
- 표정 인식
- 특정 포인트 이동
- 순찰 모드
- 기타 로봇 제어 및 상호작용 기능

즉, 이 리포는 개별 음성 모델 모음이 아니라 로봇 기능을 음성으로 연결하는 상위 플랫폼으로 발전시키는 것을 지향한다.

## 현재 가장 앞서 있는 영역

현재 구현과 실험이 가장 많이 진행된 영역은 [`wake_word`](wake_word/README.md)다.

- negative 데이터셋 준비 완료
  - `AI Hub + MUSAN + FSD50K`
- positive clean / mixed augmentation 완료
- feature extraction 완료
- baseline 학습, grid search, full-data 최종 학습 완료
- 현재 best validation snapshot
  - `val_recall 0.9966`
  - `val_fp_rate 0.0114`
  - `threshold 0.80`
- 다음 단계
  - ONNX export
  - Jetson 실시간 추론
  - GUI 데모
  - 실제 마이크 기반 검증

최신 상태는 [docs/status.md](docs/status.md)에서 계속 갱신한다.

## 모듈 바로가기

이 리포는 상위 프로젝트 하나 아래에 요소기술별 하위 프로젝트를 두는 구조로 운영한다.

| 모듈 | 설명 | 상태 |
|------|------|------|
| [wake_word](wake_word/README.md) | 호출어 `하이 포포` 감지 모델 학습, 평가, 추론 | 가장 많이 진행됨 |
| [vad](vad/README.md) | 발화 구간 감지 모듈 | 구조만 확보 |
| [stt](stt/README.md) | 음성 인식 계층 | 구조만 확보 |
| [llm](llm/README.md) | 명령 해석 및 응답 생성 계층 | 구조만 확보 |
| [tts](tts/README.md) | 음성 합성 계층 | 구조만 확보 |

루트 README는 상위 프로젝트 설명과 모듈 연결을 담당하고, 실제 구현이 진행된 모듈은 각 디렉토리의 README에서 더 자세히 설명한다.

## Wake Word 핵심 결과

현재 wake word 기준 최종 후보 모델은 `final_full_best_trial40` run이다.

- 모듈 문서: [wake_word/README.md](wake_word/README.md)
- artifact 설명:
  - [wake_word/models/hi_popo/README.md](wake_word/models/hi_popo/README.md)
- 최종 checkpoint 경로:
  - `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`
- held-out validation 기준:
  - positive-only recall: `1177 / 1181 = 0.9966`
  - negative-only false positive rate: `128 / 11250 = 0.0114`

중요한 점:
- 이 수치는 현재 파이프라인 내에서는 강한 결과다.
- 다만 실제 배치 성능은 Jetson 실기와 연속 오디오 평가에서 다시 확인해야 한다.

## 리포지토리 구조

```text
.
├── wake_word/   # 현재 핵심 구현 영역: 데이터, 학습, 평가, 추론
├── vad/         # voice activity detection
├── stt/         # speech-to-text
├── llm/         # language model orchestration
├── tts/         # text-to-speech
├── docs/        # 프로젝트 문서 허브
└── secrets/     # 로컬 전용 민감 메모 및 비공개 정보 (gitignore)
```

## 문서 읽는 순서

새 세션에서 빠르게 컨텍스트를 복구하려면 아래 순서를 권장한다.

1. [docs/project_overview.md](docs/project_overview.md)
2. [docs/status.md](docs/status.md)
3. [wake_word/README.md](wake_word/README.md)
4. [docs/개발방침.md](docs/개발방침.md)
5. [docs/decisions.md](docs/decisions.md)
6. [docs/logbook.md](docs/logbook.md)

## 공개 리포지토리 운영 기준

- 대용량 데이터셋, feature, 학습 산출물은 리포에 포함하지 않는다.
- 외부 데이터셋 원본 샘플은 공개 리포에 포함하지 않는다.
- 공개용 오디오 샘플은 `wake_word/examples/audio_samples/` 아래의 직접 생성한 소량 샘플만 유지한다.
- 내부 주소, 계정 식별자, SSH 경로 같은 민감한 운영 정보는 공개 문서가 아니라 `secrets/` 아래의 로컬 전용 문서에서 관리한다.

## 문서 허브

세부 문서는 [docs/README.md](docs/README.md)에서 한 번에 찾을 수 있다.  
현재 구현 상태를 가장 빠르게 확인하려면 [docs/status.md](docs/status.md)와 [wake_word/README.md](wake_word/README.md)를 먼저 보면 된다.
