# Logbook

> 최근 작업만 유지한다. 이전 상세 로그는 `docs/archive/logbook_2026_03_full_before_refactor.md`에 보관한다.

## 2026-03-17 | Human + Codex | AGX Orin TRT handoff 문서화

### Context

- 사용자가 AGX Orin 장비에 SSH로 접속해, 현재 Jetson 기준 실험 내용을 그대로 참고하면서 WhisperTRT 빌드를 다시 시도하려고 했다.
- 장비가 바뀌면 JetPack, TensorRT, 메모리, power mode 차이 때문에 기존 Nano 기준 값만으로는 반복 재현성이 떨어질 수 있었다.

### Actions

- `stt/experiments/stt_trt_collect_jetson_profile.py`를 추가해 Jetson 장비 프로파일을 JSON으로 저장할 수 있게 했다.
- `docs/envs/jetson/stt_trt_agx_orin_experiment.md`를 추가해 AGX Orin에서 Codex가 따라야 할 순서와 빌드/검증 기준을 정리했다.
- `docs/envs/stt_trt_experiment_env.md`, `docs/jetson_transition_plan.md`, `stt/README.md`, `stt/models/whisper_trt_base_ko_ctx64/README.md`에 새 handoff 경로를 연결했다.

### Next

- AGX Orin에서 먼저 장비 프로파일을 저장한다.
- 저장된 프로파일을 기준으로 `workspace`, `max_text_ctx`, chunk 크기를 조정해 TRT build를 재시도한다.

## 2026-03-17 | Human + Codex | WhisperTRT small 장기 시도 진행 중

### Context

- 사용자가 다국어 `WhisperTRT small`을 Jetson에서 실제로 변환 성공할 때까지 체계적으로 계속 시도하길 원했다.
- 단일 decoder/encoder 빌드로는 `small`이 메모리와 allocator 문제로 통과하지 못했다.

### Actions

- `stt/experiments/stt_trt_builder_experiment.py`를 확장해 `decoder_chunk_size`, `encoder_chunk_size`를 받아 block 단위 chunk 빌드를 지원하도록 바꿨다.
- ONNX export 단계의 메모리 피크를 줄이기 위해 `torch.onnx.export(do_constant_folding=False)`와 ONNX graph folding 비활성 경로를 추가했다.
- 그 결과 `small ko / ctx64 / ws64MB`에서 다음을 확인했다.
  - `decoder 2-block chunk`는 전체 6개 chunk를 모두 저장하고 checkpoint/load-check까지 통과했다.
  - 다만 이 checkpoint는 50문장 benchmark에서 모든 예측이 `[�]`로 나와, 속도는 확보됐지만 전사 품질은 실패했다.
  - 추가 진단 결과 `decoder 2-block` 경로는 첫 decoder chunk 출력부터 `NaN`으로 무너졌다.
- 그래서 현재는 `decoder 1-block` 경로로 다시 시도 중이며, decoder 전체 12개 chunk는 실제로 저장까지 성공한 상태다.
- 이어서 encoder도 `6-block`, 필요 시 `3-block`까지 더 잘게 나눠 재시도하고 있다.

### Next

- `decoder 1-block` + 더 작은 encoder chunk 조합으로 checkpoint 생성과 load-check를 다시 끝낸다.
- 그 다음 1~3번 smoke로 `[�]` 문제가 사라졌는지 확인한다.
- smoke가 정상일 때만 50문장 benchmark를 다시 돌린다.

## 2026-03-17 | Human + Codex | STT GUI 데모 1차 구현 시작

### Context

- wake word / VAD / STT 통합 데모로 바로 가기 전에, STT 단독 GUI에서 녹음과 모델 전환 UX를 먼저 확인하기로 했다.

### Actions

- `docs/reports/stt_demo_plan.md`에 STT GUI 데모와 통합 GUI 데모의 2단계 계획을 정리했다.
- `whisper base (trt)`를 STT 백엔드로 직접 부를 수 있도록 `stt_whisper_trt.py`를 추가했다.
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
- TRT는 `stt/models/whisper_trt_base_ko_ctx64/whisper_trt_split.pth`를 직접 읽어 평가했다.
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
