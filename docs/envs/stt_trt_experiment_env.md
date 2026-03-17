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

## 실험용 코드

- 분리 빌드 스크립트:
  - `stt/stt_trt_builder_experiment.py`

이 스크립트는 아래 순서로 동작한다.

1. decoder 엔진을 별도 프로세스로 빌드해 저장
2. encoder 엔진을 별도 프로세스로 빌드해 저장
3. 중간 산출물을 최종 checkpoint로 합치기
4. 합쳐진 checkpoint가 실제로 load 가능한지 확인

즉, 기존 `whisper_trt`의 단일 프로세스 builder 대신, 피크 메모리를 줄이기 위해 `encoder / decoder / combine / load-check`를 분리했다.

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

### 4. 분리 빌드 결과

단일 builder 대신 `stt/stt_trt_builder_experiment.py`로 `decoder -> encoder -> combine -> load-check`를 분리한 뒤에는 `base.en` 공식 경로가 실제로 통과했다.

확인된 결과:

- `decoder` 빌드 성공
  - 약 `79.627 sec`
- `encoder` 빌드 성공
  - 약 `154.023 sec`
- 최종 checkpoint 생성 성공
  - `whisper_trt_split.pth`
- checkpoint load 성공
  - `WhisperTRT`
  - 약 `2.255 sec`

생성된 중간 산출물 예:

- `decoder_engine.pt`
- `decoder_extra.pt`
- `encoder_engine.pt`
- `encoder_extra.pt`
- `whisper_trt_split.pth`

해석:

- Jetson Orin Nano 8GB에서 `base.en`이 아예 불가능한 것은 아니었다.
- 문제는 모델 자체가 아니라, 기존 단일 프로세스 builder의 빌드 피크 메모리였다.
- `encoder / decoder`를 분리하고 프로세스를 끊어 주면 `base.en` 공식 TensorRT checkpoint까지 만들 수 있다.

### 5. 영어 전사 smoke

생성한 split checkpoint로 영어 샘플 wav를 실제 전사했다.

- checkpoint load: 약 `2.144 sec`
- transcribe: 약 `2.612 sec`
- 결과 텍스트 정상 출력 확인

이 단계는 한국어 성능 검증이 아니라, `WhisperTRT base.en` 경로가 실제 로드와 추론까지 이어진다는 기술적 확인용이다.

### 6. 다국어 `base` 한국어 경로 1차 시도

`stt/stt_trt_builder_experiment.py`에 아래 실험 경로를 추가해 다국어 `base`를 한국어 tokenizer 기준으로 다시 시도했다.

- `--model-name base`
- `--language ko`

추가로 decoder 메모리를 줄이기 위해 아래 옵션도 실험했다.

- `--max-text-ctx 128`, `--workspace-mb 256`
- `--max-text-ctx 64`, `--workspace-mb 128`

1차 결과:

- 다국어 `base`는 split builder 기준으로도 처음에는 **decoder 단계에서 OOM**이 났다.
- 즉, 영어 전용 `base.en`은 split build로 통과했지만, 한국어 다국어 `base`는 처음엔 같은 방식으로 바로 이어지지 않았다.

확인된 OOM 메시지 예:

- `autotuning: User allocator error allocating 21504000-byte buffer`
- `region '__mye103221-consts' allocation failed` (`50438400 bytes`)
- `Requested size was 100872448 bytes`

해석:

- 다국어 `base`는 영어 전용 `base.en`보다 decoder 빌드 피크 메모리 요구량이 더 크다.
- 처음에는 `max_text_ctx`와 workspace를 줄여도 현재 Jetson Orin Nano 8GB 조건에서 decoder 빌드가 통과하지 않았다.

### 7. 다국어 `base` 한국어 경로 2차 시도

split builder 내부에서 아래 두 지점을 추가로 줄였다.

- `write_dims()`와 tokenizer 판별용 `whisper.load_model()`을 CPU로만 로드
- decoder 빌드 직후 엔진을 저장하고 바로 해제한 뒤, extra state는 CPU 모델로 다시 읽음
- decoder `mask` 입력 shape를 `dims.n_text_ctx` 전체가 아니라 `max_text_ctx` 기준으로 실제 축소
- 최종 checkpoint의 `dims.n_text_ctx`, `positional_embedding`, `mask`도 `max_text_ctx`에 맞춰 함께 축소

이후 재부팅 직후 조건에서 아래 설정으로 다시 시도했다.

- `--model-name base`
- `--language ko`
- `--workspace-mb 128`
- `--max-text-ctx 64`

2차 결과:

- `decoder` 성공
  - 약 `85.672 sec`
- `encoder` 성공
  - 약 `152.262 sec`
- `combine` 성공
- `load-check` 성공
  - `WhisperTRT`
  - 약 `2.176 sec`

생성된 checkpoint 예:

- `/home/everybot/workspace/ondevice-voice-agent/project/results/stt_trt_split_base_ko_ctx64_ws128_patch2/whisper_trt_split.pth`

### 8. 한국어 smoke / benchmark

다국어 `base`는 upstream `WhisperTRT.transcribe()`를 그대로 쓰면 `sot` 하나만 넣고 시작해서, `<|translate|>` 토큰이 섞이거나 번역 경로로 빠지는 문제가 있었다.

그래서 한국어 평가에서는 아래 시작 토큰을 직접 넣는 custom transcribe 경로를 썼다.

- `tokenizer.sot_sequence_including_notimestamps`

1~3번 smoke 결과:

- load: `2.1037 sec`
- sample `001`: `0.4259 sec`
- sample `002`: `0.2809 sec`
- sample `003`: `0.2101 sec`

50문장 전체 benchmark 결과:

- 결과 디렉토리:
  - `/home/everybot/workspace/ondevice-voice-agent/project/results/stt_trt_eval_results/korean_eval_50/20260317_112711`
- code-generated summary 기준:
- `mean_stt_sec 0.2115`
- `p95_stt_sec 0.2946`
- `mean_rtf 0.0435`
- `normalized_exact_match_rate 0.1600`
- `mean_normalized_cer 0.1759`

### 9. `small` 한국어 경로 가능성 확인

`small`은 같은 split builder를 그대로 쓰면 모델을 GPU에 올리는 단계에서 먼저 실패했다.

그래서 builder 내부를 추가로 조정했다.

- 빌드용 Whisper 모델을 CPU에서 `half()`로 줄인 뒤 GPU에 적재
- `LayerNorm`만 다시 `float()`로 유지

이후 확인된 점:

- `small` 모델 자체를 GPU에 올리는 단계는 통과했다.
- 즉, 이전처럼 "모델 로드 자체가 불가능한 상태"는 벗어났다.

하지만 decoder split build는 현재도 통과하지 못했다.

확인한 조건:

- `--model-name small`
- `--language ko`
- `--workspace-mb 128`
- `--max-text-ctx 64`

결과:

- ONNX export / constant folding 단계에서 다시 `CUDACachingAllocator` 계열 오류가 났다.

더 공격적인 조건:

- `--workspace-mb 64`
- `--max-text-ctx 32`

결과:

- TRT decoder 빌드 단계에서 다시 OOM이 났다.
- 확인된 메시지 예:
  - `autotuning: User allocator error allocating 30031872-byte buffer`
  - `Could not find any implementation for node ...`

현재 해석:

- `small`은 메모리 최적화를 조금 더 하면 가능성이 완전히 0은 아니다.
- 다만 현 시점 Jetson Orin Nano 8GB 조건에서는 `base`처럼 바로 실용 경로로 가져가기는 아직 어렵다.
- 즉, 지금은 `base` TRT 경로를 먼저 활용하는 편이 맞다.

## 현재 결론

- `WhisperTRT` 실험 환경 자체는 구성됐다.
- `base.en` 공식 경로는 기본 builder 그대로는 OOM이 났지만, 분리 빌드 방식으로는 checkpoint 생성과 로드까지 성공했다.
- 즉, 현재 핵심은 TensorRT 자체 지원 여부가 아니라 **빌드 전략**이다.
- 한국어 다국어 `base` 경로도 현재는 split builder + `max_text_ctx 64` 기준으로 checkpoint 생성과 benchmark까지 성공했다.

## 현재 판단

- 현 시점의 STT 기본 경로는 계속 `Whisper base (PyTorch + CUDA)`로 유지하는 편이 안전하다.
- 이유:
  - 한국어 `WhisperTRT base`는 속도는 확실히 빨라졌지만, 현재 code-generated 수치 기준으로는 정확도가 PyTorch `base(cuda)`보다 약간 불리하다.
  - `Whisper base (PyTorch + CUDA)`
    - `mean_stt_sec 0.7428`
    - `mean_rtf 0.1526`
    - `normalized_exact_match_rate 0.1800`
    - `mean_normalized_cer 0.1653`
  - `WhisperTRT base`
    - `mean_stt_sec 0.2115`
    - `mean_rtf 0.0435`
    - `normalized_exact_match_rate 0.1600`
    - `mean_normalized_cer 0.1759`
- 다만 `WhisperTRT`는 이제 Jetson에서 영어 전용 경로뿐 아니라, 한국어 `base` 경로도 실제 checkpoint 생성과 benchmark까지 되는 경로로 본다.
- 이후 다시 시도한다면 아래부터 검토한다.
  1. custom transcribe 시작 토큰 처리를 실험 코드가 아니라 공식 래퍼 형태로 옮기기
  2. default stream 경고를 없애는 CUDA stream 경로 검토
  3. `max_text_ctx 64`가 긴 문장에서 주는 영향 확인
