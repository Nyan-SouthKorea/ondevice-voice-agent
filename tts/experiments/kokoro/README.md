# Kokoro Experiment

목표:

- A100에서 `Kokoro`를 공통 인터페이스 아래에 붙인다.
- 경량 모델 구조와 ONNX 경로의 실용성을 확인한다.

현재 상태:

- A100 env `../env/tts_kokoro` 생성 완료
- `TTSSynthesizer(model="kokoro", ...)` backend 연결 완료
- 공식 영어 smoke 통과
- 공식 language code 기준 한국어 미지원 확인

1차 산출물:

- `TTSSynthesizer(model="kokoro", ...)` 형태의 backend
- 한국어 처리 가능성, latency, 음질 비교 기록

중점 평가:

- 한국어 품질 실측
- 경량성 대비 체감 자연스러움
- ONNX/양자화 경로의 운영 편의성
- Jetson 이전 가능성

현재 smoke 메모:

- 공식 repo/model:
  - `hexgrad/Kokoro-82M`
- 공식 language code:
  - `a`, `b`, `e`, `f`, `h`, `i`, `p`, `j`, `z`
  - alias 기준 `en-us`, `en-gb`, `es`, `fr-fr`, `hi`, `it`, `pt-br`, `ja`, `zh`
- 현재 smoke:
  - language: `a`
  - voice: `af_heart`
  - output: `../results/tts/20260318_kokoro_smoke/hello_en.wav`
  - `model_load_sec 15.646`
  - `elapsed_sec 2.941`
  - output length: `4.600 sec`
- SDK smoke:
  - output: `../results/tts/20260318_kokoro_smoke/sdk_import.wav`
  - `model_load_sec 3.524`
  - `elapsed_sec 1.138`
- CLI smoke:
  - output: `../results/tts/20260318_kokoro_smoke/demo_cli.wav`
  - `model_load_sec 3.403`
  - `elapsed_sec 1.231`

현재 구현 메모:

- backend는 현재 official `hexgrad/Kokoro-82M` 단일 repo 기준으로 연결했다.
- `model_name`은 language code로 쓰고, `voice`는 `af_heart` 같은 Kokoro voice 이름을 받는다.
- `ko`, `ko-kr`, `korean`을 넣으면 backend가 공식 미지원이라고 바로 에러를 낸다.
- 첫 영어 실행에서는 `en_core_web_sm`가 자동 설치됐다.
- 현재 env에서는 `espeakng-loader`가 같이 설치되어 system `espeak-ng` 없이도 공식 영어 경로가 동작했다.

현재 판단:

- A100 비교 후보로는 유효하다.
- 하지만 공식 Korean path가 없으므로, 현 시점의 한국어 제품 기본 후보로는 올리지 않는다.
