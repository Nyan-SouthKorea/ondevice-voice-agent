# Status

> 마지막 업데이트: 2026-03-13

## 현재 목표

- `하이 포포` wake word 모델을 Jetson Orin Nano Developer Kit에서 실시간으로 검증한다.
- ONNX 추론 경로와 GUI 데모를 먼저 완성한다.
- 실기 결과를 보고 threshold 조정 또는 재학습 필요 여부를 판단한다.

## 현재 최종 기준

- wake word: `하이 포포`
- negative 데이터 최종 기준: `AI Hub + MUSAN + FSD50K`
- mixed positive 증강: 원본 positive 기반
- 학습 환경: Linux 서버 + A100
- 추론 타깃: Jetson Orin Nano Developer Kit 8GB

## 현재 상태

- negative 데이터셋 3종 준비 완료
  - `negative/musan`: `20,000`
  - `negative/fsd50k`: `20,000`
  - `negative/aihub_free_conversation`: `72,500`
- positive 증강 구조 정리 완료
  - `clean`: `11,250`
  - `mixed_noise`: `281`
  - `mixed_speech`: `281`
- feature 추출 완료
  - `positive_features_train.npy`: `(10631, 28, 96)`
  - `positive_features_test.npy`: `(1181, 28, 96)`
  - `negative_features_train.npy`: `(101250, 28, 96)`
  - `negative_features_test.npy`: `(11250, 28, 96)`
- baseline 학습과 grid search 완료
- 현재 best full-data run은 `final_full_best_trial40`
  - run dir: `wake_word/models/hi_popo/runs/final_full_best_trial40`
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`
  - epoch 8 기준:
    - `val_recall 0.9966`
    - `val_accuracy 0.9926`
    - `val_fp_rate 0.0114`
    - `threshold 0.80`
- 분리 평가 스크립트 추가
  - `wake_word/train/05c_evaluate.py`
  - 저장된 checkpoint 기준 재평가 결과:
    - positive-only recall: `1177 / 1181 = 0.9966`
    - negative-only false positive rate: `128 / 11250 = 0.0114`
    - negative-only specificity: `11122 / 11250 = 0.9886`
- 다음 세션의 주 작업 환경은 Jetson이다.
- Jetson 단계 상세 계획은 `docs/jetson_transition_plan.md`에 정리돼 있다.
- `_tmp_download` 원본 보관 구조를 3개 폴더로 정리했다.
  - `1_aihub_free_conversation`
  - `2_fsd50k`
  - `3_musan`

## 중요 메모

- 현재 서버 환경에서는 ONNX feature 추출이 실제로는 GPU가 아니라 CPU로 동작했다.
- 원인은 `onnxruntime-gpu==1.23.2`의 CUDA 12 의존성과 현재 서버의 CUDA 11.8 조합 불일치다.
- PyTorch 학습은 사용자 셸에서 GPU 사용 가능했다.
- 현재 evaluation 비율은 대략 positive:negative = `1:10`이다.
- 이 비율은 모델 비교와 학습 선택에는 유효하지만, 실제 배치 성능을 바로 의미하지는 않는다.
- 현재 코드에서는 이름이 `test`인 split을 best epoch와 threshold 선택에 사용하므로, 엄밀히는 held-out validation에 가깝다.

## 다음 작업

1. `06_export_onnx.py` 구현
2. 현재 best run을 ONNX로 export
3. Jetson에서 실시간 추론 래퍼 구현
4. Jetson GUI 데모 구현
5. 실제 마이크 연결 후 positive / background 실기 검증
