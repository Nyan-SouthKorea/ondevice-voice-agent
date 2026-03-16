# Logbook

이 문서는 사람과 AI 도구를 포함한 작업 로그를 시간순으로 기록한다.

---

## 2026-03-16 | Human + Codex | STT 50문장 직접 녹음 평가 세트와 비교 파이프라인 추가

### Context

- 사용자는 STT 기본 모델을 감으로 정하지 않고, 직접 녹음한 고정 문장 세트로 속도와 정확도를 비교하는 방식으로 진행하길 원했다.
- 이를 위해 txt 기준 세트, 녹음 GUI, 다중 STT 비교 스크립트가 필요했다.

### Actions

- `stt/datasets/korean_eval_50/`를 추가했다.
- 한국어 평가 문장 50개를 `001.txt`부터 `050.txt`까지 번호형 파일로 정리했다.
- 직접 녹음 wav는 같은 파일명으로 저장하고 기본적으로 git 추적에서 제외하도록 `.gitignore`를 추가했다.
- `stt/stt_dataset_recorder.py`를 추가했다.
- `녹음 시작 / 녹음 정지 / 들어보기 / 재시도 / 녹음 완료` 버튼으로 순차 녹음하는 GUI를 구현했다.
- `stt/stt_benchmark.py`를 추가했다.
- 같은 데이터셋으로 여러 STT 설정을 순차 실행하고, 샘플별 결과와 요약 CSV/JSON을 저장하는 구조를 만들었다.

### Findings

- STT는 wake word처럼 작은 synthetic sample 하나만으로 최종 모델값을 정하기 어렵다.
- 사용자 직접 녹음 50문장 기준 세트를 먼저 만드는 편이 실사용 속도와 정확도 판단에 더 적합하다.
- 같은 파일명 `txt + wav` 구조가 사람이 보기에도 가장 단순하고, recorder와 benchmark를 함께 유지하기도 쉽다.

### Next

- 사용자가 50문장을 직접 녹음한다.
- 같은 세트로 `whisper tiny / base / small`과 필요 시 API 경로를 비교한다.
- 결과를 바탕으로 STT 기본 backend와 모델값을 확정한다.

---

## 2026-03-12 | Human + Codex | 문서 기준 정리 및 기록 체계 개편

### Context

- 사용자는 다른 도구에서 진행하던 프로젝트를 Codex와 병행하기 시작했다.
- `docs`를 먼저 읽고 현재 프로젝트 기준을 파악해달라고 요청했다.

### Actions

- `docs/README.md`, `docs/개발방침.md`, `docs/envs/wake_word_env.md`
- 초기 환경/positive/negative 작업 메모
- `docs/research/wake_word.md`, `tts_korean.md`, `negative_datasets.md`
- 실제 디렉토리와 학습 스크립트 상태를 함께 확인했다.
- `하이 케어로봇`으로 남아 있던 문서를 `하이 포포` 기준으로 수정했다.
- negative 전략을 `AI Hub + MUSAN + FSD50K` 기준으로 수정했다.
- 과거 AI 도구별 메모를 별도 보관했다.
- 세션 기록 방식 논의를 거쳐 `status / decisions / logbook` 체계로 개편했다.

### Findings

- 실제 코드와 데이터 파이프라인은 `hi_popo` 기준이었다.
- 과거 `Common Voice KO` 검토 흔적이 있었지만, 최종 방향은 AI Hub 중심이었다.
- 현재 구현은 `03_prepare_negative.py`까지이고, `04~06`은 아직 없다.

### Next

- AI Hub 다운로드 완료 대기
- 완료 후 `03_prepare_negative.py`를 최신 기준으로 개편
- 이후 `04_extract_features.py`, `05_train.py`, `06_export_onnx.py` 구현

### Notes

- 사용자는 세션 사이를 넘나들어도 전체 맥락을 읽을 수 있을 정도로 상세한 기록을 원한다.
- 이후 중요한 전환점마다 이 문서와 `status.md`, `decisions.md`를 함께 갱신한다.

### Update

- `docs/개발방침.md`에 문서 동기화 원칙을 추가했다.
- 앞으로 작업 중 문서 실시간 갱신을 프로젝트 운영 규칙으로 따른다.

---

## 2026-03-12 | Human + Codex | Negative 데이터 공통 포맷 정의 및 MUSAN 선행 작업 시작

### Context

- AI Hub 다운로드가 약 2시간 소요될 예정이라, 대기 시간 동안 다른 negative 데이터셋 전처리를 먼저 진행하기로 했다.
- 세 데이터셋은 이후 동일한 feature extraction 파이프라인을 타야 하므로 공통 포맷 정리가 먼저 필요했다.

### Actions

- `wake_word/train/03_prepare_negative.py`를 공통 출력 스펙 기준으로 재구성했다.
- 최종 출력 스펙을 `16kHz / mono / WAV(PCM_16) / 3.0초 고정 클립`으로 정했다.
- 현재 스크립트는 `MUSAN`을 먼저 처리할 수 있게 만들고, `FSD50K`와 `AI Hub` 자리를 확보했다.
- `MUSAN` 원본 디렉토리와 현재 negative 출력 디렉토리 상태를 확인했다.

### Findings

- `MUSAN` 원본은 이미 `_tmp_download/musan` 아래에 풀려 있다.
- `negative/` 출력 디렉토리는 아직 비어 있다.
- 현재 셸 환경에서는 `librosa`가 없어 스크립트 실행 검증은 아직 하지 못했다.

### Next

- 올바른 Python 환경에서 `MUSAN` 전처리를 먼저 실행한다.
- 이후 같은 스펙으로 `FSD50K`, `AI Hub` 처리 로직을 이어 붙인다.

### Follow-up

- 첫 실행에서 `librosa/numba` 캐시 권한 문제로 `MUSAN` 후보 청크가 0개 생성됐다.
- `03_prepare_negative.py`에 `NUMBA_CACHE_DIR=/tmp/numba_cache` 설정을 추가해 재실행하기로 했다.
- 추가로, 전체 청크 배열을 메모리에 쌓는 구조가 비효율적이라 `MUSAN` 청크 참조만 먼저 수집하는 2단계 방식으로 수정했다.

### Validation

- `--limit-input-files 1 --limit-output-count 1` 옵션으로 `MUSAN` 1파일 테스트를 수행했다.
- 후보 청크 100개가 생성됐고, 최종 WAV 1개 저장까지 성공했다.
- 출력 파일 스펙은 `16kHz / mono / WAV / PCM_16 / 3.0초`로 확인했다.

---

## 2026-03-12 | Human + Codex | Positive 증강 디렉토리 구조 개편

### Context

- 사용자는 positive background mixing 증강을 추가하는 방향에 동의했지만, 실제 증강 실행은 negative 데이터셋 준비가 모두 끝난 뒤로 미루기로 했다.

### Actions

- `wake_word/data/hi_popo/positive_aug/` 아래에 `clean`, `mixed_noise`, `mixed_speech`, `_manifests` 디렉토리를 생성했다.
- 기존 `positive_aug` 평면 구조의 clean WAV 11,250개를 `positive_aug/clean/`으로 이동했다.
- `wake_word/train/02_augment.py` 출력 경로를 `positive_aug/clean/`으로 수정했다.

### Findings

- 기존 clean 증강 산출물 11,250개가 모두 `clean/` 아래로 정리됐다.
- mixed 증강용 디렉토리는 준비만 해두고 아직 비어 있다.

### Next

- mixed background 증강은 시작하지 않는다.
- negative 데이터셋 준비를 이어서 진행하고, 모두 완료된 뒤 mixed 증강 구현/실행으로 돌아온다.

---

## 2026-03-12 | Human + Codex | FSD50K 손상 파일 정리

### Context

- `FSD50K` 추출 준비 중 `FSD50K.eval_audio.zip`이 정상 zip 헤더가 아닌 손상 파일로 확인됐다.

### Actions

- 재다운로드를 시도했지만, 사용자의 판단에 따라 손상된 `FSD50K.eval_audio.zip`을 삭제했다.

### Findings

- `metadata.zip`과 `ground_truth.zip`은 정상 zip이다.
- `eval_audio.zip`은 손상 상태였고, 현재 삭제된 상태다.

### Next

- 이후 사용자가 `AI Hub` 압축 파일 경로를 알려주면 그 작업을 우선 이어간다.
- `FSD50K`는 남은 정상 파트 기준으로 진행 가능 범위를 다시 판단한다.

### Retrospective

- 이미 일부 다운로드된 대용량 파일을 바로 삭제한 것은 비효율적이었다.
- 이후에는 대용량 파일에 대해 무결성 확인과 이어받기 가능 여부를 먼저 점검하는 원칙으로 수정한다.

---

## 2026-03-12 | Human + Codex | FSD50K dev_audio 전처리 시작

### Context

- `FSD50K dev_audio` 병합과 해제가 완료되어, `MUSAN`과 같은 방식으로 negative 샘플링을 시작할 수 있는 상태가 됐다.

### Actions

- `wake_word/train/03_prepare_negative.py`에 `fsd50k` 처리 로직을 추가했다.
- `FSD50K.dev_audio` 원본을 공통 스펙으로 변환하고, 최종 `20,000개`를 샘플링 저장하는 흐름으로 구현했다.
- 현재 `conda run -n wake_word python wake_word/train/03_prepare_negative.py --sources fsd50k`를 실행 중이다.

### Next

- `negative/fsd50k/` 샘플링이 끝나는 즉시 개수와 경로를 확인한다.
- 이후 AI Hub 경로를 받으면 마지막 negative 소스로 이어간다.

### Update

- `negative/fsd50k/`에 최종 `20,000개` 저장이 완료됐다.
- 이어서 `AI Hub` 원천 zip 해제 및 샘플링 전처리를 시작했다.

---

## 2026-03-13 | Human + Codex | Mixed positive 증강 스크립트 추가

### Context

- 사용자는 clean 증강본이 아니라 원본 positive를 기준으로 `mixed_noise`, `mixed_speech`를 생성하기로 결정했다.

### Actions

- `wake_word/train/02b_mix_background.py`를 추가했다.
- 원본 positive의 50%를 mixed 대상으로 뽑고, 절반은 `mixed_noise`, 절반은 `mixed_speech`로 생성하는 구조로 구현했다.
- 배경 소스는 `MUSAN`, `FSD50K`, `AI Hub`를 사용하도록 반영했다.

### Next

- 필요한 negative 배경 데이터가 모두 준비된 상태에서 mixed 증강을 실행한다.

### Follow-up

- 첫 실행에서 `librosa/numba` 캐시 권한 문제로 mixed 증강이 즉시 중단됐다.
- `02b_mix_background.py`에 `NUMBA_CACHE_DIR=/tmp/numba_cache` 설정을 추가해 재실행한다.

### Update

- mixed 증강 재실행 후 `mixed_noise 281개`, `mixed_speech 281개` 생성이 완료됐다.

---

## 2026-03-13 | Human + Codex | openWakeWord feature 추출 시작

### Context

- openWakeWord 레포 흐름에 맞춰 학습 전 Google Speech Embedding feature를 먼저 추출하기로 했다.

### Actions

- `wake_word/train/04_extract_features.py`를 추가했다.
- positive(clean/mixed)와 negative(3종)를 train/test로 나누고 `.npy` feature 파일과 manifest를 만드는 구조로 구현했다.
- 현재 `conda run -n wake_word python wake_word/train/04_extract_features.py`를 실행 중이다.

### Findings

- `wake_word` 환경에서 openWakeWord import는 정상이다.
- 현재 `torch.cuda.is_available()`는 `False`로 확인되어, feature 추출은 CPU 경로로 진행된다.

### Update

- `04_extract_features.py`의 CPU 경로는 openWakeWord 내부 `ThreadPool` 권한 문제로 실패했다.
- 이를 피하기 위해 CPU에서는 `embed_clips(...)` 대신 clip 단위 직렬 `_get_embeddings(...)` 경로를 사용하도록 수정했다.
- 수정 후 아래 smoke test가 에러 없이 통과했다.
  - `python wake_word/train/04_extract_features.py --device cpu --batch-size 1 --test-ratio 0.5 --limit-positive 2 --limit-negative 2`
- 추가 확인 결과 초기 `wake_word` 환경의 `onnxruntime` 제공자는 `['AzureExecutionProvider', 'CPUExecutionProvider']`이고 `CUDAExecutionProvider`가 없었다.
- 이후 `onnxruntime`를 제거하고 `onnxruntime-gpu==1.23.2`를 설치했다.
- 현재 제공자는 `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']`로 확인됐다.
- 이후 작은 GPU smoke test를 직접 실행했다.
  - `python wake_word/train/04_extract_features.py --device gpu --batch-size 2 --test-ratio 0.5 --limit-positive 2 --limit-negative 2`
- 결과적으로 실행은 완료됐지만, 실제 CUDA provider 로딩은 실패했고 CPU로 폴백했다.
- 핵심 오류는 `libcublasLt.so.12: cannot open shared object file`였고, 현재 설치한 `onnxruntime-gpu==1.23.2`가 CUDA 12 계열을 요구하는 것으로 확인됐다.
- 사용자가 자기 셸에서 ONNX GPU 가능 여부만 독립적으로 확인할 수 있도록 `wake_word/train/check_onnx_gpu.py`를 추가했다.
- 사용자 셸에서 해당 스크립트를 직접 실행했고, 결과는 `RESULT: GPU_FALLBACK`이었다.
- 즉 provider 목록에는 `CUDAExecutionProvider`가 보여도, 실제 세션은 `CPUExecutionProvider`로 생성됐다.
- 따라서 feature 추출은 Codex가 CPU로 직접 진행하고, 이후 학습 단계에서만 사용자가 PyTorch GPU를 활용하는 운영으로 정리했다.
- 전체 실행 명령:
  - `python wake_word/train/04_extract_features.py --device cpu --batch-size 128`
- 시작 직후 분할 결과:
  - positive train `10,631`, test `1,181`
  - negative train `101,250`, test `11,250`
- 이후 사용자 인터럽트로 장시간 모니터링 세션이 끊겼고, 본 feature 추출도 중단됐다.
- 이에 `04_extract_features.py`에 아래 보완을 추가했다.
  - `--groups`로 `positive_train`, `positive_test`, `negative_train`, `negative_test` 중 필요한 split만 재실행
  - `--progress-interval-sec`로 별도 진행 로그 출력
- 현재는 이미 끝난 positive는 건드리지 않고 `negative_train`, `negative_test`만 다시 실행하는 방향으로 전환했다.
- 이후 운영 기준을 확장해, 1분 이상 소요될 수 있는 모든 실행 코드는 기본적으로 1분 주기 로그를 출력하도록 `docs/개발방침.md`와 `docs/README.md`에 반영했다.
- `04_extract_features.py`의 기본 진행 로그 주기도 `60초`로 조정했다.
- 사용자의 요청으로 중단된 `negative_features_train.npy`, `negative_features_test.npy`는 삭제하고 다시 시작하기로 했다.
- 재실행 이후 현재 feature 파일 shape를 확인했고, 전체 추출 완료가 확정됐다.
  - `positive_features_train.npy`: `(10631, 28, 96)`
  - `positive_features_test.npy`: `(1181, 28, 96)`
  - `negative_features_train.npy`: `(101250, 28, 96)`
  - `negative_features_test.npy`: `(11250, 28, 96)`

---

## 2026-03-13 | Human + Codex | 분류기 학습 스크립트 구현

### Context

- feature 추출이 모두 끝나서 wake word 분류기 학습 단계로 넘어갈 수 있게 됐다.
- 학습은 사용자의 실제 셸에서 PyTorch GPU를 사용해 실행하는 방향으로 정리돼 있었다.

### Actions

- `wake_word/train/05_train.py`를 추가했다.
- openWakeWord의 FC 분류기 구조와 같은 형태의 binary classifier를 로컬 스크립트에 직접 구현했다.
- `(28, 96)` clip feature에서 랜덤 `16 x 96` window를 뽑아 학습 배치로 사용하는 구조를 만들었다.
- clip-level validation은 각 clip의 sliding window score 최대값을 기준으로 recall/accuracy/false positive rate를 계산하도록 구현했다.
- 체크포인트와 학습 히스토리를 `wake_word/models/hi_popo/`에 저장하도록 했다.

### Validation

- 작은 CPU smoke test를 에러 없이 통과했다.
- 실행 명령:
  - `python wake_word/train/05_train.py --device cpu --epochs 1 --batch-size 32 --limit-train-positive 32 --limit-train-negative 32 --limit-val-positive 8 --limit-val-negative 8`
- 산출물:
  - `wake_word/models/hi_popo/hi_popo_classifier.pt`
  - `wake_word/models/hi_popo/hi_popo_training_history.json`

### Notes

- `openwakeword.train.Model`를 직접 import하면 `torchinfo` 같은 추가 의존성이 필요해서, 학습 구조는 로컬 스크립트 내에 같은 형태로 독립 구현했다.
- 장시간 학습은 `1분` 주기 진행 로그 원칙을 따르도록 설계했다.
- baseline과 이후 고도화 실험을 분리 보관하기 위해 `wake_word/models/hi_popo/runs/<run_name>/` 아카이브 구조를 추가했다.
- 각 run에는 최소한 아래가 함께 저장된다.
  - `hi_popo_classifier.pt`
  - `training_history.json`
  - `run_metadata.json`

### Validation Update

- 아카이브 구조 검증용 smoke test를 추가로 수행했다.
- 실행 명령:
  - `python wake_word/train/05_train.py --device cpu --epochs 1 --batch-size 32 --run-name smoke_archive_check --limit-train-positive 32 --limit-train-negative 32 --limit-val-positive 8 --limit-val-negative 8`
- 결과:
  - `wake_word/models/hi_popo/runs/smoke_archive_check/`에 체크포인트, 히스토리, 메타데이터가 생성됨
  - 최신 결과 파일도 `wake_word/models/hi_popo/` 루트에 갱신됨

### Baseline Runs

- `baseline_small`
  - train: positive `4,000`, negative `12,000`
  - val: positive `500`, negative `2,000`
  - epoch 5 기준: `val_recall 0.9960`, `val_accuracy 0.9345`, `val_fp_rate 0.1270`, `threshold 0.30`
  - 판단: 학습 가능성 검증은 성공, false positive는 아직 높음

- `baseline_medium`
  - train: positive `10,631`, negative `40,000`
  - val: positive `1,181`, negative `5,000`
  - epoch 6 기준 best: `val_recall 0.9907`, `val_accuracy 0.9664`, `val_fp_rate 0.0578`, `threshold 0.35`
  - epoch 8 종료: `val_recall 0.9907`, `val_accuracy 0.9603`, `val_fp_rate 0.0700`, `threshold 0.35`
  - 판단: baseline으로는 의미 있는 개선이 확인됐고, 현재 best baseline으로 간주

---

## 2026-03-13 | Grid Search 실행기 추가

### Context

- baseline 구조는 동작이 확인됐고, 다음 큰 학습 전에 핵심 하이퍼파라미터를 좁게 탐색하는 방향으로 정리됐다.

### Actions

- `wake_word/train/05_train.py`에 `--seed` 인자를 추가했다.
- `wake_word/train/05b_search.py`를 추가했다.
- 탐색 축:
  - `lr`
  - `negative_weight`
  - `layer_dim`
  - `n_blocks`
- 각 trial은 기존 `05_train.py`를 실행하고, 결과를 `run_metadata.json`에서 읽어 ranking으로 정리한다.
- 탐색 결과는 `wake_word/models/hi_popo/searches/<search_name>/` 아래에 저장된다.

### Validation

- 작은 CPU smoke search를 에러 없이 통과했다.
- 실행 명령:
  - `python wake_word/train/05b_search.py --device cpu --epochs 1 --batch-size 32 --search-name smoke_search_check --lr-grid 0.0001 --negative-weight-grid 5.0 --layer-dim-grid 32 --n-blocks-grid 1 --limit-train-positive 32 --limit-train-negative 32 --limit-val-positive 8 --limit-val-negative 8`
- 산출물:
  - `wake_word/models/hi_popo/searches/smoke_search_check/ranking.json`
  - `wake_word/models/hi_popo/searches/smoke_search_check/best_trial.json`

### Search Result Update

- 사용자가 `baseline_grid_v1` 전체 탐색을 직접 GPU로 완료했다.
- 최종 top 5는 `ranking.json`에 저장됐고, 최고 trial은 아래였다.
  - `baseline_grid_v1_trial40`
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`
  - `val_recall 0.9966`
  - `val_accuracy 0.9855`
  - `val_fp_rate 0.0256`
  - `threshold 0.70`

---

## 2026-03-13 | .gitignore 정리

### Context

- 프로젝트 안에 대용량 데이터셋, 학습 산출물, secrets가 함께 존재해 추적 대상을 정리할 필요가 있었다.

### Actions

- 루트 `.gitignore`를 현재 리포 기준으로 보강했다.
- 주요 제외 대상:
  - `secrets/`
  - `.env`, `.env.*`
  - Python 캐시와 editor 파일
  - `wake_word/data/`
  - `wake_word/models/`
  - `wake_word/openWakeWord/.git/`

### Notes

- 이 설정은 코드/문서/스크립트만 리포에 남기고, 데이터와 모델 산출물은 제외하는 보수적 기준이다.
- 이후 예시 오디오 샘플은 `third-party dataset`가 아니라 직접 생성한 TTS만 `examples/audio_samples/` 아래에 두는 방향으로 정리했다.
- 이에 맞춰 `.gitignore`에 `examples/audio_samples/` 예외 경로를 추가했다.

### Follow-up

- `examples/audio_samples/positive_tts/`를 실제로 만들고, 직접 생성한 TTS 샘플 3개를 복사했다.
- `examples/audio_samples/README.md`를 추가해 포함 원칙과 샘플 목록을 명시했다.

---

## 2026-03-13 | 루트 README 추가

### Context

- 사용자는 문서 허브용 `docs/README.md`와 별도로, 프로젝트 자체를 설명하는 루트 `README.md`가 필요하다고 요청했다.

### Actions

- 루트 `README.md`를 새로 추가했다.
- 내용은 프로젝트 개요, 현재 범위, 목표, 진행 상태, 구조, 문서 링크, 운영 원칙 중심으로 구성했다.
- `docs/README.md`는 문서 허브 역할로 유지하고, 루트 `README.md`가 상위 프로젝트 소개를 맡도록 역할을 분리했다.

---

## 2026-03-13 | 전체 데이터 학습 시도 후 정리

### Context

- 사용자는 baseline 학습이 끝난 뒤, 가장 좋은 파라미터 기준으로 전체 학습을 바로 시작해두길 요청했다.
- grid search 결과는 아직 없으므로, 현재 best baseline인 `baseline_medium` 파라미터를 기준으로 확장하는 보수적 경로를 택했다.

### Decision

- 현재 전체 학습 시작 파라미터는 아래를 사용한다.
  - `lr=0.0001`
  - `negative_weight=5.0`
  - `layer_dim=32`
  - `n_blocks=1`
  - `epochs=8`
  - `batch_size=512`
- train/val은 feature 전체를 사용한다.

### Note

- Codex 실행 컨텍스트에서는 여전히 GPU가 보이지 않아, 자동으로 시작된 전체 학습은 CPU 경로로 동작했다.
- 이후 사용자의 요청에 따라 이 CPU run 기록은 삭제했다.
- 삭제 대상 run:
  - `full_from_baseline_medium_all_data`
- 최신 포인터 파일은 다시 `baseline_medium` 결과로 복구했다.

---

## 2026-03-13 | Human + Codex | Grid search 완료 및 best trial 확정

### Context

- baseline 구조는 동작이 확인됐고, 전체 데이터 최종 학습 전에 핵심 하이퍼파라미터를 좁게 탐색하기로 했다.

### Actions

- 사용자가 A100 GPU 환경에서 `05b_search.py`를 직접 실행했다.
- 탐색 축은 아래 4개였다.
  - `lr`
  - `negative_weight`
  - `layer_dim`
  - `n_blocks`
- 총 `48`개 trial이 실행됐다.

### Result

- search name: `baseline_grid_v1`
- best trial: `baseline_grid_v1_trial40`
- best parameter:
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`
- best metric:
  - `val_recall 0.9966`
  - `val_accuracy 0.9855`
  - `val_fp_rate 0.0256`
  - `threshold 0.70`

### Artifacts

- `wake_word/models/hi_popo/searches/baseline_grid_v1/ranking.json`
- `wake_word/models/hi_popo/searches/baseline_grid_v1/best_trial.json`

### Notes

- baseline_medium 대비 false positive rate가 크게 줄어들었다.
- 이 결과를 기준으로 전체 데이터 최종 학습 파라미터를 확정했다.

---

## 2026-03-13 | Human + Codex | Best trial 파라미터로 전체 데이터 최종 학습 완료

### Context

- grid search best trial이 정해졌고, 같은 파라미터로 전체 train/val feature에 대해 최종 후보 모델을 학습했다.

### Actions

- 사용자가 A100 GPU 환경에서 아래 명령으로 전체 학습을 수행했다.
- run name: `final_full_best_trial40`
- 핵심 파라미터:
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`
  - `epochs=8`
  - `batch_size=512`

### Result

- train: positive `10,631`, negative `101,250`
- val: positive `1,181`, negative `11,250`
- epoch 8 기준:
  - `val_recall 0.9966`
  - `val_accuracy 0.9926`
  - `val_fp_rate 0.0114`
  - `threshold 0.80`

### Artifacts

- `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`
- `wake_word/models/hi_popo/runs/final_full_best_trial40/training_history.json`
- `wake_word/models/hi_popo/runs/final_full_best_trial40/run_metadata.json`

### Interpretation

- 현재까지의 full-data 기준 best result다.
- 동일한 pipeline 안에서는 매우 강한 recall / fp_rate 조합이 나왔다.
- 다만 이 평가는 clip-level validation이므로, 실제 배치 성능을 보려면 연속 오디오 기준 평가가 추가로 필요하다.

---

## 2026-03-13 | Human + Codex | 프로젝트 통합 문서 정리

### Context

- 사용자는 현재 대화 컨텍스트가 줄어드는 상황을 고려해, 대화 기록이 없어도 `docs`만 읽으면 프로젝트의 목적, 과정, 중요 포인트, 현재 상태를 모두 이해할 수 있어야 한다고 요청했다.

### Actions

- `docs/project_overview.md`를 새로 작성했다.
- 목적, 범위, 데이터 전략, 환경, 구현된 스크립트, 학습 결과, 현재 한계, 다음 단계까지 한 문서에 통합했다.
- `docs/README.md`의 우선 참고 순서를 통합 문서 중심으로 재구성했다.
- `docs/status.md`를 실제 최신 상태에 맞게 다시 정리했다.
- `docs/decisions.md`에 최종 전체 학습 파라미터 채택 결정을 추가했다.

### Result

- 새 세션에서는 최소한 아래 문서만 읽어도 전체 맥락을 빠르게 복구할 수 있게 됐다.
  - `docs/project_overview.md`
  - `docs/개발방침.md`
  - `docs/status.md`
  - `docs/decisions.md`
  - `docs/logbook.md`

---

## 2026-03-13 | Human + Codex | positive-only / negative-only 분리 평가 정리

### Context

- 사용자는 현재 학습 완료 모델에 대해 `하이 포포를 불렀을 때 얼마나 잘 맞추는지`와 `배경 음성에서 얼마나 오탐이 나는지`를 분리해서 보고 싶어 했다.
- 동시에 현재 학습 로직이 이 평가 요소를 이미 반영하고 있는지도 확인하고자 했다.

### Actions

- `wake_word/train/05_train.py`의 validation 로직을 다시 검토했다.
- 저장된 checkpoint를 기준으로 positive-only / negative-only를 별도로 계산하는 `wake_word/train/05c_evaluate.py`를 추가했다.
- `final_full_best_trial40` checkpoint를 저장된 threshold `0.80`으로 재평가했다.

### Result

- positive-only test:
  - total `1,181`
  - true positives `1,177`
  - false negatives `4`
  - recall `0.9966`
- negative-only test:
  - total `11,250`
  - false positives `128`
  - true negatives `11,122`
  - false positive rate `0.0114`
  - specificity `0.9886`

### Interpretation

- 현재 학습 로그에 표시된 `val_recall`은 사용자가 원하는 positive-only 성능과 같은 값이다.
- `val_fp_rate`는 사용자가 원하는 negative-only 배경 오탐 비율과 같은 값이다.
- 다만 현재 파이프라인은 이름이 `test`인 split을 best epoch와 threshold 선택에도 사용하므로, 이 평가는 순수 final test라기보다 held-out validation 해석이 더 정확하다.

### Next

- 연속 오디오 기준 평가 세트를 따로 구성해 `false accepts per hour`와 실제 배경 환경 오탐을 측정해야 한다.

---

## 2026-03-13 | Human + Codex | Jetson 전환 계획 문서화

### Context

- 사용자는 현재 서버 학습 단계는 잠시 멈추고, 이제 Jetson으로 넘어가 실제 마이크 기반 GUI 테스트를 진행하려고 한다.
- 다음 세션이 바뀌더라도 Jetson 단계에서 바로 이어갈 수 있도록, 앞으로의 계획을 문서에 자세히 남기길 원했다.

### Actions

- `docs/jetson_transition_plan.md`를 새로 작성했다.
- 현재 best 모델 경로, Jetson 단계 목표, ONNX export 우선순위, 실시간 추론 래퍼 계획, GUI 요구사항, positive/background 실기 검증 계획을 정리했다.
- `docs/README.md`의 우선 참고 순서를 Jetson 전환 문서 기준으로 재배치했다.
- `docs/status.md`를 Jetson phase 중심으로 갱신했다.
- `docs/decisions.md`에 다음 phase는 Jetson 실시간 검증을 우선한다는 결정을 추가했다.
- `docs/project_overview.md`에도 Jetson 전환 문서 링크를 추가했다.

### Result

- 다음 세션에서 아래 문서만 읽으면 Jetson 단계로 바로 이어갈 수 있게 됐다.
  - `docs/jetson_transition_plan.md`
  - `docs/status.md`
  - `docs/project_overview.md`
  - `docs/decisions.md`
  - `docs/logbook.md`

### Notes

- 현재 기준 모델은 `wake_word/models/hi_popo/runs/final_full_best_trial40/hi_popo_classifier.pt`다.
- Jetson 단계의 1차 목적은 추가 학습이 아니라 실시간 추론과 실기 검증이다.

---

## 2026-03-13 | Human + Codex | `_tmp_download` 원본 보관 구조 정리

### Context

- 사용자는 `wake_word/data/hi_popo/_tmp_download` 안에서 압축 원본만 남기고, 이미 전처리에 사용한 추출본과 중간 산출물을 정리하길 원했다.
- 또한 이후 보관과 이동을 쉽게 하기 위해 `_tmp_download` 구조를 3개 폴더로 단순화하길 원했다.

### Actions

- 추출된 작업용 폴더를 삭제했다.
  - `aihub_free_conversation`
  - `fsd50k`
  - `musan`
- 불필요한 중간 산출물과 실패 잔여물을 삭제했다.
  - `FSD50K.dev_audio_merged.zip`
  - `FSD50K.eval_audio.z01`
  - 각종 extract log
- 원본 보관 구조를 아래처럼 재배치했다.
  - `_tmp_download/1_aihub_free_conversation`
  - `_tmp_download/2_fsd50k`
  - `_tmp_download/3_musan`

### Result

- `1_aihub_free_conversation`
  - AI Hub zip 원본만 남김
- `2_fsd50k`
  - FSD50K 분할 압축 원본과 metadata / ground truth zip만 남김
- `3_musan`
  - `musan.tar.gz`와 README만 남김

### Notes

- 정리 후 `_tmp_download`에는 압축 원본 보관용 파일만 남아 있다.
- 이후 D드라이브 등 다른 저장소로 옮길 때도 이 3개 폴더만 보면 된다.

---

## 2026-03-13 | Human + Codex | Markdown 링크를 상대경로로 정리

### Context

- 문서 안의 절대 로컬 경로 링크가 문서 뷰에서 열리지 않는 문제가 있었다.

### Actions

- 루트 `README.md`의 문서 링크를 상대경로 링크로 변경했다.
- `docs/project_overview.md` 안의 문서/스크립트 링크를 문서 안에서 열리는 상대경로로 바꿨다.
- 동시에 루트 `README.md`의 현재 진행 상태 문구도 최신 상태에 맞게 갱신했다.

### Result

- 문서 뷰에서 링크가 정상 동작하는 구조로 정리됐다.
- 더 이상 `/data2/...` 절대경로 링크는 Markdown 파일에 남아 있지 않다.

---

## 2026-03-13 | Human + Codex | 문서 민감 정보 일반화

### Context

- 사용자는 문서 기준으로 내부 식별 정보나 불필요한 운영 상세가 남아 있지 않은지 마지막 검토를 요청했다.

### Actions

- 문서 전반에서 내부 주소, 계정 식별자, 로컬 SSH 경로, 고객사 직접 표현을 점검했다.
- 문서에 불필요한 운영 상세와 SSH 설정 상세를 일반화했다.
- 개발 방침의 대외 민감도가 높은 표현을 더 일반적인 문장으로 조정했다.

### Result

- 최신 문서 기준으로는 내부 주소, 내부 사용자 식별자, 로컬 SSH 경로가 직접 노출되지 않게 정리됐다.

## 2026-03-13 | Human + Codex | 문서/샘플 구조 재정리

### Context

- 사용자는 문서 품질을 더 높이고, 민감 정보와 모듈 구조를 다시 정리하길 원했다.
- 특히 wake word 관련 예시 샘플이 상위 `examples/`에 있는 점과, `wake_word` 루트에 README가 없는 점을 문제로 봤다.

### Actions

- 예시 오디오 샘플을 `examples/`에서 `wake_word/examples/audio_samples/`로 이동했다.
- 루트 `README.md`를 상위 프로젝트 진입점으로 전면 보강했다.
- `wake_word/README.md`를 새로 작성해 wake word 서브프로젝트 진입 문서로 추가했다.
- `vad/README.md`, `stt/README.md`, `llm/README.md`, `tts/README.md`를 추가해 루트 README에서 각 모듈로 이동할 수 있게 했다.
- `docs/개발방침.md`에 민감 정보 문서화 원칙을 명시했다.
- `secrets/` 아래의 로컬 전용 문서에서 민감 운영 메모를 관리하는 방향으로 정리했다.

### Result

- 예시 샘플 위치가 모듈 구조와 일치하게 정리됐다.
- 루트 README와 `wake_word/README.md`만 읽어도 상위 프로젝트와 wake word 프로젝트의 현재 상태를 각각 이해할 수 있게 됐다.
- 민감 정보는 문서에서 직접 다루지 않고 로컬 전용 문서로 분리하는 기준이 더 명확해졌다.

---

## 2026-03-13 | Human + Codex | 루트 README 하단 링크 정리

### Context

- 사용자는 루트 `README.md` 하단 링크가 중복된다고 판단했다.

### Actions

- 루트 `README.md` 하단의 중복 링크 목록을 `docs/README.md` 중심의 짧은 안내로 정리했다.

### Result

- 루트 README 하단이 더 간결해졌고, 문서 진입 경로가 중복 없이 정리됐다.

---

## 2026-03-13 | Human + Codex | 프로젝트의 SDK 지향 장기 목표 문서화

### Context

- 사용자는 이 프로젝트의 큰 목표 중 하나가 Jetson 내부에서 재사용 가능한 음성 에이전트 SDK를 만드는 것이라고 설명했다.
- 이 SDK는 다른 프론트엔드, 백엔드, 동료 개발자가 쉽게 활용할 수 있어야 하며, 로봇의 다른 기능과도 자연스럽게 연결되어야 한다.

### Actions

- 루트 `README.md`에 장기 제품 방향과 SDK 지향 설명을 추가했다.
- `docs/project_overview.md`에 SDK형 음성 에이전트 아키텍처 목표를 별도 섹션으로 정리했다.
- `docs/개발방침.md`에 SDK 지향 아키텍처 원칙을 추가했다.
- `docs/decisions.md`에 장기 목표를 공식 결정사항으로 기록했다.

### Result

- 이제 문서만 읽어도 현재 wake word 개발이 최종적으로 어떤 상위 플랫폼으로 이어지는지 이해할 수 있다.
- 프로젝트의 목적이 개별 모델 구현이 아니라, 로봇 기능과 결합 가능한 재사용형 음성 에이전트 SDK라는 점이 명확해졌다.

---

## 2026-03-13 | Human + Codex | ONNX export 및 Jetson용 classifier 추론 코드 준비

### Context

- 사용자는 현재 best checkpoint를 ONNX로 export하고, 이후 Jetson으로 코드를 복사해 이어서 개발할 계획이다.
- 따라서 export 스크립트와, export된 ONNX를 Jetson에서 어떻게 로드해 추론하는지에 대한 최소 샘플 코드가 필요했다.

### Actions

- `wake_word/train/06_export_onnx.py`를 추가했다.
- `wake_word/detector.py`를 classifier ONNX wrapper로 구현했다.
- `wake_word/wake_word_demo.py`에 간단한 CLI 샘플을 추가했다.
- `wake_word/README.md`와 `docs/status.md`에 현재 export 경로와 Jetson 준비 관점을 반영했다.

### Notes

- 현재 export 대상은 raw audio end-to-end 모델이 아니라 `classifier only` ONNX다.
- 입력은 `(16, 96)` feature window이며, 실제 마이크 추론에는 upstream embedding 추출 단계가 별도로 필요하다.

### Follow-up

- `wake_word` 환경에 `onnx` 패키지가 없어서 첫 export가 실패했다.
- `onnx` 설치 후 export를 다시 실행해 아래 산출물을 생성했다.
  - `wake_word/models/hi_popo/hi_popo_classifier.onnx`
  - `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`
- 같은 ONNX와 metadata를 `final_full_best_trial40` run 디렉토리에도 같이 복사했다.
- `wake_word/models/`는 git에 포함하지 않으므로, Jetson에는 ONNX와 metadata를 별도로 복사해야 한다는 점도 문서에 반영했다.
- 초기 demo는 `(28, 96)` clip feature를 그대로 넣어 실패했는데, classifier 입력이 `(16, 96)` window이기 때문이었다.
- 이를 해결하기 위해 `wake_word/detector.py`를 보완해 `(T, 96)` clip feature를 받으면 sliding window를 만든 뒤 max score를 반환하도록 수정했다.
- `wake_word/wake_word_demo.py`에도 provider override와 clip feature 입력 지원을 반영했다.

---

## 2026-03-13 | Human + Codex | 상위 문서를 ONNX export 이후 기준으로 동기화

### Context

- `wake_word/README.md`와 `docs/status.md`는 이미 ONNX export 완료 상태를 반영하고 있었지만, 일부 상위 문서는 아직 `06_export_onnx.py`를 미구현 TODO처럼 설명하고 있었다.
- 또한 Jetson handoff 문서 일부는 현재 구현된 classifier-only ONNX 래퍼 상태와 앞으로 남은 raw audio 연결 작업을 명확히 구분하지 못하고 있었다.

### Actions

- `docs/project_overview.md`를 현재 구현 상태 기준으로 갱신했다.
- `docs/jetson_transition_plan.md`를 ONNX export 완료 이후 단계 기준으로 수정했다.
- `docs/개발방침.md`의 Wake Word 상태를 실제 진행 단계에 맞게 갱신했다.
- `wake_word/models/hi_popo/README.md`에 ONNX 산출물 설명을 추가했다.

### Result

- 상위 문서에서도 `06_export_onnx.py`가 이미 구현 완료된 상태로 정리됐다.
- 현재 남은 핵심 작업이 `raw audio -> feature extractor -> classifier ONNX` 연결이라는 점이 문서에 명확히 반영됐다.
- model artifact 문서에서도 latest `.onnx`와 `_onnx.json` 산출물을 함께 설명하게 됐다.

---

## 2026-03-13 | Human + Codex | Jetson runtime venv 생성 및 환경 문서화

### Context

- 사용자는 `project/env/` 아래에 Jetson 전용 venv를 만들고, ONNX Runtime이 Jetson의 CUDA 설정으로 실제 동작하는 상태를 기준 환경으로 관리하길 원했다.
- 또한 환경 세팅 절차를 읽는 사람이 쉽게 따라갈 수 있도록 문서 허브에서 바로 찾을 수 있게 만들고, 환경이 바뀔 때마다 문서를 갱신하는 원칙도 명시하길 요청했다.
- 설치 방식은 NVIDIA 공식 JetPack 가이드를 기준으로 정리하길 원했다.

### Actions

- 환경 이름을 `wake_word_jetson`으로 정했다.
- 현재 Jetson 상태를 확인했다.
  - L4T: `R36.4.7`
  - Python: `3.10.12`
  - 시스템 ORT package: `onnxruntime-gpu 1.23.0`
  - providers: `TensorrtExecutionProvider`, `CUDAExecutionProvider`, `CPUExecutionProvider`
- 기본 `python3 -m venv`는 `ensurepip` 부재로 실패해, 사용자 영역에 `virtualenv`를 설치해 우회했다.
- `project/env/wake_word_jetson` venv를 생성했다.
- venv 안에서 Jetson의 기존 ORT를 재사용할 수 있도록 `.pth` bridge를 추가했다.
- venv에 `requests`, `soundfile` 등 필요한 런타임 패키지를 보강했다.
- `wake_word/train/check_onnx_gpu.py`를 새 venv에서 실행해 실제 CUDA session 생성 여부를 검증했다.
- Jetson 환경 문서 `docs/envs/jetson_wake_word_env.md`를 새로 작성했다.
- `docs/README.md`, `docs/status.md`, `docs/jetson_transition_plan.md`, `docs/개발방침.md`, `docs/envs/wake_word_env.md`를 함께 갱신했다.

### Result

- Jetson runtime 기준 venv 경로:
  - `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson`
- ORT 검증 결과:
  - `RESULT: GPU_OK`
- 실제 session provider:
  - `['CUDAExecutionProvider', 'CPUExecutionProvider']`
- 문서 허브에서 Jetson env 문서를 바로 찾을 수 있게 됐다.
- 환경 변경 시 env 문서를 즉시 갱신한다는 기준이 `docs/개발방침.md`에 반영됐다.

---

## 2026-03-16 | Human + Codex | 개발 방침에 오버엔지니어링 금지 원칙 추가

### Context

- 사용자는 필요한 기능은 분명하게 구현하되, 처음부터 지나치게 많은 예외처리나 방어 코드를 넣는 스타일을 원하지 않는다고 명시했다.
- 특히 실제로 발생하지 않은 에러를 미리 상정해 복잡하게 만드는 것보다, 에러가 실제로 드러난 뒤 보고 수정하는 방향을 선호한다고 정리했다.

### Actions

- `docs/개발방침.md`에 `오버엔지니어링 금지 원칙`을 추가했다.
- 원칙 내용에는 아래를 반영했다.
  - 초기 구현은 주경로 우선
  - 추측성 예외처리와 fallback 최소화
  - 실제로 발생한 에러를 보고 필요한 만큼만 보강
  - 단, 데이터 손실/보안/복구 어려운 부작용은 최소 보호 장치 유지
- 같은 내용을 `docs/decisions.md`에도 의사결정으로 기록했다.

### Result

- 앞으로 이 프로젝트의 기본 구현 스타일은 `단순한 주경로 우선, 실제 에러 기반 보강`으로 명확히 문서화됐다.

---

## 2026-03-16 | Human + Codex | Jetson venv에서 ROS Python 경로 누수 차단

### Context

- `wake_word_jetson` venv 안에서 ROS2 패키지가 보이는 현상이 확인됐다.
- 확인 결과 이 문제는 이번 세션에서 새로 설치한 것이 아니라, 기존 Jetson 셸 설정에서 `/opt/ros/humble/setup.bash`가 자동 source되며 `PYTHONPATH`를 주입하던 영향이었다.
- 사용자는 이 내용은 작업 로그에는 남기되, 공식 셋업 문서에는 반영하지 않길 원했다.

### Actions

- `wake_word_jetson/bin/activate`를 수정해 활성화 시 ROS 관련 환경 변수와 `PYTHONPATH`가 venv 안으로 섞이지 않도록 정리했다.
- `deactivate` 시에는 원래 셸 값이 복원되도록 보완했다.
- 검증 시, 활성화 후에는 ROS 경로가 `sys.path`에서 사라지고 `deactivate` 후에는 원래 값이 돌아오는 것을 확인했다.
- 관련 설명은 셋업 문서에서 제거하고 이 `logbook`에만 남겼다.

### Result

- `wake_word_jetson`은 ROS2가 자동 source되는 셸에서도 독립 Python 환경으로 동작하게 됐다.
- 이 현상은 Jetson 기존 셸 설정 영향으로 분류하고, 공식 환경 세팅 절차 문서에는 포함하지 않았다.

---

## 2026-03-16 | Human + Codex | Jetson 실시간 wake word GUI demo 추가

### Context

- 사용자는 A100에서 학습한 wake word 모델을 Jetson에서 ONNX 가속으로 실제 마이크 입력에 연결하고, GUI에서 실시간으로 `하이 포포` 인식 score를 보고 싶어 했다.
- 필요한 UI는 기본 입력 마이크 확인, 실시간 게이지바, detection 상태, threshold 조정 정도의 단순한 형태를 원했다.

### Actions

- `wake_word/wake_word_gui_demo.py`를 새로 추가했다.
- `HiPopoWakeWordRealtime`를 마이크 입력과 연결해 raw audio -> ONNX feature extractor -> ONNX classifier 흐름으로 실시간 추론하도록 구현했다.
- GUI에는 아래 요소를 넣었다.
  - 기본 입력 마이크 정보
  - classifier / feature provider 정보
  - mic input level gauge
  - wake score gauge
  - threshold slider
  - `DETECTED / IDLE` 상태
  - 마지막 감지 시각
- 기존 `wake_word/wake_word_demo.py`는 feature `.npy` 입력용 CLI demo로 유지했다.
- `wake_word/__init__.py`에 `HiPopoWakeWordRealtime`와 `StreamingPrediction` export를 추가했다.
- `wake_word/README.md`, `docs/status.md`, `docs/jetson_transition_plan.md`, `docs/envs/jetson_wake_word_env.md`를 현재 상태에 맞게 갱신했다.

### Validation

- `python3 -m py_compile`로 관련 Python 파일 문법 검증을 통과했다.
- `wake_word_gui_demo.py --help`가 정상 출력되는 것을 확인했다.
- `PYTHONPATH=/home/everybot/workspace/ondevice-voice-agent/project/repo` 기준으로 `wake_word` 패키지 import가 정상인 것도 확인했다.

### Result

- Jetson에서 바로 띄워 볼 수 있는 실시간 GUI demo 진입점이 추가됐다.
- 현재 남은 핵심 작업은 실제 마이크 환경에서 score 분포를 보고 threshold를 현장 튜닝하는 것이다.

---

## 2026-03-16 | Human + Codex | runtime 파일명 정리와 함수 시그니처 단순화

### Context

- 사용자는 폴더명 `wake_word/`와 같은 이름의 파일 `wake_word.py`보다, 역할이 드러나는 별도 파일명이 더 낫다고 판단했다.
- 또한 함수 정의에 `-> list[str]` 같은 타입 힌트를 넣지 않는 쪽을 프로젝트 기본 스타일로 정하길 원했다.

### Actions

- `wake_word/wake_word.py`를 `wake_word/detector.py`로 옮겼다.
- `wake_word/__init__.py`와 관련 문서의 참조 경로를 `detector.py` 기준으로 정리했다.
- `wake_word/detector.py`와 `wake_word/wake_word_demo.py`에서 함수 시그니처 타입 힌트를 제거했다.
- `docs/개발방침.md`와 `docs/decisions.md`에 해당 원칙을 반영했다.

### Result

- 추론 모듈 파일명이 역할 중심으로 정리됐다.
- 새로 수정하는 runtime/demo 코드는 단순한 함수 시그니처 기준을 따르게 됐다.

---

## 2026-03-16 | Human + Codex | 함수 한국어 docstring 규칙과 ONNX timing 표시 추가

### Context

- 사용자는 지금까지 작성한 코드의 모든 함수 아래에 한국어 docstring을 넣고, `기능 / 입력 / 반환` 형식으로 친절하게 유지하길 원했다.
- 또한 Jetson GUI demo에서 `melspectrogram.onnx`, `embedding_model.onnx`, `hi_popo_classifier.onnx` 각각의 실행 시간을 직접 보고 싶어 했다.

### Actions

- `wake_word/`와 `wake_word/train/`의 함수들 아래에 한국어 docstring을 일괄 추가했다.
- `docs/개발방침.md`에 함수 docstring 작성 원칙을 추가했다.
- `wake_word/detector.py`에서 streaming 경로를 따라 `melspectrogram`, `embedding`, `classifier` ONNX 실행 시간을 따로 집계하도록 보강했다.
- `wake_word/wake_word_gui_demo.py`에 아래 표시를 추가했다.
  - chunk 크기와 classifier window 길이
  - `melspectrogram / embedding / classifier` ONNX 실행 시간
  - 전체 pipeline 처리 시간

### Result

- 함수 단위 설명이 코드 안에 직접 남게 됐다.
- Jetson GUI demo에서 ONNX 3개 각각의 실행 시간을 바로 확인할 수 있게 됐다.

---

## 2026-03-16 | Human + Codex | Jetson GUI demo 실기 확인 및 최종 문서 반영

### Context

- 사용자가 Jetson에서 `wake_word_gui_demo.py`를 직접 실행했고, 현재 데모가 실제로 잘 동작한다고 확인했다.
- 이에 따라 현재 working state와 timing 수치를 문서 기준에도 반영해, 다음 세션에서도 그대로 이어갈 수 있게 정리할 필요가 있었다.

### Actions

- `docs/status.md`에 Jetson GUI demo 실기 확인 상태를 반영했다.
- `docs/envs/jetson_wake_word_env.md`에 GUI 실행 확인 절차와 현재 timing 수치를 추가했다.
- `docs/project_overview.md`와 `wake_word/README.md`에 현재 실시간 ONNX 체인과 chunk/window 기준을 반영했다.
- synthetic chunk 기준 timing을 다시 측정했다.
  - `melspectrogram.onnx`: `1.52 ms`
  - `embedding_model.onnx`: `4.59 ms`
  - `hi_popo_classifier.onnx`: `1.03 ms`
  - total pipeline: `8.35 ms`

### Result

- 현재 기준 문서들에 Jetson GUI demo의 실제 작동 상태가 반영됐다.
- 다음 세션에서도 `80 ms chunk`, `1.28 s classifier window`, ONNX timing 확인 기준으로 바로 이어갈 수 있게 됐다.

### Update

- `wake_word_gui_demo.py`에 `tegrastats` 기반 Jetson 리소스 표시를 추가했다.
- 현재 GUI에서 `CPU 평균 / CPU 코어 / RAM / GPU(GR3D)` 상태를 실시간으로 같이 볼 수 있다.

---

## 2026-03-16 | Human + Codex | 문서 최신 상태 재동기화

### Context

- 사용자가 `wake_word/README.md`의 `다음 작업`에 이미 끝난 Jetson 구현 단계가 남아 있는 점을 지적했다.
- 이를 계기로 상위 README와 상태 문서, Jetson handoff 문서에도 같은 종류의 누락이 있는지 다시 점검할 필요가 생겼다.

### Actions

- 루트 `README.md`, `wake_word/README.md`, `docs/status.md`, `docs/project_overview.md`를 현재 코드 상태 기준으로 다시 읽었다.
- `docs/jetson_transition_plan.md`, `docs/envs/jetson_wake_word_env.md`, `docs/README.md`의 Jetson 관련 TODO 문구도 함께 재점검했다.
- 이미 완료된 항목은 완료 상태로 돌리고, 남은 작업은 아래 기준으로 다시 정리했다.
  - threshold / input gain 확정
  - hard negative / 일반 대화 오탐 점검
  - false accepts per hour 측정
  - 상위 SDK 연결 준비

### Findings

- 일부 문서는 여전히 `Jetson 실시간 추론`, `GUI demo`, `raw audio -> feature extractor -> classifier ONNX 연결`을 앞으로 할 일처럼 적고 있었다.
- 실제 코드 기준으로는 `wake_word/detector.py`, `wake_word/wake_word_gui_demo.py`, Jetson venv, ONNX GPU 검증이 이미 동작 중이다.
- GUI 리소스 표시는 현재 게이지가 아니라 `tegrastats` 기반 텍스트 표시가 최신 상태다.

### Result

- 현재 기준 문서들의 `다음 작업`과 `현재 목표`를 코드 상태와 맞췄다.
- Jetson 단계 문서는 “구현 예정” 중심에서 “구현 완료 + 남은 실기 검증” 중심으로 정리됐다.
- 다음 세션에서는 문서를 읽었을 때 곧바로 현재 남은 일만 따라가면 되도록 맞췄다.

---

## 2026-03-16 | Human + Codex | VAD 초기 구조 구현 시작

### Context

- 사용자는 다음 모듈로 VAD 개발을 시작하길 원했다.
- 데모는 사용성을 강조하기 위해 매우 단순해야 했고, 터미널에 `True / False`만 계속 보이길 원했다.
- 또한 `webrtcvad` 기반 VAD와 ONNX 기반 학습형 VAD를 같은 사용법으로 갈아끼울 수 있길 원했다.

### Actions

- `vad/README.md`, `docs/개발방침.md`, `docs/project_overview.md`, `docs/status.md`를 다시 읽고 현재 VAD 요구사항과 상위 구조 기준을 정리했다.
- `vad/detector.py`를 공통 진입점으로 추가했다.
- `vad/model_webrtcvad.py`와 `vad/model_silero.py`를 같은 `infer(audio_chunk) -> bool` 인터페이스로 구현했다.
- `vad/vad_demo.py`는 기본 마이크를 받아 현재 상태를 `True / False`만 출력하는 최소 데모로 정리했다.
- `vad/vad.py`는 제거하고, `vad/__init__.py`로 공통 export를 정리했다.
- VAD 시작 상태와 dual-backend 방침을 상위 문서에도 반영했다.

### Findings

- 현재 프로젝트 기준 샘플레이트는 `16kHz mono`로 고정하는 것이 가장 단순하다.
- `webrtcvad`는 바로 실행 가능한 시작점이고, Silero ONNX는 모델 파일만 준비되면 같은 인터페이스로 교체할 수 있다.
- 데모를 최소 형태로 유지하면 이후 상위 SDK에 붙일 때도 인터페이스가 더 깔끔하다.

### Result

- VAD 모듈의 첫 구조가 `detector.py + backend model 2개 + 초간단 demo` 형태로 잡혔다.
- 외부 사용자는 `VADDetector(model=\"webrtcvad\" | \"silero\")`와 `infer(audio_chunk)`만 알면 된다.
- 다음 단계는 실제 마이크로 `webrtcvad` 경로를 먼저 확인하고, 이후 Silero ONNX 모델 파일을 연결해 비교하는 것이다.

### Validation

- `python vad/vad_demo.py --model webrtcvad`를 짧게 실행해 기본 마이크에서 `True / False` 출력이 계속 갱신되는 것을 확인했다.
- `VADDetector(model="webrtcvad")`는 zero chunk 입력 기준 `False` 반환과 `status` 동기화가 확인됐다.
- 공식 Silero ONNX를 `vad/models/silero_vad.onnx`로 내려받았다.
- `VADDetector(model="silero")`는 zero chunk 입력 기준 `False` 반환과 `last_score` 갱신이 확인됐다.
- `python vad/vad_demo.py --model silero`도 기본 마이크에서 `True / False` 출력이 계속 갱신되는 것을 확인했다.

---

## 2026-03-16 | Human + Codex | Jetson 학습 smoke env 생성 및 최소 검증

### Context

- 사용자는 Jetson에서도 학습 코드가 실제로 도는지 불안해했다.
- 특히 `torch`와 `librosa`가 없는 상태라 `05_train.py`는 import 단계에서 막혀 있었고, `04_extract_features.py`도 현재 env 기준으로는 런타임 재검증이 필요했다.
- 추론용 `wake_word_jetson` env를 건드리지 않고, 학습 smoke 전용 venv를 별도로 만들기로 했다.

### Actions

- Jetson 현재 상태를 다시 확인했다.
  - JetPack: `6.2.1+b38`
  - L4T: `R36.4.7`
  - Python: `3.10.12`
  - CUDA toolkit: `12.6`
- NVIDIA 공식 PyTorch for Jetson 문서와 release notes, Jetson 공식 포럼의 JP6.2.1 설치 안내를 기준으로 `wake_word_train_smoke` venv를 만들었다.
- `torch==2.8.0`을 `https://pypi.jetson-ai-lab.io/jp6/cu126` 인덱스에서 설치했다.
- `librosa`, `soundfile`, `tqdm`, `numpy<2`를 함께 설치했다.
- feature extraction smoke를 위해 기존 Jetson의 `onnxruntime-gpu 1.23.0`을 `.pth` 방식으로 재사용 연결했다.
- `04_extract_features.py`는 zero clip 1개로 feature backbone smoke를 돌렸다.
- `05_train.py`는 temporary synthetic feature로 `1 epoch`만 실행했다.
- `06_export_onnx.py`도 smoke checkpoint 기준으로 끝까지 통과시켰다.
- smoke 검증 직후 synthetic feature와 `smoke_test` run은 삭제했고, `hi_popo_classifier.pt` 최신 포인터는 다시 `final_full_best_trial40` 기준으로 복구했다.

### Findings

- Jetson에서도 `torch.cuda.is_available()`는 `True`로 확인됐다.
- `04_extract_features.py`는 embedding provider `CUDAExecutionProvider`로 zero clip feature를 생성했다.
- `05_train.py`는 `cuda:0`에서 실제로 1 epoch를 완료했다.
- `06_export_onnx.py`도 ONNX 파일과 metadata JSON을 정상 생성했다.
- 즉 현재 Jetson에서는 학습 코드를 전혀 검증할 수 없는 상태가 아니라, 최소 smoke 수준까지는 재현 가능하다.

### Result

- Jetson 학습 smoke 전용 env 경로가 확정됐다.
  - `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke`
- 추론용 env와 학습 smoke env의 역할이 분리됐다.
- 다음부터는 Jetson에서 학습 관련 리팩토링을 건드려도, 최소한 `feature extraction -> train -> export` smoke까지는 바로 확인할 수 있게 됐다.

### Validation

- `torch 2.8.0`, `cuda_available=True`, `device_name=Orin`
- `onnxruntime 1.23.0`, provider에 `CUDAExecutionProvider` 포함
- `04_extract_features.py` smoke output shape `(1, 28, 96)`
- `05_train.py --device gpu --epochs 1` 완료
- `06_export_onnx.py` smoke checkpoint export 완료

---

## 2026-03-16 | Human + Codex | openWakeWord 실행 의존성 제거 및 재검증

### Context

- `wake_word/openWakeWord/`는 원래 참고용으로 두었지만, 실제로는 추론과 feature extraction 코드가 직접 import하고 있었다.
- 사용자는 이 clone을 지워도 학습과 추론이 깨지지 않는 상태를 원했다.

### Actions

- `melspectrogram.onnx`, `embedding_model.onnx`를 `wake_word/assets/feature_models/`로 옮겼다.
- `wake_word/features.py`를 추가해 feature backbone 호출 로직을 로컬 구현으로 정리했다.
- `wake_word/detector.py`, `wake_word/train/04_extract_features.py`, `wake_word/train/check_onnx_gpu.py`가 모두 새 로컬 모듈만 보도록 리팩토링했다.
- `wake_word/openWakeWord/` 폴더를 실제로 치운 상태에서 추론과 학습 smoke를 다시 실행했다.
- smoke 때문에 갱신된 최신 체크포인트 포인터는 다시 `final_full_best_trial40` 기준으로 복구했다.

### Findings

- 현재 wake word 실행에 필요한 것은 `features.py`와 feature backbone ONNX 2개, 그리고 classifier ONNX뿐이다.
- `openWakeWord` clone 없이도 `check_onnx_gpu.py`, realtime detector, `04_extract_features.py`, `05_train.py`, `06_export_onnx.py`가 모두 다시 통과했다.
- 따라서 지금 시점에는 `openWakeWord` 로컬 clone이 더 이상 실행 의존성이 아니다.

### Result

- wake word 추론과 feature extraction 경로가 로컬 구현으로 독립했다.
- `wake_word/openWakeWord/` clone은 제거했다.
- 문서와 환경 안내도 새 구조에 맞게 갱신했다.

### Validation

- `wake_word/train/check_onnx_gpu.py` 결과 `GPU_OK`
- `HiPopoWakeWordRealtime` zero chunk streaming smoke 통과
- `wake_word/wake_word_gui_demo.py --help` 통과
- `04_extract_features.py` zero clip smoke output `(1, 28, 96)`
- `05_train.py` 1 epoch smoke 통과
- `06_export_onnx.py` smoke export 통과

---

## 2026-03-16 | Human + Codex | VAD 기본 filtering 추가

### Context

- 사용자는 `webrtcvad` 데모가 조용한 사무실에서도 `True/False`로 흔들리는 점을 확인했다.
- 현재 `VADDetector`는 backend raw 판정을 그대로 외부에 반환하고 있었고, 최소 filtering도 없는 상태였다.

### Actions

- `vad/detector.py`에 연속 speech / silence frame 기반 filtering을 추가했다.
- 새 인자:
  - `min_speech_frames`
  - `min_silence_frames`
- 기본값:
  - `min_speech_frames=3`
  - `min_silence_frames=10`
- raw backend 결과는 `raw_status`로 따로 유지하게 했다.
- `vad/vad_demo.py`에도 같은 인자를 추가했다.
- 상태 문서와 결정 문서에 기본 filtering 기준을 기록했다.

### Findings

- `webrtcvad`는 raw frame 기준으로는 쉽게 흔들릴 수 있다.
- 하지만 시작/종료 방향에 서로 다른 연속 frame 기준을 주면, 적은 코드로도 체감 안정성이 꽤 좋아진다.

### Result

- VAD는 이제 backend raw 결과 위에 최소 hysteresis 레이어를 가진다.
- 기본 데모에서도 `webrtcvad`가 이전보다 덜 흔들리는 방향으로 정리됐다.

### Update

- 이후 사용자 실험 결과를 반영해 VAD 기본 백엔드는 `silero`로 변경했다.
- `webrtcvad`는 비교와 실험용 옵션으로만 유지한다.

---

## 2026-03-16 | Human + Codex | wake word / VAD 완료 기준으로 문서 재동기화

### Context

- 사용자는 wake word와 VAD 요소기술 개발이 끝난 현재 상태를 기준으로 모든 문서를 다시 맞추길 원했다.
- 추가로 Jetson에서 직접 찍은 wake word GUI와 VAD demo 스크린샷을 문서 안에서 바로 보이게 정리하길 원했다.

### Actions

- 루트 `README.md`, `wake_word/README.md`, `vad/README.md`, `docs/status.md`, `docs/project_overview.md`, `docs/개발방침.md`, `docs/README.md`, `docs/jetson_transition_plan.md`, `docs/research/wake_word.md`를 현재 완료 기준으로 다시 정리했다.
- `wake word 먼저 구현 중`, `VAD 초기 구현 시작`처럼 오래된 상태 표현을 제거했다.
- `docs/envs/jetson_wake_word_env.md`도 실제 사용 기준에 맞게 wake word/VAD demo 공용 runtime 문서로 갱신했다.
- 홈 디렉토리의 스크린샷 4장을 리포 안 `docs/assets/screenshots/jetson_demos/`로 복사하고 설명형 이름으로 정리했다.
  - `wake_word_gui_idle.png`
  - `wake_word_gui_detected.png`
  - `vad_demo_idle_terminal.png`
  - `vad_demo_speech_terminal.png`
- `wake_word/README.md`와 `vad/README.md`에 각 스크린샷과 설명을 추가했다.

### Findings

- 현재 문서에서 중요한 기준은 `wake word와 VAD가 각각 동작한다`가 아니라, `둘 다 요소기술 완료 상태이고 다음은 연동`이라는 점이다.
- 데모 화면은 모듈 README에서 직접 보이게 두는 편이 루트 문서보다 이해가 빠르다.

### Result

- 현재 문서 전체 기준은 `wake word 완료 + VAD 완료 + 다음은 튜닝/연동`으로 통일됐다.
- Jetson 데모 스크린샷도 이제 리포 안 문서 자산으로 함께 관리된다.

### Validation

- 문서 검색 기준으로 `VAD 초기 구현 시작` 같은 오래된 표현은 핵심 문서에서 제거했다.
- 스크린샷은 `wake_word/README.md`와 `vad/README.md`에서 바로 렌더링 가능한 상대 경로로 연결했다.

### Update

- 사용자가 이번 사이클의 소형 runtime ONNX는 예외적으로 리포에 포함하길 원했다.
- 이에 맞춰 `.gitignore`와 문서 문구를 조정해, 필요한 ONNX만 정확히 추적하고 대용량 학습 산출물은 계속 제외하는 방향으로 정리했다.

---

## 2026-03-16 | Human + Codex | Jetson 데모 자산 정리

### Context

- wake word와 VAD의 GUI 데모 영상을 문서에서 더 보기 좋게 보여줄 필요가 있었다.

### Actions

- wake word와 VAD mp4를 `docs/assets/videos/jetson_demos/` 아래 설명형 파일명으로 정리했다.
- 각 mp4에서 짧은 GIF 미리보기를 만들어 `docs/assets/gifs/jetson_demos/` 아래에 추가했다.
- `wake_word/README.md`, `vad/README.md`에서 GIF가 바로 보이고 클릭하면 원본 mp4가 열리도록 연결했다.
- `docs/assets/videos/jetson_demos/README.md`와 `docs/assets/gifs/jetson_demos/README.md`를 추가해 자산 위치와 역할을 명시했다.

### Result

- 모듈 README에서 Jetson 데모를 더 직관적으로 확인할 수 있게 됐다.
- 문서 자산 구조가 `screenshots / videos / gifs`로 나뉘어 더 찾기 쉬워졌다.
- `secrets/`는 어떤 경우에도 추적하지 않는 기준을 그대로 유지했다.
- 문서 흐름도 구현, 검증, 자산 정리에 집중하는 방향으로 단순해졌다.

---

## 2026-03-16 | Human + Codex | STT 초기 구조 구현 시작

### Context

- wake word와 VAD 요소기술 구현이 끝나면서 다음 단계로 STT 개발을 시작할 시점이 됐다.
- 현재 문서 기준으로는 `온디바이스 Whisper + API 백업 경로`를 같은 사용법으로 묶는 방향이 이미 정해져 있었다.

### Actions

- `stt/transcriber.py`를 추가해 공통 STT 진입점을 만들었다.
- `stt/stt_whisper.py`에 OpenAI Whisper 기반 온디바이스 백엔드를 구현했다.
- `stt/stt_api.py`에 OpenAI Audio Transcriptions API 백엔드를 구현했다.
- `stt/stt_demo.py`에 wav 파일 또는 짧은 마이크 녹음을 받아 텍스트를 출력하는 최소 데모를 추가했다.
- `stt/__init__.py`, `stt/README.md`, `docs/research/stt.md`를 추가/갱신해 현재 구조와 선택 이유를 기록했다.
- 상위 문서에서 STT 상태를 `구조만 확보`에서 `초기 구현 시작`으로 갱신했다.

### Result

- STT도 wake word/VAD와 비슷하게 `공통 래퍼 + backend 2개 + 최소 demo` 구조를 갖게 됐다.
- 현재 v1 기준으로는 짧은 utterance를 텍스트로 바꾸는 기본 경로를 붙일 준비가 됐다.

### Validation

- `python3 -m py_compile` 기준 STT 파일 문법 확인 완료
- `python stt/stt_demo.py --help` 확인 완료
- `wake_word_train_smoke` env에 `openai-whisper`, `openai` 설치 완료
- `tiny + cuda` 기준 예시 샘플 전사 결과 `하이포포` 확인
- 전사 시간은 약 `3.031 sec`
