# Jetson Transition Plan

> 이 문서는 Jetson 연동 체크리스트만 유지한다. 현재 상태 요약은 `docs/status.md`를 기준으로 본다.

## 목적

- wake word와 VAD를 Jetson 실기 기준으로 안정화한다.
- STT와 TTS의 Jetson 적합 경로를 검증한다.
- 상위 음성 파이프라인 연결 전 필요한 handoff 항목을 명확히 유지한다.

## 현재 handoff 입력

- 현재 상태: [status.md](status.md)
- 개발 원칙: [개발방침.md](개발방침.md)
- wake word 사용법: [../wake_word/README.md](../wake_word/README.md)
- VAD 사용법: [../vad/README.md](../vad/README.md)
- STT 사용법: [../stt/README.md](../stt/README.md)
- TTS 사용법: [../tts/README.md](../tts/README.md)
- Jetson runtime env: [envs/jetson_wake_word_env.md](envs/jetson_wake_word_env.md)
- Jetson smoke train env: [envs/wake_word_train_smoke_env.md](envs/wake_word_train_smoke_env.md)

## 완료된 항목

- wake word ONNX runtime과 Jetson GUI demo 검증
- VAD 공통 detector와 기본 backend 정리
- Jetson runtime env 정리
- Jetson 학습 smoke env 정리
- STT recorder / benchmark 준비
- TTS 공통 래퍼와 API 최소 경로 확보

## 남은 항목

1. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값 확정
2. hard negative 문구와 연속 배경 오디오 기준 false accept 점검
3. wake word 뒤에 VAD를 연결하고 utterance cut 기준 확정
4. STT 50문장 직접 녹음 세트 비교 후 기본 모델 확정
5. Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke 검증
6. 상위 SDK 연결용 공통 음성 파이프라인 인터페이스 정리

## 성공 기준

- wake word와 VAD가 Jetson 마이크 환경에서 연속 실행 기준으로 안정적이다.
- STT 기본 모델과 TTS 기본 경로가 Jetson 제약을 고려한 실제 선택지로 좁혀져 있다.
- 다음 세션에서 필요한 문서가 `status / envs / module README` 기준으로 빠르게 복구된다.

## 새 세션 시작 순서

1. `docs/status.md`
2. 관련 모듈 `README.md`
3. `docs/envs/jetson_wake_word_env.md`
4. `docs/decisions.md`
5. 필요 시 `docs/logbook.md` 또는 `docs/archive/`
