# Status

> 마지막 업데이트: 2026-03-18

## 현재 목표

- TTS는 API 최소 경로를 유지한 채 Jetson에서 `MeloTTS` 온디바이스 가능성을 검증한다.
- STT는 `WhisperTRT small nano safe`를 온디바이스 기본값으로 유지하고, wake word + VAD + STT 통합 GUI에서 실사용 조건을 다듬는다.
- `Whisper base (PyTorch + CUDA)`와 `WhisperTRT base legacy`는 비교 기준/속도 fallback으로 유지한다.
- wake word와 VAD를 연결해 STT 입력 구간 절단 기준을 확정한다.
- 상위 음성 파이프라인을 SDK형 인터페이스로 연결할 준비를 한다.
- STT 전용 GUI와 wake word + VAD + STT 통합 GUI를 기준으로 상위 파이프라인 UX를 검증한다.

## 현재 고정 기준

- wake word 호출어: `하이 포포`
- 추론 타깃: `Jetson Orin Nano Developer Kit 8GB`
- wake word runtime: ONNX 기반 로컬 feature backbone + classifier
- VAD 기본 backend: `silero`
- STT 기본 방향: 온디바이스 기본값은 `WhisperTRT small nano safe`로 고정하고, `Whisper base (PyTorch + CUDA)`와 `WhisperTRT base legacy`는 비교 기준과 fallback으로 병행 관리
- TTS 기본 방향: `공통 래퍼 + API 최소 경로`, 온디바이스 후보는 `MeloTTS`

## 모듈 상태

| 모듈 | 상태 | 메모 |
|---|---|---|
| Wake word | 완료 후 튜닝 단계 | `final_full_best_trial40`, `threshold 0.80`, Jetson GUI demo 완료 |
| VAD | 완료 | `VADDetector` 공통 진입점, `silero` 기본 backend |
| STT | 기본값 확정 완료, 통합 GUI 실사용 검증 단계 | 온디바이스 기본값은 `WhisperTRT small nano safe`, wake word + VAD + STT 통합 GUI 데모 유지 |
| TTS | 초기 구조 구현, 다음 우선 개발 대상 | `TTSSynthesizer`, API backend, file save demo 준비 |
| LLM | 대기 | 상위 orchestration만 남아 있음 |

## 핵심 메모

- wake word 핵심 수치
  - best run: `wake_word/models/hi_popo/runs/final_full_best_trial40`
  - `val_recall 0.9966`
  - `val_fp_rate 0.0114`
  - 현재 runtime 기준 threshold: `0.80`
- Jetson runtime과 smoke 학습 환경은 각각 `docs/envs/jetson_wake_word_env.md`, `docs/envs/wake_word_train_smoke_env.md`에 정리돼 있다.
- STT 50문장 직접 녹음 평가 세트와 benchmark 파이프라인은 준비돼 있다.
- 현재 로컬에 유지하는 TRT 자산 기준은 아래와 같다.
  - `whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy`
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_nano_safe`
- 50문장 현재 active 비교 기준은 아래 문서를 본다.
  - `docs/reports/stt_korean_eval50_six_model_overview.md`
- 현재 로컬 워크스페이스 기준은 `repo / env / secrets` sibling 구조다.
  - A100에서는 `env`를 비워 두고 필요할 때만 다시 만든다.
  - Jetson에서는 같은 repo branch를 기준으로 실기 검증과 TRT 빌드를 진행한다.
- STT 자동 생성 결과물은 `stt/eval_results/` 아래에 두고, 사람이 읽는 요약은 `docs/reports/stt_korean_eval50_six_model_overview.md`를 기준으로 본다.
- 현재 STT 기본값은 `WhisperTRT small nano safe`다.
  - code-generated 비교 요약 기준:
    - `normalized_exact_match_rate 0.4600`
    - `mean_normalized_cer 0.0886`
    - `mean_stt_sec 0.3823`
  - Jetson Orin Nano 8GB에서 직접 생성한 safe TRT 경로라서 cross-device 불확실성이 없다.
  - 현재 로컬 온디바이스 경로 중 정확도가 가장 좋고, 동시에 평균 처리 시간도 실사용 가능한 수준이다.
  - API 의존 없이 Jetson 내부에서 바로 재사용할 수 있어 상위 음성 파이프라인 기본값으로 두기 적합하다.
  - 속도 fallback은 `WhisperTRT base legacy`다.
  - 최고 정확도 참고값은 `gpt-4o-mini-transcribe (api)`지만, 기본값으로는 두지 않는다.
- TTS는 현재 `OpenAI Audio Speech API`로 최소 합성 경로를 열어 두었고, 지금 다음 집중 모듈은 `MeloTTS` Jetson 검증이다.
- 데모 구현 계획 문서는 `docs/reports/stt_demo_plan.md`에 둔다.
- 통합 GUI 데모의 화면 설명과 스크린샷은 `stt/README.md`를 기준으로 본다.

## 다음 작업

1. Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
2. `TTSSynthesizer`에 온디바이스 backend를 추가하고 playback, cache 전략을 붙인다.
3. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값을 확정한다.
4. hard negative 문구와 연속 배경 오디오 기준 false accept 패턴을 정리한다.
5. wake word 뒤에 VAD를 연결하고 speech start / end 기준을 고정한다.
6. `WhisperTRT small nano safe`를 기준으로 wake word + VAD + STT 통합 GUI 동작을 실제 마이크 조건에서 점검한다.
7. 통합 GUI 사용 결과를 기준으로 상위 SDK형 orchestrator가 정말 필요한지 판단하고, 필요하면 구조 변경 범위를 확정한다.

## 참조 문서

- [project_overview.md](project_overview.md)
- [jetson_transition_plan.md](jetson_transition_plan.md)
- [decisions.md](decisions.md)
- [logbook.md](logbook.md)
