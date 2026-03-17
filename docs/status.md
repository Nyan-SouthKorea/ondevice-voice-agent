# Status

> 마지막 업데이트: 2026-03-17

## 현재 목표

- wake word와 VAD를 연결해 STT 입력 구간 절단 기준을 확정한다.
- STT는 직접 녹음한 50문장 세트로 `tiny / base / small`과 필요 시 API 경로를 비교한다.
- TTS는 API 최소 경로를 유지한 채 Jetson에서 `MeloTTS` 온디바이스 가능성을 검증한다.
- 상위 음성 파이프라인을 SDK형 인터페이스로 연결할 준비를 한다.

## 현재 고정 기준

- wake word 호출어: `하이 포포`
- 추론 타깃: `Jetson Orin Nano Developer Kit 8GB`
- wake word runtime: ONNX 기반 로컬 feature backbone + classifier
- VAD 기본 backend: `silero`
- STT 기본 방향: `Whisper` 비교 후 확정
- TTS 기본 방향: `공통 래퍼 + API 최소 경로`, 온디바이스 후보는 `MeloTTS`

## 모듈 상태

| 모듈 | 상태 | 메모 |
|---|---|---|
| Wake word | 완료 후 튜닝 단계 | `final_full_best_trial40`, `threshold 0.80`, Jetson GUI demo 완료 |
| VAD | 완료 | `VADDetector` 공통 진입점, `silero` 기본 backend |
| STT | 비교 평가 준비 | recorder, benchmark, API/Whisper 래퍼 준비 |
| TTS | 초기 구조 구현 | `TTSSynthesizer`, API backend, file save demo 준비 |
| LLM | 대기 | 상위 orchestration만 남아 있음 |

## 핵심 메모

- wake word 핵심 수치
  - best run: `wake_word/models/hi_popo/runs/final_full_best_trial40`
  - `val_recall 0.9966`
  - `val_fp_rate 0.0114`
  - 현재 runtime 기준 threshold: `0.80`
- Jetson runtime과 smoke 학습 환경은 각각 `docs/envs/jetson_wake_word_env.md`, `docs/envs/wake_word_train_smoke_env.md`에 정리돼 있다.
- STT 50문장 직접 녹음 평가 세트와 benchmark 파이프라인은 준비돼 있다.
- STT 자동 생성 결과물은 `stt/eval_results/` 아래에 두고, 사람이 읽는 요약은 `docs/reports/stt_korean_eval50_overview.md`를 기준으로 본다.
- TTS는 현재 `OpenAI Audio Speech API`로 최소 합성 경로를 열어 두었고, 다음 검증 대상은 `MeloTTS`다.

## 다음 작업

1. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값을 확정한다.
2. hard negative 문구와 연속 배경 오디오 기준 false accept 패턴을 정리한다.
3. wake word 뒤에 VAD를 연결하고 speech start / end 기준을 고정한다.
4. STT 50문장 세트를 실제로 녹음하고 `tiny / base / small`을 비교한다.
5. 비교 결과를 바탕으로 STT 기본 모델을 확정한다.
6. Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.

## 참조 문서

- [project_overview.md](project_overview.md)
- [jetson_transition_plan.md](jetson_transition_plan.md)
- [decisions.md](decisions.md)
- [logbook.md](logbook.md)
