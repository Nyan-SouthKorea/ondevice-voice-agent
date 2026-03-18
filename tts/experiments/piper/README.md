# Piper Experiment

목표:

- A100에서 `Piper`를 공통 인터페이스 아래에 붙인다.
- 경량 ONNX 계열 TTS로서 속도와 운영 단순성을 확인한다.

현재 상태:

- A100 env `../env/tts_piper` 생성 완료
- `TTSSynthesizer(model="piper", ...)` backend 연결 완료
- 공식 영어 voice 기준 smoke 통과
- 서드파티 한국어 model `neurlang/piper-onnx-kss-korean`은 로드/합성까지는 되지만 품질 무효
- ORT CUDA provider는 runtime preload 보정 후 A100에서 정상 확인

1차 산출물:

- `TTSSynthesizer(model="piper", ...)` 형태의 backend
- 한국어 지원 가능성, 음질, latency 기록

현재 smoke 메모:

- asset root:
  - `../results/tts_assets/piper`
- 현재 확인 voice:
  - `en_US-lessac-medium`
- 공식 기본 voice 목록:
  - 한국어 없음
- 서드파티 한국어 모델:
  - `../results/tts_assets/piper/neurlang_kss_korean/piper-kss-korean.onnx`
  - 라이선스 표기: `CC-BY-NC-SA-4.0`
- 첫 smoke:
  - output: `../results/tts/20260318_piper_smoke/hello_en.wav`
  - output length: `3.808 sec`
- SDK smoke:
  - output: `../results/tts/20260318_piper_smoke/sdk_import.wav`
  - `model_load_sec 1.572`
  - `elapsed_sec 1.300`
  - providers: `CUDAExecutionProvider`, `CPUExecutionProvider`
- CLI smoke:
  - output: `../results/tts/20260318_piper_smoke/demo_cli.wav`
  - `model_load_sec 1.551`
  - `elapsed_sec 1.268`
- 한국어 SDK smoke:
  - output: `../results/tts/20260318_piper_korean_smoke/sdk_import.wav`
  - `model_load_sec 2.150`
  - `elapsed_sec 1.550`
  - providers: `CUDAExecutionProvider`, `CPUExecutionProvider`
  - `raw_phoneme_type pygoruut`
- 한국어 CLI smoke:
  - output: `../results/tts/20260318_piper_korean_smoke/demo_cli.wav`
  - `model_load_sec 2.384`
  - `elapsed_sec 1.446`
- 한국어 품질 디버깅:
  - `pygoruut 0.7.0`은 `안녕하세요 -> 녕 + 안하세요`처럼 분절이 깨졌다
  - `pygoruut v0.6.2` + word phonetic 기준이 그나마 가장 나았지만, STT 역전사 기준으로도 `"파이퍼 한국어 테스트입니다"`를 안정적으로 재현하지 못했다
  - 현재 Python 경로 비교 결과:
    - `../results/tts/20260318_piper_runtime_compare_16k/python_sdk_16k.wav`
    - 역전사: `안녕하세요. 투페이파 하이단국가리 테스다시입니다.`
  - `piper-rs` 원 저자 lockfile 경로 결과:
    - `../results/tts/20260318_piper_korean_rust_smoke/wav_text_locked.wav`
    - 역전사: `안녕하세요. 카이퍼 땡구그린의 습들입니다.`
  - `piper-rs` + `pygoruut_version=v0.6.2` 경로는 현재 rustruut가 해당 goruut 실행 파일을 찾지 못해 재현되지 않았다

중점 평가:

- 한국어 품질 확보 가능 여부
- ONNX 기반 운영 단순성
- warm/cold latency
- Jetson 실기 경량성

현재 구현 메모:

- `model_name`은 Piper voice code 또는 로컬 `.onnx` 경로를 받는다.
- `checkpoint_root`는 voice 다운로드/캐시 루트로 사용한다.
- `voice`는 multi-speaker voice용 speaker id 정수만 받는다.
- GPU 경로는 `onnxruntime.preload_dlls(directory='')` 후 `PiperVoice.load(..., use_cuda=True)`로 연다.
- `phoneme_type=pygoruut` custom model은 `pygoruut`를 설치하고, backend 안에서 phonemizer 호환 레이어를 통해 로드한다.
- backend는 config에 `pygoruut_version`이 있으면 그 값을 우선 사용하고, 없으면 한국어에 한해 `v0.6.2`를 기본 시도한다.
- 이 한국어 모델은 현재 smoke와 비교 연구에는 유효하지만, 현재 품질과 모델 페이지 라이선스 `CC-BY-NC-SA-4.0` 때문에 상용 후보로 바로 두지는 않는다.
