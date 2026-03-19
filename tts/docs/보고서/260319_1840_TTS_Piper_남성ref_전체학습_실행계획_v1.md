# TTS Piper 남성ref 전체학습 실행계획 v1

> 마지막 업데이트: 2026-03-20 08:22 KST
> 목적: `ko_male_lee_sunkyun` reference와 `v1~v3 전체 텍스트`를 사용해 OpenVoice synthetic dataset을 새로 만들고, 그 결과로 `Piper` 한국어 공식 fine-tune run을 다시 수행한다.

## 한 줄 결론

- 이번 run은 기존 여성 ref 성공 경로를 그대로 복제하되, 아래 두 가지만 바꾼다.
  1. reference를 `ko_female_announcer -> ko_male_lee_sunkyun`으로 변경
  2. 입력 텍스트를 `v1~v3 union` 전체로 사용
- 목표는 세 가지다.
  1. 남성 ref synthetic data로도 `Piper 공식 fine-tune`이 안정적으로 수렴하는지 확인
  2. 각 단계의 실행시간을 모두 기록
  3. 최종 ONNX를 Jetson Nano에서 실제로 측정하고 문서화

## 현재 상태 점검

- `OpenVoice` 남성 ref 전체 generation은 완료됐다.
  - `24,689 wav`
  - `30.300시간`
- 생성 완료 뒤 자동으로 `inventory -> official fine-tune`으로 넘어가야 했지만, 실제로는 그렇지 않았다.
  - `monitor_generation_progress.py`만 남아 있었고
  - `wait_generation_and_continue.pid`, `watch_generation_and_continue.pid`가 가리키는 실제 프로세스는 모두 죽어 있었다.
- 따라서 이 문서의 다음 액션은 `generation 완료 가정` 아래에서 `inventory`부터 다시 시작하는 것이다.

## 기준 문서

- `docs/README.md`
- `docs/개발방침.md`
- `tts/README.md`
- `tts/docs/환경/260319_1925_Piper_한국어_전체학습_재현가이드.md`
- `tts/docs/보고서/260319_1736_TTS_Piper_공식_파인튜닝_자동평가_결과.md`

## 공식 기준 링크

- Piper training guide:
  - https://tderflinger.github.io/piper-docs/guides/training/
- Piper checkpoints / voices:
  - https://huggingface.co/rhasspy/piper-voices
- base checkpoint source used in this run:
  - https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/en/en_US/lessac/medium/epoch=2164-step=1355540.ckpt

## 이번 run의 입력 기준

### reference

- reference id:
  - `ko_male_lee_sunkyun`
- prepared wav:
  - `/data2/iena/260318_ondevice-voice-agent/results/tts_custom/references/ko_male_lee_sunkyun/ko_male_lee_sunkyun.wav`
- source archive:
  - `/data2/iena/260318_ondevice-voice-agent/ref 음성-남성 이션균 배우.mp4`
- speed:
  - `1.1`

### text corpus

- canonical union:
  - `/data2/iena/260318_ondevice-voice-agent/results/tts_custom/corpora/260319_1510_tts_텍스트코퍼스_통합_v1/master_union_unique_by_text.tsv`
- row count:
  - `24,689문장`
- 의미:
  - `v1 + v2 + v3`의 exact dedupe union

### 예상 총 오디오 길이

- 기존 성공 run 평균치 기준 추정:
  - `약 28.819시간`
- 계산 근거:
  - 이전 성공 run `21.568시간 / 18,477문장`

## GPU 배치

- 현재 `GPU1`은 외부 `ollama`가 점유 중이므로 이번 시작 시점의 안전한 기본 배치는 아래다.
  - `GPU0`: OpenVoice male synthetic generation
  - generation 완료 후 `GPU0`: Piper preprocess + official fine-tune + postprocess
- 즉 이번 run은 일단 `GPU0 single pipeline`으로 시작한다.
- 이후 `GPU1`이 비면 다음 scale-up generation에서 generation/training 분리로 되돌린다.

## run root

### synthetic

- root:
  - `/data2/iena/260318_ondevice-voice-agent/results/tts_custom/synthetic_dataset/full_male_v1_tts_only/openvoice_ko_male_lee_sunkyun_speed_1p1/`

### training

- root:
  - `/data2/iena/260318_ondevice-voice-agent/results/tts_custom/training/260319_1840_Piper_한국어_공식_파인튜닝_남성ref_v1/`

## 단계

1. 남성 ref generation 완료 상태를 기준으로 inventory 생성
2. `deduped_rows.tsv` 기준 dataset snapshot 생성
3. Piper preprocess
4. official lessac medium checkpoint 기준 fine-tune
5. checkpoint sampler
6. ONNX export + benchmark
7. A100 smoke
8. Jetson Nano smoke
9. 결과 보고서 정리

## 시간 기록 원칙

- 각 단계는 가능한 한 `/usr/bin/time -v` 로그를 별도로 남긴다.
- 최소 기록 대상:
  - synthetic generation wall time
  - inventory 생성 wall time
  - dataset snapshot 생성 wall time
  - preprocess wall time
  - fine-tune wall time
  - postprocess wall time
  - Jetson Nano smoke wall time
- 결과 보고서에는 위 값을 표로 요약한다.

## 성공 기준

- synthetic generation이 `24,689문장` 기준으로 끝까지 닫힌다.
- Piper official fine-tune이 checkpoint와 ONNX export까지 정상 완료된다.
- 자동 benchmark가 나온다.
- Jetson Nano에서 `TTSSynthesizer(model="piper")` 경로로 실제 합성이 된다.

## 중단 조건

- OpenVoice generation이 reference 기준으로 명백히 붕괴하고, 랜덤 샘플 청취에서 전반적으로 unusable하다.
- official fine-tune이 반복적으로 checkpoint corruption 또는 loader failure를 낸다.
- Jetson Nano runtime에서 model load조차 닫히지 않는다.

## 현재 판단

- reference만 남성으로 바뀌고 레시피는 여성 성공 run과 동일하므로, 실패하더라도 원인 분리는 비교적 명확하다.
- 가장 가능성이 높은 비교 포인트는 아래다.
  - synthetic data 품질 차이
  - 남성 ref에서의 발음 안정성 차이
  - Jetson Nano runtime latency 차이
- 현재 가장 먼저 해결해야 할 문제는 모델 품질이 아니라 `자동 이어짐이 실제로 동작하게 만드는 것`이다.
- 즉 이 run의 다음 단계는 `generation 성공 여부 확인`이 아니라 `generation 이후 chain을 detached 실행으로 다시 복구`하는 것이다.
