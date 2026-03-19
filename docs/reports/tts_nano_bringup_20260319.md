# Orin Nano TTS Bring-Up 2026-03-19

> 마지막 업데이트: 2026-03-19
> Nano host: `everybot@192.168.20.165`
> Nano result root: `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/`

## 목적

- `AGX Orin`에서 먼저 살린 4개 로컬 TTS 후보를 `Jetson Orin Nano`에서도 실제로 실행 가능한 상태로 만든다.
- 첫 목표는 속도 최적화가 아니라, `thin wrapper + split env + TTSSynthesizer` 구조를 유지한 채 4모델이 한 문장 이상 실제로 합성되게 만드는 것이다.
- 이후 ONNX, TensorRT, hybrid runtime 검토는 이 성공 경로 위에서만 진행한다.

## 환경 기준

- workspace root: `/home/everybot/workspace/ondevice-voice-agent`
- repo: `/home/everybot/workspace/ondevice-voice-agent/repo`
- env root: `/home/everybot/workspace/ondevice-voice-agent/env`
- 장비 모델:
  - `NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super`
- thin demo:
  - `tts/tools/tts_jetson_demo.py`

## 모델별 결과

| 모델 | 언어 | device | 결과 | model_load_sec | elapsed_sec | 메모 |
|---|---|---|---|---:|---:|---|
| `Piper` | EN | `cpu` | 성공 | `1.983` | `0.400` | 현재 Nano 기준 최경량 영어 local 경로 |
| `Kokoro` | EN | `cuda` | 성공 | `9.312` | `5.235` | GPU warm path는 동작, 첫 실행보다 많이 줄어든 상태 |
| `MeloTTS` | KO | `cpu` | 성공 | `4.274` | `15.057` | 한국어 local 경로는 가능하지만 실시간 후보로는 무거움 |
| `OpenVoice V2` | KO | `cpu` | 성공 | `16.201` | `39.795` | Nano에서도 reference cloning은 가능하지만 가장 무겁다 |

## 실패 후 우회 경로

- `OpenVoice V2`
  - Nano에서 `cuda` 기본 경로는 `NvMapMemAlloc error 12`, `CUDA out of memory`로 실패했다.
  - 따라서 Nano에서는 `cpu`가 현재 유일한 안정 경로다.
- `MeloTTS`
  - Nano `cuda` 경로는 이전 screening에서 `NvMapMemAlloc error 12`로 실패한 상태를 유지한다.
  - 현 시점에서 Nano 기본 경로는 `cpu`로 두는 편이 안전하다.

## 구현 메모

- Nano에서는 `tts_openvoice_v2_jetson`을 완전히 독립된 새 env로 복제하기보다, 검증된 `tts_melotts_jetson`에 OpenVoice extras를 얹는 실용 경로를 먼저 택했다.
- 현재 Nano `tts_openvoice_v2_jetson`은 `tts_melotts_jetson`을 가리키는 symlink다.
- `OpenVoice V2`가 실제로 필요로 하는 base MeloTTS가 같은 계열 의존성을 쓰기 때문에, 이 방식이 가장 빠르게 runtime을 살렸다.
- `tts/tools/tts_jetson_demo.py`는 이제 `/proc/device-tree/model`을 읽어 장비별 기본 device를 다르게 고른다.
  - `AGX Orin`: `melotts -> cuda`, `openvoice_v2 -> cuda`
  - `Orin Nano`: `melotts -> cpu`, `openvoice_v2 -> cpu`
  - `piper -> cpu`, `kokoro -> cuda`는 공통 유지
- 또 `openvoice_v2` 전용 env에 실제 `openvoice` 패키지가 없을 경우 `tts_melotts_jetson`으로 자동 fallback한다.

## 산출물 경로

- `Piper`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/piper/demo_cpu_recheck.wav`
- `Kokoro`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/kokoro/demo_cuda_recheck.wav`
- `MeloTTS`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/melotts/demo_cpu_recheck.wav`
- `OpenVoice V2`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/openvoice_v2/demo_cpu.wav`

## 파일 메타

- `Piper`
  - `22.05kHz mono`, `2.264 sec`
- `Kokoro`
  - `24kHz mono`, `3.000 sec`
- `MeloTTS`
  - `44.1kHz mono`, `4.613 sec`
- `OpenVoice V2`
  - `22.05kHz mono`, `5.190 sec`

## 현재 결론

- `Jetson Orin Nano`에서도 4개 로컬 후보를 모두 실제 합성 가능한 상태로 만들었다.
- 다만 실사용 shortlist는 여전히 아래로 좁혀진다.
  - 영어 local: `Piper cpu`, `Kokoro cuda`
  - 한국어 local: `MeloTTS cpu`, `OpenVoice V2 cpu`는 기능 확인 단계까지는 성공했지만 실시간 경로로는 무겁다.
- 따라서 다음 최적화 검토는 아래 순서가 맞다.
  1. `Piper`, `Kokoro`를 기준으로 Jetson 상위 voice pipeline 통합
  2. `MeloTTS`, `OpenVoice V2`는 ONNX, TensorRT, hybrid runtime, 더 가벼운 text frontend 분리 가능성 조사
  3. 실제 필요성이 확인된 뒤에만 더 공격적인 구조 변경을 진행
