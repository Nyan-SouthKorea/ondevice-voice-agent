# TTS Evaluation

이 디렉토리는 TTS 후보 비교 기준을 고정해 두는 자리다.

## 평가 목적

- A100에서 4개 로컬 후보를 공통 기준으로 비교한다.
- `Edge TTS`, `OpenAI API TTS`는 reference backend로 함께 유지한다.
- 사람 귀로 듣는 품질과 시스템 메트릭을 함께 본다.
- Jetson 이전 뒤에도 같은 문장셋과 같은 지표로 다시 비교한다.

현재 canonical 실행 계획은 `../docs/reports/260318_TTS_벤치마크_계획.md`를 기준으로 본다.
현재 canonical registry는 `benchmark_registry_v1.json`이고, 사람 청취용 subset은 `prompts/tts_listening_subset_v1.tsv`를 기준으로 본다.
실행 코드는 `../tools/tts_benchmark.py`, env별 worker는 `../tools/tts_benchmark_worker.py`를 사용한다.

## OpenVoice Reference 재선정 기준

- `OpenVoice V2`는 reference 음성 선택에 민감하므로, full benchmark 이후 별도 재평가를 허용한다.
- 한국어 reference 후보는 `../stt/datasets/korean_eval_50/`의 사용자가 직접 녹음한 문장 세트에서 고른다.
- 영어 reference 후보는 직접 녹음한 영어 세트가 없으므로 `OpenAI Audio Speech API`로 생성한 음성을 임시 후보로 사용한다.
- 현재 영어 후보 생성 기본값은 `gpt-4o-mini-tts` + `marin` 또는 `cedar`다.
- 근거:
  - OpenAI 공식 TTS guide는 `gpt-4o-mini-tts`를 최신 기본 text-to-speech 모델로 안내한다.
  - 같은 guide는 best quality voice로 `marin`, `cedar`를 권장한다.
- 후보 파일은 먼저 `../results/tts_assets/openvoice_v2/ref_candidates/` 아래에만 임시 저장하고, 사용자가 직접 청취해 결정한 뒤에만 실제 OpenVoice 재평가에 반영한다.
- 현재 active benchmark reference는 아래로 고정했다.
  - 한국어:
    - `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
    - source: `stt/datasets/korean_eval_50/021.wav`
  - 영어:
    - `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
    - source: `gpt-4o-mini-tts / marin`
- rerun 뒤 canonical benchmark는 `../results/tts/benchmark_full_v1_20260318/`를 기준으로 읽는다.
- STT 역전사 결과는 아래 두 파일을 기준으로 확인한다.
  - prompt별 상세: `../results/tts/benchmark_full_v1_20260318/per_prompt.tsv`
  - entry별 요약: `../results/tts/benchmark_full_v1_20260318/per_entry_summary.tsv`

## 평가 순서

1. A100 cold start 측정
2. A100 warm run 측정
3. 사람 청취 평가
4. STT back-transcription 기반 가독성 평가
5. Jetson cold/warm 재측정

## 핵심 메트릭

- `model_load_sec`
  - 프로세스 시작 후 모델 사용 가능 상태까지 걸린 시간
- `time_to_audio_ready_sec`
  - 파일 저장 완료 또는 첫 재생 가능 시점까지 시간
- `audio_duration_sec`
  - 생성 음성 길이
- `real_time_factor`
  - `time_to_audio_ready_sec / audio_duration_sec`
  - 1.0 미만이면 오디오 길이보다 빠르게 생성한 것
- `peak_vram_mb`
  - GPU 메모리 최대 사용량
- `peak_ram_mb`
  - 시스템 메모리 최대 사용량
- `success_rate`
  - 문장셋 전체 중 실패 없이 합성한 비율
- `stt_back_transcription_cer`
  - 생성 음성을 STT로 다시 받아 적었을 때의 문자 오류율
- `stt_back_transcription_exact_match_rate`
  - 정규화 문장 기준 정확히 일치한 비율

현재 기본 scorer 계획:

- A100 로컬 `STTTranscriber(model="whisper", model_name="large-v3")`
- API scorer는 이번 benchmark 기본 경로에서 제외

현재 확인 상태:

- `../env/tts_eval_stt`에서 `large-v3` 초기화는 통과했다.
- 1-prompt smoke 기준으로 `melotts_ko`, `openvoice_v2_ko`, `piper_en`, `kokoro_en`, `edge_tts_ko`, `edge_tts_en` 경로가 자동 역전사까지 통과했다.
- `melotts_en`, `openvoice_v2_en`은 `nltk averaged_perceptron_tagger_eng` 리소스를 추가한 뒤 다시 통과했다.

## 청취 평가 항목

- `naturalness`
  - 너무 합성음처럼 들리지 않는지
- `voice_appeal`
  - 고객 시연에서 듣기 좋은 목소리인지
- `pronunciation`
  - 숫자, 영어, 고유명사, 조사 발음이 안정적인지
- `conversational_fit`
  - 로봇 응답으로 들었을 때 어색하지 않은지
- `persona_fit`
  - 원하는 캐릭터나 브랜드 톤에 맞는지

사람 청취 평가는 사용자가 모델별 샘플을 직접 듣고 `10점 만점` 기준으로 기록한다.

현재 바로 듣기 좋은 묶음 경로:

- grouped score sheet:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/ko_grouped_score_sheet.tsv`
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/en_grouped_score_sheet.tsv`
- prompt pack:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/prompt_packs/`
- Jetson Nano GUI:
  - script: `tts/tools/tts_listening_review_gui.py`
  - env: `../env/wake_word_jetson`
  - save target:
    - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/ko_grouped_score_sheet.tsv`
    - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/en_grouped_score_sheet.tsv`
    - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_scores_flat.tsv`

권장 수기 항목:

- `overall_impression_10`
- `naturalness_10`
- `voice_appeal_10`
- `pronunciation_10`
- `notes`

## 권장 평가 환경

- 같은 GPU 상태에서 모델별로 cold start 1회, warm run 3회 이상 측정
- 동일 문장셋 사용
- 출력 포맷과 sample rate를 통일
- 청취 평가는 같은 스피커 또는 같은 헤드폰으로 비교
- Jetson 단계에서는 같은 전원 모드와 같은 오디오 출력 장치를 유지

## 문장셋

- benchmark canonical prompt는 `prompts/tts_benchmark_prompts_v1.tsv`를 기준으로 한다.
- 사람 청취 canonical subset은 `prompts/tts_listening_subset_v1.tsv`를 기준으로 한다.
- 총 200문장:
  - 한국어 100문장
  - 영어 100문장
- 이 중 40쌍은 한영 대응 prompt로 묶고, 나머지는 언어 특화 prompt로 유지한다.
- 기존 얇은 데모 prompt는 `prompts/ko_demo_sentences_v1.txt`를 계속 보관한다.

## 산출물 위치 원칙

- 리포 안:
  - 문장셋, 평가 기준, 보고서 템플릿
- 리포 밖:
  - 실제 생성 오디오, 로그, CSV/JSON 결과
  - 권장 경로: `../results/tts/<date>/`
- benchmark smoke 결과 예시:
  - `../results/tts/benchmark_smoke_v1/`
  - `../results/tts/benchmark_smoke_en_fix/`
