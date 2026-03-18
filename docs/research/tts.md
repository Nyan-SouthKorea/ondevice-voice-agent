# TTS 기술 조사

> 마지막 업데이트: 2026-03-18
> 목적: Jetson Orin Nano 기준 TTS v1 선택과 구현 순서를 정리한다.

## 현재 결론

- 기본 아키텍처:
  - 공통 래퍼 `TTSSynthesizer`
  - 빠른 end-to-end 확인용 API 경로
  - 후보 엔진별 runtime backend와 평가 구조를 분리
- 현재 구현 진행:
  - `OpenAI API TTS`, `Edge TTS`, `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`는 A100 기준 공통 인터페이스에 연결됐다.
  - `OpenAI API TTS`는 `api`, `openai_api`, `chatgpt_api` alias를 모두 지원한다.
  - `Edge TTS`는 wake word positive 생성 스크립트에서 쓰던 경로를 공통 backend로 다시 묶었고, 현재 SDK는 `.wav` 요청 시 실제 WAV 변환까지 처리한다.
  - `OpenVoice V2`는 `reference_audio_path`를 추가로 받아 zero-shot voice conversion 경로까지 smoke를 통과했다.
  - `Piper`는 A100에서 ORT CUDA provider 경로까지 확인했고, 공식 영어 voice smoke는 통과했다.
  - 서드파티 한국어 Piper model은 로드/합성 경로와 author runtime까지 확인했지만, 현재 기준으로는 제품성 있는 한국어 품질을 재현하지 못했다.
  - `Kokoro`는 A100에서 공식 영어 smoke를 통과했지만, 현재 official language code 기준 한국어 path가 없다.
- 개발 판단:
  - A100에서는 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 4개를 모두 같은 구조 아래에 붙여 비교한다.
  - `OpenAI API TTS`, `Edge TTS`는 4개 로컬 후보와 별개로 reference baseline으로 유지한다.
  - Jetson 최종 후보는 A100 비교와 Jetson 실측을 거친 뒤 좁힌다.
  - `기존 한국어 TTS 선택`은 여전히 제품 관점의 우선 경로다.
  - `zero-shot / voice cloning`은 품질 향상 폭이 확인될 때만 다음 단계로 본다.
  - `custom voice training`은 현재 단계에서는 보류한다.
- v1 구현 순서:
  1. 공통 TTS 인터페이스 확정
  2. A100에서 4개 후보 backend를 같은 방식으로 호출 가능하게 정리
  3. 공통 문장셋과 공통 메트릭으로 A100 비교
  4. Jetson에서 실측해 후보 축소
  5. 재생/캐시/LLM 연결

## 현재 제품 고민

- 고객 시연에서 TTS는 단순 보조 기능이 아니라, 비기술 사용자 기준 "로봇 완성도"를 결정하는 핵심 요소다.
- 하지만 최종 제품은 Jetson 위에서 `Wake word + VAD + STT + TTS + CV`가 동시에 돌아야 하므로, TTS 품질만 보고 무거운 구조를 채택할 수는 없다.
- A100에서는 학습과 다양한 실험이 가능하지만, 최종 채택 기준은 Jetson 실시간성과 메모리 안정성이다.
- 현재 repo 내부에는 대화형 한국어 TTS 학습용 데이터셋이 없다.
  - `wake_word/examples/audio_samples/positive_tts/` 공개 샘플 3개
  - `wake_word/data/hi_popo/positive/tts/` 로컬 생성 샘플 1125개
  - 이 데이터는 wake word positive 보강용이라, "원하는 사람 목소리" 학습용 데이터로 바로 보기 어렵다.
- 따라서 초반 전략은 "가장 좋은 연구 주제"가 아니라 "비교 가능한 baseline을 빨리 만들고, Jetson에 가져갈 후보를 빠르게 거르는 것"이 되어야 한다.
- 다만 A100 단계에서는 조기 탈락을 줄이기 위해 후보 4개를 모두 같은 기준으로 한번은 보는 편이 낫다.

## 세 가지 선택지에 대한 판단

### 1. 이미 잘 되어 있는 한국어 TTS를 사용하고 voice만 고르는 방식

- 현재 메인 경로다.
- 장점:
  - 개발 속도가 가장 빠르다.
  - 고객 시연용 baseline을 가장 빨리 만들 수 있다.
  - Jetson 탑재 가능성을 빠르게 검증할 수 있다.
- 단점:
  - voice 선택 폭이 제한되면 차별화가 약할 수 있다.
  - 아주 특정한 persona를 만들기 어렵다.
- 현재 판단:
  - 가장 FM이다.
  - 우선 `MeloTTS`로 baseline을 확보하고, 부족한지부터 본다.
  - 현재 baseline backend 연결과 첫 한국어 smoke는 완료했다.

### 2. 원하는 목소리를 직접 학습하는 방식

- 현재는 보류한다.
- 장점:
  - 가장 원하는 voice identity에 가깝게 갈 수 있다.
  - 고객 맞춤형 브랜딩 가능성이 크다.
- 단점:
  - 데이터 수집, 음질 정제, 화자 일관성, 라이선스 검토, 학습, 추론 경량화까지 전부 필요하다.
  - 짧은 일정에서 가장 오버엔지니어링으로 흐르기 쉽다.
  - YouTube 등 소량 샘플만으로 항상 안정적인 결과를 보장하기 어렵다.
- 현재 판단:
  - baseline TTS가 고객 시연 품질을 만족하지 못할 때만 다음 단계로 검토한다.

### 3. reference 음성을 넣는 zero-shot / voice cloning 방식

- 보조 실험 가치가 있다.
- 장점:
  - 성공하면 데모 인상 개선 폭이 크다.
  - 소량 샘플로 voice identity를 빠르게 바꿀 가능성이 있다.
- 단점:
  - 2-stage(`기본 TTS -> voice conversion`)는 지연 시간과 복잡도가 늘어난다.
  - 1-stage zero-shot도 모델이 무겁거나 한국어 품질이 흔들릴 수 있다.
  - Jetson 동시 구동 제약에서 가장 먼저 탈락할 가능성이 있다.
- 현재 판단:
  - A100에서만 먼저 실험하고, 품질 개선 폭이 충분히 클 때만 Jetson 검증으로 가져간다.
  - 현재 `OpenVoice V2` A100 backend 연결과 reference 음성 smoke는 완료했다.

### 4. A100에서 네 후보를 모두 구현하는 이유

- 현재 비교 후보는 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`다.
- 이유:
  - A100에서는 설치와 초기 검증 비용을 감당할 수 있다.
  - 나중에 wake word positive 생성용 추가 TTS 분포를 확보하는 데도 도움이 될 수 있다.
  - 한국어 품질이 약할 것 같은 후보도 실제 구현 결과가 의외로 쓸모 있을 수 있다.
- 단, 이 결정이 곧 "Jetson에도 4개를 다 올린다"는 뜻은 아니다.
- Jetson은 여전히 상위 후보만 가져가 실측한다.

## 선택 이유

### 1. OpenAI API TTS

- 공식 Audio API `audio/speech` endpoint 사용 가능
- 현재 공식 지원 모델:
  - `gpt-4o-mini-tts`
  - `tts-1`
  - `tts-1-hd`
- 장점:
  - 구현 속도가 가장 빠름
  - 스트리밍 파일 저장 경로가 명확함
  - 말투 지시와 속도 조절 지원
  - 한국어 입력도 지원 문서에 포함
- 한계:
  - 네트워크 의존
  - 음성은 현재 영어 최적화가 중심
  - 온디바이스 목표와는 거리가 있음

### 2. MeloTTS

- 공식 저장소 기준 한국어 지원
- MIT 라이선스
- 다국어/다화자 구조
- README 기준 `CPU real-time inference`를 강조
- 현재 프로젝트 목표와 가장 잘 맞는 점:
  - 온디바이스 가능성
  - 상업적 사용 가능
  - 한국어 지원이 명시적

### 3. OpenVoice V2

- 공식 저장소 기준 한국어 지원
- MIT 라이선스
- 강점:
  - 음성 복제까지 포함한 확장성
- 현재 보류 이유:
  - 지금 단계에서는 voice cloning이 요구사항이 아님
  - 기본 TTS보다 시스템 복잡도가 커짐

### 4. Piper / Kokoro

- Piper:
  - 로컬 추론과 MIT 라이선스 측면은 좋다
  - 현재 한국어 기본 채택 근거는 MeloTTS보다 약하다
  - 하지만 ONNX 기반 경량 경로라서 A100 비교 대상에는 포함한다
  - 현재 `TTSSynthesizer(model="piper")` backend 연결과 A100 공식 영어 voice smoke는 완료했다
  - 공식 기본 `VOICES.md` 목록에는 한국어가 없다
  - 대신 `neurlang/piper-onnx-kss-korean` 같은 서드파티 한국어 model이 있어, A100 한국어 smoke까지는 바로 진행 가능했다
  - 다만 현재 확인한 한국어 model 페이지 라이선스 표기가 `CC-BY-NC-SA-4.0`라서, 제품 기본 후보보다는 비교 연구 후보로 두는 편이 맞다
  - Python `piper-tts`가 `phoneme_type=pygoruut`를 기본 지원하지 않아, backend에 얇은 호환 레이어가 추가됐다
  - `piper-rs` 원 저자 lockfile 경로까지 확인했지만, 기본 설정 역전사도 `"카이퍼 땡구그린의 습들입니다"` 수준으로 무너져 현재는 한국어 제품 후보로 보기 어렵다
  - `pygoruut_version=v0.6.2`를 config에 명시한 author runtime 검증은 현재 rustruut 실행 파일 부재로 막혀 있다
- Kokoro:
  - Apache 2.0은 장점
  - 현재 한국어 운영 기준으로 바로 채택할 근거가 부족하다
  - A100 `cuda` 기준 `hexgrad/Kokoro-82M` 공식 영어 smoke는 통과했다
  - direct smoke: `model_load_sec 15.646`, `elapsed_sec 2.941`
  - SDK smoke: `model_load_sec 3.524`, `elapsed_sec 1.138`
  - CLI smoke: `model_load_sec 3.403`, `elapsed_sec 1.231`
  - 현재 공식 language code는 `en-us`, `en-gb`, `es`, `fr-fr`, `hi`, `it`, `pt-br`, `ja`, `zh` 계열뿐이라 한국어 제품 후보로는 바로 올리지 않는다
  - 그래도 경량성과 실제 runtime 구조 확인 차원에서 A100 비교 대상에는 포함한다

### 5. Edge TTS

- wake word positive 생성에 이미 사용했던 network TTS 경로다
- 장점:
  - 한국어 voice와 다국어 multilingual voice를 바로 쓸 수 있다
  - `rate`, `pitch`를 직접 조절해 wake word positive 생성 분포를 재현하기 쉽다
- 현재 구현 메모:
  - `TTSSynthesizer(model="edge_tts")`로 호출 가능하다
  - 기존 wake word 생성 스크립트는 `.wav` 이름으로 실제 MP3를 저장했지만, 현재 SDK backend는 `ffmpeg`를 사용해 `.wav` 요청 시 실제 WAV로 변환한다
- 현재 판단:
  - 제품 최종 후보라기보다 wake word 데이터 생성용과 reference 청취 baseline 용도로 유지한다

## 현재 결정

- A100 비교 후보: `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`
- 보조 reference backend: `OpenAI API TTS`, `Edge TTS`
- 즉시 구현 경로: `OpenAI API TTS`
- 제품 관점 초기 우선 경로: `MeloTTS`
- 즉, 지금은 인터페이스와 상위 파이프라인을 먼저 열고, A100에서는 4개 후보를 같은 구조 아래에 붙여 비교한다.
- `OpenVoice V2` 같은 zero-shot 계열은 품질 향상 폭이 확인될 때만 Jetson 검증 후보로 올린다.
- custom training은 지금 단계에서 바로 들어가지 않는다.

## v1 인터페이스

- 공통 진입점:
  - `tts/tts.py`
- 공통 사용 방식:
  - `TTSSynthesizer(model="api")`
  - `synthesize_to_file(text, output_path)`

예시:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="api",
    model_name="gpt-4o-mini-tts",
    voice="alloy",
    response_format="wav",
)
synthesizer.synthesize_to_file("안녕하세요. 테스트를 시작합니다.", "out.wav")
```

## 단계별 개발 계획

### Phase 1. 인터페이스와 A100 비교 구조

- 목표:
  - TTS 자리를 코드상으로 열어 둔다
  - 후보 엔진 4개를 같은 구조 아래에 붙일 준비를 한다
- 범위:
  - `TTSSynthesizer`
  - `tts/backends/`
  - `tts/experiments/`
  - `tts/evaluation/`
  - `OpenAIAPITTSModel`
  - `tts_demo.py`
  - usage log 기록
  - 대표 문장셋 정의
  - 기본 평가 항목 정의

성공 기준:

- 텍스트 입력부터 파일 저장까지 실패 없이 돌아간다.
- 이후 온디바이스 backend를 교체해도 같은 인터페이스를 유지할 수 있다.
- 후보 엔진별 작업 위치와 산출물 위치가 뒤섞이지 않는다.

### Phase 2. A100 후보 4개 구현

- 목표:
  - `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`를 A100에서 SDK처럼 호출 가능하게 만든다.
- 범위:
  - backend별 env 분리
  - 후보별 smoke script
  - 공통 인터페이스 호출 확인

성공 기준:

- 각 후보가 A100에서 `TTSSynthesizer(model="<candidate>")` 형태로 호출된다.
- 공통 문장셋 전체를 최소 1회 이상 합성할 수 있다.
- 결과와 오류 로그가 `../results/tts/`에 정리된다.

### Phase 3. A100 정량/정성 비교

- 목표:
  - A100에서 4개 후보를 공통 기준으로 비교한다
- 범위:
  - cold/warm latency
  - `real_time_factor`
  - RAM/VRAM 피크 사용량
  - STT back-transcription 기준 intelligibility
  - 청취 평가 시트

성공 기준:

- 각 후보의 강점과 약점이 숫자와 청취 메모로 분리된다.
- Jetson으로 내릴 상위 후보 1~2개를 정할 수 있다.

### Phase 4. Jetson 실측

- 목표:
  - A100 상위 후보를 Jetson에서 실제로 돌려 최종 후보를 좁힌다
- 범위:
  - cold/warm load 측정
  - `Wake word + VAD + STT`와의 동시 실행 안정성
  - 오디오 출력 경로와 체감 latency 확인

성공 기준:

- 후보별 Jetson 실기 가능 여부가 분명해진다.
- 최종 기본 TTS 후보와 fallback 후보를 정할 수 있다.

### Phase 5. 재생과 캐시

- 목표:
  - 반복 문구는 재합성 없이 재사용
  - 오디오 플레이백까지 연결
- 범위:
  - output cache key
  - `synthesize_to_bytes()` 또는 `play()` 보강
  - 응답 문장 길이 제한 및 chunking 기준
  - 반복 문구 prebuild 가능성 검토

성공 기준:

- 반복 안내 문구는 즉시 재생에 가깝게 응답한다.
- 문장 분절과 pause 제어로 체감 자연스러움이 올라간다.

### Phase 6. 상위 파이프라인 통합

- 목표:
  - LLM 텍스트 응답을 TTS로 넘기고 재생
- 범위:
  - LLM 출력 텍스트 -> TTS -> speaker output
  - 실패 시 fallback 정책
  - latency budget 정리

성공 기준:

- 상위 음성 파이프라인에서 TTS가 병목이 되지 않는다.
- 실패 시 API 또는 사전 생성 음성으로 fallback할 수 있다.

## 현재 추천 전략

- A100:
  - 후보 4개를 모두 붙여 비교
- Jetson:
  - A100 상위 후보만 가져가 실측
- 제품 관점:
  - 한국어 품질과 운영 단순성이 먼저다
- 확장:
  - voice cloning 강화와 custom training은 최종 기본 후보가 정해진 뒤 검토

즉, 지금은 "후보 4개를 다 본다"와 "최종 제품은 단순하게 간다"를 동시에 만족시키는 방향으로 가야 한다.

## 평가 메트릭

### 시스템 메트릭

- `model_load_sec`
  - 모델 import부터 첫 합성 가능 상태까지 시간
- `time_to_audio_ready_sec`
  - 요청 후 저장 완료 또는 첫 재생 가능 시점까지 시간
- `audio_duration_sec`
  - 생성 음성 길이
- `real_time_factor`
  - `time_to_audio_ready_sec / audio_duration_sec`
- `peak_vram_mb`
  - GPU 메모리 최대 사용량
- `peak_ram_mb`
  - 시스템 메모리 최대 사용량
- `success_rate`
  - 실패 없는 합성 비율

### 음성 품질 메트릭

- `stt_back_transcription_cer`
  - 생성 음성을 다시 STT에 넣었을 때 문자 오류율
- `stt_back_transcription_exact_match_rate`
  - 정규화 문장 기준 정확 일치율
- `naturalness`
  - 청취 기준 자연스러움
- `voice_appeal`
  - 고객 시연에서 듣기 좋은지
- `pronunciation`
  - 숫자, 영어, 고유명사, 조사 발음 안정성
- `conversational_fit`
  - 대화형 로봇 응답으로서의 적합성
- `persona_fit`
  - 원하는 캐릭터와 브랜드 톤 적합성

## 평가 환경 구성 원칙

- 문장셋은 `tts/evaluation/prompts/ko_demo_sentences_v1.txt`로 고정해 시작한다.
- A100에서는 후보별 cold start 1회, warm run 3회 이상 측정한다.
- 청취 평가는 같은 재생 장치로 연속 비교한다.
- Jetson에서는 같은 전원 모드, 같은 오디오 출력 장치, 같은 동시 구동 조건을 유지한다.
- 리포에는 평가 기준만 남기고, 실제 생성 오디오와 수치 결과는 `../results/tts/`로 분리한다.

## 현재 바로 볼 파일

- `tts/tts.py`
- `tts/tts_api.py`
- `tts/tts_demo.py`
- `tts/README.md`
- `tts/backends/`
- `tts/experiments/`
- `tts/evaluation/README.md`
- `tts/evaluation/prompts/ko_demo_sentences_v1.txt`
- `wake_word/train/01_generate_positive.py`
- `wake_word/examples/audio_samples/README.md`
- `docs/research/tts_korean.md`

## 참고 출처

- OpenAI Audio / Speech 공식 문서
- OpenAI Text-to-Speech 공식 가이드
- OpenAI Audio API Reference
- `myshell-ai/MeloTTS` 공식 GitHub README
- `myshell-ai/OpenVoice` 공식 GitHub README
