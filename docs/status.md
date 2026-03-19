# Status

> 마지막 업데이트: 2026-03-19

## 현재 목표

- TTS는 공통 래퍼 구조 아래에서 A100 기준 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 4개 로컬 후보를 비교하고, `Edge TTS`, `OpenAI API TTS`는 reference backend로 함께 유지한 뒤 Jetson 실측으로 후보를 좁힌다.
- STT는 `WhisperTRT small nano safe`를 온디바이스 기본값으로 유지하고, wake word + VAD + STT 통합 GUI에서 실사용 조건을 다듬는다.
- `Whisper base (PyTorch + CUDA)`와 `WhisperTRT base legacy`는 비교 기준/속도 fallback으로 유지한다.
- wake word와 VAD를 연결해 STT 입력 구간 절단 기준을 확정한다.
- 상위 음성 파이프라인을 SDK형 인터페이스로 연결할 준비를 한다.
- STT 전용 GUI와 wake word + VAD + STT 통합 GUI를 기준으로 상위 파이프라인 UX를 검증한다.

## 현재 고정 기준

- wake word 호출어: `하이 포포`
- 추론 타깃: `Jetson Orin Nano Developer Kit 8GB`
- wake word runtime: ONNX 기반 로컬 feature backbone + classifier
- VAD 기본 backend: `silero`
- STT 기본 방향: 온디바이스 기본값은 `WhisperTRT small nano safe`로 고정하고, `Whisper base (PyTorch + CUDA)`와 `WhisperTRT base legacy`는 비교 기준과 fallback으로 병행 관리
- TTS 기본 방향: `공통 래퍼 + API 최소 경로`를 유지하되, A100에서는 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro` 4개 로컬 후보를 비교하고 `Edge TTS`, `OpenAI API TTS`는 reference baseline으로 함께 본다

## 모듈 상태

| 모듈 | 상태 | 메모 |
|---|---|---|
| Wake word | 완료 후 튜닝 단계 | `final_full_best_trial40`, `threshold 0.80`, Jetson GUI demo 완료 |
| VAD | 완료 | `VADDetector` 공통 진입점, `silero` 기본 backend |
| STT | 기본값 확정 완료, 통합 GUI 실사용 검증 단계 | 온디바이스 기본값은 `WhisperTRT small nano safe`, wake word + VAD + STT 통합 GUI 데모 유지 |
| TTS | A100 full benchmark 확정, partial human listening 반영, AGX/Nano 4모델 bring-up 완료, Jetson runtime winner + custom training planning 단계 | `TTSSynthesizer`, OpenAI API backend, Edge TTS backend, MeloTTS backend, OpenVoice V2 backend, Piper backend, Kokoro backend, A100 4후보 + 2 reference full benchmark 완료, OpenVoice reference 재선정 반영, local STT scorer, listening sample 구조 준비, Jetson Nano GUI 기반 partial human listening 반영, Jetson split env + thin demo 완료, AGX와 Orin Nano에서 4개 로컬 후보 smoke 완료, 다음 active 방향은 `Piper/Kokoro` runtime winner 검증 + `OpenVoice V2` synthetic dataset pipeline |
| LLM | 대기 | 상위 orchestration만 남아 있음 |

## 핵심 메모

- wake word 핵심 수치
  - best run: `wake_word/models/hi_popo/runs/final_full_best_trial40`
  - `val_recall 0.9966`
  - `val_fp_rate 0.0114`
  - 현재 runtime 기준 threshold: `0.80`
- Jetson runtime과 smoke 학습 환경은 각각 `wake_word/docs/환경/260313_1700_Jetson_웨이크워드_환경.md`, `wake_word/docs/환경/260316_1616_웨이크워드_학습스모크_환경.md`에 정리돼 있다.
- STT 50문장 직접 녹음 평가 세트와 benchmark 파이프라인은 준비돼 있다.
- 현재 로컬에 유지하는 TRT 자산 기준은 아래와 같다.
  - `whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy`
  - `whisper_trt_small_ko_ctx64_fp16e_fp32w_nano_safe`
- 50문장 현재 active 비교 기준은 아래 문서를 본다.
  - `stt/docs/보고서/260318_1056_STT_한국어평가50_6모델_개요.md`
- 현재 로컬 워크스페이스 기준은 `repo / env / secrets` sibling 구조다.
  - A100에서는 `env`를 비워 두고 필요할 때만 다시 만든다.
  - Jetson에서는 같은 repo branch를 기준으로 실기 검증과 TRT 빌드를 진행한다.
- STT 자동 생성 결과물은 `stt/eval_results/` 아래에 두고, 사람이 읽는 요약은 `stt/docs/보고서/260318_1056_STT_한국어평가50_6모델_개요.md`를 기준으로 본다.
- 현재 STT 기본값은 `WhisperTRT small nano safe`다.
  - code-generated 비교 요약 기준:
    - `normalized_exact_match_rate 0.4600`
    - `mean_normalized_cer 0.0886`
    - `mean_stt_sec 0.3823`
  - Jetson Orin Nano 8GB에서 직접 생성한 safe TRT 경로라서 cross-device 불확실성이 없다.
  - 현재 로컬 온디바이스 경로 중 정확도가 가장 좋고, 동시에 평균 처리 시간도 실사용 가능한 수준이다.
  - API 의존 없이 Jetson 내부에서 바로 재사용할 수 있어 상위 음성 파이프라인 기본값으로 두기 적합하다.
  - 속도 fallback은 `WhisperTRT base legacy`다.
  - 최고 정확도 참고값은 `gpt-4o-mini-transcribe (api)`지만, 기본값으로는 두지 않는다.
- TTS는 현재 `OpenAI Audio Speech API`로 최소 합성 경로를 열어 두었고, 다음 집중 모듈은 A100 기준 4후보 비교 구조 확립이다.
- `OpenAI API TTS`는 현재 `api`, `openai_api`, `chatgpt_api` alias로 모두 같은 backend를 사용한다.
  - env: `../env/tts_openai_api`
  - 현재 기본 모델: `gpt-4o-mini-tts`
  - 현재 기본 voice: `alloy`
  - 현재 검증: 실제 API 호출 없이 alias 인스턴스화만 확인했다
- wake word positive 생성에 사용했던 TTS는 Amazon이 아니라 `Edge TTS`였다.
  - env: `../env/tts_edge_tts`
  - wake word 생성 스크립트: `wake_word/train/01_generate_positive.py`
  - 현재 smoke voice: `ko-KR-InJoonNeural`
  - SDK smoke: `model_load_sec 0.000`, `elapsed_sec 0.915`
  - CLI smoke: `model_load_sec 0.000`, `elapsed_sec 0.849`
  - smoke output:
    - `../results/tts/20260318_edge_tts_smoke/sdk_import.wav`
    - `../results/tts/20260318_edge_tts_smoke/demo_cli.wav`
  - 구현 메모: 기존 wake word 생성 스크립트는 `.wav` 이름으로 MP3를 저장했지만, 현재 SDK backend는 `ffmpeg`로 실제 WAV로 변환한다
- `MeloTTS`는 A100 `cuda:0` 기준 첫 한국어 smoke를 통과했다.
  - env: `../env/tts_melotts`
  - 첫 smoke: `model_load_sec 3.700`, `elapsed_sec 16.515`
  - 두 번째 새 프로세스 재실행: `model_load_sec 2.713`, `elapsed_sec 5.972`
  - output length: `6.006 sec`
  - 설치 메모: `setuptools<81` pin 필요, 첫 한국어 실행에서 `python-mecab-ko` 자동 설치 발생
- `OpenVoice V2`는 A100 `cuda:0` 기준 reference 음성 기반 한국어 smoke를 통과했다.
  - env: `../env/tts_openvoice_v2`
  - checkpoint root: `../results/tts_assets/openvoice_v2/checkpoints_v2`
  - 첫 SDK smoke: `model_load_sec 16.185`, `elapsed_sec 13.327`, total wall `34.442`
  - CLI smoke: `model_load_sec 12.149`, `elapsed_sec 10.528`
  - 같은 reference 재사용 cache smoke: `model_load_sec 10.771`, `elapsed_sec 7.115`
  - output length 예시: `6.304 sec`, `22.05kHz`, `mono`
  - 구현 메모: `reference_audio_path` 필수, `se.pth` cache 재사용 추가
- `Piper`는 A100 `cuda:0` 기준 공식 영어 voice smoke를 통과했고, 서드파티 한국어 model은 Python 경로와 `piper-rs` 원 저자 lockfile 경로 둘 다 현재 품질은 무효로 본다.
  - env: `../env/tts_piper`
  - asset root: `../results/tts_assets/piper`
  - 공식 smoke voice: `en_US-lessac-medium`
  - 공식 기본 `VOICES.md` 목록에는 한국어가 없다
  - 서드파티 한국어 model: `../results/tts_assets/piper/neurlang_kss_korean/piper-kss-korean.onnx`
  - 서드파티 한국어 model 페이지 라이선스 표기: `CC-BY-NC-SA-4.0`
  - 영어 SDK smoke: `model_load_sec 1.572`, `elapsed_sec 1.300`
  - 영어 CLI smoke: `model_load_sec 1.551`, `elapsed_sec 1.268`
  - 한국어 custom model은 `pygoruut` custom phonemizer와 Python `piper-tts` 사이 호환 레이어가 필요했다
  - `pygoruut` 버전, phoneme 정규화, `noise_scale / noise_w_scale`까지 짧게 탐색했지만, STT 역전사 기준으로도 여전히 `"파이퍼 한국어 테스트입니다"`를 안정적으로 재현하지 못했다
  - `piper-rs` 원 저자 repo는 lockfile 기준 library bin 빌드와 기본 합성까지는 가능했지만, 역전사 기준 `"카이퍼 땡구그린의 습들입니다"` 수준으로 여전히 품질이 무효였다
  - `pygoruut_version=v0.6.2`를 config에 명시한 `piper-rs` 경로는 현재 rustruut 실행 파일 부재로 재현이 막혔다
  - providers: `CUDAExecutionProvider`, `CPUExecutionProvider`
  - 구현 메모: `onnxruntime.preload_dlls(directory='')`, NVIDIA CUDA wheel, `pygoruut` 호환 레이어가 필요했다
  - 결론 메모: 현재 Python 경로와 author runtime 기준 모두 한국어 품질이 무효라 제품 기본 후보로는 두지 않는다
- `Kokoro`는 A100 `cuda` 기준 공식 영어 smoke를 통과했고, 현재 공식 language code에는 한국어가 없다.
  - env: `../env/tts_kokoro`
  - 공식 repo/model: `hexgrad/Kokoro-82M`
  - 공식 language code: `en-us`, `en-gb`, `es`, `fr-fr`, `hi`, `it`, `pt-br`, `ja`, `zh`
  - direct smoke: `model_load_sec 15.646`, `elapsed_sec 2.941`
  - direct smoke output: `../results/tts/20260318_kokoro_smoke/hello_en.wav`
  - direct smoke output length: `4.600 sec`, `24kHz`, `mono`
  - SDK smoke: `model_load_sec 3.524`, `elapsed_sec 1.138`
  - SDK smoke output: `../results/tts/20260318_kokoro_smoke/sdk_import.wav`
  - CLI smoke: `model_load_sec 3.403`, `elapsed_sec 1.231`
  - CLI smoke output: `../results/tts/20260318_kokoro_smoke/demo_cli.wav`
  - 구현 메모: 첫 영어 실행에서 `en_core_web_sm` 자동 설치, 현재 env에서는 `espeakng-loader`가 함께 설치되어 system `espeak-ng` 없이도 공식 영어 경로가 동작했다
  - 결론 메모: A100 비교 후보로는 유지하되, 현재 공식 Korean path가 없으므로 한국어 제품 기본 후보로 바로 올리지는 않는다
- Jetson TTS screening 1차 결과는 `tts/docs/보고서/260318_1912_TTS_Jetson_스크리닝.md`를 기준으로 본다.
  - thin demo wrapper: `tts/tools/tts_jetson_demo.py`
  - split env:
    - `../env/tts_network_jetson`
    - `../env/tts_piper_jetson`
    - `../env/tts_melotts_jetson`
    - `../env/tts_kokoro_jetson`
  - Jetson remote output root:
    - `/home/everybot/workspace/ondevice-voice-agent/results/tts/jetson_demo/`
  - screening 요약:
    - `Edge TTS (KO)` 성공, `elapsed_sec 2.213`
    - `OpenAI API TTS (KO)` 성공, `elapsed_sec 2.087`
    - `Piper (EN, cpu)` 성공, `elapsed_sec 0.318`
    - `Piper (EN, cuda:0)` 성공, `elapsed_sec 1.802`
    - `MeloTTS (KO, cuda:0)` 실패, `NvMapMemAlloc error 12`
    - `MeloTTS (KO, cpu warm)` 성공, `elapsed_sec 14.506`
    - `Kokoro (EN, cuda warm)` 성공, `elapsed_sec 1.629`
  - 현재 Jetson shortlist:
    - 영어 local: `Piper cpu`, `Kokoro cuda`
    - 한국어는 일단 network fallback 유지
- Orin Nano 4모델 bring-up 결과는 `tts/docs/보고서/260319_0930_TTS_나노_구동기록.md`를 기준으로 본다.
  - `Piper (EN, cpu)` 성공, `elapsed_sec 0.400`
  - `Kokoro (EN, cuda)` 성공, `elapsed_sec 5.235`
  - `MeloTTS (KO, cpu)` 성공, `elapsed_sec 15.057`
  - `OpenVoice V2 (KO, cpu)` 성공, `elapsed_sec 39.795`
  - `OpenVoice V2 (KO, cuda)`는 `NvMapMemAlloc error 12`로 실패해 Nano 기본 경로를 `cpu`로 둔다
  - `tts/tools/tts_jetson_demo.py`는 이제 `/proc/device-tree/model`을 읽어 `AGX Orin`과 `Orin Nano`에서 다른 기본 device를 자동 선택한다
- AGX Orin 4모델 bring-up 결과는 `tts/docs/보고서/260319_0907_TTS_AGX_구동기록.md`를 기준으로 본다.
  - AGX result root:
    - `/home/everybot/workspace/ondevice-voice-agent/results/tts/agx_smoke/`
  - AGX smoke 요약:
    - `Piper (EN, cpu)` 성공, `elapsed_sec 0.269`
    - `Kokoro (EN, cuda)` 성공, `elapsed_sec 2.752`
    - `MeloTTS (KO, cpu)` 성공, `elapsed_sec 10.504`
    - `MeloTTS (KO, cuda:0)` 성공, `elapsed_sec 5.428`
    - `OpenVoice V2 (KO, cuda:0)` 성공, `elapsed_sec 10.640`
  - 구현 메모:
    - `MeloTTS`는 `torchaudio` ABI mismatch를 repo fallback으로 우회했다
    - `OpenVoice V2`는 `tts_melotts_jetson` env 복제 + extras 추가 + `numpy==1.26.4` 고정으로 살렸다
  - 현재 `tts/tools/tts_jetson_demo.py`는 `openvoice_v2`도 포함하며, reference와 checkpoint root 기본값을 자동으로 채운다
- TTS 개발 판단은 아래 순서를 따른다.
  - 1차: A100에서 `MeloTTS`, `OpenVoice V2`, `Piper`, `Kokoro`를 모두 같은 기준으로 구현하고 비교한다.
  - 2차: A100 결과를 바탕으로 Jetson 실측 후보를 좁힌다.
  - 3차: 위 둘이 모두 부족할 때만 custom voice 학습을 검토한다.
- 현재 TTS benchmark canonical 계획은 `tts/docs/보고서/260318_1708_TTS_벤치마크_계획.md`를 기준으로 본다.
- 현재 canonical prompt는 `tts/evaluation/prompts/tts_benchmark_prompts_v1.tsv`다.
  - 한국어 100문장
  - 영어 100문장
  - 이 중 40쌍은 한영 대응 prompt다
- 현재 canonical benchmark registry는 `tts/evaluation/benchmark_registry_v1.json`이다.
- 현재 canonical listening subset은 `tts/evaluation/prompts/tts_listening_subset_v1.tsv`다.
- 사람 청취 평가는 사용자가 모델별 샘플을 직접 듣고 10점 만점으로 입력하는 방식으로 진행한다.
- 현재 canonical full benchmark 결과 루트는 `../results/tts/benchmark_full_v1_20260318/`다.
  - 자동 요약: `../results/tts/benchmark_full_v1_20260318/per_entry_summary.tsv`
  - 자동 상세: `../results/tts/benchmark_full_v1_20260318/per_prompt.tsv`
  - 사람 청취 템플릿: `../results/tts/benchmark_full_v1_20260318/listening_scores_template.tsv`
  - Jetson Nano GUI 수기 입력:
    - script: `tts/tools/tts_listening_review_gui.py`
    - grouped score sheet:
      - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/ko_grouped_score_sheet.tsv`
      - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/en_grouped_score_sheet.tsv`
    - flat export:
      - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_scores_flat.tsv`
    - partial summary:
      - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_score_summary.tsv`
    - GUI screenshot:
      - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/assets/tts_listening_review_gui_20260319.png`
- 현재 partial human listening coverage는 아래다.
  - 한국어: `KO001`, `KO010`, `KO018`
  - 영어: `EN001`
- partial human listening 기준 요약은 아래처럼 본다.
  - 한국어: `MeloTTS (KO) 9.00`, `OpenAI API TTS (KO) 8.33`, `Edge TTS (KO) 8.00`, `OpenVoice V2 (KO) 8.00`
  - 영어: `Kokoro (EN) 10.00`, `Piper (EN) 10.00`, `MeloTTS (EN) 10.00`, `OpenVoice V2 (EN) 9.00`
  - 단, 영어는 `EN001` 한 문장만 평가했으므로 순위 확정 근거로 쓰지 않는다.
- 현재 active TTS 후속 계획은 아래 문서를 기준으로 본다.
  - `tts/docs/보고서/260319_1052_TTS_커스텀_학습_계획_v1.md`
- 현재 training feasibility audit 기준 문서는 아래다.
  - `tts/docs/보고서/260319_1100_TTS_학습_가능성_점검.md`
- 현재 `Piper` pilot 실행 계획 기준 문서는 아래다.
  - `tts/docs/보고서/260319_1308_TTS_Piper_파일럿_학습_실행계획.md`
- 현재 `Piper` pilot 자동평가 결과 기준 문서는 아래다.
  - `tts/docs/보고서/260319_1324_TTS_Piper_파일럿_자동평가_결과.md`
- 현재 `Piper` pilot training env 기준 문서는 아래다.
  - `tts/docs/환경/260319_1100_Piper_학습환경.md`
- 현재 `Piper` pilot 학습은 완료됐다.
  - root: `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/`
  - GPU: `GPU0`
  - dataset snapshot: `2.0시간 / 1,928문장`
  - 현재 중요한 checkpoint review 정책은 실제로 동작 중이다.
    - 별도 보관된 checkpoint:
      - `epoch=0-step=118`
      - `epoch=1-step=236`
      - `epoch=5-step=708`
    - review sample root:
      - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/checkpoint_review/review_samples/`
  - 학습 종료 후 자동 후처리도 걸어뒀다.
    - 상태 파일:
      - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/postprocess_status.local.md`
    - 완료 후 생성 예정:
      - `exported_onnx/`
      - `benchmark_postprocess/`
- 현재 `Piper` pilot은 학습, ONNX export, 자동 benchmark까지 완료됐다.
  - benchmark root:
    - `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/benchmark_postprocess/20260319_132231/`
  - 자동지표 기준 최고 checkpoint:
    - `epoch=10-step=1298`
  - 현재 자동지표 결론:
    - `20`개 한국어 prompt 기준 모든 checkpoint의 exact match가 `0.0`
    - best `mean_normalized_cer`도 `0.9149`로 아직 품질이 부족하다
  - 따라서 현재 pilot은 파이프라인 성립 검증에는 성공했지만, full training 확대는 보류한다.
- 현재 active 역할 분리는 아래와 같다.
  - Jetson runtime winner 후보: `Piper`, `Kokoro`
  - voice audition / synthetic dataset 생성기: `OpenVoice V2`
  - 기존 benchmark anchor와 비교용 후보: `MeloTTS`
- 현재 training 우선순위 판단은 아래처럼 둔다.
  - `Piper`: training pilot 1순위
  - `Kokoro`: runtime 우선, training 후순위
- 현재 `Piper` pilot training env는 A100에서 아래까지 확인했다.
  - `torch 1.13.1+cu117`, `pytorch-lightning 1.7.7`
  - `numpy<2`, `torchmetrics<0.12`, `setuptools<81`, `pip<24.1`
  - `build_monotonic_align.sh`
  - `piper_train`, `piper_train.preprocess`, `piper_train.export_onnx` help
  - `piper_phonemize` 기반 한국어 phonemization
  - 한국어 `preprocess --skip-audio` smoke
- 현재 `Piper` training blocker는 초기 예상보다 줄었다.
  - system `espeak-ng`는 아직 미설치지만, 현재 env 기준 즉시 blocker는 아니었다
  - 실제 다음 관문은 synthetic dataset와 pilot training 본 실행이다
- 현재 synthetic inventory snapshot은 아래를 기준으로 본다.
  - root: `../results/tts_custom/synthetic_dataset/260319_1308_합성데이터_인벤토리/`
- 현재 active 대규모 생성 run은 아래다.
  - `../results/tts_custom/synthetic_dataset/full_v2_tts_only/openvoice_ko_female_announcer_speed_1p1/`
  - 진행률 파일:
    - `progress.local.md`
  - 다음 run은 `v3` corpus 기준으로 supervisor가 자동 연결한다.
    - supervisor 상태:
      - `../results/tts_custom/synthetic_dataset/_local_supervisor/run_openvoice_v3_after_v2.local.md`
  - usable unique: `7,876문장 / 9.398시간`
  - archive/reference 전용 row: `1,058`
- 현재 active Piper pilot run은 아래다.
  - root: `../results/tts_custom/training/260319_1312_Piper_한국어_파일럿_v1/`
  - dataset snapshot: `1,928문장 / 2.0시간`
  - mode: `medium scratch / single-speaker / GPU0`
  - generation은 GPU1에서 계속 진행하고, pilot 학습은 GPU0에서 분리 실행한다
- 현재 checkpoint review 정책은 아래처럼 둔다.
  - 매 epoch checkpoint 저장
  - 중요 checkpoint는 `epoch 0`, `epoch 1`, 이후 `5 epoch`마다 별도 보관
  - 중요 checkpoint마다 review prompt wav를 같이 저장해 사람이 직접 듣고 선택할 수 있게 한다
- 한국어 custom training용 준비물은 아래까지 실제로 만들었다.
  - 한국어 text-only corpus: `../results/tts_custom/corpora/ko_text_corpus_v1/`
  - corpus 준비 스크립트: `tts/tools/prepare_ko_text_corpus.py`
  - OpenVoice reference 준비 스크립트: `tts/tools/openvoice_prepare_reference.py`
  - OpenVoice audition 스크립트: `tts/tools/openvoice_audition.py`
  - synthetic dataset 생성 스크립트: `tts/tools/openvoice_generate_dataset.py`
- 현재 `ko_text_corpus_v1` 기준 pilot 후보 규모는 아래다.
  - `pilot_count=1352`
  - `pilot_estimated_sec=5402.78`
  - `pilot_estimated_hour=1.501`
- 부분 생성본 실측 기준 pilot synthetic dataset 생성 예상 시간은 아래처럼 본다.
  - 부분 생성 결과: `168 wav`, `774.757 sec` audio
  - global wall span: `205.123 sec`
  - observed global RTF: `0.2648`
  - 현재 추정: `1.5시간 pilot audio -> 약 24분`, 안전하게는 `25~30분`
- 현재 OpenVoice 신규 audition reference 후보는 아래 둘을 active pending 상태로 둔다.
  - 남성 reference: `../results/tts_custom/references/ko_male_lee_sunkyun/ko_male_lee_sunkyun.wav`
  - 여성 reference: `../results/tts_custom/references/ko_female_announcer/ko_female_announcer.wav`
- 현재 사용자가 직접 들어볼 OpenVoice 10문장 샘플 경로는 아래다.
  - 남성: `../results/tts_custom/audition/openvoice_ref_audition_20260319_v2/ko_male_lee_sunkyun/`
  - 여성: `../results/tts_custom/audition/openvoice_ref_audition_20260319_v2/ko_female_announcer/`
  - prompt 기준: `tts/evaluation/prompts/openvoice_audition_prompts_ko_v2.tsv`
- OpenVoice custom training active selection은 아래로 고정한다.
  - reference: `ko_female_announcer`
  - reference audio: `../results/tts_custom/references/ko_female_announcer/ko_female_announcer.wav`
  - source archive: `../results/tts_custom/references/source_videos/20260319/ref 음성-여성 아나운서.mp4`
  - approved speed: `1.1`
  - 이번 승인 과정에서는 speed만 바꿨고, `tau`, `sdp_ratio`, `noise_scale`, `noise_scale_w`는 건드리지 않았다.
  - canonical selection manifest: `tts/experiments/custom_training/openvoice_active_selection_20260319.json`
- OpenVoice synthetic dataset 생성 정책은 아래처럼 둔다.
  - 기본값: `TTS only`
  - STT 역전사 필터: 명시적으로 요청할 때만 사용
  - 이유: `Whisper large-v3` 필터는 품질 보조에는 유효하지만 처리량을 크게 낮춘다.
- 현재 active full generation run은 아래다.
  - active run root: `../results/tts_custom/synthetic_dataset/full_v1_tts_only/openvoice_ko_female_announcer_speed_1p1/`
  - progress file: `progress.local.md`
  - mode: `OpenVoice TTS only (no STT filtering)`
- 이전 filtered partial run은 아래에 archive/reference로 남겨둔다.
  - `../results/tts_custom/synthetic_dataset/full_v1/openvoice_ko_female_announcer_speed_1p1/`
  - `stt_spotcheck_100`과 `problem_audio_5`도 이 경로를 기준으로 본다.
- 한국어 custom training은 아래 순서를 따른다.
  - `1~3시간 pilot synthetic dataset`
  - pilot 학습
  - 검증 통과 시 full 학습으로 확대
- `runtime winner`와 `training winner`는 같다고 가정하지 않는다.
- A100 `80GB x 2`는 generation, STT filtering, training 같은 독립 작업을 병렬로 나눠 적극 사용한다.
- 현재 기준에서는 리소스 때문에 transfer learning을 고집하지 않는다.
  - 필요하면 scratch와 transfer를 모두 pilot에서 비교하고, 더 나은 쪽으로 간다.
- `OpenVoice V2`는 reference 재선정 뒤 canonical benchmark에 다시 반영했다.
  - active 한국어 reference: `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
  - source: `stt/datasets/korean_eval_50/021.wav`
  - active 영어 reference: `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
  - source: `OpenAI Audio Speech API gpt-4o-mini-tts / marin`
- 현재 자동 평가 기준 요약은 아래처럼 본다.
  - 한국어 제품성:
    - `OpenAI API TTS (KO)` CER `0.0496`, exact `0.50`, RTF `0.2799`
    - `Edge TTS (KO)` CER `0.0803`, exact `0.39`, RTF `0.1811`
    - `MeloTTS (KO)` CER `0.0999`, exact `0.42`, RTF `0.1462`
    - `OpenVoice V2 (KO)` CER `0.1130`, exact `0.33`, RTF `0.1970`
  - 영어 엔진:
    - `OpenAI API TTS (EN)` CER `0.0483`, exact `0.67`, RTF `0.2696`
    - `Kokoro (EN)` CER `0.0541`, exact `0.68`, RTF `0.0483`
    - `Piper (EN)` CER `0.0590`, exact `0.66`, RTF `0.0645`
    - `Edge TTS (EN)` CER `0.0622`, exact `0.64`, RTF `0.4051`
    - `MeloTTS (EN)` CER `0.0647`, exact `0.60`, RTF `0.0712`
    - `OpenVoice V2 (EN)` CER `0.0776`, exact `0.53`, RTF `0.1516`
- 숫자/금액/영문 혼합 prompt는 거의 모든 엔진에서 공통적으로 STT 역전사 오차가 크게 튀었다.
  - 예: `EN017`, `EN050`, `KO055`, `KO076`
  - 따라서 `large-v3` 역전사 평가는 주로 발음 명료도와 문장 보존성 지표로 해석하고, 최종 품질 판단은 listening score를 함께 본다.
- STT 역전사 scorer는 이번 benchmark 기본 경로에서 API를 제외하고, A100 로컬 `STTTranscriber(model="whisper", model_name="large-v3")` 경로를 우선 사용한다.
- benchmark 실행 코드는 아래를 기준으로 본다.
  - `tts/tools/tts_benchmark.py`
  - `tts/tools/tts_benchmark_worker.py`
- 현재 smoke 결과는 아래 경로에 있다.
  - `../results/tts/benchmark_smoke_v1/`
  - `../results/tts/benchmark_smoke_en_fix/`
- smoke 기준 확인 결과:
  - `melotts_ko`, `melotts_en`, `openvoice_v2_ko`, `openvoice_v2_en`, `piper_en`, `kokoro_en`, `edge_tts_ko`, `edge_tts_en`가 모두 1-prompt 자동 역전사까지 통과했다.
  - `melotts_en`, `openvoice_v2_en`은 `nltk averaged_perceptron_tagger_eng` 리소스 보강 후 통과했다.
- benchmark용 OpenVoice V2 reference 자산은 아래를 기준으로 둔다.
  - `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
  - `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
- 현재 repo 안의 TTS 관련 데이터는 wake word positive 생성용 합성 음성 중심이라, custom speaker training의 바로 쓸 수 있는 기반 데이터셋으로 보지는 않는다.
- TTS 평가 기준은 `tts/evaluation/README.md`, 대표 문장셋은 `tts/evaluation/prompts/ko_demo_sentences_v1.txt`를 기준으로 시작한다.
- 데모 구현 계획 문서는 `stt/docs/보고서/260318_1055_STT_데모_계획.md`에 둔다.
- 통합 GUI 데모의 화면 설명과 스크린샷은 `stt/README.md`를 기준으로 본다.

## 다음 작업

1. Orin Nano에서 살아난 4모델 경로를 기준으로 ONNX, TensorRT, hybrid runtime 같은 경량화 가능성을 모델별로 나눈다.
2. `Piper cpu`, `Kokoro cuda`를 Jetson 상위 voice pipeline local 후보로 먼저 유지한다.
3. `MeloTTS`, `OpenVoice V2`는 Nano에서 기능 성공 경로를 기준으로 더 가벼운 runtime 변환 가능성을 검토한다.
4. 현재 partial listening score를 기준으로 우선순위를 유지하고, 추가 수기 평가는 필요할 때만 다시 연다.
5. 한국어 text-only corpus를 정리하고 pilot dataset 구조를 고정한다.
6. `OpenVoice V2` voice audition에서 최종 reference 1개를 승인한다.
7. active `tts_only` full generation 경과를 보면서 text corpus를 더 확장해 `15~30시간`급 full_v2 후보를 준비한다.
8. `Piper` preprocessing -> pilot 학습 -> export smoke를 연결한다.
9. `Piper` pilot 학습 뒤에만 full training 확대 여부를 판단한다.
10. `Kokoro`는 runtime winner 재검증을 유지하고, training은 후순위 research로 남긴다.
11. A100 benchmark와 Jetson runtime 코드가 서로 깨지지 않도록 공통 SDK 진입점 기준으로 구조를 유지한다.
12. 실제 현장 오디오 기준으로 wake word threshold와 input gain 기본값을 확정한다.
13. wake word 뒤에 VAD를 연결하고 speech start / end 기준을 고정한다.
14. `WhisperTRT small nano safe`를 기준으로 wake word + VAD + STT 통합 GUI 동작을 실제 마이크 조건에서 점검한다.

## 참조 문서

- [project_overview.md](project_overview.md)
- [jetson_transition_plan.md](jetson_transition_plan.md)
- [decisions.md](decisions.md)
- [logbook.md](logbook.md)
