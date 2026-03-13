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

---

## 2026-03-13 | Git 초기화 및 GitHub 첫 push

### Context

- 사용자는 원격 저장소에서 현재 작업 디렉토리를 관리 대상으로 올리길 원했다.
- 작성자 정보는 개인 계정 식별자가 직접 노출되지 않도록 로컬 전용 값으로 설정하기로 했다.

### Actions

- 루트 디렉토리에서 `git init`을 수행하고 기본 브랜치를 `main`으로 변경했다.
- 로컬 Git 작성자 정보를 공개용 일반 값으로 설정했다.
- 외부 clone인 `wake_word/openWakeWord/`는 embedded repo 문제를 피하기 위해 `.gitignore`에서 전체 제외했다.
- 로컬 설정 폴더 `.claude/`도 ignore에 추가했다.
- 첫 커밋 `Initial project import`를 생성했다.
- 기본 원격 `origin`을 설정하고 `main` 브랜치를 push했다.

### Result

- `origin/main` 첫 push 완료
- 현재 로컬 브랜치 `main`은 원격 `origin/main`을 추적한다

### Follow-up

- 사용자의 요청으로 `docs/개발방침.md`에 Git 연동 시 버전 관리 원칙을 추가했다.
- 원칙 내용은 코드 변경, 문서 변경, 추적 대상 점검을 같은 흐름 안에서 관리하도록 정리했다.

---

## 2026-03-13 | 루트 README 추가

### Context

- 사용자는 문서 허브용 `docs/README.md`와 별도로, 프로젝트 자체를 설명하는 루트 `README.md`가 필요하다고 요청했다.

### Actions

- 루트 `README.md`를 새로 추가했다.
- 내용은 프로젝트 개요, 현재 범위, 목표, 진행 상태, 구조, 문서 링크, 운영 원칙 중심으로 구성했다.
- `docs/README.md`는 문서 허브 역할로 유지하고, 루트 `README.md`가 상위 프로젝트 소개를 맡도록 역할을 분리했다.

---

## 2026-03-13 | GitLab remote 추가

### Context

- 사용자는 기본 원격 외에 내부 Git 원격도 함께 관리 대상으로 추가하길 원했다.

### Actions

- 내부 Git 원격을 `gitlab` 이름으로 추가했다.
- 로컬 Git alias `push-all`을 추가했다.
  - `git push origin main && git push gitlab main`
- SSH host key verification 문제를 해결하기 위해 내부 Git 서버 호스트 키를 `known_hosts`에 추가했다.

### Result

- remote 등록 완료
- `known_hosts` 등록 완료
- 초기에는 SSH 공개키 미등록 상태로 인해 push가 실패했다.

### Next

- 이 머신에서 사용할 SSH 키를 준비한 뒤 내부 원격 push를 다시 시도하기로 했다.

### Follow-up

- 이후 Git 운용 원칙을 추가로 정리했다.
- 중간 커밋은 작업 단위 기준으로 자율 수행하고, 원격 push는 항상 사용자 확인 후 진행한다.

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

## 2026-03-13 | Human + Codex | Markdown 링크를 GitHub 상대경로로 정리

### Context

- 사용자는 문서 안의 절대 로컬 경로 링크가 GitHub 웹에서 열리지 않는 문제를 지적했다.

### Actions

- 루트 `README.md`의 문서 링크를 상대경로 링크로 변경했다.
- `docs/project_overview.md` 안의 문서/스크립트 링크를 GitHub에서 열리는 상대경로로 바꿨다.
- 동시에 루트 `README.md`의 현재 진행 상태 문구도 최신 상태에 맞게 갱신했다.

### Result

- GitHub 웹에서 문서 링크가 정상 동작하는 구조로 정리됐다.
- 더 이상 `/data2/...` 절대경로 링크는 Markdown 파일에 남아 있지 않다.

---

## 2026-03-13 | Human + Codex | GitLab SSH 키 설정 정리

### Context

- 사용자는 내부 Git 원격 SSH push가 되지 않는 문제를 해결하려고 했다.

### Actions

- 현재 remote 설정과 SSH 상태를 확인했다.
- 기존에는 이 머신에 사용할 SSH 키가 없다는 것을 확인했다.
- 새 SSH 키를 생성했다.
- 내부 Git 서버 접속에 이 키를 쓰도록 SSH 설정을 추가했다.

### Result

- 로컬 SSH 키 준비 완료
- 초기 SSH test 결과, 서버에는 아직 공개키가 등록되지 않은 상태였다.

### Interpretation

- 현재 문제는 로컬 설정이 아니라, 생성한 공개키가 아직 내부 Git 계정에 등록되지 않은 상태라는 뜻이다.
- 다음 단계는 생성한 공개키를 SSH Keys에 등록하는 것이다.

### Follow-up

- 사용자가 공개키를 등록한 뒤 다시 SSH 테스트를 수행했다.
- 결과적으로 내부 Git 원격 SSH 인증은 정상 동작하게 됐다.

### Policy Update

- 이후 원격 반영은 `origin`과 `gitlab`에 같은 커밋을 같은 타이밍에 push하는 방식으로 운영하기로 했다.
- 단, push 자체는 계속 사용자 확인 후 진행한다.

---

## 2026-03-13 | Human + Codex | 공개 문서 민감 정보 일반화

### Context

- 사용자는 공개 문서 기준으로 내부 식별 정보나 불필요한 운영 상세가 남아 있지 않은지 마지막 검토를 요청했다.

### Actions

- 문서 전반에서 내부 원격 주소, 내부 계정 식별자, 로컬 SSH 경로, 고객사 직접 표현을 점검했다.
- 공개 문서에 불필요한 Git remote 상세와 SSH 설정 상세를 일반화했다.
- 개발 방침의 대외 민감도가 높은 표현을 더 일반적인 문장으로 조정했다.

### Result

- 최신 문서 기준으로는 내부 Git 서버 주소, 내부 사용자 식별자, 로컬 SSH 경로가 직접 노출되지 않게 정리됐다.
- 다만 이미 push된 과거 커밋 기록까지 완전히 숨기려면 별도의 history rewrite가 필요하다.

### Policy Update

- 이후 민감한 운영 메모가 꼭 필요하면 `secrets/` 아래의 로컬 전용 문서로 분리하고, 공개 문서에는 일반화한 내용만 남기기로 했다.

---

## 2026-03-13 | Human + Codex | 모듈별 README 연결 구조 추가

### Context

- 사용자는 루트 `README.md`에서 각 요소기술 설명 페이지로 바로 이동할 수 있길 원했다.
- 특히 `wake_word`는 현재 구현이 많이 진행된 만큼 별도 설명 페이지를 완성하길 원했다.

### Actions

- 루트 `README.md`에 각 모듈 설명 페이지 링크를 추가했다.
- 아래 디렉토리에 `README.md`를 새로 만들었다.
  - `wake_word/README.md`
  - `vad/README.md`
  - `stt/README.md`
  - `llm/README.md`
  - `tts/README.md`
- `wake_word/README.md`에는 현재 데이터 상태, best 모델, 핵심 지표, 주요 스크립트, 다음 작업을 정리했다.

### Result

- 이제 루트 `README.md`에서 각 요소기술 설명 페이지로 직접 이동할 수 있다.
- `wake_word`는 독립 README만 읽어도 현재 구현 상태와 다음 단계가 복구되도록 정리됐다.

---

## 2026-03-13 | Human + Codex | 원격 동기화를 위해 non-rewritten history로 재정렬

### Context

- 사용자는 민감 정보는 최신 문서에서 일반화하되, GitHub와 GitLab을 계속 함께 동기화할 수 있는 상태를 원했다.
- GitHub에는 rewritten history가 반영됐지만, GitLab `main`은 보호 브랜치라 force push가 거부됐다.

### Actions

- 실제 GitLab `main`을 다시 fetch해 기준 히스토리로 삼았다.
- 그 히스토리 위에 필요한 최신 공개 문서 변경만 정상 커밋으로 다시 얹는 방식으로 재정렬했다.
- 이 방식으로 두 원격이 다시 같은 커밋 라인을 공유하도록 복구하기로 했다.

### Result

- 민감한 운영 정보는 최신 문서 기준에서 일반화 유지
- 두 원격은 다시 같은 non-rewritten history 라인에서 동기화되도록 복구했다.
- GitLab `main`은 일반 push로 갱신했고, GitHub `main`은 한 번의 force push로 같은 커밋 라인에 맞췄다.

### Notes

- 보호 브랜치 force push가 풀리기 전까지는 history rewrite를 원격 정리 전략으로 사용하지 않는다.
