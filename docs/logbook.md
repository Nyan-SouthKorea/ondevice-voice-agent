# Logbook

> 최근 작업만 유지한다. 이전 상세 로그는 `docs/archive/logbook_2026_03_full_before_refactor.md`에 보관한다.

## 2026-03-17 | Human + Codex | STT 디렉토리 역할 기준 재정리

### Context

- `stt/` 루트에 런타임 코드와 실험/도구 스크립트가 함께 있어 구조가 빠르게 읽히지 않았다.

### Actions

- 실제 런타임 코드는 `stt/` 루트에 남기고, 반복 실행 도구는 `stt/tools/`, 실험성 TRT 코드는 `stt/experiments/`로 분리했다.
- 실행 명령과 환경 문서, STT README를 새 경로 기준으로 다시 맞췄다.

### Next

- 이후 새 STT 관련 파일은 처음부터 `런타임 / tools / experiments / models / datasets / eval_results` 역할을 구분해 추가한다.

## 2026-03-17 | Human + Codex | TTS 초기 구조와 개발 계획 시작

### Context

- `tts/`는 아직 상위 파이프라인이 바로 붙일 수 있는 공통 인터페이스가 없었다.

### Actions

- `TTSSynthesizer` 공통 진입점을 추가했다.
- OpenAI Audio Speech API 기반 최소 backend를 추가했다.
- 텍스트를 오디오 파일로 저장하는 데모를 추가했다.
- TTS 조사 문서와 상위 상태 문서를 현재 기준으로 동기화했다.

### Next

- Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
- playback, cache, LLM 출력 연결 순서로 확장한다.

## 2026-03-16 | Human + Codex | STT 직접 녹음 평가 파이프라인 추가

### Context

- STT 기본 모델을 감으로 정하지 않고, 실제 사용자의 직접 녹음 50문장으로 비교하기로 했다.

### Actions

- `stt/datasets/korean_eval_50/` 평가 세트를 추가했다.
- 순차 녹음 GUI와 다중 STT benchmark 스크립트를 추가했다.
- 샘플별 결과와 요약 CSV/JSON 저장 구조를 만들었다.

### Next

- 사용자가 50문장을 직접 녹음한다.
- `whisper tiny / base / small`과 필요 시 API 경로를 비교한다.

## 2026-03-16 | Human + Codex | VAD 구조와 기본 filtering 정리

### Context

- wake word 다음 단계로 붙일 수 있는 최소 VAD 구조와 흔들림 완화가 필요했다.

### Actions

- `VADDetector` 공통 진입점과 `webrtcvad` / `silero` backend를 정리했다.
- `min_speech_frames=3`, `min_silence_frames=10` 기본 filtering을 추가했다.
- 기본 backend를 `silero` 기준으로 정리했다.

### Next

- wake word 뒤에 붙여 speech start / end 기준을 확정한다.

## 2026-03-16 | Human + Codex | wake word / VAD 완료 기준으로 상위 문서 재정렬

### Context

- 상위 문서 여러 곳에 같은 상태가 반복돼 있어, 완료 기준을 다시 맞출 필요가 있었다.

### Actions

- 루트 README, status, Jetson 관련 문서, 모듈 README를 현재 완료 상태에 맞춰 동기화했다.
- Jetson demo 스크린샷과 영상 자산을 리포 문서 자산 구조로 정리했다.

### Next

- 상위 문서 중복을 더 줄이고, 현재 상태 기준은 `status.md` 하나로 수렴한다.
