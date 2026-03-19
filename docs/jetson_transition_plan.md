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
- Jetson runtime env: [../wake_word/docs/환경/260313_1700_Jetson_웨이크워드_환경.md](../wake_word/docs/환경/260313_1700_Jetson_웨이크워드_환경.md)
- Jetson TTS env: [../tts/docs/환경/260319_0930_Jetson_TTS_환경.md](../tts/docs/환경/260319_0930_Jetson_TTS_환경.md)
- Jetson smoke train env: [../wake_word/docs/환경/260316_1616_웨이크워드_학습스모크_환경.md](../wake_word/docs/환경/260316_1616_웨이크워드_학습스모크_환경.md)
- STT TRT 실험 env (AGX 대응): [../stt/docs/환경/260317_1510_STT_TRT_AGX_Orin_실험가이드.md](../stt/docs/환경/260317_1510_STT_TRT_AGX_Orin_실험가이드.md)

## 완료된 항목

- wake word ONNX runtime과 Jetson GUI demo 검증
- VAD 공통 detector와 기본 backend 정리
- Jetson runtime env 정리
- Jetson 학습 smoke env 정리
- STT recorder / benchmark 준비
- STT 50문장 비교와 기본 모델 확정 (`WhisperTRT small nano safe`)
- TTS 공통 래퍼와 API 최소 경로 확보
- TTS SDK lazy import 정리
- `OpenVoice V2` 제외 후보 Jetson smoke 검증
  - `Edge TTS`, `OpenAI API TTS`
  - `Piper`
  - `MeloTTS`
  - `Kokoro`

## 남은 항목

1. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값 확정
2. hard negative 문구와 연속 배경 오디오 기준 false accept 점검
3. wake word 뒤에 VAD를 연결하고 utterance cut 기준 확정
4. Jetson TTS shortlist를 상위 voice pipeline 통합 대상으로 고정
  - 영어 local: `Piper cpu`, `Kokoro cuda`
  - 한국어는 일단 network fallback 유지
5. Jetson용 TTS demo 경로를 상위 SDK 연결 포인트와 함께 정리
6. 영어 local 후보가 우세하다고 판단되면 custom training 계획을 별도 문서로 연다
7. `WhisperTRT small nano safe` 기준으로 통합 GUI 실마이크 조건을 점검

## 성공 기준

- wake word와 VAD가 Jetson 마이크 환경에서 연속 실행 기준으로 안정적이다.
- STT 기본 모델과 TTS 기본 경로가 Jetson 제약을 고려한 실제 선택지로 좁혀져 있다.
- TTS backend별 smoke env와 최종 통합 대상 env가 구분돼 있고, benchmark 코드와 충돌하지 않는다.
- Jetson TTS screening 결과와 상위 통합 shortlist가 문서에 숫자와 경로 기준으로 정리돼 있다.
- 다음 세션에서 필요한 문서가 `status / module docs / module README` 기준으로 빠르게 복구된다.

## 새 세션 시작 순서

1. `docs/status.md`
2. 관련 모듈 `README.md`
3. `wake_word/docs/환경/260313_1700_Jetson_웨이크워드_환경.md`
4. `docs/decisions.md`
5. 필요 시 `docs/logbook.md` 또는 `docs/archive/`
