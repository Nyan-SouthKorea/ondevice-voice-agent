# Jetson Wake Word Runtime Env

> 마지막 업데이트: 2026-03-13
> 목적: Jetson Orin Nano에서 wake word ONNX 추론을 위한 로컬 venv와 검증 절차를 관리한다.

## 1. 이 문서의 역할

이 문서는 Jetson 런타임 환경 문서다.

- 위치: `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson`
- 용도: `wake_word` 실시간 ONNX 추론과 CUDA provider 검증
- 성격: Linux 서버 학습 환경 문서가 아니라 Jetson 배포/검증용 로컬 venv 문서

학습 환경은 아래 문서를 본다.

- `docs/envs/wake_word_env.md`

## 2. 공식 기준

Jetson의 CUDA / TensorRT / JetPack 기본 스택은 NVIDIA 공식 문서를 기준으로 유지한다.

- JetPack 설치/구성 공식 문서:
  - https://docs.nvidia.com/jetson/jetpack/install-setup/index.html
- JetPack 문서 루트:
  - https://docs.nvidia.com/jetson/jetpack/
- ONNX Runtime for Jetson 관련 NVIDIA 공식 배경 자료:
  - https://developer.nvidia.com/blog/announcing-onnx-runtime-for-jetson/

현재 운영 원칙:

- Ubuntu 일반 CUDA 패키지를 별도로 덮어쓰지 않는다.
- Jetson에 이미 맞춰진 JetPack/CUDA/TensorRT 조합을 기준으로 간다.
- venv 안에서 ONNX Runtime을 임의로 다시 바꾸기보다, 현재 Jetson에서 검증된 ORT를 우선 재사용한다.
- ORT 버전이나 설치 위치가 바뀌면 이 문서와 검증 결과를 즉시 갱신한다.

## 3. 현재 확인된 시스템 상태

2026-03-13 기준 확인값:

- Jetson L4T: `R36.4.7`
- Python: `3.10.12`
- venv 이름: `wake_word_jetson`
- venv 경로: `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson`
- Jetson ORT 패키지:
  - package: `onnxruntime-gpu`
  - version: `1.23.0`
  - location: `/home/everybot/.local/lib/python3.10/site-packages`
- 시스템에서 보이는 provider:
  - `TensorrtExecutionProvider`
  - `CUDAExecutionProvider`
  - `CPUExecutionProvider`

실기 검증 결과:

- 검증 명령:
  - `python wake_word/train/check_onnx_gpu.py`
- 결과:
  - `RESULT: GPU_OK`
- 실제 세션 provider:
  - `['CUDAExecutionProvider', 'CPUExecutionProvider']`

즉 현재 이 Jetson에서는 ONNX Runtime CUDA provider 세션 생성이 정상이다.

## 4. 환경 이름과 경로

이 환경 이름은 `wake_word_jetson`으로 고정한다.

이유:

- 학습용 conda 환경명 `wake_word`와 구분된다.
- 현재 phase가 wake word + Jetson runtime 검증이므로 목적이 분명하다.
- 나중에 상위 SDK 환경을 따로 만들더라도 역할이 섞이지 않는다.

## 5. 세팅 절차

## 5-1. virtualenv 준비

기본 `python3 -m venv`가 바로 되지 않는 경우가 있어, 현재는 `virtualenv`를 사용자 영역에 설치해 사용한다.

```bash
python3 -m pip install --user virtualenv
python3 -m virtualenv /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson
```

## 5-2. Jetson ORT 재사용 연결

현재 Jetson에는 `onnxruntime-gpu 1.23.0`이 사용자 site-packages에 이미 설치되어 있고, CUDA provider 검증도 통과했다.

따라서 새 venv에는 아래 `.pth` 파일로 기존 Jetson ORT를 참조시킨다.

파일:

- `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/lib/python3.10/site-packages/jetson_user_site.pth`

내용:

```text
/home/everybot/.local/lib/python3.10/site-packages
```

이 방식의 의미:

- Jetson에서 이미 맞춰진 ORT/CUDA 조합을 그대로 재사용
- venv는 프로젝트별 패키지와 실행 경로를 분리
- ORT를 임의 wheel로 다시 덮어쓰는 리스크를 줄임

## 5-3. venv 활성화

```bash
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/bin/activate
```

## 5-4. 런타임 최소 패키지 설치

현재 `wake_word.py`와 `check_onnx_gpu.py` 실행 기준으로 필요한 최소 패키지는 아래다.

```bash
python -m pip install --prefer-binary requests tqdm scipy scikit-learn soundfile
```

비고:

- `onnxruntime-gpu`는 현재 Jetson의 기존 설치를 재사용한다.
- `openwakeword`는 로컬 repo의 `wake_word/openWakeWord/`를 코드 경로로 직접 사용한다.

## 6. 검증 절차

### 6-1. ORT import 및 provider 확인

```bash
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/bin/activate
python - <<'PY'
import onnxruntime as ort
print("version", ort.__version__)
print("providers", ort.get_available_providers())
print("path", ort.__file__)
PY
```

기대값:

- version: `1.23.0`
- providers 안에 `CUDAExecutionProvider` 포함

### 6-2. 실제 CUDA session 생성 확인

```bash
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/bin/activate
python /home/everybot/workspace/ondevice-voice-agent/project/repo/wake_word/train/check_onnx_gpu.py
```

기대값:

- `RESULT: GPU_OK`

`GPU_FALLBACK` 또는 `GPU_FAILED`가 나오면:

1. JetPack/CUDA/TensorRT 상태부터 확인
2. ORT 설치 위치와 버전 확인
3. 이 문서의 현재 상태 섹션과 결과를 갱신

## 7. 다음 작업에서의 사용 기준

Jetson에서 다음 작업은 이 venv를 기준으로 진행한다.

- `wake_word/wake_word.py`
- `wake_word/wake_word_demo.py`
- 마이크 입력 연결
- raw audio -> feature extractor -> classifier ONNX 연결
- GUI/CLI 실시간 score 확인

## 8. 문서 업데이트 규칙

아래가 바뀌면 같은 세션에서 이 문서를 바로 갱신한다.

- JetPack 버전
- L4T 버전
- CUDA / TensorRT 상태
- ORT 버전 또는 설치 위치
- venv 경로 또는 이름
- 설치 패키지 목록
- 검증 명령
- `GPU_OK / GPU_FALLBACK / GPU_FAILED` 결과

함께 점검할 문서:

- `docs/README.md`
- `docs/status.md`
- `docs/jetson_transition_plan.md`
- `docs/개발방침.md`
- `docs/logbook.md`
