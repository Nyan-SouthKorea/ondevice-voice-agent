# Wake Word

이 디렉토리는 `하이 포포` wake word 모델의 데이터 준비, feature 추출, 학습, 평가, 추론 이관 작업을 담당한다.

## 현재 상태

- 데이터 준비 완료
  - positive clean / mixed augmentation 완료
  - negative: `AI Hub + MUSAN + FSD50K` 완료
- feature 추출 완료
- baseline 학습 완료
- grid search 완료
- full-data final training 완료
- positive-only / negative-only 분리 평가 완료
- 다음 단계: ONNX export, Jetson 실시간 추론, GUI 데모

## 현재 기준 모델

- run name: `final_full_best_trial40`
- checkpoint:
  - [`models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`](models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt)

핵심 지표:

- positive-only recall: `1177 / 1181 = 0.9966`
- negative-only false positive rate: `128 / 11250 = 0.0114`
- stored threshold: `0.80`

중요한 해석:

- 현재 지표는 held-out validation 기준으로 매우 좋다.
- 아직 연속 오디오 기준 실배치 평가는 남아 있다.

## 디렉토리 구조

```text
wake_word/
├── data/              # raw / augmented / negative / features
├── models/            # run artifacts and exported models
├── openWakeWord/      # reference repository for training flow
├── train/             # training and evaluation scripts
├── wake_word.py       # Jetson inference wrapper (to be implemented)
└── wake_word_demo.py  # Jetson GUI demo (to be implemented)
```

## 주요 스크립트

- [`train/01_generate_positive.py`](train/01_generate_positive.py)
- [`train/02_augment.py`](train/02_augment.py)
- [`train/02b_mix_background.py`](train/02b_mix_background.py)
- [`train/03_prepare_negative.py`](train/03_prepare_negative.py)
- [`train/04_extract_features.py`](train/04_extract_features.py)
- [`train/05_train.py`](train/05_train.py)
- [`train/05b_search.py`](train/05b_search.py)
- [`train/05c_evaluate.py`](train/05c_evaluate.py)

## 관련 문서

- [프로젝트 통합 개요](../docs/project_overview.md)
- [Wake Word 기술 배경](../docs/research/wake_word.md)
- [Negative 데이터 전략](../docs/research/negative_datasets.md)
- [Jetson 전환 계획](../docs/jetson_transition_plan.md)

## 다음 작업

1. `06_export_onnx.py` 구현
2. 현재 best checkpoint ONNX export
3. `wake_word.py` 실시간 추론 래퍼 구현
4. `wake_word_demo.py` GUI 데모 구현
5. Jetson에서 실제 마이크 기반 검증
