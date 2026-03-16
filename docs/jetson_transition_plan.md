# Jetson Transition Plan

> 마지막 업데이트: 2026-03-16

## 1. 이 문서의 목적

이 문서는 Linux 서버(A100) 단계에서 완료된 wake word 학습 결과와, 현재 Jetson에서 완료된 wake word/VAD 요소기술 구현을 바탕으로,  
다음 작업을 Jetson Orin Nano Developer Kit에서 바로 이어서 진행할 수 있도록 만드는 handoff 문서다.

이 문서를 보면 아래를 바로 이해할 수 있어야 한다.

- 지금까지 서버와 Jetson에서 무엇이 끝났는지
- 어떤 모델과 모듈을 Jetson 기준으로 쓸지
- Jetson에서 무엇부터 연동하고 검증해야 하는지
- 어떤 순서로 테스트하고, 어떤 기준으로 성공/실패를 판단할지

## 2. 현재 서버 단계 요약

현재 wake word 학습 파이프라인은 아래까지 완료됐다.

- positive / negative 데이터셋 준비 완료
- feature 추출 완료
- baseline 학습 완료
- grid search 완료
- best parameter 선정 완료
- full-data final training 완료
- positive-only / negative-only 분리 평가 완료
- classifier ONNX export 완료
- classifier ONNX wrapper / CLI sample 준비 완료
- Jetson GUI demo 완료
- feature backbone 로컬 구현 전환 완료
- Jetson 학습 smoke 검증 완료

현재 VAD도 요소기술 기준으로 아래까지 완료됐다.

- `vad/detector.py` 공통 진입점 구현 완료
- `webrtcvad` / `Silero VAD ONNX` dual backend 구현 완료
- 기본 backend를 `silero`로 확정
- 기본 마이크 demo 검증 완료

현재 Jetson 이관 후보 모델은 아래 run이다.

- run name: `final_full_best_trial40`
- checkpoint:
  - `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`
- exported ONNX:
  - `wake_word/models/hi_popo/hi_popo_classifier.onnx`
- exported metadata:
  - `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`

현재 기록된 핵심 성능:

- positive-only recall: `1177 / 1181 = 0.9966`
- negative-only false positive rate: `128 / 11250 = 0.0114`
- negative-only specificity: `11122 / 11250 = 0.9886`
- stored threshold: `0.80`

중요한 해석:

- 이 수치는 현재 파이프라인 기준으로 매우 좋다.
- 하지만 아직 연속 오디오 기준 실배치 검증은 하지 않았다.
- 따라서 Jetson 단계에서는 먼저 `실시간 추론 + GUI 확인 + 실제 마이크 테스트`가 우선이다.

## 3. Jetson 단계에서의 목표

Jetson 단계의 현재 목표는 아래처럼 정리된다.

1. export된 classifier ONNX와 metadata를 Jetson에서 계속 재현 가능하게 유지한다.
2. Jetson에서 실시간 GUI demo를 기준으로 score, detection, timing을 즉시 확인한다.
3. 실제 환경에서 `하이 포포` 호출 성능과 배경 오탐을 직접 확인한다.
4. threshold와 input gain 기본값을 현장 기준으로 확정한다.
5. wake word 감지 뒤에 VAD를 연결해 STT 입력 전 구간 절단 기준을 정리한다.

즉, 지금 단계의 목적은 “이미 구현된 wake word/VAD 요소기술을 실기 기준으로 정리하고, 둘을 연결할 준비를 마무리하는 것”이다.

## 4. Jetson으로 넘어갈 때 기준 모델과 산출물

Jetson 단계에서 우선 기준으로 삼을 파일은 아래다.

### 반드시 참조할 파일

- 모델 checkpoint
  - `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`
- latest classifier ONNX
  - `wake_word/models/hi_popo/hi_popo_classifier.onnx`
- latest export metadata
  - `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`
- run metadata
  - `wake_word/models/hi_popo/runs/final_full_best_trial40/run_metadata.json`
- training history
  - `wake_word/models/hi_popo/runs/final_full_best_trial40/training_history.json`

### 참고용 문서

- `docs/project_overview.md`
- `docs/status.md`
- `docs/envs/jetson_wake_word_env.md`
- `docs/decisions.md`
- `docs/logbook.md`
- `docs/개발방침.md`

## 5. Jetson 단계의 현재 완료 항목과 남은 일

Jetson 단계에서는 wake word와 VAD의 핵심 구현이 이미 끝났고, 현재는 검증, 조정, 두 모듈의 연동이 남아 있다.

### 5-1. ONNX export와 런타임 검증

ONNX export 자체는 이미 끝났고, Jetson runtime 환경 검증도 완료됐다.

현재 준비된 파일:

- `wake_word/train/06_export_onnx.py`
- `wake_word/models/hi_popo/hi_popo_classifier.onnx`
- `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`
- `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.onnx`
- `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier_onnx.json`

현재 완료 상태:

- ONNX와 metadata가 Jetson 작업 기준 산출물로 정리돼 있다
- Jetson 쪽 Python 환경에서 `onnxruntime-gpu` 로딩을 확인했다
- `wake_word/train/check_onnx_gpu.py` 결과 `GPU_OK`를 확인했다
- metadata의 threshold와 input shape도 현재 기준과 일치한다

### 5-2. Jetson 추론 래퍼 구현

현재 `wake_word/detector.py`는 실시간 추론 래퍼로 구현돼 있다.

목표 파일:

- `wake_word/detector.py`

최소 역할:

- classifier ONNX 로드
- `(16, 96)` window와 `(T, 96)` clip feature 입력 처리
- ONNX 추론 실행
- wake word score 계산
- threshold 초과 시 detection 상태 반환

현재 추가로 이미 붙은 역할:

- 마이크 입력 수집
- raw audio를 Google Speech Embedding feature로 변환
- 변환된 feature를 classifier ONNX 래퍼에 전달

즉 `raw audio -> feature extractor -> classifier ONNX` 연결은 이미 끝났고, 남은 핵심은 실기 데이터로 tuning하는 것이다.

현재 ONNX 체인은 아래처럼 구성된다.

- `melspectrogram.onnx`
- `embedding_model.onnx`
- `hi_popo_classifier.onnx`

### 5-3. 실시간 GUI 데모 구현

현재 `wake_word/wake_word_demo.py`는 export된 ONNX를 feature `.npy` 입력으로 테스트하는 CLI 예제다.
추가로 `wake_word/wake_word_gui_demo.py`는 마이크 기반 실시간 GUI demo로 구현됐다.

목표 파일:

- `wake_word/wake_word_demo.py`
- `wake_word/wake_word_gui_demo.py`

GUI에서 최소한 보여야 하는 요소:

- 현재 score
- 현재 threshold
- `DETECTED / IDLE` 상태
- 최근 감지 시각
- 최근 몇 초간의 score 변화
- 마이크 입력 레벨
- `melspectrogram / embedding / classifier` ONNX 실행 시간
- 입력 chunk 길이와 classifier window 길이

현재 GUI demo는 위 목적을 넘어서 아래까지 지원한다.

- 1초 유지 감지 램프
- 3초 유지 최고점 표시
- 마이크 입력 레벨 조절 슬라이더
- `tegrastats` 기반 CPU / RAM / GPU 텍스트

이제 남은 핵심은 실제 환경에서 score 분포를 보고 threshold와 input gain을 같이 조정하는 것이다.

### 5-4. VAD 모듈 구현

현재 `vad/detector.py`는 공통 VAD 진입점으로 구현돼 있다.

목표 파일:

- `vad/detector.py`
- `vad/model_silero.py`
- `vad/model_webrtcvad.py`
- `vad/vad_demo.py`

현재 완료 상태:

- `infer(audio_chunk) -> bool` 공통 사용 방식 정리 완료
- 기본 backend를 `silero`로 확정
- 최소 filtering 적용 완료
  - `min_speech_frames=3`
  - `min_silence_frames=10`
- 기본 마이크에서 `status / level / conf` 기준 terminal demo 확인 완료

이제 남은 핵심은 wake word 뒤에 VAD를 붙여 실제 utterance segmentation 기준을 만드는 것이다.

## 6. Jetson 실기 검증 계획

Jetson에서 GUI까지 붙으면 아래 순서로 검증한다.

### 6-1. Positive 검증

목적:

- `하이 포포`를 불렀을 때 실제로 잘 감지되는지 확인

초기 체크:

- 조용한 환경에서 20회
- 보통 말하기 크기로 20회
- 약하게 말하기 20회
- 조금 멀리 떨어진 거리에서 20회

확인 포인트:

- score가 threshold를 넘는지
- detection latency가 너무 느리지 않은지
- 반복 호출 시 놓치는 패턴이 있는지

### 6-2. Negative 검증

목적:

- 배경에서 false positive가 얼마나 나는지 확인

초기 체크:

- 아무 말 없는 idle 상태 10~30분
- TV/유튜브/음악 재생 상태
- 주변 대화가 있는 상태
- 한국어 일반 대화가 들어오는 상태

확인 포인트:

- 오탐이 나는 상황이 무엇인지
- 특정 화자나 특정 음절에서 score가 튀는지
- threshold를 조금 올리거나 내려야 하는지

### 6-3. GUI 기반 즉시 판단

GUI를 보는 동안 아래를 바로 판단할 수 있어야 한다.

- positive에서 score peak가 충분한가
- background에서 baseline score가 얼마나 안정적인가
- threshold `0.80`이 너무 높거나 낮지 않은가

### 6-4. Threshold 설정 기준

처음에는 `0.80`을 기준값으로 두고 아래 순서로 본다.

1. positive 테스트를 여러 조건에서 20회 이상 반복해, 호출 시 peak score가 어디까지 오르는지 확인한다.
2. idle/background를 10~30분 이상 틀어두고, false positive 없이 score가 어디까지 튀는지 본다.
3. background 최고점보다 충분히 위이면서, positive 최저 peak보다 충분히 아래인 구간에 threshold를 둔다.

실무적으로는 아래처럼 판단하면 된다.

- positive 최저 peak가 `0.90` 근처인데 background 최고점이 `0.35`라면 `0.75~0.85` 범위가 안전하다.
- positive와 background score가 많이 겹치면 threshold만 만지지 말고, 실패 음성을 모아 데이터 보강이나 재학습으로 돌아간다.

## 7. Jetson 단계에서 당장 하지 않을 일

아래는 Jetson 현재 단계에서 바로 하지 않는다.

- 새 학습 파이프라인 확장
- 추가 grid search
- backbone 교체
- STT/LLM/TTS 통합
- 구조 변경을 동반한 재학습

이유:

- 지금 단계에서는 STT 이후 확장보다 wake word/VAD의 실시간 동작과 배치 감각을 먼저 보는 것이 중요하다.
- 실기 테스트 없이 다시 학습으로 돌아가면 조정 방향이 흐려진다.

## 8. Jetson 단계의 성공 기준

초기 성공 기준은 대부분 달성됐고, 남은 검증 기준은 아래다.

- ONNX 모델이 Jetson에서 정상 로드된다.
- feature extractor와 classifier ONNX가 연결되어, 마이크 입력이 끊기지 않고 실시간 score가 나온다.
- `하이 포포` 호출 시 GUI에서 명확한 score 상승과 detection이 보인다.
- idle/background에서 오탐 패턴을 확인할 수 있다.
- threshold와 input gain 기본값을 실기 기준으로 판단할 수 있다.
- VAD가 기본 마이크 기준으로 안정적으로 `status`를 내보낸다.
- wake word 뒤에 VAD를 연결할 때 구간 절단 기준을 설명할 수 있다.

즉, 이 단계의 성공은 “제품 수준 완료”가 아니라  
“실시간 데모가 가능하고, 다음 개선 방향이 명확해지는 것”이다.

## 9. Jetson 단계 이후 다음 분기

Jetson 실기 검증이 끝난 뒤 분기는 두 가지다.

### 경우 1. 성능이 충분히 좋다

- 현재 threshold를 기준값으로 채택
- wake word와 VAD를 연결해 상위 음성 에이전트 파이프라인의 첫 입력 모듈로 정리
- 이후 STT/LLM/TTS로 확장

### 경우 2. 실기에서 오탐 또는 미탐이 많다

- 어떤 상황에서 문제가 나는지 먼저 정리
- threshold 조정으로 해결 가능한지 확인
- 안 되면 데이터 보강 또는 재학습 사이클 재진입

## 10. 새 세션 시작 시 읽을 문서

Jetson 단계에서 새 세션을 시작하면 아래 순서로 읽는다.

1. `docs/jetson_transition_plan.md`
2. `docs/envs/jetson_wake_word_env.md`
3. `docs/status.md`
4. `docs/project_overview.md`
5. `docs/decisions.md`
6. `docs/logbook.md`

이 순서를 따르면 현재 기준, 과거 결정, 실제 작업 흐름을 짧은 시간 안에 복구할 수 있다.
