# STT TRT 실험 환경 메모

## 목적

- Jetson Orin Nano 8GB에서 `WhisperTRT`가 실제로 올라가는지 확인한다.
- 기존 `Whisper PyTorch + CUDA`보다 더 빠른 로컬 STT 경로가 가능한지 탐색한다.
- 기존 프로젝트 env를 오염시키지 않고 별도 실험 환경에서만 확인한다.

## 실험 환경 경로

- venv: `/home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment`
- 기존 CUDA torch 재사용 원본:
  - `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke`

## 시스템 기준

- Jetson: `Jetson Orin Nano Developer Kit 8GB`
- CUDA: `12.6`
- cuDNN: `9.3`
- TensorRT: `10.3.0`

## 구성 방식

새 env는 완전 재설치 대신 아래 두 경로를 `.pth` 브리지로 읽는다.

- 시스템 TensorRT:
  - `/usr/lib/python3.10/dist-packages`
- 기존 smoke env의 torch / whisper:
  - `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke/lib/python3.10/site-packages`

이렇게 한 이유:

- Jetson용 CUDA torch는 이미 기존 smoke env에서 정상 동작이 확인돼 있다.
- TensorRT Python 바인딩은 JetPack 시스템 패키지로 이미 설치돼 있다.
- 새 실험 env에서는 TRT 관련 추가 패키지만 최소로 얹는 편이 더 안전하다.

## 추가 설치 패키지

- `numpy==1.26.4`
- `packaging`
- `psutil`
- `onnx>=1.17,<1.20`
- `onnx_graphsurgeon`
- NVIDIA 공식 `torch2trt`
- NVIDIA 공식 `whisper_trt`

설치 시 `torch2trt`, `whisper_trt`는 `--no-build-isolation`로 넣었다.

이유:

- build isolation이 켜지면 격리 빌드 환경에서 시스템 `tensorrt`를 못 보고 실패했다.

## 공식 기준

- WhisperTRT 공식 저장소:
  - https://github.com/NVIDIA-AI-IOT/whisper_trt
- torch2trt 공식 저장소:
  - https://github.com/NVIDIA-AI-IOT/torch2trt

## 실제 확인 결과

### 1. import 단계

아래 import는 모두 통과했다.

- `torch`
- `tensorrt`
- `onnx`
- `onnx_graphsurgeon`
- `torch2trt`
- `whisper_trt`

즉, TRT 실험을 시작할 수 있는 Python 환경 자체는 구성됐다.

### 2. 첫 blocker

공식 `load_trt_model("base.en")`를 그대로 호출하면 ONNX trace 단계에서 아래 오류가 발생했다.

- `scaled_dot_product_attention(): argument 'is_causal' must be bool, not Tensor`

해석:

- 현재 `torch 2.8`과 `openai-whisper` 조합에서 SDPA 경로가 `whisper_trt`의 trace 과정과 바로 맞지 않았다.

대응:

- `whisper.model.MultiHeadAttention.use_sdpa = False`로 강제해 fallback attention 경로로 우회했다.

### 3. 두 번째 blocker

SDPA를 끈 뒤에는 실제 TensorRT 엔진 생성 단계까지 진행됐지만, `base.en`에서 아래 오류로 중단됐다.

- `NvMapMemAllocInternalTagged ... error 12`
- `TensorRT resizingAllocator ... Cuda Runtime (out of memory)`

추가 확인:

- `BaseEnBuilder.max_workspace_size`를 `256MB`까지 줄여 다시 시도했지만 동일하게 OOM이 발생했다.

## 현재 결론

- `WhisperTRT` 실험 환경 자체는 구성됐다.
- 그러나 현재 Jetson Orin Nano 8GB 조건에서는 `base.en` TensorRT 엔진 빌드를 아직 통과시키지 못했다.
- 즉, 현재 blocker는 의존성 미설치가 아니라 **엔진 생성 시점의 GPU 메모리 한계** 쪽으로 보는 것이 맞다.

## 현재 판단

- 현 시점의 STT 기본 경로는 계속 `Whisper base (PyTorch + CUDA)`로 유지하는 편이 안전하다.
- `WhisperTRT`는 환경 재현 경로는 확보했지만, `base.en` 빌드 성공 전까지는 정식 후보로 올리지 않는다.
- 이후 다시 시도한다면 아래부터 검토한다.
  1. 더 작은 모델(`tiny.en`)로 엔진 생성 교차 확인
  2. 메모리 더 여유 있는 Jetson 조건에서 `base.en` 재시도
  3. `base.en` 대신 다국어 모델을 바로 건드리기 전에 공식 영어 경로부터 안정화
