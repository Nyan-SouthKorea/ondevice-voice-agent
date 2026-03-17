# Project Overview

> 이 문서는 빠른 배경 설명용이다. 최신 상태와 다음 작업은 항상 `docs/status.md`를 기준으로 본다.

## 프로젝트 목적

이 프로젝트의 목표는 Jetson Orin Nano 안에서 재사용 가능한 로봇용 음성 에이전트 스택을 만드는 것이다. 구성 요소는 `wake word -> VAD -> STT -> LLM -> TTS` 순서로 확장한다.

## 현재 전달 범위

| 영역 | 상태 |
|---|---|
| Wake word | 요소기술 완료, 현장 튜닝 진행 |
| VAD | 요소기술 완료 |
| STT | 래퍼와 비교 평가 준비 완료 |
| TTS | 래퍼와 API 최소 경로 시작 |
| LLM | 대기 |

## 시스템 파이프라인

```text
[Mic]
  -> [Wake Word]
  -> [VAD]
  -> [STT]
  -> [LLM]
  -> [TTS]
```

## 기준 문서

| 문서 | 용도 |
|---|---|
| [status.md](status.md) | 현재 상태와 다음 작업 |
| [개발방침.md](개발방침.md) | 장기적으로 유지할 원칙 |
| [decisions.md](decisions.md) | 현재 유효한 핵심 결정 |
| [jetson_transition_plan.md](jetson_transition_plan.md) | Jetson 연동 체크리스트 |
| [research/](research/) | 기술 조사 배경 |
| [envs/](envs/) | 환경 재현 절차 |

## 구현 진입점

- [../wake_word/README.md](../wake_word/README.md)
- [../vad/README.md](../vad/README.md)
- [../stt/README.md](../stt/README.md)
- [../tts/README.md](../tts/README.md)

상세 이력이나 과거 판단 과정을 찾는 용도라면 [logbook.md](logbook.md)와 [archive/README.md](archive/README.md)를 본다.
