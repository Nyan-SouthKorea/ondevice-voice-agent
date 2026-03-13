# Status

> 마지막 업데이트: 2026-03-13

## 현재 목표

- `하이 포포` wake word 모델을 학습하고 평가한다.
- 성능이 충분하면 Jetson Orin Nano Developer Kit으로 이관한다.
- Jetson 이관 이후에는 ONNX 추론 중심으로 개발을 이어간다.

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

## 중요 메모

- 현재 서버 환경에서는 ONNX feature 추출이 실제로는 GPU가 아니라 CPU로 동작했다.
- 원인은 `onnxruntime-gpu==1.23.2`의 CUDA 12 의존성과 현재 서버의 CUDA 11.8 조합 불일치다.
- PyTorch 학습은 사용자 셸에서 GPU 사용 가능했다.
- 현재 validation 비율은 대략 positive:negative = `1:10`이다.
- 이 비율은 모델 비교와 학습 선택에는 유효하지만, 실제 배치 성능을 바로 의미하지는 않는다.

## 다음 작업

1. `06_export_onnx.py` 구현
2. 현재 best run을 ONNX로 export
3. threshold sweep 및 평가 스크립트 추가
4. 연속 오디오 기준 false positive / false reject 평가
5. 성능이 충분하면 Jetson 이관 준비
