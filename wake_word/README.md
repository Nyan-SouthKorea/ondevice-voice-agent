# Wake Word

이 디렉토리는 `하이 포포` 한국어 wake word 프로젝트의 실제 구현 영역이다.  
현재 이 리포에서 가장 많이 진행된 하위 프로젝트이며, 데이터 준비부터 feature extraction, 학습, 평가, Jetson 배포 준비까지 이 디렉토리 아래에서 관리한다.

## 목표

- 호출어 `하이 포포`를 안정적으로 감지하는 경량 wake word 모델을 만든다.
- Linux 서버(A100)에서 학습하고 Jetson Orin Nano에서 ONNX 기반으로 실시간 추론한다.
- 실제 사용 환경에서 background 오탐과 호출어 미탐을 동시에 관리할 수 있는 수준까지 검증한다.

## 현재 상태

- positive 데이터 준비 완료
  - clean augmentation 완료
  - background mixed augmentation 완료
- negative 데이터 준비 완료
  - `AI Hub + MUSAN + FSD50K`
- feature extraction 완료
- baseline 학습 완료
- grid search 완료
- full-data 최종 학습 완료
- 다음 단계
  - ONNX export
  - Jetson 실시간 추론 및 GUI 검증

## 현재 best 모델

- run: `final_full_best_trial40`
- artifact 설명:
  - [`models/hi_popo/README.md`](models/hi_popo/README.md)
- checkpoint 경로:
  - `models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`
- 파라미터:
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`

검증 결과:

- positive-only recall: `1177 / 1181 = 0.9966`
- negative-only false positive rate: `128 / 11250 = 0.0114`
- threshold: `0.80`

해석:

- 학습 파이프라인 기준으로는 매우 강한 후보다.
- 다만 이 수치는 held-out validation 기준이다.
- 실제 배치 성능은 Jetson 실기와 연속 배경 오디오 기준으로 다시 확인해야 한다.

## 구현 흐름

이 프로젝트는 openWakeWord의 구조를 참고하되, 데이터 파이프라인과 운영 방식은 이 리포에 맞게 별도로 정리했다.

1. positive 생성
2. positive augmentation
3. negative 준비
4. feature extraction
5. classifier 학습
6. 평가
7. ONNX export
8. Jetson 추론 검증

## 디렉토리 구조

```text
wake_word/
├── README.md                 # 이 문서
├── train/                    # 학습/평가 스크립트
├── models/                   # 모델 아카이브
├── examples/                 # 공개 가능한 소량 샘플
├── wake_word.py              # 추론 모듈
├── wake_word_demo.py         # 데모 진입점
└── openWakeWord/             # 참고용 upstream clone (공개 리포에는 제외)
```

### `train/`

학습 파이프라인 스크립트를 단계별로 관리한다.

- [`train/01_generate_positive.py`](train/01_generate_positive.py)
- [`train/02_augment.py`](train/02_augment.py)
- [`train/02b_mix_background.py`](train/02b_mix_background.py)
- [`train/03_prepare_negative.py`](train/03_prepare_negative.py)
- [`train/04_extract_features.py`](train/04_extract_features.py)
- [`train/05_train.py`](train/05_train.py)
- [`train/05b_search.py`](train/05b_search.py)
- [`train/05c_evaluate.py`](train/05c_evaluate.py)
- `06_export_onnx.py` 예정

### `models/`

모델과 실험 결과를 run 단위로 보관한다.

- [`models/hi_popo/README.md`](models/hi_popo/README.md)
- `runs/<run_name>/`
- `hi_popo_classifier.pt`
- `hi_popo_training_history.json`
- `hi_popo_latest_run.json`

### `examples/`

공개 저장소에 포함 가능한 소량 샘플만 관리한다.

- [`examples/README.md`](examples/README.md)
- [`examples/audio_samples/README.md`](examples/audio_samples/README.md)

## 데이터 전략 요약

### Positive

- wake word: `하이 포포`
- synthetic TTS 기반 생성
- clean 증강과 background mixed 증강을 분리

현재 수량:

- clean: `11,250`
- mixed_noise: `281`
- mixed_speech: `281`

### Negative

최종 기준:

- AI Hub 자유대화 음성
- MUSAN
- FSD50K

최종 수량:

- `negative/musan`: `20,000`
- `negative/fsd50k`: `20,000`
- `negative/aihub_free_conversation`: `72,500`

### Feature

추출된 feature shape:

- positive train: `(10631, 28, 96)`
- positive test: `(1181, 28, 96)`
- negative train: `(101250, 28, 96)`
- negative test: `(11250, 28, 96)`

## 평가 관점

현재 코드에서 보고 있는 핵심 값은 아래 두 가지다.

- positive-only recall
- negative-only false positive rate

즉 아래 질문에 직접 대응한다.

- `하이 포포`를 불렀을 때 얼마나 잘 알아듣는가?
- background에서 얼마나 오탐이 나는가?

다만 현재 평가는 clip-level held-out validation 기준이다.  
실제 배치 관점에서는 아래가 추가로 필요하다.

- false accepts per hour
- 연속 오디오 기반 false positive 측정
- 실제 마이크 조건에서의 false reject 측정

## 다음 작업

1. `06_export_onnx.py` 구현
2. 현재 best 모델 ONNX export
3. Jetson 실시간 추론 래퍼 구현
4. score / threshold / detection 상태를 보여주는 GUI 데모 구현
5. 실제 마이크 연결 후 `하이 포포` 감지와 background 오탐 검증

## 관련 문서

- [`../docs/project_overview.md`](../docs/project_overview.md)
- [`../docs/status.md`](../docs/status.md)
- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/research/wake_word.md`](../docs/research/wake_word.md)
- [`../docs/jetson_transition_plan.md`](../docs/jetson_transition_plan.md)
