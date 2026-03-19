# TTS Benchmark Full V1

> 마지막 업데이트: 2026-03-19
> canonical result root: `../results/tts/benchmark_full_v1_20260318/`

## 목적

- A100 기준으로 로컬 후보 4개와 reference backend 2개를 같은 prompt와 같은 STT scorer로 비교한다.
- 한국어 제품 후보, 영어 엔진 후보, 언어 독립 엔지니어링 관점을 분리해 본다.
- automatic metric과 partial human listening score를 함께 정리해 Jetson 이식 우선순위를 정할 수 있게 한다.

## 평가 고정 조건

- prompt:
  - `tts/evaluation/prompts/tts_benchmark_prompts_v1.tsv`
  - 한국어 100문장 + 영어 100문장
- listening subset:
  - `tts/evaluation/prompts/tts_listening_subset_v1.tsv`
- STT scorer:
  - A100 로컬 `STTTranscriber(model="whisper", model_name="large-v3")`
- canonical 산출물:
  - summary: `../results/tts/benchmark_full_v1_20260318/per_entry_summary.tsv`
  - detail: `../results/tts/benchmark_full_v1_20260318/per_prompt.tsv`
  - listening template: `../results/tts/benchmark_full_v1_20260318/listening_scores_template.tsv`

## OpenVoice V2 reference 재선정 반영

- 기존 full benchmark 뒤에 OpenVoice만 별도 rerun 했다.
- 이유:
  - 기존 reference 음성이 한국어/영어 모두 부자연스럽고 공정 비교에 불리하다고 판단했다.
- 최종 active reference:
  - 한국어:
    - active: `../results/tts_assets/openvoice_v2/references/ko_benchmark_reference.wav`
    - source: `stt/datasets/korean_eval_50/021.wav`
    - format: `16kHz mono`, `5.716 sec`
  - 영어:
    - active: `../results/tts_assets/openvoice_v2/references/en_benchmark_reference.wav`
    - source: `OpenAI Audio Speech API gpt-4o-mini-tts / marin`
    - format: `24kHz mono`, `9.850 sec`
- rerun 원본 보관:
  - `../results/tts/openvoice_rerun_tmp_20260318/`

## OpenVoice V2 변경 전후

| entry | CER old | CER new | exact old | exact new | RTF old | RTF new | 해석 |
|---|---:|---:|---:|---:|---:|---:|---|
| `openvoice_v2_ko` | 0.1029 | 0.1130 | 0.36 | 0.33 | 0.1337 | 0.1970 | 더 적절한 reference를 썼지만 자동 점수는 오히려 하락 |
| `openvoice_v2_en` | 0.0809 | 0.0776 | 0.53 | 0.53 | 0.1320 | 0.1516 | CER는 소폭 개선, exact는 동일, 속도는 소폭 하락 |

즉 이번 rerun은 "OpenVoice를 더 좋게 보이게 만들기 위한 교체"가 아니라, reference를 더 공정하게 고른 뒤 결과를 다시 측정한 값이다.

## 사람 listening partial 반영

- 이번 listening score는 사용자가 Jetson Nano GUI에서 직접 청취하면서 입력했다.
- 평가 GUI 스크린샷:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/assets/tts_listening_review_gui_20260319.png`
- 사람이 실제로 점수를 입력한 범위만 평균에 반영했다.
  - 한국어: `KO001`, `KO010`, `KO018`
  - 영어: `EN001`
- 따라서 아래 human score는 `부분 평가 평균`이며, coverage가 작은 영어 점수는 순위를 강하게 해석하지 않는다.
- 현재 사용자가 입력한 값은 `overall`, `naturalness`, `voice_appeal`, `pronunciation`이 동일하게 들어가 있어, 모델 비교에는 `overall_10` 평균만 대표값으로 쓴다.
- 요약 TSV:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_score_summary.tsv`

## 한국어 제품성 표

| 모델 | family | CER | exact | RTF | human overall_10 | peak VRAM MB | 메모 |
|---|---|---:|---:|---:|---:|---:|---|
| `OpenAI API TTS (KO)` | reference | 0.0496 | 0.50 | 0.2799 | 8.33 (`n=3`) | 0 | 품질 상한 reference, 네트워크 의존 |
| `Edge TTS (KO)` | reference | 0.0803 | 0.39 | 0.1811 | 8.00 (`n=3`) | 0 | wake word 생성 baseline, 네트워크 의존 |
| `MeloTTS (KO)` | local | 0.0999 | 0.42 | 0.1462 | 9.00 (`n=3`) | 1522 | 부분 listening score까지 보면 현재 한국어 로컬 후보 중 가장 강함 |
| `OpenVoice V2 (KO)` | local | 0.1130 | 0.33 | 0.1970 | 8.00 (`n=3`) | 1886 | cloning 가능성은 있으나 이번 partial listening에서는 `MeloTTS`보다 낮음 |

자동 평가와 partial listening score를 함께 보면, 한국어 로컬 기본 후보는 여전히 `MeloTTS`다.

## 영어 엔진 표

| 모델 | family | CER | exact | RTF | human overall_10 | peak VRAM MB | 메모 |
|---|---|---:|---:|---:|---:|---:|---|
| `OpenAI API TTS (EN)` | reference | 0.0483 | 0.67 | 0.2696 | - | 0 | 이번 partial listening에서는 미평가 |
| `Kokoro (EN)` | local | 0.0541 | 0.68 | 0.0483 | 10.00 (`n=1`) | 1400 | 자동 점수는 가장 좋고, partial listening에서도 긍정적 |
| `Piper (EN)` | local | 0.0590 | 0.66 | 0.0645 | 10.00 (`n=1`) | 950 | 경량성 강점, partial listening도 우수 |
| `Edge TTS (EN)` | reference | 0.0622 | 0.64 | 0.4051 | - | 0 | 이번 partial listening에서는 미평가 |
| `MeloTTS (EN)` | local | 0.0647 | 0.60 | 0.0712 | 10.00 (`n=1`) | 1480 | `EN001` 한 문장 기준으로는 우수했지만 coverage가 작음 |
| `OpenVoice V2 (EN)` | local | 0.0776 | 0.53 | 0.1516 | 9.00 (`n=1`) | 1872 | reference를 바꾼 뒤에도 자동/수기 모두 상위권은 아님 |

영어는 현재 `EN001` 한 문장만 사람이 평가했기 때문에, 수기 점수만으로 우열을 확정하지 않는다. 자동 점수와 경량성까지 함께 보면 여전히 `Kokoro`와 `Piper`가 우선 검토 대상이다.

## 엔지니어링 관점 요약

| 모델 | 오프라인 | 한국어 제품성 | 영어 제품성 | Jetson 관점 1차 메모 |
|---|---|---|---|---|
| `MeloTTS` | 가능 | 높음 | 중간 | 한국어 주력 후보, GPU/메모리 검증 필요 |
| `OpenVoice V2` | 가능 | 현재 보류 | 현재 보류 | 이번 단계 Jetson 제외 대상 |
| `Piper` | 가능 | 현재 무효 | 높음 | 영어 경량 runtime 후보, 한국어는 제외 |
| `Kokoro` | 가능 | 공식 Korean 없음 | 높음 | 영어 경량 runtime 후보, Jetson 검증 가치 높음 |
| `Edge TTS` | 불가 | reference | reference | 네트워크 fallback/demo용 |
| `OpenAI API TTS` | 불가 | reference | reference | 품질 상한 reference, 비용/네트워크 경로 |

## 공통 오류 패턴

- 숫자/금액/영문 혼합 prompt는 거의 모든 엔진에서 공통적으로 STT 역전사 오차가 컸다.
- 대표 예:
  - `KO055`: `On-Device Voice Agent PoC`
  - `KO076`: `WhisperTRT small nano safe`
  - `EN017`: `one million two hundred thirty-four thousand won`
  - `EN050`: `forty-eight thousand five hundred won`
- 따라서 `large-v3` 역전사 평가는 발음 명료도와 문장 보존성 기준으로 해석하고, 최종 제품 판단은 반드시 listening score를 함께 봐야 한다.

## 사람 listening 평가 경로

- listening template:
  - `../results/tts/benchmark_full_v1_20260318/listening_scores_template.tsv`
- partial summary:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/human_score_summary.tsv`
- grouped score sheet:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/ko_grouped_score_sheet.tsv`
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/en_grouped_score_sheet.tsv`
- GUI screenshot:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/assets/tts_listening_review_gui_20260319.png`
- prompt pack:
  - `../results/tts/benchmark_full_v1_20260318/listening_review_20260319/prompt_packs/`
- 대표 listening 폴더:
  - 한국어:
    - `../results/tts/benchmark_full_v1_20260318/listening/ko/melotts_ko/`
    - `../results/tts/benchmark_full_v1_20260318/listening/ko/openvoice_v2_ko/`
    - `../results/tts/benchmark_full_v1_20260318/listening/ko/edge_tts_ko/`
    - `../results/tts/benchmark_full_v1_20260318/listening/ko/openai_api_ko/`
  - 영어:
    - `../results/tts/benchmark_full_v1_20260318/listening/en/melotts_en/`
    - `../results/tts/benchmark_full_v1_20260318/listening/en/openvoice_v2_en/`
    - `../results/tts/benchmark_full_v1_20260318/listening/en/piper_en/`
    - `../results/tts/benchmark_full_v1_20260318/listening/en/kokoro_en/`
    - `../results/tts/benchmark_full_v1_20260318/listening/en/edge_tts_en/`
    - `../results/tts/benchmark_full_v1_20260318/listening/en/openai_api_en/`

## 현재 결론

- 한국어 로컬 기본 후보:
  - `MeloTTS`
- 영어 로컬 우선 검토 후보:
  - `Kokoro`
  - `Piper`
- partial listening score 기준:
  - 한국어는 `MeloTTS`가 가장 높았다 (`9.00 / 10`, `n=3`)
  - 영어는 `Kokoro`, `Piper`, `MeloTTS`가 `EN001` 한 문장에서 모두 `10 / 10`으로 묶였고, coverage가 작아 참고값으로만 본다
- `OpenVoice V2`는 reference 재선정을 반영한 뒤에도 이번 자동 평가 기준에서는 상위권으로 올라오지 못했다.
- 따라서 다음 Jetson 단계는 `OpenVoice V2`를 제외하고 진행하는 것이 맞다.

## 다음 단계

1. 현재 partial listening score를 기준으로 Jetson local 후보 우선순위를 유지한다.
2. `OpenVoice V2`를 제외한 후보의 Jetson 이식 계획을 문서화한다.
3. Jetson에서 `MeloTTS`, `Piper`, `Kokoro`, `Edge TTS`, `OpenAI API TTS`를 공통 SDK 경로로 실제 호출해 본다.
