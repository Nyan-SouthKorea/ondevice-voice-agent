# Jetson TTS Env

> 목적: Jetson 계열 장비에서 TTS 후보를 backend별 split env로 검증하기 위한 구조와 실행 순서를 고정한다.

## 기본 원칙

- Jetson에서는 처음부터 모든 TTS 의존성을 한 env에 넣지 않는다.
- 먼저 backend별 smoke env를 분리해 실제 설치 가능성과 추론 가능성을 확인한다.
- 그 다음에만 최종 채택 후보를 상위 통합 env로 올린다.
- benchmark 코드는 A100 기준 per-backend env 구조를 유지하므로, Jetson 쪽도 같은 철학을 따른다.
- 공통 SDK 이름은 계속 `TTSSynthesizer`로 유지하되, backend import는 env 분리 친화적으로 정리한다.

## 이번 단계 범위

- 포함:
  - `MeloTTS`
  - `OpenVoice V2`
  - `Piper`
  - `Kokoro`
  - `Edge TTS`
  - `OpenAI API TTS`

## 왜 env를 나누는가

- 현재 TTS 후보는 의존성 차이가 크다.
- Jetson에서 가장 먼저 확인할 것은 "좋은 구조"가 아니라 "실제로 설치되고, 실제로 한 문장을 말할 수 있는가"다.
- `TTSSynthesizer`가 lazy import를 지원하면, 각 env는 자기 backend 의존성만 갖고도 같은 SDK 진입점을 쓸 수 있다.
- 이 방식이면 benchmark harness와 Jetson runtime 실험이 서로 덜 충돌한다.

## 권장 env 이름

- `../env/tts_network_jetson`
  - `Edge TTS`, `OpenAI API TTS`
- `../env/tts_melotts_jetson`
  - `MeloTTS`
- `../env/tts_openvoice_v2_jetson`
  - `OpenVoice V2`
- `../env/tts_piper_jetson`
  - `Piper`
- `../env/tts_kokoro_jetson`
  - `Kokoro`

메모:
- `Orin Nano`에서는 가장 빠른 bring-up을 위해 `tts_openvoice_v2_jetson`을 `tts_melotts_jetson` 기반 shared env 또는 symlink로 두는 실용 경로를 허용한다.
- `AGX Orin`처럼 여유가 있는 장비에서는 별도 env를 유지하는 편이 더 깔끔하다.
- 현재 `tts/tools/tts_jetson_demo.py`는 `openvoice_v2` 실행 시 전용 env에 `openvoice` 패키지가 실제로 없으면 `tts_melotts_jetson`으로 자동 fallback한다.

## Jetson TTS 진행 순서

1. repo 최신화
2. TTS SDK lazy import 반영 여부 확인
3. `tts_network_jetson` 생성 후 `Edge TTS`, `OpenAI API TTS` smoke
4. `tts_melotts_jetson` 생성 후 한국어 smoke
5. `tts_openvoice_v2_jetson` 생성 후 reference voice smoke
6. `tts_piper_jetson` 생성 후 영어 smoke
7. `tts_kokoro_jetson` 생성 후 영어 smoke
8. 모델별 추론 시간, 메모리, 실패 원인 기록
9. 최종 채택 후보만 상위 voice pipeline 통합 대상으로 올림

## demo 원칙

- demo는 `tts/tts_demo.py` 공통 CLI를 유지한다.
- Jetson 전용 helper가 필요하면 wrapper script를 따로 두고, backend별 env python으로 `tts_demo.py`를 호출한다.
- 즉 demo wrapper는 추가할 수 있지만, backend 구현이나 benchmark 코드를 갈아엎지 않는다.

## 현재 기대 결과

- `Edge TTS`, `OpenAI API TTS`:
  - 네트워크 경로이므로 설치 난이도는 낮다.
- `MeloTTS`:
  - 한국어 주력 local 후보라 Jetson에서 가장 먼저 검증한다.
- `Piper`:
  - 영어 경량 후보로 검증 가치가 높다.
- `Kokoro`:
  - 영어 품질/속도 우수 후보지만 Jetson aarch64 설치 난이도는 직접 확인이 필요하다.

## 2026-03-18 screening 결과

- 결과 보고서:
  - `docs/reports/tts_jetson_screening_20260318.md`
- Jetson 산출물 루트:
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/`

### env별 관찰

- `../env/tts_network_jetson`
  - `Edge TTS`, `OpenAI API TTS` 성공
  - local GPU 최적화 대상은 아니고, network fallback/demo 경로로 유지
- `../env/tts_piper_jetson`
  - 공식 영어 voice 성공
  - pip가 설치한 CPU `onnxruntime`를 제거해 system CUDA/TensorRT provider를 다시 보게 해야 했다
  - 짧은 영어 문장에서는 `cpu`가 `cuda:0`보다 더 빨랐다
- `../env/tts_melotts_jetson`
  - `MeloTTS` 자체는 설치 성공
  - GPU 경로는 `NvMapMemAlloc error 12`로 실패
  - CPU 경로는 성공하지만 warm run도 약 `19.6s`라 Jetson 실시간 후보로는 무겁다
- `../env/tts_kokoro_jetson`
  - warm GPU 경로가 성공했고 `elapsed_sec 2.013`까지 내려왔다
  - 첫 실행에는 model, voice, `en_core_web_sm` 다운로드 비용이 크다

### 당시 제외 대상

- `OpenVoice V2`
  - 2026-03-18 Orin Nano 1차 screening에서는 제외했다.
  - 이후 AGX Orin bring-up에서 별도로 올렸다.

## 2026-03-19 AGX bring-up 결과

- 상세 결과:
  - `docs/reports/tts_agx_bringup_20260319.md`
- AGX result root:
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/`

### env별 관찰

- `../env/tts_melotts_jetson`
  - `MeloTTS`는 CPU, CUDA 둘 다 성공
  - `torchaudio` ABI mismatch는 repo fallback으로 우회
- `../env/tts_openvoice_v2_jetson`
  - 가장 빠른 재현 경로는 검증된 `tts_melotts_jetson` env를 복제한 뒤 OpenVoice extras를 추가하는 방식이었다
  - `numpy==1.26.4`를 유지해야 `librosa/scipy`가 안 깨진다
  - `wavmark==0.0.3`는 `--no-deps`로만 설치해 constructor import를 만족시켰다
  - 한국어 reference smoke가 CUDA에서 성공했다
- `../env/tts_piper_jetson`
  - AGX에서도 영어 CPU smoke가 즉시 성공했다
- `../env/tts_kokoro_jetson`
  - AGX CUDA smoke가 성공했다

### 현재 권장 device

- 공통
  - `edge_tts`: network
  - `openai_api`: network
  - `piper`: `cpu`
  - `kokoro`: `cuda`
- `AGX Orin`
  - `melotts`: `cuda`
  - `openvoice_v2`: `cuda`
- `Orin Nano`
  - `melotts`: `cpu`
  - `openvoice_v2`: `cpu`

현재 `tts/tools/tts_jetson_demo.py`는 `/proc/device-tree/model`을 읽어 위 장비별 기본 device를 자동으로 고른다. 필요한 경우 `--device`로 덮어쓴다.

## 2026-03-19 Orin Nano 4모델 bring-up 결과

- 상세 결과:
  - `docs/reports/tts_nano_bringup_20260319.md`

### env별 관찰

- `../env/tts_piper_jetson`
  - 영어 CPU smoke 재검증 성공
  - `model_load_sec 1.983`
  - `elapsed_sec 0.400`
- `../env/tts_kokoro_jetson`
  - 영어 CUDA smoke 재검증 성공
  - `model_load_sec 9.312`
  - `elapsed_sec 5.235`
- `../env/tts_melotts_jetson`
  - 한국어 CPU smoke 재검증 성공
  - `model_load_sec 4.274`
  - `elapsed_sec 15.057`
- `../env/tts_openvoice_v2_jetson`
  - Nano에서는 `cuda`가 `NvMapMemAlloc error 12`로 실패
  - `cpu` 경로는 성공
  - `model_load_sec 16.201`
  - `elapsed_sec 39.795`

### 현재 해석

- `Orin Nano`에서도 4개 로컬 후보 모두 실제 합성까지는 도달했다.
- 다만 `MeloTTS`, `OpenVoice V2`는 현재 기준으로는 기능 확인용 성공이고, 실시간 후보는 아니다.
- 실제 Jetson shortlist는 계속 아래가 맞다.
  - 영어 local: `Piper cpu`, `Kokoro cuda`
  - 한국어는 network fallback 유지, 혹은 더 공격적인 경량화/변환 경로를 별도 검토

## 성공 기준

- 각 후보가 최소 1문장 이상 Jetson에서 실제 합성된다.
- 실패한 후보는 실패 원인이 문서화된다.
- 성공한 후보는 `TTSSynthesizer` 또는 thin demo wrapper로 바로 다시 실행할 수 있다.
- 다음 단계에서 어떤 후보를 상위 통합 env로 올릴지 판단할 수 있다.
