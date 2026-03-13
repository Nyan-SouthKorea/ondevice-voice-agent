# Logbook

이 문서는 사람과 AI 도구를 포함한 작업 로그를 시간순으로 기록한다.

---

## 2026-03-12 | Human + Codex | 문서 기준 정리 및 기록 체계 개편

### Context

- 사용자는 Claude Code에서 진행하던 프로젝트를 Codex와 병행하기 시작했다.
- `docs`를 먼저 읽고 현재 프로젝트 기준을 파악해달라고 요청했다.

### Actions

- `docs/README.md`, `docs/개발방침.md`, `docs/envs/wake_word_env.md`
- `docs/archive/01_env_setup_claude.md`, `02_positive_data_claude.md`, `03_negative_data_claude.md`
- `docs/research/wake_word.md`, `tts_korean.md`, `negative_datasets.md`
- 실제 디렉토리와 학습 스크립트 상태를 함께 확인했다.
- `하이 케어로봇`으로 남아 있던 문서를 `하이 포포` 기준으로 수정했다.
- negative 전략을 `AI Hub + MUSAN + FSD50K` 기준으로 수정했다.
- 과거 AI 도구별 메모는 `docs/archive/`로 이동해 보관했다.
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

---

## 2026-03-13 | GitHub 공개용 .gitignore 정리

### Context

- 사용자는 현재 프로젝트를 GitHub에 올릴 계획이고, 대용량 데이터셋과 학습 산출물, secrets가 함께 존재한다.

### Actions

- 루트 `.gitignore`를 공개용 기준으로 보강했다.
- 주요 제외 대상:
  - `secrets/`
  - `.env`, `.env.*`
  - Python 캐시와 editor 파일
  - `wake_word/data/`
  - `wake_word/models/`
  - `wake_word/openWakeWord/.git/`

### Notes

- 이 설정은 코드/문서/스크립트만 리포에 남기고, 데이터와 모델 산출물은 제외하는 보수적 기준이다.
- 이후 공개용 오디오 샘플은 `third-party dataset`가 아니라 직접 생성한 TTS만 `examples/audio_samples/` 아래에 두는 방향으로 정리했다.
- 이에 맞춰 `.gitignore`에 `examples/audio_samples/` 예외 경로를 추가했다.

### Follow-up

- `examples/audio_samples/positive_tts/`를 실제로 만들고, 직접 생성한 TTS 샘플 3개를 복사했다.
- `examples/audio_samples/README.md`를 추가해 포함 원칙과 샘플 목록을 명시했다.
