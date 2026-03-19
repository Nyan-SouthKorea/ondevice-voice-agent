# TTS

이 디렉토리는 text-to-speech 계층 자리다.

TTS 문서 허브:

- 모듈 문서 허브: `docs/README.md`
- 현재 상태 기준: `../docs/status.md`
- 현재 active custom training 계획: `../tts/docs/보고서/260319_1052_TTS_커스텀_학습_계획_v1.md`
- 현재 Piper pilot 실행 계획: `../tts/docs/보고서/260319_1308_TTS_Piper_파일럿_학습_실행계획.md`
- 현재 Piper pilot 자동평가 결과: `../tts/docs/보고서/260319_1324_TTS_Piper_파일럿_자동평가_결과.md`
- 현재 Piper 공식 파인튜닝 실행 계획: `../tts/docs/보고서/260319_1445_TTS_Piper_공식_파인튜닝_실행계획_v1.md`
- 현재 Piper 공식 파인튜닝 자동평가 결과: `../tts/docs/보고서/260319_1736_TTS_Piper_공식_파인튜닝_자동평가_결과.md`
- 현재 TTS 상태점검과 다음 계획: `../tts/docs/보고서/260320_0822_TTS_상태점검_및_다음계획.md`
- 현재 학습 가능성 점검: `../tts/docs/보고서/260319_1100_TTS_학습_가능성_점검.md`
- 현재 active Piper pilot run root: `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/`
- 현재 active Piper 공식 파인튜닝 run root: `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/`
- 현재 active Piper 남성 ref run root: `../results/tts_custom/training/260319_1840_Piper_한국어_공식_파인튜닝_남성ref_v1/`
- 현재 TTS 통합 텍스트 코퍼스 인덱스: `../results/tts_custom/corpora/260319_1510_tts_텍스트코퍼스_통합_v1/`
- Jetson Nano 구동 기록: `../tts/docs/보고서/260319_0930_TTS_나노_구동기록.md`
- AGX Orin 구동 기록: `../tts/docs/보고서/260319_0907_TTS_AGX_구동기록.md`
- A100 전체 benchmark 결과: `../tts/docs/보고서/260318_1824_TTS_전체_벤치마크_결과_v1.md`
- Jetson screening 요약: `../tts/docs/보고서/260318_1912_TTS_Jetson_스크리닝.md`
- benchmark 설계 기준: `../tts/docs/보고서/260318_1708_TTS_벤치마크_계획.md`
- 조사 문서: `../tts/docs/조사/260317_1005_TTS_기술_조사.md`
- Jetson 환경 문서: `../tts/docs/환경/260319_0930_Jetson_TTS_환경.md`
- A100 실험 환경 문서: `../tts/docs/환경/260318_1708_A100_TTS_실험환경.md`
- Piper 학습 환경 문서: `../tts/docs/환경/260319_1100_Piper_학습환경.md`
- Piper 전체 재현 가이드: `../tts/docs/환경/260319_1925_Piper_한국어_전체학습_재현가이드.md`
- custom training 실험 README: `experiments/custom_training/README.md`

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

Jetson 한국어 텍스트 입력 GUI:

```bash
cd /home/everybot/workspace/ondevice-voice-agent
repo/tts/tools/tts_text_input_gui_jetson.sh
```

- `tts/tools/tts_text_input_gui.py`는 Jetson에서 한글 IME 입력을 안정적으로 받기 위해 `PyQt5` 기반으로 동작한다.
- GUI 자체는 `/usr/bin/python3`로 띄우고, 실제 합성은 `env/tts_piper_jetson/bin/python repo/tts/tts_demo.py`를 subprocess로 호출한다.
- 기본 한국어 Piper ONNX는 우선 `repo/tts/models/piper_ko_260319_공식파인튜닝/`를 보고, 없으면 `results/tts_custom/training/.../exported_onnx/` 경로를 fallback으로 사용한다.

Jetson 음성 파이프라인 TTS 응답 GUI:

```bash
cd /home/everybot/workspace/ondevice-voice-agent/repo
tts/tools/voice_pipeline_tts_gui_jetson.sh
```

- `voice_pipeline_tts_gui_demo.py`는 기존 `voice_pipeline_gui_demo.py`를 확장해 `wake word -> VAD -> STT -> TTS`를 한 번에 데모한다.
- LLM은 넣지 않고, STT로 인식한 결과 원문을 그대로 한국어 Piper TTS가 읽는다.
- GUI 본체는 `env/stt_trt_experiment/bin/python`으로 실행한다. 이유는 이 env가 Jetson에서 `wake_word + vad + stt + tkinter + torch`를 모두 함께 만족하기 때문이다.
- TTS 합성은 `env/tts_piper_jetson/bin/python repo/tts/tts_demo.py`를 subprocess로 호출하고, 결과 wav는 `results/tts/jetson_demo/voice_pipeline_tts/` 아래에 저장한다.
- GUI에는 `TTS 재생 중` 램프가 별도로 있고, 최근 turn의 `stt wall sec / tts sec / total sec`를 화면에 표시한다.
- turn별 실행 기록은 `results/tts/jetson_demo/voice_pipeline_tts/metrics.jsonl`에 누적 저장한다.

현재 v1 방향:

- 빠른 end-to-end 연결용:
  - `OpenAI API TTS`
- wake word 데이터 생성 / reference baseline:
  - `Edge TTS`
- Jetson 영어 runtime shortlist:
  - `Piper`
  - `Kokoro`
- 후속 custom training 트랙:
  - `OpenVoice V2`를 voice audition + synthetic dataset 생성기로 사용

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
   - 초기 검토 시점에는 가장 빠른 기준선 후보였다.
   - 하지만 현재 Jetson 실측 기준으로는 `MeloTTS`가 runtime 기본 후보라고 보지 않는다.
   - 지금은 한국어 품질 anchor와 비교 기준으로만 유지한다.
2. 원하는 목소리를 직접 학습해 사용
   - 현재 단계에서는 보류한다.
   - 데이터 수집, 음성 정제, 권리 검토, 학습, 추론 경량화까지 동시에 열려 오버엔지니어링이 되기 쉽다.
   - 기본 한국어 baseline이 충분히 좋지 않을 때만 다음 단계로 검토한다.
3. reference 음성을 넣어 zero-shot 또는 voice cloning 계열로 사용
   - 보조 실험 가치가 있다.
   - 성공하면 시연용 인상 개선 폭이 클 수 있다.
   - 다만 2-stage(`TTS -> voice conversion`) 또는 무거운 1-stage 구조가 되면 Jetson 동시 구동 제약에 걸릴 가능성이 있어, 기본 경로가 아니라 2차 후보로 둔다.

2026-03-19 이후 active 결론:

- A100 비교 트랙:
  - `MeloTTS`
  - `OpenVoice V2`
  - `Piper`
  - `Kokoro`
- Jetson runtime 우선 트랙:
  - `Piper`
  - `Kokoro`
- `OpenVoice V2`는 최종 runtime 후보가 아니라, 원하는 목소리 audition과 synthetic dataset 생성기로 본다.
- 한국어 custom training은 `1~3시간 pilot dataset -> pilot 학습 -> 확대` 순서로 진행한다.
- `runtime winner`와 `training winner`는 같다고 가정하지 않는다.
- 현재 training feasibility audit 기준으로는 `Piper`를 custom training 1순위, `Kokoro`를 runtime 우선 후보로 본다.
- 현재 `Piper` pilot은 학습, ONNX export, 자동 benchmark까지 완료됐고, 중요한 checkpoint와 review sample을 자동 보관한다.
  - important checkpoint root:
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/checkpoint_review/important_checkpoints/`
  - review sample root:
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/checkpoint_review/review_samples/`
  - 학습 종료 후 자동 후처리:
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/postprocess_status.local.md`
- 현재 `Piper` 공식 fine-tune control run도 학습, ONNX export, 자동 benchmark까지 완료됐다.
  - final checkpoint:
    - `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/train_root/lightning_logs/version_1/checkpoints/epoch=2183-step=1376858.ckpt`
  - review sample root:
    - `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/checkpoint_review/review_samples/epoch=2183-step=1376858/`
  - final benchmark root:
    - `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/benchmark_postprocess/20260319_173609/`
  - A100 SDK smoke:
    - `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/a100_sdk_smoke_20260319/sdk_smoke.wav`
    - `model_load_sec 1.1268`
    - `elapsed_sec 0.9715`
  - Jetson Nano SDK smoke:
    - `../results/tts_custom/training/260319_1440_Piper_한국어_공식_파인튜닝_v1/jetson_nano_sdk_smoke_20260319/sdk_smoke.wav`
    - `model_load_sec 2.0032`
    - `elapsed_sec 0.4569`
  - 핵심 자동지표:
    - `mean_normalized_cer 0.1247`
    - `exact_match_rate 0.30`
  - 해석:
    - 직전 scratch pilot 대비 intelligibility가 크게 개선돼, 현재 synthetic Korean single-speaker 경로에서도 `공식 fine-tune 레시피`가 유효하다는 근거가 생겼다.

## 한국어 text 코퍼스 구성

현재 OpenVoice 합성과 Piper 학습에 쓰는 한국어 텍스트는 `v1`, `v2`, `v3` 세 단계로 정리되어 있다. 각 버전은 서로 exact duplicate가 없도록 관리하고, 최종 통합 인덱스는 아래에 따로 모아둔다.

- 통합 인덱스:
  - `../results/tts_custom/corpora/260319_1510_tts_텍스트코퍼스_통합_v1/`
- 통합 TSV:
  - `master_union_unique_by_text.tsv`
- 데이터셋 설명 아카이브:
  - `../results/tts_custom/corpora/260319_1635_데이터셋_설명_아카이브_v1/`
- 역할 분리:
  - `260319_1510...`: generation/training에 쓰는 canonical text index
  - `260319_1635...`: dataset card, license, local summary를 모아둔 설명 아카이브

| 버전 | 목적 | 사용한 공개 데이터셋 | 수집 방식 | 현재 문장 수 | 현재 확인 가능한 원본/캐시 경로 |
|---|---|---|---|---:|---|
| `v1` | 첫 번째 clean seed corpus | `Bingsu/KSS_Dataset`, `Bingsu/zeroth-korean` | Hugging Face `streaming=True`로 읽고 `audio` 컬럼은 버리고 text만 사용 | `4,893` | `~/.cache/huggingface/datasets/Bingsu___kss_dataset/`, `~/.cache/huggingface/datasets/Bingsu___zeroth-korean/` |
| `v2` | `v1`의 확장판 | `KSS + Zeroth-Korean` 동일 계열 확장 | 같은 계열 소스를 더 넓게 수집해 text corpus 확장 | `10,396` | 현재는 최종 text corpus만 남아 있고, 별도 source cache 경로는 명시적으로 관리하지 않음 |
| `v3` | `v1/v2`와 겹치지 않는 신규 text 추가 | `malaysia-ai/Korean-Single-Speaker-TTS`, `NX2411/AIhub-korean-speech-data-large` | 새 공개 소스에서 text를 추가 수집하고 `v1/v2`와 exact duplicate 제거 | `9,400` | 현재는 최종 text corpus만 남아 있고, 식별 가능한 raw cache/download 경로는 확인되지 않음 |
| `통합본` | 이후 generation/training의 canonical index | `v1 + v2 + v3` | 기존 corpus를 비파괴적으로 합쳐 인덱스만 통합 | `24,689` | `../results/tts_custom/corpora/260319_1510_tts_텍스트코퍼스_통합_v1/` |

각 corpus 경로:

- `v1`: `../results/tts_custom/corpora/ko_text_corpus_v1/`
- `v2`: `../results/tts_custom/corpora/ko_text_corpus_v2/`
- `v3`: `../results/tts_custom/corpora/ko_text_corpus_v3/`
- `통합`: `../results/tts_custom/corpora/260319_1510_tts_텍스트코퍼스_통합_v1/`
- `설명 아카이브`: `../results/tts_custom/corpora/260319_1635_데이터셋_설명_아카이브_v1/`
- 중복 파일 정리 후 현재 canonical TSV는 `master_union_unique_by_text.tsv` 하나만 유지한다.

## OpenVoice synthetic generation 운영 메모

- 긴 generation run은 [`openvoice_generate_dataset.py`](/data2/iena/260318_ondevice-voice-agent/repo/tts/tools/openvoice_generate_dataset.py)의 `--skip-existing`를 기본으로 사용한다.
- 이 스크립트는 row 단위로 `manifest.tsv`를 즉시 append하므로, generation이 중간에 멈춰도 이미 생성된 `wav`와 `manifest.tsv`를 기준으로 안전하게 resume할 수 있다.
- 현재 남성 ref 전체생성 run은 [`260319_1840_TTS_Piper_남성ref_전체학습_실행계획_v1.md`](/data2/iena/260318_ondevice-voice-agent/repo/tts/docs/보고서/260319_1840_TTS_Piper_남성ref_전체학습_실행계획_v1.md) 기준으로 진행 중이다.

중복 검사는 이렇게 했다.

1. `v1` 생성 시에는 `prepare_ko_text_corpus.py`에서
   - `NFKC` 정규화
   - 공백 정리
   - 문장부호 앞 공백 제거
   - 길이 필터
   를 거친 뒤 최종 `text` 문자열을 `set`으로 exact dedupe했다.
2. `v1/v2/v3` 상호 비교는 각 `corpus_full.tsv`의 최종 `text` 컬럼을 집합으로 읽어 exact match 기준으로 비교했다.
3. 현재 확인 결과는 아래와 같다.
   - `v1 ∩ v2 = 0`
   - `v1 ∩ v3 = 0`
   - `v2 ∩ v3 = 0`
   - union = `24,689`

현재 custom training 기준 최신 usable synthetic snapshot은 아래를 본다.

- inventory root:
  - `../results/tts_custom/synthetic_dataset/260319_1450_합성데이터_인벤토리_v3/`
- 요약:
  - `18,477문장`
  - `21.568시간`

주의:

- 이 검사는 `exact duplicate` 기준이다.
- 의미는 같지만 표현이 조금 다른 문장까지 잡는 semantic dedupe는 아직 하지 않았다.
- `v3` source 두 개는 현재 로컬에 남아 있는 건 최종 text corpus와 summary이며, 원본 다운로드 경로를 다시 추적할 수 있도록 별도 raw archive를 보관하지는 않았다.
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/exported_onnx/`
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/benchmark_postprocess/`
  - 현재 자동지표 기준 best checkpoint:
    - `epoch=10-step=1298`
  - 현재 자동평가 결론:
    - 파이프라인은 성립했지만, full training으로 바로 확대할 정도의 품질은 아직 아니다.

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
- 다음 단계는 아래다.
  - `Piper`, `Kokoro` runtime winner 재검증
  - `Piper` training pilot 경로 구체화
  - `Kokoro` training은 후순위 research 유지
  - `OpenVoice V2` reference audition pipeline
  - 한국어 synthetic dataset `1~3시간` pilot 생성과 pilot 학습

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
- `../tts/docs/조사/260317_1005_TTS_기술_조사.md`
- `../tts/docs/환경/260318_1708_A100_TTS_실험환경.md`

다음 작업:

1. `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 공통 benchmark 수집 코드를 붙인다
2. 공통 문장셋으로 A100 smoke와 메트릭 수집 구조를 만든다
3. A100 비교 결과를 바탕으로 Jetson 실측 우선순위를 정한다

현재 참고 기준:

- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/project_overview.md`](../docs/project_overview.md)
- [`../tts/docs/조사/260317_1005_TTS_기술_조사.md`](../tts/docs/조사/260317_1005_TTS_기술_조사.md)
