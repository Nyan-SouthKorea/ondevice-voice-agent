# Logbook

> 최근 작업만 유지한다. 이전 상세 로그는 `docs/archive/logbook_2026_03_full_before_refactor.md`에 보관한다.

## 2026-03-19 | Human + Codex | Jetson Nano listening review GUI 연속 재생 오류 수정

- 기준 문서는 `docs/status.md`, `tts/evaluation/README.md`였다.
- 사용자가 같은 음성을 연속으로 2번 재생했을 때 GUI가 오류를 띄운다고 보고했다.
- `tts/tools/tts_listening_review_gui.py`에 playback token 기반 취소 처리를 추가해, 이전 재생이 `sd.stop()`으로 중단될 때 이를 사용자 오류로 간주하지 않도록 바꿨다.
- Nano에는 수정된 스크립트를 다시 반영했고, `DISPLAY=:0` 기준 GUI를 재실행했다.
- Nano에서 같은 파일을 짧은 간격으로 두 번 호출하는 probe를 실행했고, 예외 없이 `REPLAY_OK`를 확인했다.

## 2026-03-19 | Human + Codex | Jetson Nano TTS listening review GUI 실행

- 기준 문서는 `tts/evaluation/README.md`, `docs/status.md`, 기존 benchmark 결과물이었다.
- `tts/tools/tts_listening_review_gui.py`를 추가했다.
- `tkinter + sounddevice + soundfile` 조합으로 같은 prompt를 모델별로 재생하고 10점 점수를 남길 수 있게 했다.
- Nano에서는 `env/wake_word_jetson`이 GUI와 오디오 재생 의존성을 모두 만족해 그 env로 실행했다.
- benchmark listening 오디오와 grouped sheet를 Nano workspace로 복사했고, GUI는 `DISPLAY=:0`로 실제 화면에 띄웠다.
- 현재 저장 위치는 아래다.
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/ko_grouped_score_sheet.tsv`
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/en_grouped_score_sheet.tsv`
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_scores_flat.tsv`

## 2026-03-19 | Human + Codex | Orin Nano에서 TTS 4모델 bring-up 완료

- 기준 문서는 `docs/envs/jetson_tts_env.md`, `docs/reports/tts_agx_bringup_20260319.md`였다.
- Nano host `192.168.20.165`에서 `Piper`, `Kokoro`, `MeloTTS`, `OpenVoice V2` 4개 로컬 후보를 모두 실제 합성 가능한 상태로 만들었다.
- 핵심 결과는 아래였다.
  - `Piper (cpu)` 성공, `elapsed_sec 0.400`
  - `Kokoro (cuda)` 성공, `elapsed_sec 5.235`
  - `MeloTTS (cpu)` 성공, `elapsed_sec 15.057`
  - `OpenVoice V2 (cpu)` 성공, `elapsed_sec 39.795`
- `OpenVoice V2`는 Nano `cuda`에서 `NvMapMemAlloc error 12`로 실패했고, 현재 안정 경로는 `cpu`다.
- Nano에서는 `tts_openvoice_v2_jetson`을 `tts_melotts_jetson` 기반 shared env로 두는 실용 경로를 택했다.
- `tts/tools/tts_jetson_demo.py`는 이제 `/proc/device-tree/model`을 읽어 `AGX Orin`과 `Orin Nano`에서 다른 기본 device를 자동 선택하고, 필요하면 `openvoice_v2 -> tts_melotts_jetson` fallback도 자동 처리한다.
- 상세 숫자와 산출물 경로는 `docs/reports/tts_nano_bringup_20260319.md`로 승격했다.

## 2026-03-19 | Human + Codex | AGX Orin에서 TTS 4모델 bring-up 완료

- 기준 문서는 `docs/envs/jetson_tts_env.md`, `docs/envs/jetson/stt_trt_agx_orin_experiment.md`였다.
- AGX host `192.168.20.173`에서 새 root 구조 `/home/everybot/workspace/ondevice-voice-agent/{repo,env,results,secrets}`를 기준으로 작업했다.
- `Piper`, `Kokoro`, `MeloTTS`, `OpenVoice V2` 4개 로컬 후보를 모두 실제 smoke 가능한 상태로 만들었다.
- 핵심 우회 포인트는 아래였다.
  - `MeloTTS`: `torchaudio` ABI mismatch를 repo fallback으로 우회
  - `OpenVoice V2`: 검증된 `tts_melotts_jetson` env를 복제한 뒤 extras만 추가, `numpy==1.26.4` 유지, `wavmark`는 `--no-deps` 설치
- 상세 숫자와 산출물 경로는 `docs/reports/tts_agx_bringup_20260319.md`로 승격했다.
- 다음 단계는 같은 경로를 `Orin Nano`에 최소 변경으로 옮기는 것이다.

## 2026-03-18 | Human + Codex | Jetson TTS 1차 screening 완료

- 기준은 `OpenVoice V2`를 제외한 후보를 Jetson split env + thin demo wrapper로 직접 호출해 보는 것이었다.
- `tts/tools/tts_jetson_demo.py`와 split env 구조를 기준으로 아래 경로를 확인했다.
  - `tts_network_jetson`
  - `tts_piper_jetson`
  - `tts_melotts_jetson`
  - `tts_kokoro_jetson`
- network backend:
  - `Edge TTS` 성공, `elapsed_sec 2.213`
  - `OpenAI API TTS` 성공, `elapsed_sec 2.087`
- `Piper`:
  - 공식 영어 voice 성공
  - CPU `elapsed_sec 0.463`
  - GPU `elapsed_sec 1.802`
  - Jetson short-form 영어에는 CPU가 더 유리했다
- `MeloTTS`:
  - GPU는 `NvMapMemAlloc error 12`로 실패
  - CPU cold `elapsed_sec 105.405`
  - CPU warm `elapsed_sec 19.569`
  - 현재 Jetson 실시간 한국어 local 후보로는 무겁다고 판단했다
- `Kokoro`:
  - GPU cold `elapsed_sec 41.600`
  - GPU warm `elapsed_sec 2.013`
  - 영어 local 후보로 유지 가치가 높다
- thin wrapper 기본값 재검증:
  - `piper auto` `elapsed_sec 0.318`
  - `kokoro auto` `elapsed_sec 1.629`
  - `melotts auto` `elapsed_sec 14.506`
- screening 결론은 `docs/reports/tts_jetson_screening_20260318.md`로 승격했다.
- 현재 Jetson shortlist는 아래다.
  - 영어 local: `Piper cpu`, `Kokoro cuda`
  - 한국어는 일단 network fallback 유지

## 2026-03-18 | Human + Codex | OpenVoice rerun 반영과 TTS full benchmark 확정

- OpenVoice reference 재선정 뒤 A100 full rerun을 완료했다.
- 최종 active reference는 아래로 고정했다.
  - 한국어: `stt/datasets/korean_eval_50/021.wav` -> `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
  - 영어: `gpt-4o-mini-tts / marin` -> `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
- rerun 원본은 `../results/tts/openvoice_rerun_tmp_20260318/`에 보관했다.
- canonical benchmark `../results/tts/benchmark_full_v1_20260318/`에는 OpenVoice audio, listening sample, per_prompt, per_entry_summary를 새 결과로 교체했다.
- 결과는 `docs/reports/tts_benchmark_full_v1_20260318.md`로 승격했다.
- 자동 평가 기준 결론은 아래다.
  - 한국어 로컬 후보: `MeloTTS` 우위 유지
  - 영어 로컬 후보: `Kokoro`, `Piper` 우선
  - `OpenVoice V2`는 ref 재선정 뒤에도 이번 자동 평가 기준에서는 상위권으로 올라오지 못했다

## 2026-03-18 | Human + Codex | 진행 보고 빈도와 마일스톤 commit 규칙 보강

- 사용자가 장시간 작업에서 진행 보고를 더 자주 받고 싶어 했고, 중간 커밋 규칙이 문서에 명시적으로 없다는 점을 지적했다.
- 이에 따라 `docs/README.md`, `docs/개발방침.md`, `docs/decisions.md`에 아래 규칙을 추가했다.
  - 주요 액션 2~3개마다 한 줄 진행 보고
  - 긴 명령의 핵심 출력 요약
  - 장시간 작업의 마일스톤별 local commit 필요 여부 점검
  - push 시점은 별도 판단
  - 가능하면 `local commit 2회당 push 1회` 정도의 기본 cadence 유지

## 2026-03-18 | Human + Codex | OpenVoice reference 재선정 기준 변경

- 사용자가 현재 OpenVoice 결과가 reference 음성 때문에 불공정하다고 판단했고, 재평가 전에 후보 음성을 직접 듣고 고르길 원했다.
- `wake_word/data/hi_popo/positive/recorded`는 비어 있다는 점을 확인했다.
- 한국어 reference 후보는 `stt/datasets/korean_eval_50/` 직접 녹음 세트에서 다시 고르기로 했다.
- 영어 reference 후보는 직접 녹음한 영어 세트가 없으므로 `OpenAI Audio Speech API`의 `gpt-4o-mini-tts`로 생성하되, 공식 guide가 best quality로 권장하는 `marin`, `cedar`를 우선 후보로 두기로 했다.
- 후보 파일은 적용 전 검토용으로만 `../results/tts_assets/openvoice_v2/ref_candidates/20260318_stt_openai_v1/` 아래에 정리하고, 사용자가 선택하기 전까지는 기존 benchmark 결과나 active reference 파일을 교체하지 않기로 했다.

## 2026-03-18 | Human + Codex | TTS benchmark harness 구현과 A100 1-prompt smoke 검증

### Context

- 사용자가 장기 TTS benchmark 작업이 중간에 압축되더라도 흔들리지 않도록, 계획만이 아니라 실제 실행 코드와 canonical registry까지 문서에 고정하길 원했다.
- 또 사람 청취는 사용자가 직접 이어폰으로 듣고 10점 만점으로 입력할 예정이므로, 모델별 샘플 경로가 바로 열리게 정리되길 원했다.

### Actions

- `tts/evaluation/benchmark_registry_v1.json`를 추가해 10개 benchmark entry를 고정했다.
  - `melotts_ko`, `melotts_en`
  - `openvoice_v2_ko`, `openvoice_v2_en`
  - `piper_en`, `kokoro_en`
  - `edge_tts_ko`, `edge_tts_en`
  - `openai_api_ko`, `openai_api_en`
- `tts/evaluation/prompts/tts_listening_subset_v1.tsv`를 추가해 사람 청취용 canonical subset을 고정했다.
- `tts/tools/tts_benchmark_worker.py`와 `tts/tools/tts_benchmark.py`를 추가했다.
  - env별 worker subprocess 실행
  - peak RAM / VRAM 측정
  - `ffprobe` 기반 오디오 메타 수집
  - `ffmpeg` 기반 16k mono 변환
  - A100 로컬 `large-v3` scorer 기반 역전사
  - listening sample 복사와 `listening_scores_template.tsv` 생성
- `../env/tts_eval_stt`에서 `STTTranscriber(model="whisper", model_name="large-v3")` 초기화를 확인했다.
- OpenVoice V2 benchmark용 고정 reference를 `Edge TTS`로 생성했다.
  - `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
  - `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
- 영어 경로 smoke에서 `averaged_perceptron_tagger_eng` 누락을 확인하고, `tts_melotts`, `tts_openvoice_v2` env가 참조하는 `nltk_data`에 해당 리소스를 내려받았다.

### Results

- `../results/tts/benchmark_smoke_v1/`에서 1-prompt smoke를 실행했다.
- `../results/tts/benchmark_smoke_en_fix/`에서 영어 리소스 보강 후 재검증을 실행했다.
- 최종적으로 아래 entry들이 모두 1-prompt 자동 역전사까지 통과했다.
  - `melotts_ko`, `melotts_en`
  - `openvoice_v2_ko`, `openvoice_v2_en`
  - `piper_en`, `kokoro_en`
  - `edge_tts_ko`, `edge_tts_en`
- smoke 요약 예시:
  - `melotts_ko`: `mean_elapsed_sec 6.656`, `mean_rtf 1.332`, CER `0.0`
  - `openvoice_v2_ko`: `mean_elapsed_sec 8.016`, `mean_rtf 1.602`, CER `0.0`
  - `piper_en`: `mean_elapsed_sec 1.936`, `mean_rtf 0.701`, CER `0.0`
  - `kokoro_en`: `mean_elapsed_sec 1.794`, `mean_rtf 0.629`, CER `0.0`
  - `edge_tts_ko`: `mean_elapsed_sec 1.134`, `mean_rtf 0.204`, CER `0.0`
  - `edge_tts_en`: `mean_elapsed_sec 1.422`, `mean_rtf 0.524`, CER `0.0`
- 사람 청취용 경로와 수기 입력 템플릿도 생성된다.
  - 예: `../results/tts/benchmark_smoke_v1/listening/`
  - 예: `../results/tts/benchmark_smoke_v1/listening_scores_template.tsv`

### Next

- full prompt benchmark를 실행한다.
- 사용자가 listening sample을 듣고 10점 만점 수기 평가를 입력한다.
- 결과를 3개 비교 표로 정리한 뒤 Jetson shortlist를 좁힌다.

## 2026-03-18 | Human + Codex | TTS 6-backend benchmark 계획과 한영 200문장 canonical prompt 고정

### Context

- 사용자가 TTS 자동 평가를 바로 돌리기 전에, 장기 작업이 중간에 압축되더라도 흔들리지 않도록 benchmark 계획을 문서에 명확하게 고정하길 원했다.
- 또 `Piper`, `Kokoro`는 영어 기준으로라도 비교하고 싶어 했고, 사람 청취 평가는 사용자가 직접 이어폰으로 듣고 10점 만점으로 입력하는 방식으로 진행하길 원했다.

### Actions

- `docs/reports/tts_benchmark_plan.md`를 추가해 6개 backend 기준 benchmark 구조를 고정했다.
- 비교 표를 세 갈래로 나눴다.
  - 한국어 제품성 표
  - 영어 엔진 비교 표
  - 언어 독립 엔지니어링 표
- `tts/evaluation/README.md`를 현재 계획에 맞게 갱신했다.
- `tts/evaluation/prompts/tts_benchmark_prompts_v1.tsv`를 추가했다.
  - 한국어 100문장
  - 영어 100문장
  - 한영 대응 prompt 40쌍 포함
- STT 역전사 scorer는 API가 아니라 A100 로컬 `STTTranscriber(model="whisper", model_name="large-v3")` 경로를 우선 쓰는 쪽으로 정리했다.

### Results

- benchmark의 기준 문서와 canonical prompt가 고정되었다.
- 이후 컨텍스트가 압축되더라도 아래 두 파일을 기준으로 바로 이어갈 수 있다.
  - `docs/reports/tts_benchmark_plan.md`
  - `tts/evaluation/prompts/tts_benchmark_prompts_v1.tsv`

### Next

- A100 로컬 STT scorer env를 만들고 `STTTranscriber(model="whisper", model_name="large-v3")` 경로를 평가용으로 붙인다.
- 이어서 6개 backend 공통 benchmark harness를 작성한다.

## 2026-03-18 | Human + Codex | Edge TTS backend 추가와 OpenAI API alias 정리

### Context

- 사용자가 4개 로컬 TTS 후보를 평가하기 전에, wake word 학습에 쓰던 TTS도 같은 SDK형 인터페이스 아래에서 다시 쓸 수 있길 원했다.
- 또 기존 `api` TTS를 명시적으로 `chatgpt api tts`처럼 부를 수 있게 정리하길 원했다.

### Actions

- wake word positive 생성 스크립트를 다시 확인해, 사용한 TTS가 Amazon이 아니라 `edge_tts`임을 확인했다.
- `tts/backends/edge_tts.py`를 추가하고, `TTSSynthesizer(model="edge_tts")`로 공통 인터페이스에 연결했다.
- `tts_demo.py`와 공통 진입점에 `rate`, `pitch` 인자를 추가해 wake word 생성 조건을 그대로 재현할 수 있게 했다.
- `api`, `openai_api`, `chatgpt_api`가 모두 `OpenAIAPITTSModel`을 가리키도록 alias를 정리했다.
- `../env/tts_edge_tts`, `../env/tts_openai_api` env를 새로 만들었다.

### Results

- `Edge TTS` 한국어 smoke:
  - SDK smoke output: `../results/tts/20260318_edge_tts_smoke/sdk_import.wav`
  - CLI smoke output: `../results/tts/20260318_edge_tts_smoke/demo_cli.wav`
  - SDK smoke: `model_load_sec 0.000`, `elapsed_sec 0.915`
  - CLI smoke: `model_load_sec 0.000`, `elapsed_sec 0.849`
- 현재 SDK backend는 `.wav` 요청 시 `ffmpeg`로 실제 RIFF WAV를 만든다.
- 기존 wake word 공개 샘플은 `.wav` 이름이지만 실제 포맷은 MP3라는 점도 다시 확인했다.
- `OpenAI API TTS`는 실제 API 호출 없이 alias instantiation까지만 검증했다.
  - `openai_api -> OpenAIAPITTSModel`
  - `chatgpt_api -> OpenAIAPITTSModel`

### Next

- A100 4개 로컬 후보 benchmark를 진행하고, 필요하면 `Edge TTS`와 `OpenAI API TTS`를 reference 청취 baseline으로 함께 듣는다.

## 2026-03-18 | Human + Codex | Kokoro A100 env 구축과 공식 영어 smoke 검증

### Context

- 사용자가 `Kokoro`도 같은 방식으로 A100에서 실제 env와 backend까지 붙여 보길 원했다.
- 현재 프로젝트 방향상 과도한 구조 확장 없이 `TTSSynthesizer(model="kokoro")`로 공통 인터페이스를 유지하고, 공식 runtime 기준 smoke만 먼저 확인하면 충분했다.

### Actions

- `../env/tts_kokoro`를 만들고 `kokoro`, `soundfile`를 설치했다.
- 설치된 `kokoro/pipeline.py`를 확인해 공식 language code와 alias를 직접 확인했다.
- `tts/backends/kokoro.py`를 추가하고, `TTSSynthesizer(model="kokoro", model_name=<lang_code>, voice=<voice>)` 형태로 공통 인터페이스에 연결했다.
- A100 `cuda` 기준 공식 영어 경로 `lang_code='a'`, `voice='af_heart'`로 direct smoke, SDK smoke, CLI smoke를 순차 실행했다.

### Results

- 공식 language code는 `en-us`, `en-gb`, `es`, `fr-fr`, `hi`, `it`, `pt-br`, `ja`, `zh` 계열뿐이고, 현재 공식 Korean path는 없다.
- direct smoke:
  - `model_load_sec 15.646`
  - `elapsed_sec 2.941`
  - output `../results/tts/20260318_kokoro_smoke/hello_en.wav`
  - output length `4.600 sec`
- SDK smoke:
  - `model_load_sec 3.524`
  - `elapsed_sec 1.138`
  - output `../results/tts/20260318_kokoro_smoke/sdk_import.wav`
- CLI smoke:
  - `model_load_sec 3.403`
  - `elapsed_sec 1.231`
  - output `../results/tts/20260318_kokoro_smoke/demo_cli.wav`
- 첫 영어 실행에서는 `en_core_web_sm`가 자동 설치됐고, 현재 env에서는 `espeakng-loader`가 함께 설치되어 system `espeak-ng` 없이도 공식 영어 경로가 동작했다.

### Next

- `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 공통 benchmark 수집 구조를 붙인다.
- 한국어 제품 후보 판단은 `MeloTTS`, `OpenVoice V2` 중심으로 두고, `Kokoro`는 A100 비교 후보로만 유지한다.

## 2026-03-18 | Human + Codex | Piper 시행착오 산출물 정리

- `results/tts` 안에는 의미 있는 smoke와 비교 결과만 남기고, `20260318_piper_korean_debug`, `20260318_piper_korean_noise_search`, `20260318_piper_korean_norm_search`, `interactive.wav`, `manual_test.wav`는 `../results/_piper_artifact_archive_20260318_cleanup/`로 옮겨 작업 경로를 정리했다.

## 2026-03-18 | Human + Codex | Piper 한국어 품질 디버깅과 author runtime 비교

### Context

- 사용자가 `../results/tts/20260318_piper_korean_smoke/` 결과를 직접 들어 보고, 일본어 억양처럼 들려 현재 결과가 전혀 쓸 수 없다고 지적했다.
- 이어서 기존 STT 모듈을 이용해 가장 빠른 시간 안에 원인을 분리하고, 내 wrapper 실수인지 모델 자체 문제인지 더 명확히 확인하길 원했다.

### Actions

- `tts/backends/piper.py`의 `pygoruut` 경로를 다시 추적해 `pygoruut 0.7.0`과 `v0.6.2`를 비교했고, 단어 단위 `CleanWord / PrePunct / Phonetic` 출력을 직접 확인했다.
- 우리 STT 모듈의 API backend `gpt-4o-mini-transcribe`를 사용해 여러 phoneme 정규화와 `noise_scale / noise_w_scale` 조합을 짧게 역전사 비교했다.
- Hugging Face 모델 카드가 `piper-rs` 예제를 기준으로 배포된 점을 확인하고, Rust toolchain 설치 뒤 `piper-rs` 원 저자 repo를 lockfile 기준으로 library bin 형태로 빌드해 author runtime 합성 결과도 따로 생성했다.
- Python backend는 config에 `pygoruut_version`이 있으면 그 값을 우선 사용하도록 보완했다.

### Results

- `pygoruut 0.7.0`은 `안녕하세요 -> 녕 + 안하세요`처럼 분절이 명확히 깨졌다.
- `pygoruut v0.6.2`는 분절이 더 자연스러웠지만, Python `piper-tts` 경로에서는 역전사 기준 여전히 `"투페이파 하이단국가리 테스다시입니다"` 수준으로 무너졌다.
- `piper-rs` 원 저자 repo는 lockfile 기준 library bin 빌드와 합성까지는 성공했다.
  - output: `../results/tts/20260318_piper_korean_rust_smoke/wav_text_locked.wav`
  - 역전사: `안녕하세요. 카이퍼 땡구그린의 습들입니다.`
- 즉 현재 문제는 내 Python wrapper만의 문제로 보기 어렵고, 현재 model/phonemizer 조합 자체가 우리 한국어 기준에 맞지 않는 쪽에 가깝다고 판단했다.
- `pygoruut_version=v0.6.2`를 author runtime config에 명시한 추가 검증은 rustruut가 해당 goruut 실행 파일을 찾지 못해 재현이 막혔다.

### API Usage

- `purpose: tts_piper_debug`
  - 호출 `33회`
  - 총 오디오 길이 `144.822s`
  - 총 요청 시간 `33.659s`
  - 총 usage `2118 tokens`
- `purpose: tts_piper_runtime_compare`
  - 호출 `2회`
  - 총 오디오 길이 `8.556s`
  - 총 요청 시간 `1.691s`
  - 총 usage `130 tokens`
  - 비교 대상:
    - Python output `../results/tts/20260318_piper_runtime_compare_16k/python_sdk_16k.wav`
    - Rust output `../results/tts/20260318_piper_runtime_compare_16k/rust_locked_16k.wav`

### Next

- `Piper`는 영어 공식 voice 경량성 비교용으로만 유지하고, 한국어 제품 후보 판단은 사실상 보류한다.
- 다음 TTS 후보 구현과 공통 benchmark 쪽으로 무게중심을 옮긴다.

## 2026-03-18 | Human + Codex | Piper 서드파티 한국어 model smoke와 문서 정정

### Context

- 사용자가 `Piper` 한국어 지원 여부를 다시 검토했고, 공식 기본 voice 목록과 별개로 `neurlang/piper-onnx-kss-korean` 같은 서드파티 model까지 포함해 사실을 정리하길 원했다.
- 이어서 문서 표현을 정확히 고치고, A100에서 바로 한국어 smoke까지 확인하길 원했다.

### Actions

- 공식 Piper `VOICES.md`, Korean support discussion, Hugging Face `neurlang/piper-onnx-kss-korean` model 페이지를 다시 확인했다.
- `../results/tts_assets/piper/neurlang_kss_korean/` 아래에 `piper-kss-korean.onnx`, `piper-kss-korean.onnx.json`을 내려받았다.
- `tts/backends/piper.py`에 `phoneme_type=pygoruut` custom model용 얇은 호환 레이어를 추가했다.
- `../env/tts_piper`에 `pygoruut`를 설치하고, A100 `cuda:0`에서 SDK/CLI smoke를 순차 실행했다.
- `tts/README.md`, `tts/experiments/piper/README.md`, `docs/status.md`, `docs/research/tts.md`, `docs/envs/tts_a100_experiment_env.md`를 현재 사실에 맞게 정정했다.

### Results

- 공식 기본 Piper voice 목록에는 한국어가 없다는 점을 다시 확인했다.
- 서드파티 한국어 model `neurlang/piper-onnx-kss-korean`은 A100에서 로드와 합성까지는 확인했다.
  - SDK smoke: `model_load_sec 2.150`, `elapsed_sec 1.550`
  - CLI smoke: `model_load_sec 2.384`, `elapsed_sec 1.446`
  - providers: `CUDAExecutionProvider`, `CPUExecutionProvider`
  - output:
    - `../results/tts/20260318_piper_korean_smoke/sdk_import.wav`
    - `../results/tts/20260318_piper_korean_smoke/demo_cli.wav`
- 다만 이후 품질 디버깅 결과, 현재 이 model은 제품 기본 후보가 아니라 비교 연구 후보로만 두는 쪽이 맞다고 정리했다.

### Next

- `MeloTTS`, `OpenVoice V2`, `Piper` 공통 benchmark 수집 코드를 붙인다.
- 이어서 `Kokoro` env와 backend를 같은 구조로 시작한다.

## 2026-03-18 | Human + Codex | Piper A100 env 구축과 CUDA smoke 검증

### Context

- 사용자가 `Piper`도 A100에서 같은 공통 인터페이스 아래에 붙이고, 가능하면 GPU 경로까지 확인하길 원했다.
- 현재 프로젝트 방향상 과도한 확장 없이 `TTSSynthesizer(model="piper")` 형태의 backend와 1차 smoke만 확보하면 충분했다.

### Actions

- `/usr/bin/python3.10 -m venv` 기준으로 `../env/tts_piper`를 만들고 `piper-tts`, `onnxruntime-gpu`를 설치했다.
- `piper-tts` 기본 설치만으로는 ORT CUDA provider가 CPU로 fallback되는 것을 확인하고, `nvidia-cublas-cu12`, `nvidia-cuda-runtime-cu12`, `nvidia-cufft-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-nvrtc-cu12`를 env에 추가했다.
- `tts/backends/piper.py`를 추가하고, `TTSSynthesizer(model="piper")`로 공통 인터페이스에 연결했다.
- runtime에서는 `onnxruntime.preload_dlls(directory='')`를 사용해 NVIDIA wheel 라이브러리를 먼저 로드한 뒤 `PiperVoice.load(..., use_cuda=True)`가 `CUDAExecutionProvider`를 잡도록 정리했다.
- 공식 voice `en_US-lessac-medium`를 `../results/tts_assets/piper/` 아래로 내려받아 A100 smoke를 실행했다.

### Results

- 첫 smoke:
  - output `../results/tts/20260318_piper_smoke/hello_en.wav`
  - output length `3.808 sec`
- SDK smoke:
  - `model_load_sec 1.572`
  - `elapsed_sec 1.300`
  - providers `CUDAExecutionProvider`, `CPUExecutionProvider`
  - output `../results/tts/20260318_piper_smoke/sdk_import.wav`
- CLI smoke:
  - `model_load_sec 1.551`
  - `elapsed_sec 1.268`
  - output `../results/tts/20260318_piper_smoke/demo_cli.wav`
- 현재 공식 한국어 voice는 확인되지 않아, 1차 smoke는 영어 공식 voice로만 검증했다.

### Next

- `MeloTTS`, `OpenVoice V2`, `Piper` 공통 benchmark 수집 코드를 붙인다.
- 이어서 `Kokoro` env와 backend를 같은 구조로 시작한다.

## 2026-03-18 | Human + Codex | 문서 시작 게이트와 최소 문서 부트스트랩 규칙 강화

### Context

- 사용자가 세션이 길어지고 컨텍스트가 압축되더라도, 내가 매 작업 전에 문서를 다시 읽고 프로젝트 방향성을 재정렬하길 원했다.
- 동시에 새 프로젝트나 비어 있는 디렉토리에서도, 사용자가 따로 지시하지 않아도 최소 문서 체계를 먼저 만들고 운영을 시작하길 원했다.

### Actions

- `docs/README.md`에 작업 시작 게이트 규칙과 최소 문서 부트스트랩 규칙을 추가했다.
- `docs/개발방침.md`에 문서 refresh를 비사소한 작업의 시작 게이트로 둔다는 원칙을 추가했다.
- `docs/decisions.md`에 `docs/README.md` 선독과 최소 문서 체계 선생성 결정을 현재 유효한 운영 기준으로 고정했다.

### Next

- 이후 비사소한 작업에서는 먼저 `docs/README.md`와 관련 파생 문서를 읽고, 그 기준 문서를 짧게 확인한 뒤 진행한다.

## 2026-03-18 | Human + Codex | MeloTTS A100 첫 연결과 한국어 smoke 검증

### Context

- 사용자가 TTS 검토는 `MeloTTS`부터 실제로 시작하길 원했고, 계획 수립뿐 아니라 A100에서 바로 실행 가능한 상태까지 확인하길 원했다.

### Actions

- `/usr/bin/python3.10 -m venv` 기준으로 `../env/tts_melotts`를 만들고, `MeloTTS`와 `unidic`를 설치했다.
- `librosa 0.9.1`와 최신 `setuptools` 충돌 때문에 `setuptools<81` pin이 필요하다는 점을 확인했다.
- `tts/backends/melotts.py`를 추가하고, `TTSSynthesizer(model="melotts")`로 공통 인터페이스에 연결했다.
- A100 `cuda:0` 기준 한국어 smoke를 실행해 `../results/tts/20260318_melotts_smoke/hello_kr.wav`를 생성했다.

### Results

- 첫 smoke:
  - `model_load_sec 3.700`
  - `elapsed_sec 16.515`
  - output length `6.006 sec`
- 두 번째 새 프로세스 재실행:
  - `model_load_sec 2.713`
  - `elapsed_sec 5.972`
- 현재 확인된 MeloTTS 한국어 speaker id는 `KR -> 0`이다.

### Next

- `MeloTTS` 초기 평가 메트릭 수집 코드를 붙인다.
- 이어서 `OpenVoice V2` env와 backend를 같은 구조로 시작한다.

## 2026-03-18 | Human + Codex | OpenVoice V2 A100 env 구축과 reference voice smoke 검증

### Context

- 사용자가 `OpenVoice V2`도 A100에서 실제 backend와 env까지 붙여, SDK처럼 import 가능한 상태로 만들길 원했다.
- 동시에 지나친 구조 확장 없이 `TTSSynthesizer` 공통 인터페이스 아래에서 reference 음성 기반 한국어 smoke까지 확인하길 원했다.

### Actions

- `/usr/bin/python3.10 -m venv` 기준으로 `../env/tts_openvoice_v2`를 만들고, `OpenVoice`는 `--no-deps`로 설치한 뒤 `MeloTTS`, `av`, `faster-whisper`, `whisper-timestamped`, `wavmark` 등을 별도로 정리했다.
- `tts/backends/openvoice_v2.py`를 추가하고, `TTSSynthesizer(model="openvoice_v2", reference_audio_path=...)` 형태로 공통 인터페이스에 연결했다.
- `reference_audio_path`와 `checkpoint_root`를 공통 TTS 진입점과 CLI demo 인자에 추가했다.
- official `example_reference.mp3`를 기준으로 A100 `cuda:0` 한국어 smoke를 실행했고, 결과를 `../results/tts/20260318_openvoice_v2_smoke/` 아래에 저장했다.
- 같은 reference 음성을 반복 사용할 때 `processed/.../se.pth`를 재사용하도록 cache 경로를 보완했다.

### Results

- 첫 SDK smoke:
  - `model_load_sec 16.185`
  - `elapsed_sec 13.327`
  - total wall `34.442`
  - output `../results/tts/20260318_openvoice_v2_smoke/hello_kr.wav`
- CLI smoke:
  - `model_load_sec 12.149`
  - `elapsed_sec 10.528`
  - output `../results/tts/20260318_openvoice_v2_smoke/demo_cli.wav`
- cache 재사용 CLI smoke:
  - `model_load_sec 10.771`
  - `elapsed_sec 7.115`
  - output `../results/tts/20260318_openvoice_v2_smoke/demo_cli_cached.wav`
- 첫 smoke 출력 샘플 속성:
  - `6.304 sec`
  - `22050 Hz`
  - `mono`

### Next

- `MeloTTS`, `OpenVoice V2` 공통 benchmark 수집 코드를 붙인다.
- 이어서 `Piper` env와 backend를 같은 구조로 시작한다.

## 2026-03-18 | Human + Codex | TTS 4후보 비교 구조와 평가 계획 정리

### Context

- 사용자가 TTS는 A100에서 먼저 넓게 보고, 이후 Jetson으로 좁히는 방향을 원했다.
- 동시에 `docs/README.md`의 문서 운영 규칙을 지키면서, 디렉토리 구조와 평가 기준도 같이 정리하길 원했다.

### Actions

- `tts/` 아래에 `backends/`, `experiments/`, `evaluation/` 구조를 추가해 runtime 코드와 후보별 실험 메모, 평가 기준을 분리했다.
- A100 비교 후보를 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`로 고정하고, 각 후보별 실험 디렉토리를 만들었다.
- 공통 문장셋과 핵심 메트릭 기준을 `tts/evaluation/` 아래에 정리했다.
- `docs/status.md`, `docs/research/tts.md`, `docs/decisions.md`, `tts/README.md`를 현재 방향에 맞게 갱신했다.

### Next

- A100에서 후보별 env를 만들고, 4개 backend를 같은 인터페이스 아래에 붙인다.
- 공통 문장셋 기준으로 cold/warm latency, RAM/VRAM, 청취 품질 비교를 시작한다.

## 2026-03-18 | Human + Codex | STT 기본 모델 확정 문서화와 TTS 다음 단계 정리

### Context

- 사용자가 현재 STT 최종 모델을 `WhisperTRT small nano safe`로 명확히 고정하고, 그 이유와 다음 우선순위가 TTS라는 점을 문서 전반에 반영하길 원했다.
- 동시에 이미 폐기한 AGX cross-device TRT 경로를 active 문서 기준에서 완전히 제외한 상태로 정리하길 원했다.

### Actions

- `README.md`, `docs/status.md`, `docs/project_overview.md`, `docs/decisions.md`, `docs/jetson_transition_plan.md`, `stt/README.md`, `tts/README.md`를 현재 기준으로 다시 맞췄다.
- STT 기본 온디바이스 모델은 `WhisperTRT small nano safe`로 고정하고, 선택 이유를 `Jetson 직접 생성 safe 경로`, `온디바이스 정확도 우위`, `실사용 가능한 지연 시간` 기준으로 정리했다.
- STT 단독 GUI 기본 선택과 `STTTranscriber(model="whisper_trt")` 기본 checkpoint도 `small nano safe` 기준으로 맞췄다.
- TTS는 `OpenAI Audio Speech API` 최소 경로 이후 다음 집중 모듈이 `MeloTTS` Jetson 검증이라는 점을 상위 문서에 반영했다.

### Next

- Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
- 필요하면 `TTSSynthesizer`에 온디바이스 backend, playback, cache를 순서대로 붙인다.

## 2026-03-18 | Human + Codex | A100 워크스페이스 평탄화와 운영 정책 정리

### Context

- 사용자가 A100 기준 워크스페이스를 `project/` 한 단계 없이 `repo / env / secrets` sibling 구조로 단순화하길 원했다.
- 동시에 코드와 문서에 남아 있던 예전 경로를 모두 정리하고, 현재 운영 정책을 중복 없이 기준 문서에 반영하길 원했다.

### Actions

- 로컬 워크스페이스를 `repo / env / secrets` 기준으로 평탄화하고, A100 쪽 `env` 내부의 Jetson 가상환경은 비웠다.
- `stt`/`tts`가 리포 바깥 `../secrets/`를 기준으로 동작하도록 경로 해석과 오류 메시지를 정리했다.
- active 문서와 설정 파일에서 예전 상위 단계 경로 표현을 현재 워크스페이스 구조 기준으로 갱신했다.
- 운영 정책은 `README.md`, `docs/README.md`, `docs/개발방침.md`, `docs/decisions.md`, `docs/status.md`에 역할별로 나눠 반영하고, 모듈 문서와 연구 문서는 경로 예시만 맞췄다.

### Next

- A100에서 실제로 사용할 새 로컬 env 이름 규칙을 정한다.
- Jetson에서는 같은 repo branch를 기준으로 적용/검증만 수행하는 흐름을 유지한다.

## 2026-03-17 | Human + Codex | Wake Word + VAD + STT 통합 GUI 데모와 스크린샷 문서화

### Context

- 사용자가 wake word, VAD, STT를 한 화면에서 확인할 수 있는 통합 GUI 데모를 먼저 구현하길 원했다.
- 이후 데모 스크린샷 4장을 문서 자산으로 포함해, 단계별 동작을 보기 좋게 설명하길 원했다.

### Actions

- `voice_pipeline_gui_demo.py`를 추가해 `Wake Word 대기 -> 듣는 중 -> STT 처리 중 -> 출력 완료` 단계를 하나의 GUI로 연결했다.
- 통합 GUI는 `stt_trt_experiment` env를 기준으로 실행하고, Jetson ORT는 `.pth` 브리지로 재사용하게 맞췄다.
- 스크린샷 4장을 `docs/assets/screenshots/stt/` 아래로 옮기고, `stt/README.md`에 통합 GUI 설명과 화면 예시를 추가했다.
- STT 통합 GUI 시연 MP4 2개를 `docs/assets/videos/jetson_demos/` 아래로 정리하고, GIF 썸네일을 생성해 `stt/README.md`에서 클릭 가능한 형태로 연결했다.
- 현재 상태와 다음 작업은 `docs/status.md`에서 통합 GUI 기준으로 짧게 갱신했다.

### Next

- 실제 마이크 조건에서 통합 GUI의 wake threshold, VAD 종료 타이밍, STT 모델 기본값을 점검한다.
- 사용성 검증 후 SDK형 orchestrator 리팩토링이 필요한지 별도로 판단한다.

## 2026-03-17 | Human + Codex | STT GUI 6모델 선택지와 2모델 비교 제한 반영

### Context

- 사용자가 STT GUI에서 최종 6개 모델을 모두 선택할 수 있게 하되, 메모리 문제로 전체 동시 비교는 막고 최대 2개만 비교하길 원했다.

### Actions

- `stt/tools/stt_gui_demo.py`의 모델 선택지에 `small nano safe`, `small agx cross-device`를 포함해 6개 모델 구성을 맞췄다.
- 비교 모드는 `전체 비교` 대신 `선택 모델 비교`로 바꾸고, 최대 2개까지만 체크되도록 제한했다.
- 비교 대상이 아닌 모델은 메모리에 상주시켜 두지 않고, 임시 로드한 비교 모델은 실행 후 바로 `close()`와 `gc.collect()`로 정리하게 했다.
- 전사 결과 텍스트 영역 폰트를 줄여, 다중 비교 시 한 화면에 더 많은 텍스트가 보이도록 조정했다.

### Next

- STT GUI의 선택 모델 비교 UX를 실제 시연 기준으로 한 번 더 점검한다.
- 이후 wake word + VAD + STT 통합 GUI에 같은 선택 구조를 재사용한다.

## 2026-03-17 | Human + Codex | 문서 중복 정리와 TRT 시행착오 산출물 정리

### Context

- 사용자가 상세 내역을 중복되지 않게 다시 정리하고, `docs/README.md` 기준으로 문서 전반을 보완하길 원했다.
- 동시에 프로젝트 재현에 필요 없는 대용량 TRT 시행착오 산출물은 문서 기록만 남기고 삭제하길 원했다.

### Actions

- `docs/README.md`에 문서 수정 체크리스트와 산출물 정리 규칙을 추가했다.
- `docs/status.md`는 현재 기준만 남기도록 줄이고, STT 기본 후보와 TRT 대안 경로를 최신 상태로 맞췄다.
- `stt/README.md`는 STT 구조, 실행 방법, 모델 자산 역할 중심으로 정리하고 상위 상태 설명 중복을 줄였다.
- AGX Orin 교차 장치 `small` 경로는 checkpoint 상시 보관 대신 문서 기준만 유지하는 방향으로 정리했다.
- `results/` 아래 TRT 시행착오 산출물은 재현에 필요 없는 항목부터 삭제했다.

### Next

- `small nano safe` 기준 50문장 benchmark를 다시 수행할지 판단한다.
- STT 단독 GUI 데모를 먼저 보완하고, 이후 wake word + VAD + STT 통합 데모로 확장한다.

## 2026-03-17 | Human + Codex | STT 6모델 50문장 최종 비교 아카이브

### Context

- 사용자가 `tiny-cuda`, `base-cuda`, `base-trt`, `small-trt-safe`, `small-trt-unsafe`, `api` 6개 경로를 같은 50문장 세트로 다시 비교해 한눈에 볼 수 있게 정리하길 원했다.

### Actions

- `stt/tools/stt_benchmark.py`에 config file, variant, label, checkpoint 경로를 설정별로 받을 수 있게 추가했다.
- 같은 스크립트에서 모델별 자원 정리와 실패 summary 기록을 넣어, 한 경로가 실패해도 전체 실행이 끊기지 않게 했다.
- AGX Orin의 `small` checkpoint를 다시 가져와 `whisper_trt_small_ko_ctx64_fp16e_fp32w_agx_cross_device` 경로를 복원했다.
- `small nano safe`는 혼합 배치 실행에서 allocator assert가 나와, fresh process 단독 재실행 결과를 최종 6모델 세트에 합쳤다.
- 최종 아카이브를 `stt/eval_results/korean_eval_50/20260317_172300_six_model_final/`에 정리하고, 사람이 읽는 요약을 `docs/reports/stt_korean_eval50_six_model_overview.md`로 승격했다.

### Next

- 이 6모델 비교 결과를 기준으로 STT 기본값과 TRT 대안 경로를 다시 정리한다.
- 상위 wake word + VAD + STT 통합 데모에서 어떤 STT 조합을 기본 선택지로 둘지 결정한다.

## 2026-03-17 | Human + Codex | AGX Orin TRT handoff 문서화

### Context

- 사용자가 AGX Orin 장비에 SSH로 접속해, 현재 Jetson 기준 실험 내용을 그대로 참고하면서 WhisperTRT 빌드를 다시 시도하려고 했다.
- 장비가 바뀌면 JetPack, TensorRT, 메모리, power mode 차이 때문에 기존 Nano 기준 값만으로는 반복 재현성이 떨어질 수 있었다.

### Actions

- `stt/experiments/stt_trt_collect_jetson_profile.py`를 추가해 Jetson 장비 프로파일을 JSON으로 저장할 수 있게 했다.
- `docs/envs/jetson/stt_trt_agx_orin_experiment.md`를 추가해 AGX Orin에서 Codex가 따라야 할 순서와 빌드/검증 기준을 정리했다.
- `docs/envs/stt_trt_experiment_env.md`, `docs/jetson_transition_plan.md`, `stt/README.md`, `stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/README.md`에 새 handoff 경로를 연결했다.

### Next

- AGX Orin에서 먼저 장비 프로파일을 저장한다.
- 저장된 프로파일을 기준으로 `workspace`, `max_text_ctx`, chunk 크기를 조정해 TRT build를 재시도한다.

## 2026-03-17 | Human + Codex | WhisperTRT small 모델 정리

### Context

- 사용자가 `WhisperTRT small`을 실제 운용 가능한 형태로 정리하길 원했다.
- 문서에는 시행착오 자체보다, 실제 사용 가능한 모델 기준만 남기길 원했다.

### Actions

- `stt/experiments/stt_trt_builder_experiment.py`에서 encoder build 경로를 정리해, 필요한 encoder 조각만 GPU에 올리도록 수정했다.
- 그 결과 `WhisperTRT small`을 아래 두 기준으로 정리했다.
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_nano_safe`
    - Jetson Orin Nano 기준 safe 모델
    - GPU 메모리 부족 이슈를 피하기 위해 `decoder chunk 2`, `encoder chunk 1`, `workspace 64MB` 기준으로 생성
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_agx_cross_device`
    - AGX Orin에서 빌드한 교차 장치 확인용 모델
    - Nano에서 로드될 수 있지만 cross-device TensorRT 경고가 날 수 있음
- 기존 base 모델도 `whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy`로 이름을 바꿔 fp 형식을 드러내도록 정리했다.

### Next

- `nano_safe` small 모델을 기준으로 50문장 benchmark를 다시 수행한다.
- STT GUI와 상위 데모에서 사용할 기본 TRT 경로를 필요 시 `small nano safe`로 확장한다.

## 2026-03-17 | Human + Codex | STT GUI 데모 1차 구현 시작

### Context

- wake word / VAD / STT 통합 데모로 바로 가기 전에, STT 단독 GUI에서 녹음과 모델 전환 UX를 먼저 확인하기로 했다.

### Actions

- `docs/reports/stt_demo_plan.md`에 STT GUI 데모와 통합 GUI 데모의 2단계 계획을 정리했다.
- `whisper base fp16e_fp16w (trt, legacy)`를 STT 백엔드로 직접 부를 수 있도록 `stt_whisper_trt.py`를 추가했다.
- `tools/stt_gui_demo.py`를 추가해 `녹음 시작 / 정지`, 백그라운드 모델 로딩, 전사 히스토리, API 경고/호출 횟수 표시를 넣었다.
- 하나의 녹음에 대해 `tiny / base(cuda) / base(trt) / api`를 모두 순차 실행하는 전체 비교 모드도 추가했다.

### Next

- STT GUI 데모를 직접 시연한 뒤 UI와 파라미터 보완점을 반영한다.
- 그 다음 wake word + VAD + STT 통합 GUI 데모로 확장한다.

## 2026-03-17 | Human + Codex | STT 50문장 최종 비교 재실행

### Context

- STT 기본 경로를 정하기 전에 `API / whisper tiny(cuda) / whisper base(cuda) / whisper base(TRT)`를 같은 50문장 세트로 다시 비교할 필요가 있었다.

### Actions

- `stt/datasets/korean_eval_50/` 기준으로 네 경로를 다시 실행했다.
- TRT는 `stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/whisper_trt_split.pth`를 직접 읽어 평가했다.
- code-generated summary 기준 수치를 `stt/README.md`의 최종 비교 표에 반영했다.

### Next

- STT 기본값을 실제 음성 에이전트 파이프라인에 붙일 때는 `정확도 우선 / 속도 우선` 기준을 한 번 더 정리한다.

## 2026-03-17 | Human + Codex | STT 디렉토리 역할 기준 재정리

### Context

- `stt/` 루트에 런타임 코드와 실험/도구 스크립트가 함께 있어 구조가 빠르게 읽히지 않았다.

### Actions

- 실제 런타임 코드는 `stt/` 루트에 남기고, 반복 실행 도구는 `stt/tools/`, 실험성 TRT 코드는 `stt/experiments/`로 분리했다.
- 실행 명령과 환경 문서, STT README를 새 경로 기준으로 다시 맞췄다.

### Next

- 이후 새 STT 관련 파일은 처음부터 `런타임 / tools / experiments / models / datasets / eval_results` 역할을 구분해 추가한다.

## 2026-03-17 | Human + Codex | TTS 초기 구조와 개발 계획 시작

### Context

- `tts/`는 아직 상위 파이프라인이 바로 붙일 수 있는 공통 인터페이스가 없었다.

### Actions

- `TTSSynthesizer` 공통 진입점을 추가했다.
- OpenAI Audio Speech API 기반 최소 backend를 추가했다.
- 텍스트를 오디오 파일로 저장하는 데모를 추가했다.
- TTS 조사 문서와 상위 상태 문서를 현재 기준으로 동기화했다.

### Next

- Jetson에서 `MeloTTS` 설치와 한국어 합성 smoke를 검증한다.
- playback, cache, LLM 출력 연결 순서로 확장한다.

## 2026-03-16 | Human + Codex | STT 직접 녹음 평가 파이프라인 추가

### Context

- STT 기본 모델을 감으로 정하지 않고, 실제 사용자의 직접 녹음 50문장으로 비교하기로 했다.

### Actions

- `stt/datasets/korean_eval_50/` 평가 세트를 추가했다.
- 순차 녹음 GUI와 다중 STT benchmark 스크립트를 추가했다.
- 샘플별 결과와 요약 CSV/JSON 저장 구조를 만들었다.

### Next

- 사용자가 50문장을 직접 녹음한다.
- `whisper tiny / base / small`과 필요 시 API 경로를 비교한다.

## 2026-03-16 | Human + Codex | VAD 구조와 기본 filtering 정리

### Context

- wake word 다음 단계로 붙일 수 있는 최소 VAD 구조와 흔들림 완화가 필요했다.

### Actions

- `VADDetector` 공통 진입점과 `webrtcvad` / `silero` backend를 정리했다.
- `min_speech_frames=3`, `min_silence_frames=10` 기본 filtering을 추가했다.
- 기본 backend를 `silero` 기준으로 정리했다.

### Next

- wake word 뒤에 붙여 speech start / end 기준을 확정한다.

## 2026-03-16 | Human + Codex | wake word / VAD 완료 기준으로 상위 문서 재정렬

### Context

- 상위 문서 여러 곳에 같은 상태가 반복돼 있어, 완료 기준을 다시 맞출 필요가 있었다.

### Actions

- 루트 README, status, Jetson 관련 문서, 모듈 README를 현재 완료 상태에 맞춰 동기화했다.
- Jetson demo 스크린샷과 영상 자산을 리포 문서 자산 구조로 정리했다.

### Next

- 상위 문서 중복을 더 줄이고, 현재 상태 기준은 `status.md` 하나로 수렴한다.
