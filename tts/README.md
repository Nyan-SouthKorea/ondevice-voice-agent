# TTS

이 디렉토리는 text-to-speech 계층 자리다.

현재 상태:

- 초기 구조 시작
- 공통 TTS 래퍼와 API 기반 최소 합성 경로를 추가했다.
- `OpenAI API TTS`는 `api`, `openai_api`, `chatgpt_api` alias로 호출 가능하게 정리했다.
- wake word positive 생성에 쓰던 TTS는 Amazon이 아니라 `Edge TTS`였고, `edge_tts` backend로 공통 인터페이스에 연결했다.
- `MeloTTS` backend를 A100에서 첫 번째로 붙였고, 한국어 smoke를 통과했다.
- `OpenVoice V2` env와 backend를 A100에 붙였고, reference 음성 기반 한국어 smoke를 통과했다.
- `Piper` env와 backend를 A100에 붙였고, 공식 영어 voice smoke를 통과했다.
- `Piper` 서드파티 한국어 모델은 로드와 합성까지는 되지만, 현재 Python 경로 기준 품질은 무효로 판단한다.
- `Piper` 서드파티 한국어 모델은 `piper-rs` 원 저자 lockfile 경로까지 확인했지만, 현재 기준으로는 제품성 있는 한국어 품질을 재현하지 못했다.
- `Kokoro` env와 backend를 A100에 붙였고, 공식 영어 smoke를 통과했다.
- `Kokoro`는 현재 공식 language code 기준 한국어를 지원하지 않는다.
- 현재 프로젝트의 다음 우선 개발 대상은 TTS다.

예상 역할:

- LLM 또는 명령 처리 결과를 음성으로 변환
- 온디바이스 가능 여부와 라이선스를 함께 고려한 엔진 선택

현재 구현 구조:

- `tts.py`
  - 공통 진입점
  - `TTSSynthesizer(model="api")`
- `backends/`
  - 실제 runtime backend 코드
  - 현재 구현: `OpenAI Audio Speech API`, `Edge TTS`, `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`
- `experiments/`
  - 후보 엔진별 실험 메모와 계획
- `evaluation/`
  - 공통 문장셋과 비교 기준
- `tts_demo.py`
  - 텍스트를 받아 오디오 파일로 저장하는 최소 데모

공통 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="melotts",
    model_name="KR",
    voice="KR",
    device="cuda:0",
)
path = synthesizer.synthesize_to_file("안녕하세요. 테스트를 시작합니다.", "tts_outputs/test.wav")
print(path)
print(synthesizer.model_load_sec)
print(synthesizer.last_duration_sec)
```

OpenAI API alias 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="openai_api",
    model_name="gpt-4o-mini-tts",
    voice="alloy",
)
path = synthesizer.synthesize_to_file("안녕하세요. API TTS 테스트입니다.", "tts_outputs/openai_api_test.wav")
print(path)
```

Edge TTS 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="edge_tts",
    voice="ko-KR-InJoonNeural",
    rate="+8%",
    pitch="+0Hz",
)
path = synthesizer.synthesize_to_file(
    "안녕하세요. Edge TTS 한국어 테스트입니다.",
    "tts_outputs/edge_tts_test.wav",
)
print(path)
```

OpenVoice V2 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="openvoice_v2",
    model_name="KR",
    voice="KR",
    device="cuda:0",
    reference_audio_path="/tmp/openvoice_official_8kKMEz/resources/example_reference.mp3",
)
path = synthesizer.synthesize_to_file(
    "안녕하세요. OpenVoice V2 한국어 테스트입니다.",
    "tts_outputs/openvoice_test.wav",
)
print(path)
print(synthesizer.model_load_sec)
print(synthesizer.last_duration_sec)
```

Piper 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="piper",
    model_name="en_US-lessac-medium",
    device="cuda:0",
)
path = synthesizer.synthesize_to_file(
    "Hello from Piper.",
    "tts_outputs/piper_test.wav",
)
print(path)
print(synthesizer.model_load_sec)
print(synthesizer.last_duration_sec)
```

서드파티 한국어 Piper 모델 실험 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="piper",
    model_name="/data2/iena/260318_ondevice-voice-agent/results/tts_assets/piper/neurlang_kss_korean/piper-kss-korean.onnx",
    device="cuda:0",
)
path = synthesizer.synthesize_to_file(
    "안녕하세요. 파이퍼 한국어 테스트입니다.",
    "tts_outputs/piper_korean_test.wav",
)
print(path)
print(synthesizer.model_load_sec)
print(synthesizer.last_duration_sec)
```

직접 실행:

```bash
cd /data2/iena/260318_ondevice-voice-agent/repo
source /data2/iena/260318_ondevice-voice-agent/env/tts_melotts/bin/activate
python tts/tts_demo.py \
  --model melotts \
  --model-name KR \
  --voice KR \
  --device cuda:0 \
  --text "안녕하세요. TTS 테스트를 시작합니다." \
  --output /data2/iena/260318_ondevice-voice-agent/results/tts/20260318_melotts_smoke/hello.wav
```

Jetson thin demo:

```bash
cd /home/everybot/workspace/ondevice-voice-agent/repo
python tts/tools/tts_jetson_demo.py --model piper
python tts/tools/tts_jetson_demo.py --model kokoro
```

- `tts_jetson_demo.py`는 backend별 Jetson env python을 골라 `tts/tts_demo.py`를 호출한다.
- 현재 Jetson 권장 기본 device는 아래와 같다.
  - `melotts`: `cpu`
  - `piper`: `cpu`
  - `kokoro`: `cuda`
  - `edge_tts`, `openai_api`: network
- 필요하면 `--device`로 직접 덮어쓴다.

현재 v1 방향:

- 빠른 end-to-end 연결용:
  - `OpenAI API TTS`
- wake word 데이터 생성 / reference baseline:
  - `Edge TTS`
- 온디바이스 기본 후보:
  - `MeloTTS`

현재 고민과 판단:

- 고객 시연에서는 문장 내용보다도 목소리 인상, 자연스러운 속도, 로봇 같지 않은 질감이 완성도 판단에 크게 영향을 준다.
- 하지만 최종 런타임은 Jetson에서 `Wake word + VAD + STT + TTS + 기타 CV 모델`이 함께 도는 구성이므로, TTS가 너무 무겁거나 메모리를 많이 먹으면 전체 시스템이 흔들린다.
- A100에서는 학습과 실험을 충분히 할 수 있지만, 제품 방향은 결국 Jetson 실시간성 기준으로 판단해야 한다.
- 현재 repo 안에 있는 TTS 관련 데이터는 wake word positive 생성용 합성 음성뿐이다.
  - 공개 샘플은 `wake_word/examples/audio_samples/positive_tts/` 아래 3개뿐이다.
  - 로컬 학습용 생성 데이터는 `wake_word/data/hi_popo/positive/tts/` 아래 1125개가 있다.
  - 이 데이터는 `"하이 포포"` 계열 짧은 문구 중심이라, 대화형 한국어 TTS 음색 학습 데이터셋으로 바로 쓰기에는 부족하다.
- 따라서 지금 단계에서 가장 중요한 것은 "최고 연구 성능"이 아니라 "좋은 목소리 하나를 빠르게 온디바이스 경로로 고정하는 것"이다.
- 다만 A100에서는 Jetson보다 제약이 적으므로, 초기 탈락 판단을 너무 빨리 하지 않고 후보 4개를 모두 같은 인터페이스 아래에 붙여 비교해 보는 것이 낫다.

현재 선택지 비교:

1. 이미 잘 되어 있는 한국어 TTS를 가져와 목소리만 선택해 사용
   - 현재 기준 제품 관점의 메인 경로다.
   - 가장 짧은 시간 안에 고객 시연 품질과 Jetson 실시간성을 함께 확인할 수 있다.
   - 기본 후보는 `MeloTTS`다.
2. 원하는 목소리를 직접 학습해 사용
   - 현재 단계에서는 보류한다.
   - 데이터 수집, 음성 정제, 권리 검토, 학습, 추론 경량화까지 동시에 열려 오버엔지니어링이 되기 쉽다.
   - 기본 한국어 baseline이 충분히 좋지 않을 때만 다음 단계로 검토한다.
3. reference 음성을 넣어 zero-shot 또는 voice cloning 계열로 사용
   - 보조 실험 가치가 있다.
   - 성공하면 시연용 인상 개선 폭이 클 수 있다.
   - 다만 2-stage(`TTS -> voice conversion`) 또는 무거운 1-stage 구조가 되면 Jetson 동시 구동 제약에 걸릴 가능성이 있어, 기본 경로가 아니라 2차 후보로 둔다.

현재 결론:

- A100 비교 트랙:
  - `MeloTTS`
  - `OpenVoice V2`
  - `Piper`
  - `Kokoro`
- 제품 우선순위 판단:
  - `기존 한국어 TTS 선택 + 좋은 voice 고르기`를 먼저 본다.
  - `zero-shot / voice cloning`은 품질 향상 폭이 클 때만 다음 단계로 올린다.
  - `커스텀 voice 학습`은 여전히 보류한다.

즉, 지금은 A100에서 4개 후보를 모두 붙여 보되, Jetson 최종 후보를 고를 때는 여전히 "음색 + 지연 + 메모리 + 운영 단순성" 기준으로 좁힌다.
`Edge TTS`와 `OpenAI API TTS`는 이 4개 로컬 후보와 별개로 reference backend로 유지한다.

현재 단계 판정:

- 공통 인터페이스와 API 경로 확보
- `OpenAI API TTS` alias 정리 완료
- `Edge TTS` backend A100 1차 연결 완료
- `MeloTTS` backend A100 1차 연결 완료
- `OpenVoice V2` backend A100 1차 연결 완료
- `Piper` backend A100 1차 연결 완료
- `Kokoro` backend A100 1차 연결 완료
- 서드파티 한국어 Piper 모델은 품질 무효, 비교 연구 전용
- Jetson split env + thin demo wrapper 연결 완료
- Jetson screening 1차 결과:
  - `Piper cpu`와 `Kokoro cuda`가 영어 local 후보
  - `MeloTTS`는 Jetson CPU에서만 동작했고 warm run도 느려 한국어 local 기본 후보로는 보류
  - `Edge TTS`, `OpenAI API TTS`는 network fallback/demo 경로로 유지
- 다음 단계는 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`를 공통 문장셋 기준 benchmark 수집 구조로 넘기는 것이다.
  - 필요하면 `Edge TTS`, `OpenAI API TTS`도 reference 청취 baseline으로 함께 듣는다.

현재 확인된 OpenAI API TTS 메모:

- env:
  - `../env/tts_openai_api`
- alias:
  - `api`
  - `openai_api`
  - `chatgpt_api`
- 현재 기본 모델:
  - `gpt-4o-mini-tts`
- 현재 기본 voice:
  - `alloy`
- 현재 검증:
  - 실제 API 호출 없이 alias 인스턴스화만 확인했다.
  - `openai_api -> OpenAIAPITTSModel`
  - `chatgpt_api -> OpenAIAPITTSModel`
- 운영 메모:
  - 실제 API smoke는 비용이 드니 필요할 때만 수행한다.

현재 확인된 Edge TTS 메모:

- env:
  - `../env/tts_edge_tts`
- wake word 데이터 생성 스크립트:
  - `../wake_word/train/01_generate_positive.py`
- 현재 smoke voice:
  - `ko-KR-InJoonNeural`
- SDK smoke:
  - output: `../results/tts/20260318_edge_tts_smoke/sdk_import.wav`
  - `model_load_sec 0.000`
  - `elapsed_sec 0.915`
- CLI smoke:
  - output: `../results/tts/20260318_edge_tts_smoke/demo_cli.wav`
  - `model_load_sec 0.000`
  - `elapsed_sec 0.849`
- 구현 메모:
  - wake word 생성 스크립트는 `.wav` 이름으로 저장하지만 실제 포맷은 MP3였다.
  - 현재 SDK backend는 `ffmpeg`로 `.wav` 요청 시 실제 WAV로 변환한다.
  - `rate`, `pitch`를 그대로 받아 wake word positive 생성 조건을 재현할 수 있다.

현재 확인된 MeloTTS 메모:

- env:
  - `../env/tts_melotts`
- 실행 장치:
  - `cuda:0` on `NVIDIA A100 80GB PCIe`
- 첫 smoke 결과:
  - output: `../results/tts/20260318_melotts_smoke/hello_kr.wav`
  - `model_load_sec 3.700`
  - `elapsed_sec 16.515`
  - output length: `6.006 sec`
  - `44.1kHz`, `mono`, `wav`
- 두 번째 새 프로세스 재실행:
  - `model_load_sec 2.713`
  - `elapsed_sec 5.972`
- 설치/호환성 메모:
  - `python3.10 venv` 기준으로 설치
  - `librosa 0.9.1` 때문에 `setuptools<81` pin 필요
  - 첫 한국어 실행에서 `python-mecab-ko` 추가 설치가 자동으로 발생했다

현재 확인된 OpenVoice V2 메모:

- env:
  - `../env/tts_openvoice_v2`
- checkpoint root:
  - `../results/tts_assets/openvoice_v2/checkpoints_v2`
- reference cache:
  - `../results/tts_assets/openvoice_v2/processed`
- A100 `cuda:0` + official `example_reference.mp3` 기준 첫 SDK smoke:
  - output: `../results/tts/20260318_openvoice_v2_smoke/hello_kr.wav`
  - `model_load_sec 16.185`
  - `elapsed_sec 13.327`
  - total wall `34.442 sec`
  - output length: `6.304 sec`
  - `22.05kHz`, `mono`, `wav`
- CLI 재실행:
  - `model_load_sec 12.149`
  - `elapsed_sec 10.528`
- 같은 reference 음성을 다시 쓰는 캐시 재실행:
  - `model_load_sec 10.771`
  - `elapsed_sec 7.115`
- 설치/호환성 메모:
  - `/usr/bin/python3.10 -m venv` 기준으로 구성
  - `OpenVoice`는 `--no-deps`로 설치하고, `av`, `faster-whisper`, `whisper-timestamped`는 별도 설치했다
  - `MeloTTS`와 동일하게 `setuptools<81` pin을 유지했다
  - 첫 한국어 합성 시 `python-mecab-ko`가 자동 설치됐다

현재 확인된 Piper 메모:

- env:
  - `../env/tts_piper`
- asset root:
  - `../results/tts_assets/piper`
- 공식 voice 기준:
  - 현재 사용 확인 voice는 `en_US-lessac-medium`
  - 공식 기본 `VOICES.md` 목록에는 한국어가 없다
- 서드파티 한국어 모델:
  - `../results/tts_assets/piper/neurlang_kss_korean/piper-kss-korean.onnx`
  - 출처: `neurlang/piper-onnx-kss-korean`
  - 모델 페이지 라이선스 표기: `CC-BY-NC-SA-4.0`
- A100 `cuda:0` 기준 첫 smoke:
  - output: `../results/tts/20260318_piper_smoke/hello_en.wav`
  - output length: `3.808 sec`
  - `22.05kHz`, `mono`, `wav`
- SDK import smoke:
  - output: `../results/tts/20260318_piper_smoke/sdk_import.wav`
  - `model_load_sec 1.572`
  - `elapsed_sec 1.300`
  - providers: `CUDAExecutionProvider`, `CPUExecutionProvider`
- CLI smoke:
  - output: `../results/tts/20260318_piper_smoke/demo_cli.wav`
  - `model_load_sec 1.551`
  - `elapsed_sec 1.268`
- 서드파티 한국어 custom model 디버깅 메모:
  - `pygoruut 0.7.0` 기본 경로는 `안녕하세요 -> 녕 + 안하세요`처럼 분절이 깨졌다
  - `pygoruut v0.6.2` + word phonetic 기준이 그나마 가장 나았지만, STT 역전사 기준으로도 `"안녕하세요. 파이퍼 한국어 테스트입니다."`를 안정적으로 재현하지 못했다
  - `noise_scale / noise_w_scale`와 phoneme 정규화까지 짧게 탐색했지만, 여전히 `"파이퍼 한국어"` 구간이 반복적으로 다른 단어로 무너졌다
  - `piper-rs` 원 저자 repo는 lockfile 기준으로 library bin 빌드까지는 됐지만, 기본 설정 역전사도 `"카이퍼 땡구그린의 습들입니다"` 수준으로 무너졌다
  - `pygoruut_version=v0.6.2`를 config에 명시한 `piper-rs` 경로는 현재 rustruut에서 해당 실행 파일을 찾지 못해 재현이 막혔다
  - 따라서 현재 Python `piper-tts` 경로뿐 아니라 author runtime 기준으로도 이 한국어 model을 제품성 있는 후보로 보지 않는다
- 설치/호환성 메모:
  - `/usr/bin/python3.10 -m venv` 기준으로 구성
  - `pip install piper-tts onnxruntime-gpu`
  - `neurlang/piper-onnx-kss-korean`을 쓰려면 `pip install pygoruut` 추가가 필요하다
  - CUDA provider를 실제로 쓰기 위해 `nvidia-cublas-cu12`, `nvidia-cuda-runtime-cu12`, `nvidia-cufft-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-nvrtc-cu12`를 env에 추가했다
  - runtime에서는 `onnxruntime.preload_dlls(directory='')`를 먼저 호출해야 CUDA provider가 정상 로드됐다
  - Python `piper-tts`는 `phoneme_type=pygoruut`를 기본 지원하지 않아, backend에서 `pygoruut` phonemizer 호환 레이어를 얇게 추가했다
  - `pygoruut`는 로컬 phonemizer 프로세스를 띄우므로, 같은 env에서 병렬 smoke를 여러 개 동시에 올리는 것은 피하는 편이 안전하다

현재 확인된 Kokoro 메모:

- env:
  - `../env/tts_kokoro`
- 공식 repo/model:
  - `hexgrad/Kokoro-82M`
- 공식 language code:
  - `en-us`, `en-gb`, `es`, `fr-fr`, `hi`, `it`, `pt-br`, `ja`, `zh`
  - backend 내부 단축 코드는 `a`, `b`, `e`, `f`, `h`, `i`, `p`, `j`, `z`
- direct smoke:
  - output: `../results/tts/20260318_kokoro_smoke/hello_en.wav`
  - `model_load_sec 15.646`
  - `elapsed_sec 2.941`
  - output length: `4.600 sec`
- SDK import smoke:
  - output: `../results/tts/20260318_kokoro_smoke/sdk_import.wav`
  - `model_load_sec 3.524`
  - `elapsed_sec 1.138`
- CLI smoke:
  - output: `../results/tts/20260318_kokoro_smoke/demo_cli.wav`
  - `model_load_sec 3.403`
  - `elapsed_sec 1.231`
- 출력 포맷:
  - `24kHz`, `mono`, `wav`
- 설치/호환성 메모:
  - `python -m venv ../env/tts_kokoro`
  - `pip install 'kokoro>=0.9.2' soundfile`
  - 첫 영어 실행에서 `en_core_web_sm`가 추가 설치됐다
  - 현재 env는 `espeakng-loader`를 통해 system `espeak-ng` 없이도 공식 영어 경로가 동작했다
- 현재 판단:
  - A100 비교 후보로는 유효하다
  - 하지만 공식 Korean path가 없어, 현재 프로젝트의 한국어 기본 후보로 바로 올리지는 않는다

현재 디렉토리 구조:

```text
tts/
├── __init__.py
├── tts.py
├── tts_api.py
├── tts_demo.py
├── backends/
├── experiments/
└── evaluation/
```

현재 PoC 순서:

1. 공통 인터페이스를 유지한 채 A100 비교 구조를 만든다.
   - backend 코드는 `backends/`, 후보별 실험 메모는 `experiments/`, 비교 기준은 `evaluation/`으로 나눈다.
2. A100에서 4개 후보를 각각 import 가능한 backend 형태로 붙인다.
   - 1차 산출물은 `TTSSynthesizer(model="<candidate>")` 형태다.
3. 공통 문장셋과 메트릭으로 A100 비교를 수행한다.
   - 귀로 듣는 인상과 시스템 메트릭을 함께 본다.
4. A100 결과를 바탕으로 Jetson 검증 우선순위를 정한다.
   - 유력 후보부터 `Wake word + VAD + STT`와 함께 실측한다.
5. Jetson 결과를 기준으로 최종 기본 TTS 후보를 좁힌다.
6. 그 이후에만 voice cloning 확장이나 custom training을 검토한다.

피해야 할 것:

- 시작부터 custom dataset 구축과 custom speaker training에 들어가는 것
- Jetson 제약을 무시하고 A100 기준으로만 모델을 고르는 것
- 음색 개선보다 먼저 큰 모델 복잡도를 올리는 것
- 음성 품질 문제를 모두 모델 교체로만 해결하려는 것

실제 완성도에 크게 영향을 주는 항목:

- voice 선택
- 발화 속도와 pause
- 숫자, 영문, 브랜드명 읽기
- 응답 길이 제한과 문장 분절
- 반복 문구 cache
- 스피커 출력 볼륨과 음색 일관성

현재 비교 기준 문서:

- `evaluation/README.md`
- `evaluation/prompts/ko_demo_sentences_v1.txt`
- `../docs/research/tts.md`
- `../docs/envs/tts_a100_experiment_env.md`

다음 작업:

1. `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 공통 benchmark 수집 코드를 붙인다
2. 공통 문장셋으로 A100 smoke와 메트릭 수집 구조를 만든다
3. A100 비교 결과를 바탕으로 Jetson 실측 우선순위를 정한다

현재 참고 기준:

- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/project_overview.md`](../docs/project_overview.md)
- [`../docs/research/tts.md`](../docs/research/tts.md)
