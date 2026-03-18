# Jetson TTS Screening 2026-03-18

> 마지막 업데이트: 2026-03-18
> Jetson result root: `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/`

## 목적

- `OpenVoice V2`를 제외한 TTS 후보를 Jetson Orin Nano 8GB에서 실제로 실행해 본다.
- A100 benchmark 결과와 별개로, Jetson 제약에서 어떤 경로가 실제 runtime 후보가 되는지 좁힌다.
- benchmark 코드와 충돌하지 않도록 `TTSSynthesizer + thin wrapper + split env` 구조를 유지한다.

## 환경 메모

- repo: `/home/everybot/workspace/ondevice-voice-agent/repo`
- env root: `/home/everybot/workspace/ondevice-voice-agent/env`
- thin demo: `tts/tools/tts_jetson_demo.py`
- 공통 진입점: `TTSSynthesizer`
- `OpenVoice V2`는 이번 Jetson screening에서 제외했다.

## 모델별 결과

| 모델 | 언어 | device | 결과 | model_load_sec | elapsed_sec | 메모 |
|---|---|---|---|---:|---:|---|
| `Edge TTS` | KO | network | 성공 | `0.000` | `2.213` | network fallback, 실제 WAV 저장 |
| `OpenAI API TTS` | KO | network | 성공 | `0.000` | `2.087` | 품질 reference, 비용/네트워크 의존 |
| `Piper` | EN | `cpu` | 성공 | `2.281` | `0.463` | 현재 Jetson 영어 최속 후보 |
| `Piper` | EN | `cuda:0` | 성공 | `2.545` | `1.802` | system ORT CUDA provider 사용, 짧은 문장에서는 CPU보다 느림 |
| `MeloTTS` | KO | `cuda:0` | 실패 | - | - | `NvMapMemAlloc error 12`, CUDA allocator assert |
| `MeloTTS` | KO | `cpu` cold | 성공 | `6.424` | `105.405` | 최초 실행은 checkpoint, BERT, MeCab 자산 다운로드 포함 |
| `MeloTTS` | KO | `cpu` warm | 성공 | `3.974` | `19.569` | 반복 실행도 실시간 후보로는 무거움 |
| `Kokoro` | EN | `cuda` cold | 성공 | `16.804` | `41.600` | 최초 실행은 model, voice, spaCy model 다운로드 포함 |
| `Kokoro` | EN | `cuda` warm | 성공 | `7.594` | `2.013` | warm run 기준 영어 local 후보 가치 높음 |

## 산출물 경로

- `Edge TTS`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/edge_tts/demo.wav`
- `OpenAI API TTS`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/openai_api/demo.wav`
- `Piper`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/piper/demo_cpu.wav`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/piper/demo_gpu.wav`
- `MeloTTS`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/melotts/demo_cpu.wav`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/melotts/demo_cpu_warm.wav`
- `Kokoro`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/kokoro/demo.wav`
  - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/kokoro/demo_warm.wav`

## 파일 메타

- `Edge TTS`
  - `24kHz mono`, `5.088 sec`
- `OpenAI API TTS`
  - `24kHz mono`, `4.800 sec`
- `Piper cpu`
  - `22.05kHz mono`, `2.356 sec`
- `Piper gpu`
  - `22.05kHz mono`, `2.659 sec`
- `MeloTTS cpu`
  - `44.1kHz mono`, `4.566 sec`
- `MeloTTS cpu warm`
  - `44.1kHz mono`, `4.636 sec`
- `Kokoro`
  - `24kHz mono`, `3.000 sec`

## 기술 메모

- `Piper`
  - Jetson 전용 env에서는 pip가 끌어온 CPU `onnxruntime`를 제거해야 system `CUDAExecutionProvider` / `TensorrtExecutionProvider`를 다시 볼 수 있었다.
  - 다만 짧은 영어 문장에서는 GPU 경로보다 CPU 경로가 더 빨랐다.
- `MeloTTS`
  - Jetson에서는 GPU 적재 시 메모리 부족으로 바로 실패했다.
  - CPU 경로는 동작하지만 warm run도 약 `19.6s`라 현재 Jetson 실시간 응답용으로는 무겁다.
- `Kokoro`
  - 첫 실행은 모델, voice, `en_core_web_sm` 다운로드 비용이 크다.
  - warm run 기준 `2.013s`까지 떨어져 영어 local 후보로 유지할 가치가 있다.

## 현재 결론

- Jetson 영어 local shortlist:
  - `Piper (cpu)`
  - `Kokoro (cuda)`
- Jetson 한국어 local 후보:
  - 현재 screening 기준으로 즉시 채택 가능한 경로가 없다.
  - `MeloTTS`는 동작은 가능하지만 Jetson Orin Nano 8GB 실시간 후보로는 무겁다.
- network fallback:
  - `Edge TTS`
  - `OpenAI API TTS`
- 따라서 다음 상위 voice pipeline 통합은 아래 순서가 맞다.
  1. 영어 local demo는 `Piper cpu`와 `Kokoro cuda`를 비교 유지
  2. 한국어는 일단 network fallback을 유지
  3. 영어 local 품질이 우세하면 이후 custom training 계획을 검토

