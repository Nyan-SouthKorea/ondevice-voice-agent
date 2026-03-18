# Logbook

> 최근 작업만 유지한다. 이전 상세 로그는 `docs/archive/logbook_2026_03_full_before_refactor.md`에 보관한다.

## 2026-03-18 | Human + Codex | STT 기본 모델 확정 문서화와 TTS 다음 단계 정리

### Context

- 사용자가 현재 STT 최종 모델을 `WhisperTRT small nano safe`로 명확히 고정하고, 그 이유와 다음 우선순위가 TTS라는 점을 문서 전반에 반영하길 원했다.
- 동시에 이미 폐기한 AGX cross-device TRT 경로를 active 문서 기준에서 완전히 제외한 상태로 정리하길 원했다.

### Actions

- `README.md`, `docs/status.md`, `docs/project_overview.md`, `docs/decisions.md`, `docs/jetson_transition_plan.md`, `stt/README.md`, `tts/README.md`를 현재 기준으로 다시 맞췄다.
- STT 기본 온디바이스 모델은 `WhisperTRT small nano safe`로 고정하고, 선택 이유를 `Jetson 직접 생성 safe 경로`, `온디바이스 정확도 우위`, `실사용 가능한 지연 시간` 기준으로 정리했다.
- STT 단독 GUI 기본 선택과 `STTTranscriber(model="whisper_trt")` 기본 checkpoint도 `small nano safe` 기준으로 맞췄다.
- TTS는 `OpenAI Audio Speech API` 최소 경로 이후 다음 집중 모듈이 `MeloTTS` Jetson 검증이라는 점을 상위 문서에 반영했다.

### Next

- Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
- 필요하면 `TTSSynthesizer`에 온디바이스 backend, playback, cache를 순서대로 붙인다.

## 2026-03-18 | Human + Codex | A100 워크스페이스 평탄화와 운영 정책 정리

### Context

- 사용자가 A100 기준 워크스페이스를 `project/` 한 단계 없이 `repo / env / secrets` sibling 구조로 단순화하길 원했다.
- 동시에 코드와 문서에 남아 있던 예전 경로를 모두 정리하고, 현재 운영 정책을 중복 없이 기준 문서에 반영하길 원했다.

### Actions

- 로컬 워크스페이스를 `repo / env / secrets` 기준으로 평탄화하고, A100 쪽 `env` 내부의 Jetson 가상환경은 비웠다.
- `stt`/`tts`가 리포 바깥 `../secrets/`를 기준으로 동작하도록 경로 해석과 오류 메시지를 정리했다.
- active 문서와 설정 파일에서 예전 상위 단계 경로 표현을 현재 워크스페이스 구조 기준으로 갱신했다.
- 운영 정책은 `README.md`, `docs/README.md`, `docs/개발방침.md`, `docs/decisions.md`, `docs/status.md`에 역할별로 나눠 반영하고, 모듈 문서와 연구 문서는 경로 예시만 맞췄다.

### Next

- A100에서 실제로 사용할 새 로컬 env 이름 규칙을 정한다.
- Jetson에서는 같은 repo branch를 기준으로 적용/검증만 수행하는 흐름을 유지한다.

## 2026-03-17 | Human + Codex | Wake Word + VAD + STT 통합 GUI 데모와 스크린샷 문서화

### Context

- 사용자가 wake word, VAD, STT를 한 화면에서 확인할 수 있는 통합 GUI 데모를 먼저 구현하길 원했다.
- 이후 데모 스크린샷 4장을 문서 자산으로 포함해, 단계별 동작을 보기 좋게 설명하길 원했다.

### Actions

- `voice_pipeline_gui_demo.py`를 추가해 `Wake Word 대기 -> 듣는 중 -> STT 처리 중 -> 출력 완료` 단계를 하나의 GUI로 연결했다.
- 통합 GUI는 `stt_trt_experiment` env를 기준으로 실행하고, Jetson ORT는 `.pth` 브리지로 재사용하게 맞췄다.
- 스크린샷 4장을 `docs/assets/screenshots/stt/` 아래로 옮기고, `stt/README.md`에 통합 GUI 설명과 화면 예시를 추가했다.
- STT 통합 GUI 시연 MP4 2개를 `docs/assets/videos/jetson_demos/` 아래로 정리하고, GIF 썸네일을 생성해 `stt/README.md`에서 클릭 가능한 형태로 연결했다.
- 현재 상태와 다음 작업은 `docs/status.md`에서 통합 GUI 기준으로 짧게 갱신했다.

### Next

- 실제 마이크 조건에서 통합 GUI의 wake threshold, VAD 종료 타이밍, STT 모델 기본값을 점검한다.
- 사용성 검증 후 SDK형 orchestrator 리팩토링이 필요한지 별도로 판단한다.

## 2026-03-17 | Human + Codex | STT GUI 6모델 선택지와 2모델 비교 제한 반영

### Context

- 사용자가 STT GUI에서 최종 6개 모델을 모두 선택할 수 있게 하되, 메모리 문제로 전체 동시 비교는 막고 최대 2개만 비교하길 원했다.

### Actions

- `stt/tools/stt_gui_demo.py`의 모델 선택지에 `small nano safe`, `small agx cross-device`를 포함해 6개 모델 구성을 맞췄다.
- 비교 모드는 `전체 비교` 대신 `선택 모델 비교`로 바꾸고, 최대 2개까지만 체크되도록 제한했다.
- 비교 대상이 아닌 모델은 메모리에 상주시켜 두지 않고, 임시 로드한 비교 모델은 실행 후 바로 `close()`와 `gc.collect()`로 정리하게 했다.
- 전사 결과 텍스트 영역 폰트를 줄여, 다중 비교 시 한 화면에 더 많은 텍스트가 보이도록 조정했다.

### Next

- STT GUI의 선택 모델 비교 UX를 실제 시연 기준으로 한 번 더 점검한다.
- 이후 wake word + VAD + STT 통합 GUI에 같은 선택 구조를 재사용한다.

## 2026-03-17 | Human + Codex | 문서 중복 정리와 TRT 시행착오 산출물 정리

### Context

- 사용자가 상세 내역을 중복되지 않게 다시 정리하고, `docs/README.md` 기준으로 문서 전반을 보완하길 원했다.
- 동시에 프로젝트 재현에 필요 없는 대용량 TRT 시행착오 산출물은 문서 기록만 남기고 삭제하길 원했다.

### Actions

- `docs/README.md`에 문서 수정 체크리스트와 산출물 정리 규칙을 추가했다.
- `docs/status.md`는 현재 기준만 남기도록 줄이고, STT 기본 후보와 TRT 대안 경로를 최신 상태로 맞췄다.
- `stt/README.md`는 STT 구조, 실행 방법, 모델 자산 역할 중심으로 정리하고 상위 상태 설명 중복을 줄였다.
- AGX Orin 교차 장치 `small` 경로는 checkpoint 상시 보관 대신 문서 기준만 유지하는 방향으로 정리했다.
- `results/` 아래 TRT 시행착오 산출물은 재현에 필요 없는 항목부터 삭제했다.

### Next

- `small nano safe` 기준 50문장 benchmark를 다시 수행할지 판단한다.
- STT 단독 GUI 데모를 먼저 보완하고, 이후 wake word + VAD + STT 통합 데모로 확장한다.

## 2026-03-17 | Human + Codex | STT 6모델 50문장 최종 비교 아카이브

### Context

- 사용자가 `tiny-cuda`, `base-cuda`, `base-trt`, `small-trt-safe`, `small-trt-unsafe`, `api` 6개 경로를 같은 50문장 세트로 다시 비교해 한눈에 볼 수 있게 정리하길 원했다.

### Actions

- `stt/tools/stt_benchmark.py`에 config file, variant, label, checkpoint 경로를 설정별로 받을 수 있게 추가했다.
- 같은 스크립트에서 모델별 자원 정리와 실패 summary 기록을 넣어, 한 경로가 실패해도 전체 실행이 끊기지 않게 했다.
- AGX Orin의 `small` checkpoint를 다시 가져와 `whisper_trt_small_ko_ctx64_fp16e_fp32w_agx_cross_device` 경로를 복원했다.
- `small nano safe`는 혼합 배치 실행에서 allocator assert가 나와, fresh process 단독 재실행 결과를 최종 6모델 세트에 합쳤다.
- 최종 아카이브를 `stt/eval_results/korean_eval_50/20260317_172300_six_model_final/`에 정리하고, 사람이 읽는 요약을 `docs/reports/stt_korean_eval50_six_model_overview.md`로 승격했다.

### Next

- 이 6모델 비교 결과를 기준으로 STT 기본값과 TRT 대안 경로를 다시 정리한다.
- 상위 wake word + VAD + STT 통합 데모에서 어떤 STT 조합을 기본 선택지로 둘지 결정한다.

## 2026-03-17 | Human + Codex | AGX Orin TRT handoff 문서화

### Context

- 사용자가 AGX Orin 장비에 SSH로 접속해, 현재 Jetson 기준 실험 내용을 그대로 참고하면서 WhisperTRT 빌드를 다시 시도하려고 했다.
- 장비가 바뀌면 JetPack, TensorRT, 메모리, power mode 차이 때문에 기존 Nano 기준 값만으로는 반복 재현성이 떨어질 수 있었다.

### Actions

- `stt/experiments/stt_trt_collect_jetson_profile.py`를 추가해 Jetson 장비 프로파일을 JSON으로 저장할 수 있게 했다.
- `docs/envs/jetson/stt_trt_agx_orin_experiment.md`를 추가해 AGX Orin에서 Codex가 따라야 할 순서와 빌드/검증 기준을 정리했다.
- `docs/envs/stt_trt_experiment_env.md`, `docs/jetson_transition_plan.md`, `stt/README.md`, `stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/README.md`에 새 handoff 경로를 연결했다.

### Next

- AGX Orin에서 먼저 장비 프로파일을 저장한다.
- 저장된 프로파일을 기준으로 `workspace`, `max_text_ctx`, chunk 크기를 조정해 TRT build를 재시도한다.

## 2026-03-17 | Human + Codex | WhisperTRT small 모델 정리

### Context

- 사용자가 `WhisperTRT small`을 실제 운용 가능한 형태로 정리하길 원했다.
- 문서에는 시행착오 자체보다, 실제 사용 가능한 모델 기준만 남기길 원했다.

### Actions

- `stt/experiments/stt_trt_builder_experiment.py`에서 encoder build 경로를 정리해, 필요한 encoder 조각만 GPU에 올리도록 수정했다.
- 그 결과 `WhisperTRT small`을 아래 두 기준으로 정리했다.
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_nano_safe`
    - Jetson Orin Nano 기준 safe 모델
    - GPU 메모리 부족 이슈를 피하기 위해 `decoder chunk 2`, `encoder chunk 1`, `workspace 64MB` 기준으로 생성
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_agx_cross_device`
    - AGX Orin에서 빌드한 교차 장치 확인용 모델
    - Nano에서 로드될 수 있지만 cross-device TensorRT 경고가 날 수 있음
- 기존 base 모델도 `whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy`로 이름을 바꿔 fp 형식을 드러내도록 정리했다.

### Next

- `nano_safe` small 모델을 기준으로 50문장 benchmark를 다시 수행한다.
- STT GUI와 상위 데모에서 사용할 기본 TRT 경로를 필요 시 `small nano safe`로 확장한다.

## 2026-03-17 | Human + Codex | STT GUI 데모 1차 구현 시작

### Context

- wake word / VAD / STT 통합 데모로 바로 가기 전에, STT 단독 GUI에서 녹음과 모델 전환 UX를 먼저 확인하기로 했다.

### Actions

- `docs/reports/stt_demo_plan.md`에 STT GUI 데모와 통합 GUI 데모의 2단계 계획을 정리했다.
- `whisper base fp16e_fp16w (trt, legacy)`를 STT 백엔드로 직접 부를 수 있도록 `stt_whisper_trt.py`를 추가했다.
- `tools/stt_gui_demo.py`를 추가해 `녹음 시작 / 정지`, 백그라운드 모델 로딩, 전사 히스토리, API 경고/호출 횟수 표시를 넣었다.
- 하나의 녹음에 대해 `tiny / base(cuda) / base(trt) / api`를 모두 순차 실행하는 전체 비교 모드도 추가했다.

### Next

- STT GUI 데모를 직접 시연한 뒤 UI와 파라미터 보완점을 반영한다.
- 그 다음 wake word + VAD + STT 통합 GUI 데모로 확장한다.

## 2026-03-17 | Human + Codex | STT 50문장 최종 비교 재실행

### Context

- STT 기본 경로를 정하기 전에 `API / whisper tiny(cuda) / whisper base(cuda) / whisper base(TRT)`를 같은 50문장 세트로 다시 비교할 필요가 있었다.

### Actions

- `stt/datasets/korean_eval_50/` 기준으로 네 경로를 다시 실행했다.
- TRT는 `stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/whisper_trt_split.pth`를 직접 읽어 평가했다.
- code-generated summary 기준 수치를 `stt/README.md`의 최종 비교 표에 반영했다.

### Next

- STT 기본값을 실제 음성 에이전트 파이프라인에 붙일 때는 `정확도 우선 / 속도 우선` 기준을 한 번 더 정리한다.

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
