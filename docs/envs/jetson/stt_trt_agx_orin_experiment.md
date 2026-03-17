# STT TRT 실험 환경(AGX Orin) 실행 가이드

> 목적: AGX Orin에서 Codex가 Jetson 스펙을 기준으로 WhisperTRT 빌드/평가를 재현하기 위한 실행 지침.

이 문서는 AGX Orin에서 작업할 때, 아래 경로의 코드를 기준으로 바로 재현 가능한 TRT 실험을 구성하는 용도다.

- 대상 스크립트: `stt/experiments/stt_trt_builder_experiment.py`
- 평가 스크립트: `stt/experiments/stt_trt_benchmark_experiment.py`
- 프로파일러: `stt/experiments/stt_trt_collect_jetson_profile.py`

## 1. Codex 시작 전 필수 규칙

Codex에게 다음을 바로 지시하고, 결과를 먼저 확인한다.

1. 현재 장비의 스펙을 프로파일로 저장한다.
2. 저장된 JSON을 읽고, CUDA/TensorRT/메모리 여유를 기준으로 빌드 옵션을 정한다.
3. 환경 준비가 끝난 후 `stt_trt_builder_experiment.py` step을 순차적으로 실행한다.

이 순서를 지키면 장비별 OOM 편차를 크게 줄일 수 있다.

## 2. 장비 스펙 수집 (AGX 기준)

아래 명령은 AGX 장비마다 달라지는 정보를 문서화한다.

```bash
cd /home/everybot/workspace/ondevice-voice-agent/project/repo
python stt/experiments/stt_trt_collect_jetson_profile.py \
  --output-dir /home/everybot/workspace/ondevice-voice-agent/project/results/jetson_trt_profiles \
  --tag agx_orin
```

실행 후 다음 두 파일이 생성된다.

- `/home/everybot/workspace/ondevice-voice-agent/project/results/jetson_trt_profiles/jetson_trt_profile_agx_orin_<YYYYMMDD_HHMMSS>.json`
- `/home/everybot/workspace/ondevice-voice-agent/project/results/jetson_trt_profiles/jetson_trt_profile_agx_orin_latest.json`

Codex는 `latest` 파일을 먼저 읽고 판단한다.

필수 확인 항목:

- `os.nv_tegra_release`
- `os.device_tree_model`
- `cuda_tensorrt.nvidia_smi`
- `power.nvpmodel`
- `package_versions.onnxruntime`, `package_versions.torch` 등 런타임 연동 버전
- `power.jetson_clocks_show`에서 EMC/Fan/GPU 고정 여부
- `os.meminfo`와 `storage` 용량
- `python_check.torch_is_available`와 `python_check.ort_providers`

## 3. AGX Orin 전용 TRT venv 구성

아래 경로는 예시이며, 필요 시 경로만 동일하게 바꿔도 된다.

- venv: `/home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment_agx`

```bash
python3 -m virtualenv /home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment_agx
source /home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment_agx/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir numpy==1.26.4 soundfile sounddevice psutil pydantic onnx>=1.17,<1.20
python -m pip install --no-cache-dir onnx_graphsurgeon
```

`torch`와 `whisper`는 Jetson의 기본 wheel/공식 경로가 맞는지 먼저 확인한다.

```bash
python - <<'PY'
import importlib.metadata as md
print('torch', md.version('torch'))
import torch
print('torch_cuda', torch.version.cuda)
print('torch_cuda_available', torch.cuda.is_available())
print('device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')
PY
```

실패할 경우 JetPack 버전에 맞는 index url/torch wheel을 별도 설치해야 한다.  
예를 들어 기존 환경에서 쓰던 인덱스가 `jp6/cu126`였다면 같은 조합을 우선 검증한다.

```bash
python -m pip install --no-build-isolation \
  git+https://github.com/NVIDIA-AI-IOT/torch2trt.git
python -m pip install --no-build-isolation \
  git+https://github.com/NVIDIA-AI-IOT/whisper_trt.git
```

> 설치 실패 시 경로 충돌이 흔하므로, 항상 `--no-build-isolation`으로 재시도한다.

## 4. AGX Orin용 builder 실행 전략

### 4-1. 시작값 (권장)

프로파일 확인 후 우선 아래 값으로 시작한다.

- `--model-name base`
- `--language ko`
- `--workspace-mb 128`
- `--max-text-ctx 64`

```bash
cd /home/everybot/workspace/ondevice-voice-agent/project/repo
source /home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment_agx/bin/activate
python stt/experiments/stt_trt_builder_experiment.py \
  --step run \
  --model-name base \
  --language ko \
  --work-dir /home/everybot/workspace/ondevice-voice-agent/project/results/stt_trt_split_agx_base_ctx64_ws128 \
  --workspace-mb 128 \
  --max-text-ctx 64 \
  --disable-fp16
```

### 4-2. 메모리 부족 징후 대응

`CUDA out of memory`, `Autotuning: User allocator` 같이 피크 에러가 나면 다음 순서로 하향 조정한다.

1. `--max-text-ctx 32` 시도
2. `--workspace-mb 64`
3. `--decoder-chunk-size`를 2 혹은 1로 줄여서 재시도
4. `--encoder-chunk-size`를 1 또는 2로 줄임
5. `--disable-lowmem-export` 토글을 마지막 수단으로 점검

### 4-3. AGX Orin에서 동일 checkpoint로 benchmark

```bash
python stt/experiments/stt_trt_benchmark_experiment.py \
  --checkpoint /home/everybot/workspace/ondevice-voice-agent/project/results/stt_trt_split_agx_base_ctx64_ws128/whisper_trt_split.pth \
  --model-name base \
  --language ko \
  --workspace-mb 128 \
  --max-text-ctx 64
```

성능 보고를 위해 `results` 폴더를 바로 확인하고, AGX 기준으로 따로 파일명을 남긴다.

## 5. 결과 정합성 점검 체크리스트 (Codex가 체크해야 할 항목)

빌드 후 Codex는 아래를 검증한다.

- builder 단계별 성공 메시지( `decoder`, `encoder`, `combine`, `load-check` )
- `combine` 후 `.pth` 파일 생성 여부
- `benchmark`의 `warmup` 유효 여부
- 1~3개 sample의 텍스트가 정상 문자열인지 (`[�]`가 아니어야 함)
- 최종 summary의 `summary.json` 존재

## 6. 실행 후 기록 갱신

- `docs/envs/stt_trt_experiment_env.md`에 실험 로그(값/오류/조정 파라미터)를 append
- `stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/README.md`의 재현 경로를 AGX 기준으로 갱신
- `stt/README.md`의 AGX 실습용 실행 예시를 최신 상태로 유지
- `docs/logbook.md`에 1~2줄로 실패/성공 요약만 기록

## 공식 기준

- NVIDIA TensorRT 및 Jetson 스택 문서: 공식 JetPack/딥러닝 문서를 기준으로 유지
- WhisperTRT 공식 문서: `https://github.com/NVIDIA-AI-IOT/whisper_trt`
- Torch2TRT 공식 문서: `https://github.com/NVIDIA-AI-IOT/torch2trt`

## Codex 실행 예시 (AGX Orin)

```text
/home/everybot/workspace/ondevice-voice-agent/project/repo/docs/envs/jetson/stt_trt_agx_orin_experiment.md
이 문서를 먼저 읽고, 아래 3개 명령을 순서대로 실행해.
- python stt/experiments/stt_trt_collect_jetson_profile.py ...
- source /home/everybot/workspace/ondevice-voice-agent/project/env/stt_trt_experiment_agx/bin/activate
- python stt/experiments/stt_trt_builder_experiment.py --step run ...
```
