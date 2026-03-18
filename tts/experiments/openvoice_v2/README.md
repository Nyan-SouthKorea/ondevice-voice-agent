# OpenVoice V2 Experiment

목표:

- A100에서 `OpenVoice V2`를 공통 인터페이스 아래에 붙인다.
- zero-shot voice cloning이 실제 고객 시연 품질을 얼마나 올리는지 본다.

현재 상태:

- A100 env `../env/tts_openvoice_v2` 생성 완료
- `TTSSynthesizer(model="openvoice_v2", ...)` backend 연결 완료
- reference 음성 기반 한국어 smoke 통과
- 동일 reference 재사용 시 `se.pth` cache를 읽도록 보완 완료

1차 산출물:

- `TTSSynthesizer(model="openvoice_v2", ...)` 형태의 backend
- reference voice 유무에 따른 품질 비교 결과

현재 smoke 메모:

- checkpoint root:
  - `../results/tts_assets/openvoice_v2/checkpoints_v2`
- reference cache:
  - `../results/tts_assets/openvoice_v2/processed`
- reference audio:
  - `/tmp/openvoice_official_8kKMEz/resources/example_reference.mp3`
- 첫 SDK smoke:
  - output: `../results/tts/20260318_openvoice_v2_smoke/hello_kr.wav`
  - `model_load_sec 16.185`
  - `elapsed_sec 13.327`
  - total wall `34.442 sec`
- CLI smoke:
  - output: `../results/tts/20260318_openvoice_v2_smoke/demo_cli.wav`
  - `model_load_sec 12.149`
  - `elapsed_sec 10.528`
- cache 재사용 CLI smoke:
  - output: `../results/tts/20260318_openvoice_v2_smoke/demo_cli_cached.wav`
  - `model_load_sec 10.771`
  - `elapsed_sec 7.115`

중점 평가:

- voice identity 반영 정도
- 한국어 발화 자연스러움
- 2-stage 추론에 따른 latency와 메모리 비용
- Jetson 적용 가능성

현재 구현 메모:

- base TTS는 `MeloTTS(language='KR')`를 사용한다.
- tone conversion은 `checkpoints_v2/converter`를 사용한다.
- source speaker embedding은 `base_speakers/ses/kr.pth`를 사용한다.
- 공통 인터페이스에서는 `reference_audio_path`만 추가로 요구한다.
