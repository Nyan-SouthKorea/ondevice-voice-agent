# Status

> 마지막 업데이트: 2026-03-17

## 현재 목표

- wake word와 VAD를 연결해 STT 입력 구간 절단 기준을 확정한다.
- STT는 현재 `Whisper base (PyTorch + CUDA)`를 기본 후보로 두고 상위 파이프라인 연결을 진행한다.
- 동시에 `WhisperTRT base` 한국어 경로를 실험 상태로 유지하며, 속도/정확도 균형이 더 나아지는지 추가 확인한다.
- TTS는 API 최소 경로를 유지한 채 Jetson에서 `MeloTTS` 온디바이스 가능성을 검증한다.
- 상위 음성 파이프라인을 SDK형 인터페이스로 연결할 준비를 한다.
- STT 전용 GUI 데모를 먼저 만들고, 그 다음 wake word + VAD + STT 통합 GUI 데모로 확장한다.

## 현재 고정 기준

- wake word 호출어: `하이 포포`
- 추론 타깃: `Jetson Orin Nano Developer Kit 8GB`
- wake word runtime: ONNX 기반 로컬 feature backbone + classifier
- VAD 기본 backend: `silero`
- STT 기본 방향: `Whisper base (PyTorch + CUDA)` 유지, `WhisperTRT base`는 실험 경로로 병행 확인
- TTS 기본 방향: `공통 래퍼 + API 최소 경로`, 온디바이스 후보는 `MeloTTS`

## 모듈 상태

| 모듈 | 상태 | 메모 |
|---|---|---|
| Wake word | 완료 후 튜닝 단계 | `final_full_best_trial40`, `threshold 0.80`, Jetson GUI demo 완료 |
| VAD | 완료 | `VADDetector` 공통 진입점, `silero` 기본 backend |
| STT | 비교 평가 완료 후 기본값 확정 | 기본값은 `Whisper base (PyTorch + CUDA)`, `WhisperTRT base` 한국어 실험 성공 |
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
- 현재 STT 기본 후보는 `Whisper base (PyTorch + CUDA)`다.
  - 코드가 계산한 기존 평가 수치 기준:
    - `mean_stt_sec 0.7428`
    - `mean_rtf 0.1526`
    - `normalized_exact_match_rate 0.1800`
    - `mean_normalized_cer 0.1653`
- `WhisperTRT base` 한국어 split build도 현재는 성공했다.
  - 코드가 계산한 TRT 평가 수치 기준:
    - `mean_stt_sec 0.2115`
    - `mean_rtf 0.0435`
    - `normalized_exact_match_rate 0.1600`
    - `mean_normalized_cer 0.1759`
  - 즉 속도는 더 빠르지만, 현재 정확도는 PyTorch `base(cuda)`보다 약간 불리하다.
  - 그래서 현 시점 기본값은 계속 `Whisper base (PyTorch + CUDA)`로 유지한다.
- TTS는 현재 `OpenAI Audio Speech API`로 최소 합성 경로를 열어 두었고, 다음 검증 대상은 `MeloTTS`다.
- 데모 구현 계획 문서는 `docs/reports/stt_demo_plan.md`에 둔다.

## 다음 작업

1. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값을 확정한다.
2. hard negative 문구와 연속 배경 오디오 기준 false accept 패턴을 정리한다.
3. wake word 뒤에 VAD를 연결하고 speech start / end 기준을 고정한다.
4. wake word + VAD + STT를 실제 utterance 단위로 연결한다.
5. `WhisperTRT base` 한국어 경로에서 custom transcribe 시작 토큰과 default stream 최적화를 더 정리할지 판단한다.
6. Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
7. STT GUI 데모를 먼저 시연 가능한 수준으로 만들고, 그 다음 통합 GUI 데모를 구현한다.

## 참조 문서

- [project_overview.md](project_overview.md)
- [jetson_transition_plan.md](jetson_transition_plan.md)
- [decisions.md](decisions.md)
- [logbook.md](logbook.md)
