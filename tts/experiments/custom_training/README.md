# TTS Custom Training Experiments

이 디렉토리는 영어 runtime winner 검증과 한국어 custom TTS 학습 파이프라인을 이어서 실험하는 자리다.

현재 active 방향:

1. `Piper`, `Kokoro`를 Jetson runtime 후보로 다시 검증
2. `OpenVoice V2`는 최종 runtime이 아니라 voice audition + synthetic dataset 생성기로 사용
3. 한국어 text-only corpus를 준비하고, synthetic dataset `1~3시간` pilot부터 시작
4. pilot 검증이 통과한 뒤에만 full training으로 확장
5. 현재 training 우선순위는 `Piper` 먼저, `Kokoro`는 runtime 우선 / training 후순위다.

현재 준비 완료 상태:

- 한국어 text-only corpus: `../results/tts_custom/corpora/ko_text_corpus_v1/`
- OpenVoice audition prompt: `tts/evaluation/prompts/openvoice_audition_prompts_ko_v2.tsv`
- OpenVoice reference 후보:
  - `../results/tts_custom/references/ko_male_lee_sunkyun/ko_male_lee_sunkyun.wav`
  - `../results/tts_custom/references/ko_female_announcer/ko_female_announcer.wav`
- OpenVoice 10문장 샘플:
  - `../results/tts_custom/audition/openvoice_ref_audition_20260319_v2/ko_male_lee_sunkyun/`
  - `../results/tts_custom/audition/openvoice_ref_audition_20260319_v2/ko_female_announcer/`
- 현재 승인된 active selection:
  - `reference_id`: `ko_female_announcer`
  - `reference_audio_path`: `../results/tts_custom/references/ko_female_announcer/ko_female_announcer.wav`
  - `approved speed`: `1.1`
  - manifest: `tts/experiments/custom_training/openvoice_active_selection_20260319.json`
- pilot synthetic dataset 예상 시간:
  - 현재 부분 생성본 실측 기준 `1.5시간 pilot audio -> 약 24분`, 안전하게는 `25~30분`

관련 기준 문서:

- `../../docs/보고서/260319_1052_TTS_커스텀_학습_계획_v1.md`
- `../../docs/보고서/260319_1100_TTS_학습_가능성_점검.md`
- `docs/status.md`

주의:

- 실제 생성 음성, 대규모 데이터셋, 체크포인트는 리포에 넣지 않는다.
- 리포 안에는 계획, 스크립트, 포맷, 얇은 실험 메모만 둔다.
