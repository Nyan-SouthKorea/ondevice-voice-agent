# AGX Orin TTS Bring-Up 2026-03-19

> 마지막 업데이트: 2026-03-19
> AGX host: `everybot@192.168.20.173`
> AGX result root: `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/`

## 목적

- `Jetson Orin Nano` 적용 전에 `AGX Orin`에서 TTS 4개 로컬 후보를 먼저 실제 실행 가능한 상태로 만든다.
- 방식은 고정하지 않고, `CUDA`, `CPU`, `ONNXRuntime`, dependency patch 등 가장 빠른 현실 경로를 우선한다.
- 기존 benchmark 코드와 충돌하지 않도록 `TTSSynthesizer + split env` 구조는 유지한다.

## 환경 기준

- workspace root: `/home/everybot/workspace/ondevice-voice-agent`
- repo: `/home/everybot/workspace/ondevice-voice-agent/repo`
- env root: `/home/everybot/workspace/ondevice-voice-agent/env`
- results root: `/home/everybot/workspace/ondevice-voice-agent/results`
- 장비: `AGX Orin`, `JetPack 6.2 / R36.4.7`, Python `3.10.12`

## 모델별 결과

| 모델 | 언어 | device | 결과 | model_load_sec | elapsed_sec | 메모 |
|---|---|---|---|---:|---:|---|
| `Piper` | EN | `cpu` | 성공 | `1.206` | `0.269` | AGX 기준 즉시 실행 가능, ORT CPU 경로 |
| `Kokoro` | EN | `cuda` | 성공 | `13.340` | `2.752` | `Pillow>=10` 보강 후 성공 |
| `MeloTTS` | KO | `cpu` | 성공 | `1.546` | `10.504` | 초기 안전 smoke |
| `MeloTTS` | KO | `cuda:0` | 성공 | `2.315` | `5.428` | `torchaudio` ABI mismatch를 repo fallback으로 우회 |
| `OpenVoice V2` | KO | `cuda:0` | 성공 | `9.542` | `10.640` | AGX 기준 reference voice cloning 경로 성공 |

## 핵심 시행착오

- `MeloTTS`
  - Jetson global CUDA torch와 env 안 `torchaudio` ABI가 맞지 않아 import에서 깨졌다.
  - `tts/backends/melotts.py`에 `torchaudio` 최소 stub fallback을 넣어 해결했다.
- `OpenVoice V2`
  - 새 env를 맨땅에서 만들면 `MeloTTS` 하위 의존성이 다시 꼬였다.
  - 가장 빠른 경로는 검증된 `tts_melotts_jetson` env를 복제한 뒤 OpenVoice extras만 추가하는 방식이었다.
  - `faster-whisper` 설치 과정에서 `numpy 2.x`가 들어와 `librosa/scipy`가 깨져 `numpy==1.26.4`로 다시 고정했다.
  - `wavmark`는 `--no-deps`로만 설치해 constructor import를 만족시켰다.

## 산출물 경로

- `Piper`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/piper/demo_cpu.wav`
- `Kokoro`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/kokoro/demo_cuda.wav`
- `MeloTTS`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/melotts/demo_cpu.wav`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/melotts/demo_cuda_fixed.wav`
- `OpenVoice V2`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/openvoice_v2/demo_cuda.wav`

## 현재 결론

- AGX Orin에서는 4개 로컬 후보를 모두 실제 실행 가능한 상태로 만들었다.
- 다음 단계는 이 성공 경로를 `Orin Nano`에 최소 변경으로 이식하는 것이다.
- 우선순위는 아래 순서로 둔다.
  1. `Piper`, `Kokoro`, `MeloTTS`, `OpenVoice V2`를 Nano env에 반영
  2. `tts/tools/tts_jetson_demo.py` 기준으로 Nano smoke 재현
  3. 필요 시 Nano 전용 `ONNX/TRT` 또는 더 공격적인 경량화 검토
