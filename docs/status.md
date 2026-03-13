# Status

> 마지막 업데이트: 2026-03-12

## 목표

- `하이 포포` wake word 모델을 Linux 서버(A100)에서 학습하고 평가한다.
- 성능이 충분하면 Jetson Orin Nano Developer Kit으로 이관한다.
- Jetson 이관 이후에는 ONNX 추론 중심 개발을 진행한다.

## 현재 최종 기준

- wake word: `하이 포포`
- 학습 환경: Linux 서버, NVIDIA A100 80GB, Python 3.10, PyTorch 2.7.1+cu118
- 추론 환경: Jetson Orin Nano Developer Kit 8GB, ONNX Runtime GPU
- negative 데이터 최종 기준: `AI Hub + MUSAN + FSD50K`

## 현재 상태

- 문서 기준은 `하이 포포`, `AI Hub` 기준으로 정리됨
- negative 데이터 3종이 모두 완료됨
  - `negative/musan`: `20,000개`
  - `negative/fsd50k`: `20,000개`
  - `negative/aihub_free_conversation`: `72,500개`
- `positive_aug`는 `clean / mixed_noise / mixed_speech / _manifests` 구조로 개편됨
- mixed 증강은 원본 positive 기반으로 완료됨
  - `mixed_noise`: `281개`
  - `mixed_speech`: `281개`
- `04_extract_features.py`는 openWakeWord `AudioFeatures` 기반으로 구현됨
- `wake_word/train/check_onnx_gpu.py`로 사용자 셸에서 ONNX CUDA provider 실제 동작 여부를 단독 점검할 수 있음
- 사용자 셸에서 `check_onnx_gpu.py`를 실행한 결과 `RESULT: GPU_FALLBACK`이 확인됐고, 현재 서버 환경에서는 ONNX feature 추출이 실제로는 CPU로 동작함
- 현재 `04_extract_features.py --device cpu --batch-size 128` 전체 실행을 시작했고, feature 추출은 CPU 백그라운드 작업으로 진행 중임
- `04_extract_features.py`는 `--groups` 옵션으로 특정 split만 재실행할 수 있고, `--progress-interval-sec`로 3분 간격 진행 로그를 출력하도록 보완됨
- feature 추출이 모두 완료됨
  - `positive_features_train.npy`: `(10631, 28, 96)`
  - `positive_features_test.npy`: `(1181, 28, 96)`
  - `negative_features_train.npy`: `(101250, 28, 96)`
  - `negative_features_test.npy`: `(11250, 28, 96)`
- Codex 실행 컨텍스트에서는 GPU 접근이 되지 않아 `torch.cuda.is_available()`가 `False`로 보이지만, 사용자 셸에서는 GPU 사용이 가능한 상태임
- `wake_word` 환경에 `onnxruntime-gpu==1.23.2`를 설치했고, provider 목록에는 `TensorrtExecutionProvider`, `CUDAExecutionProvider`, `CPUExecutionProvider`가 보임
- 하지만 실제 GPU smoke test에서는 `libcublasLt.so.12`가 없어 CUDA provider 로딩에 실패했고, 현재 `04_extract_features.py`는 실질적으로 CPU로만 동작함
- 원인은 현재 서버 환경이 `PyTorch cu118` 기반인데, 설치한 `onnxruntime-gpu==1.23.2`는 CUDA 12 계열 라이브러리를 요구하는 점에 있음
- CPU 경로는 openWakeWord 내부 `ThreadPool` 권한 문제를 피하도록 직렬 추출로 보완했고, `positive 1개 + negative 1개` smoke test를 에러 없이 통과함
- `05_train.py`는 baseline 학습용으로 구현됐고, 결과물은 `wake_word/models/hi_popo/runs/<run_name>/` 단위로 아카이빙됨
- 최신 실행 결과는 `wake_word/models/hi_popo/` 루트에도 별도로 갱신됨
- 현재 best baseline run은 `baseline_medium`이다
  - train: positive `10,631`, negative `40,000`
  - val: positive `1,181`, negative `5,000`
  - best observed metric: `val_recall 0.9907`, `val_accuracy 0.9664`, `val_fp_rate 0.0578`, `threshold 0.35`
- `05b_search.py`로 baseline 구조의 핵심 하이퍼파라미터 탐색을 자동 실행할 수 있음
- 탐색 결과는 `wake_word/models/hi_popo/searches/<search_name>/` 아래에 ranking과 best trial로 아카이빙됨
- 루트 Git 저장소를 초기화했고, GitHub 원격 `origin`으로 `main` 브랜치 첫 push가 완료됨
- 사내 GitLab remote `gitlab`을 추가했고, 로컬 `git push-all` alias를 설정함
- 현재 GitLab push는 SSH `publickey` 권한 문제로 미완료 상태임

## 코드 상태

- 구현 완료:
  - `wake_word/train/01_generate_positive.py`
  - `wake_word/train/02_augment.py`
  - `wake_word/train/03_prepare_negative.py`
  - `wake_word/train/04_extract_features.py`
  - `wake_word/train/05_train.py`
- 미구현:
  - `wake_word/train/06_export_onnx.py`

## 다음 작업

1. 사용자 셸의 `wake_word` 환경에서 `05b_search.py`로 좁은 grid search 실행
2. best trial 파라미터로 전체 데이터 학습 실행
3. `06_export_onnx.py` 구현 및 ONNX export
4. 평가 후 Jetson 이관 여부 판단
