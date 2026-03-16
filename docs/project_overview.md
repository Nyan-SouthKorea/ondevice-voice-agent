# On-Device Voice Agent Project Overview

> 마지막 업데이트: 2026-03-16

## 1. 프로젝트 목적

이 프로젝트의 최종 목표는 케어 로봇용 온디바이스 음성 에이전트를 만드는 것이다.  
현재 1차 집중 범위는 wake word 시스템이며, 호출어 `하이 포포`를 안정적으로 감지하는 모델을 학습하고 평가하는 데 초점을 둔다.

프로젝트는 아래 순서로 확장된다.

1. Wake word
2. VAD
3. STT
4. LLM
5. TTS
6. Jetson 배포 및 통합

## 2. 개발 목표와 운영 철학

현재 사이클의 목표는 다음과 같다.

- Linux 서버(A100)에서 wake word 모델을 학습하고 평가한다.
- 실제 배치 후보로 볼 수 있는 수준까지 성능을 끌어올린다.
- 결과가 충분히 좋으면 Jetson Orin Nano Developer Kit으로 이관한다.
- Jetson 이관 이후에는 ONNX 추론 중심으로 개발을 이어간다.
- 최종적으로는 다른 개발자가 바로 활용할 수 있는 음성 에이전트 SDK 형태로 정리한다.

중요하게 보는 원칙은 다음과 같다.

- ONNX 우선
- 온디바이스 추론 고려
- 라이선스 리스크 관리
- 문서와 코드의 실시간 동기화
- Git 상태와 문서 상태의 동시 관리
- 장시간 실행 작업의 주기 로그 보장

세부 운영 원칙은 [개발방침.md](개발방침.md)에 정리한다.

## 3. 현재 시스템 범위

현재 실제로 구현과 실험이 진행된 영역은 wake word이다.

전체 목표 파이프라인은 아래와 같다.

```text
[Mic]
  -> [Wake Word]
  -> [VAD]
  -> [STT]
  -> [LLM]
  -> [TTS]
```

지금은 이 중 `Wake Word`를 먼저 완성하고, 이후 상위 음성 에이전트 스택으로 확장하는 전략이다.

## 3-1. 장기 아키텍처 목표: SDK형 음성 에이전트

이 프로젝트는 최종적으로 Jetson 안에서 재사용 가능한 음성 에이전트 SDK를 만드는 것을 목표로 한다.

즉, 목표는 단순히 아래를 각각 구현하는 데서 끝나지 않는다.

- wake word
- VAD
- STT
- LLM
- TTS

최종적으로는 위 요소기술을 하나의 일관된 인터페이스로 묶어서:

- 프론트엔드 개발자
- 백엔드 개발자
- 로봇 기능을 개발하는 동료 개발자

가 쉽게 붙여 쓸 수 있어야 한다.

이 SDK/플랫폼이 지원해야 하는 방향은 아래와 같다.

- 음성 파이프라인 공통 API 제공
- 이벤트/콜백/상태 기반 제어
- 모듈 교체 가능 구조
- 로봇 기능과의 손쉬운 연동

예상 연동 기능 예시:

- 안면 인식
- 표정 인식
- 특정 위치 이동
- 순찰 모드
- 기타 센서/행동 제어 로직

따라서 현재 wake word는 독립 PoC이면서 동시에, 이후 전체 음성 에이전트 SDK의 첫 모듈이라는 의미를 가진다.

## 4. 하드웨어와 환경

### 학습 환경

- 서버: Linux + NVIDIA A100 80GB
- Python: 3.10
- conda env: `wake_word`
- PyTorch: `2.7.1+cu118`
- CUDA: `11.8`

### 추론 환경

- Jetson Orin Nano Developer Kit 8GB
- Ubuntu 22.04
- ONNX Runtime GPU + TensorRT 기반 추론 예정

## 5. 기술 선택

### Wake word

- backbone: Google Speech Embedding
- framework reference: openWakeWord
- classifier: 경량 FC binary classifier
- export target: ONNX

### Positive 데이터

- 최종 wake word: `하이 포포`
- 원본 생성: Edge TTS 기반 synthetic positive + 실제 녹음 확장 가능
- clean 증강과 background mixed 증강을 분리 관리

### Negative 데이터

최종 기준은 아래 3종이다.

- AI Hub 자유대화 음성(일반남녀)
- MUSAN
- FSD50K

Common Voice KO는 초기 검토 대상이었지만 최종 기준에서는 제외했다.

## 6. 데이터 파이프라인

### 공통 negative 출력 스펙

세 negative 데이터셋은 모두 아래 포맷으로 통일했다.

- `16kHz`
- `mono`
- `WAV (PCM_16)`
- `3.0초 고정 길이`

### Positive 데이터 상태

- raw positive: `wake_word/data/hi_popo/positive/`
- clean augmentation: `wake_word/data/hi_popo/positive_aug/clean/`
- mixed noise augmentation: `wake_word/data/hi_popo/positive_aug/mixed_noise/`
- mixed speech augmentation: `wake_word/data/hi_popo/positive_aug/mixed_speech/`

현재 수량:

- `clean`: `11,250`
- `mixed_noise`: `281`
- `mixed_speech`: `281`

mixed 증강은 기존 clean 증강본이 아니라 원본 positive에서 직접 생성한다.

### Negative 데이터 상태

최종 생성 수량:

- `negative/musan`: `20,000`
- `negative/fsd50k`: `20,000`
- `negative/aihub_free_conversation`: `72,500`

총 negative 수량은 `112,500`이다.

## 7. Feature 추출

학습 전에는 Google Speech Embedding feature를 사전 추출한다.

생성된 feature shape:

- positive train: `(10631, 28, 96)`
- positive test: `(1181, 28, 96)`
- negative train: `(101250, 28, 96)`
- negative test: `(11250, 28, 96)`

feature 추출 스크립트:

- [04_extract_features.py](../wake_word/train/04_extract_features.py)

중요한 환경 메모:

- 현재 서버에서는 `onnxruntime-gpu`의 CUDA provider가 실제 세션 생성에 실패한다.
- provider 목록에는 CUDA가 보이지만, 실제 smoke test 결과는 `GPU_FALLBACK`이었다.
- 원인은 현재 환경이 `PyTorch cu118` 기반인데, 설치한 `onnxruntime-gpu==1.23.2`가 CUDA 12 계열 라이브러리를 요구하는 점에 있다.
- 따라서 현재 feature 추출은 실질적으로 CPU 경로를 사용했다.

검사용 스크립트:

- [check_onnx_gpu.py](../wake_word/train/check_onnx_gpu.py)

## 8. 학습 파이프라인

현재 구현된 주요 스크립트:

- [01_generate_positive.py](../wake_word/train/01_generate_positive.py)
- [02_augment.py](../wake_word/train/02_augment.py)
- [02b_mix_background.py](../wake_word/train/02b_mix_background.py)
- [03_prepare_negative.py](../wake_word/train/03_prepare_negative.py)
- [04_extract_features.py](../wake_word/train/04_extract_features.py)
- [05_train.py](../wake_word/train/05_train.py)
- [05b_search.py](../wake_word/train/05b_search.py)
- [05c_evaluate.py](../wake_word/train/05c_evaluate.py)
- [06_export_onnx.py](../wake_word/train/06_export_onnx.py)

현재 추론 준비용 모듈:

- [detector.py](../wake_word/detector.py)
- [wake_word_demo.py](../wake_word/wake_word_demo.py)
- [wake_word_gui_demo.py](../wake_word/wake_word_gui_demo.py)

학습 산출물은 아래에 run 단위로 보관한다.

- `wake_word/models/hi_popo/runs/<run_name>/`

각 run에는 최소한 아래가 포함된다.

- checkpoint
- training history
- run metadata

현재 latest export 산출물:

- `wake_word/models/hi_popo/hi_popo_classifier.onnx`
- `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`

중요한 점:

- 현재 export 대상은 raw audio end-to-end 모델이 아니라 `classifier only` ONNX다.
- 즉 Jetson에서 실제 마이크 추론을 하려면 Google Speech Embedding feature 추출 단계를 함께 연결해야 한다.
- 현재 `detector.py`는 `(16, 96)` window와 `(T, 96)` clip feature 입력을 받아 ONNX classifier를 실행하는 래퍼다.
- 현재 실시간 GUI 데모는 `melspectrogram.onnx -> embedding_model.onnx -> hi_popo_classifier.onnx` 3단계 ONNX timing도 함께 보여준다.
- 현재 chunk 기준은 `1280 samples = 80 ms`, classifier window 기준은 `16 frames = 1.28 s`다.

## 9. 학습 결과 요약

### baseline_small

- train: positive `4,000`, negative `12,000`
- val: positive `500`, negative `2,000`
- epoch 5 기준:
  - `val_recall 0.9960`
  - `val_accuracy 0.9345`
  - `val_fp_rate 0.1270`
  - `threshold 0.30`

해석:

- 모델이 학습된다는 것은 확인
- false positive는 아직 높음

### baseline_medium

- train: positive `10,631`, negative `40,000`
- val: positive `1,181`, negative `5,000`
- best observed:
  - `val_recall 0.9907`
  - `val_accuracy 0.9664`
  - `val_fp_rate 0.0578`
  - `threshold 0.35`

해석:

- baseline으로 의미 있는 개선 확인
- grid search 전 기준 baseline으로 채택

### baseline_grid_v1

탐색 축:

- `lr`
- `negative_weight`
- `layer_dim`
- `n_blocks`

best trial:

- `baseline_grid_v1_trial40`
- `lr=0.0005`
- `negative_weight=5.0`
- `layer_dim=64`
- `n_blocks=2`
- `val_recall 0.9966`
- `val_accuracy 0.9855`
- `val_fp_rate 0.0256`
- `threshold 0.70`

해석:

- baseline_medium 대비 false positive가 크게 감소
- 최종 전체 학습 파라미터 후보로 채택

### final_full_best_trial40

실행 파라미터:

- `lr=0.0005`
- `negative_weight=5.0`
- `layer_dim=64`
- `n_blocks=2`
- `epochs=8`
- `batch_size=512`

train / val:

- train: positive `10,631`, negative `101,250`
- val: positive `1,181`, negative `11,250`

epoch 8 결과:

- `val_recall 0.9966`
- `val_accuracy 0.9926`
- `val_fp_rate 0.0114`
- `threshold 0.80`

해석:

- 현재까지의 best full-data training result
- 동일 파이프라인 기준으로는 매우 강한 결과
- 다만 이 수치는 clip-level validation 기준이며, 실제 배치 성능을 바로 보장하지는 않는다
- 저장된 checkpoint를 같은 threshold로 다시 평가하면:
  - positive-only recall: `1177 / 1181 = 0.9966`
  - negative-only false positive rate: `128 / 11250 = 0.0114`
  - negative-only specificity: `11122 / 11250 = 0.9886`

## 10. 현재 성능 해석에서 주의할 점

현재 evaluation 비율은 대략 positive:negative = `1:10`이다.

이 비율은 아래 목적에는 적합하다.

- 모델 간 비교
- 하이퍼파라미터 선택
- baseline 대비 개선 확인

다만 현재 `05_train.py`는 이름이 `test`인 split 파일을 사용해 best epoch와 threshold를 선택한다.
즉 지금 수치는 완전히 손대지 않은 final test라기보다 held-out validation에 가깝다.

하지만 실제 사용 환경은 연속 스트림의 대부분이 negative이므로, 아래 평가가 추가로 필요하다.

- false accepts per hour
- 연속 오디오 기준 false positive 측정
- noisy / mixed positive 기준 false reject 확인
- threshold 재탐색

즉 현재 모델은 `학습 관점에서는 매우 유망한 상태`지만, `실배치 검증 완료`로 보기는 아직 이르다.

## 11. Git과 공개 저장소 운영 기준

이 프로젝트는 코드와 문서는 Git으로 관리하되, 대용량 데이터와 모델 산출물은 제외한다.

현재 공개용 관리 방향:

- 포함:
  - 코드
  - 문서
  - 실행 스크립트
  - 직접 생성한 예시 TTS 샘플
- 제외:
  - `wake_word/data/`
  - `wake_word/models/`
  - `secrets/`
  - 외부 clone 저장소

샘플 공개는 third-party dataset 원본이 아니라 직접 생성한 TTS만 허용하는 보수적 기준을 사용한다.
공개용 샘플 경로는 `wake_word/examples/audio_samples/`를 사용한다.

## 12. 문서 운영 구조

이 프로젝트의 문서는 역할을 분리해 관리한다.

- 루트 `README.md`: 상위 프로젝트 진입점
- `wake_word/README.md`: wake word 서브프로젝트 진입점
- [project_overview.md](project_overview.md): 프로젝트 전체 이해용 통합 문서
- [개발방침.md](개발방침.md): 운영 원칙과 상위 기술 방침
- [status.md](status.md): 현재 최신 상태
- [decisions.md](decisions.md): 중요한 결정 이력
- [logbook.md](logbook.md): 실제 작업 로그

새 세션이 시작되더라도 위 문서만 읽으면 프로젝트 목적, 구현 상태, 남은 작업, 주의사항을 다시 파악할 수 있도록 유지한다.

## 13. 다음 단계

현재 우선순위는 아래와 같다.

1. export된 ONNX와 metadata를 Jetson으로 복사
2. Jetson에서 feature extractor + classifier ONNX + 마이크 입력을 연결
3. score / threshold / detection 상태를 즉시 확인할 수 있는 실시간 CLI/GUI를 붙인다
4. 연속 오디오 기준 false positive / false reject 평가와 threshold 점검을 진행한다
5. 성능이 충분하면 wake word 모듈을 상위 음성 에이전트 파이프라인에 연결한다
6. 이관 직전, 학습 환경과 개발 히스토리를 handoff 문서로 최종 정리한다

현재는 이관 계획을 별도 문서로 분리했다.

- [jetson_transition_plan.md](jetson_transition_plan.md)

이 문서는 Jetson 단계에서 바로 수행할 작업 순서, GUI 요구사항, 실기 검증 계획, 성공 기준을 정리한다.
