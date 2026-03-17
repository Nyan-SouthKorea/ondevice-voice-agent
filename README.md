# On-Device Voice Agent

Jetson Orin Nano 기준의 온디바이스 로봇 음성 에이전트를 단계적으로 구축하는 리포지토리다. 현재는 wake word와 VAD 요소기술을 마무리했고, STT와 TTS를 붙여 재사용 가능한 음성 에이전트 SDK 형태로 확장하는 단계에 있다.

## 현재 범위

- wake word: 학습, 평가, ONNX export, Jetson 실시간 demo 완료
- VAD: 공통 detector와 기본 backend 정리 완료
- STT: 공통 래퍼, 직접 녹음 recorder, 비교 평가 완료, TRT 재현 문서 정리
- TTS: 공통 래퍼와 API 최소 합성 경로 시작
- LLM: 상위 orchestration 대기

## 모듈 상태

| 모듈 | 역할 | 상태 |
|---|---|---|
| [wake_word](wake_word/README.md) | 호출어 `하이 포포` 감지 | 요소기술 완료, 실기 튜닝 진행 |
| [vad](vad/README.md) | 발화 구간 감지 | 요소기술 완료 |
| [stt](stt/README.md) | 음성 인식 | 비교 평가 완료, TRT 실험 경로 유지 |
| [tts](tts/README.md) | 음성 합성 | 초기 구조 구현 |
| [llm](llm/README.md) | 명령 해석 및 응답 생성 | 대기 |

## 시작 문서

1. [docs/status.md](docs/status.md)
2. [docs/README.md](docs/README.md)
3. 필요한 모듈의 `README.md`
4. [docs/decisions.md](docs/decisions.md)
5. [docs/logbook.md](docs/logbook.md)

빠른 배경 설명만 필요하면 [docs/project_overview.md](docs/project_overview.md)를 읽고, 실제 최신 상태는 반드시 [docs/status.md](docs/status.md)를 기준으로 본다.

## 문서 역할 요약

| 문서 | 역할 |
|---|---|
| [docs/status.md](docs/status.md) | 현재 상태와 다음 작업의 단일 기준 |
| [docs/개발방침.md](docs/개발방침.md) | 장기적으로 유지할 개발 원칙 |
| [docs/decisions.md](docs/decisions.md) | 현재 유효한 핵심 결정 |
| [docs/logbook.md](docs/logbook.md) | 최근 작업 로그 |
| [docs/archive/README.md](docs/archive/README.md) | 오래된 기록과 이전 상세 문서 |
| [docs/research](docs/research) | 기술 조사와 선택 배경 |
| [docs/envs](docs/envs) | 환경 세팅과 검증 절차 |
| [docs/reports](docs/reports) | 사람이 읽는 요약 보고서 |

## 리포 구조

```text
.
├── wake_word/
├── vad/
├── stt/
├── tts/
├── llm/
├── docs/
└── secrets/
```

`secrets/`는 로컬 전용 운영 문서를 두는 자리다. 리포의 공식 현재 상태나 설계 기준은 `docs/` 아래 문서를 기준으로 유지한다.
