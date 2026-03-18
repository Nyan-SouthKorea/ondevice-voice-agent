# STT 평가 개요

- 결과 디렉토리: `/home/everybot/workspace/ondevice-voice-agent/repo/stt/eval_results/korean_eval_50`
- 생성 시각: `2026-03-17 17:21:11`
- 원본 산출물: 각 run 디렉토리의 `summary.json`
- 최종 6모델 세트는 `20260317_172300_six_model_final` 기준이다.
- `small_trt_nano_safe`는 혼합 배치 실행 중 allocator assert가 있어, fresh process 단독 재실행 결과를 최종 세트에 합쳤다.
- 자동 선택 규칙:
  - 정확도 우선: `Normalized Exact Match` 내림차순, `Normalized CER` 오름차순, `Mean STT (s)` 오름차순
  - 오류율 우선: `Normalized CER` 오름차순, `Normalized Exact Match` 내림차순, `Mean STT (s)` 오름차순
  - 지연 우선: `Mean STT (s)` 오름차순, `P95 STT (s)` 오름차순, `Mean RTF` 오름차순

## 지표 설명

- `상태 (Status)`: 해당 모델 조합이 완료됐는지, 실패했는지, summary가 없는지 나타낸다.
- `모델 (Label)`: 평가한 모델 이름과 실행 장치 조합이다.
- `샘플 수 (Samples)`: 실제 평가에 사용된 문장 수다.
- `Load (s)`: 모델을 메모리에 올리는 데 걸린 시간이다. warm-up 이전 1회 비용이다.
- `Mean STT (s)`: warm-up을 제외한 문장별 STT 처리 시간 평균이다.
- `P95 STT (s)`: warm-up을 제외한 문장별 STT 처리 시간의 95퍼센타일이다. 느린 구간 체감에 가깝다.
- `Mean RTF`: 평균 실시간비다. `처리 시간 / 오디오 길이`로 계산하며, 1.0 이하면 오디오 길이보다 빠르게 처리한 것이다.
- `Normalized Exact Match`: 정규화 후 기준 문장과 예측 문장이 완전히 같은 비율이다. 공백, 일부 기호 차이를 줄인 뒤 비교한다.
- `Normalized CER`: 정규화 후 문자 오류율이다. 낮을수록 좋다.
- `원본 run (Source)`: 수치를 읽어온 run 디렉토리 이름이다.
- `오류 메모 (Error)`: 실패한 경우 summary에 저장된 마지막 오류 문자열이다.

## 질문 기반 추가 설명

### Normalized Exact Match는 어떻게 정규화하나

- 현재 평가는 `stt/tools/stt_benchmark.py`의 `normalize_text()` 기준을 그대로 사용한다.
- 정규화 순서는 다음과 같다.
  - 문자열 앞뒤 공백 제거
  - 영문 소문자 변환
  - 일반 문장부호와 `“ ” ‘ ’ … ·` 제거
  - 남아 있는 모든 공백 제거
- 즉, 띄어쓰기나 문장부호 차이는 무시하고 핵심 글자열이 완전히 같으면 `Normalized Exact Match = 1`로 본다.

예시:
- 기준: `안녕하세요, 오늘 음성 인식 테스트를 시작하겠습니다.`
- 예측: `안녕하세요 오늘 음성 인식 테스트를 시작하겠습니다`
- 정규화 후 둘 다 `안녕하세요오늘음성인식테스트를시작하겠습니다`가 되므로 일치로 처리된다.

반대로 다음은 불일치다.
- 기준: `오늘 서울 날씨는 맑고 바람이 조금 붑니다.`
- 예측: `오늘 서울 날씨는 맑고 바람이 많이 붑니다`
- 정규화 후에도 `조금`과 `많이` 차이가 남기 때문에 불일치로 처리된다.

### CER은 무엇인가

- `CER`은 `Character Error Rate`로, 문자 단위 오류율이다.
- 계산식은 `편집거리 / 기준 문자열 길이`다.
- 편집거리는 삽입, 삭제, 치환 횟수를 합친 Levenshtein distance를 사용한다.
- 값이 낮을수록 좋고, `0.0`이면 완전 일치다.

예시:
- 기준: `하이포포`
- 예측: `하이보보`
- `포 -> 보` 치환이 두 번 필요하므로 편집거리는 2다.
- 기준 문자열 길이가 4면 `CER = 2 / 4 = 0.5`다.

- 이 문서의 `Normalized CER`은 위에서 설명한 정규화 이후에 계산한 CER이다.
- 그래서 문장부호나 띄어쓰기 차이만 있는 경우에는 CER이 낮아지거나 0이 될 수 있다.

## 규칙 기반 자동 선택

| 항목 | 모델 | 원본 run | Normalized Exact Match | Normalized CER | Mean STT (s) | Mean RTF |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 정확도 우선 | gpt-4o-mini-transcribe (api) | `20260317_172300_six_model_final` | 0.6800 | 0.0693 | 1.0512 | 0.2160 |
| 오류율 우선 | gpt-4o-mini-transcribe (api) | `20260317_172300_six_model_final` | 0.6800 | 0.0693 | 1.0512 | 0.2160 |
| 지연 우선 | whisper base fp16e_fp16w (trt, legacy) | `20260317_172300_six_model_final` | 0.1600 | 0.1759 | 0.1957 | 0.0402 |

## 전체 평가 표

| 상태 | 모델 | 샘플 수 | Load (s) | Mean STT (s) | P95 STT (s) | Mean RTF | Normalized Exact Match | Normalized CER | 원본 run | 오류 메모 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 완료 | whisper tiny fp16 (cuda) | 50 | 4.2783 | 0.6488 | 0.8045 | 0.1333 | 0.0400 | 0.4753 | `20260317_172300_six_model_final` |  |
| 완료 | whisper base fp16 (cuda) | 50 | 1.5342 | 0.7017 | 0.9329 | 0.1442 | 0.1800 | 0.1653 | `20260317_172300_six_model_final` |  |
| 완료 | whisper base fp16e_fp16w (trt, legacy) | 50 | 3.4855 | 0.1957 | 0.2543 | 0.0402 | 0.1600 | 0.1759 | `20260317_172300_six_model_final` |  |
| 완료 | whisper small fp16e_fp32w (trt, nano safe) | 50 | 31.6285 | 0.3823 | 0.5129 | 0.0786 | 0.4600 | 0.0886 | `20260317_172300_six_model_final` |  |
| 완료 | whisper small fp16e_fp32w (trt, agx cross-device) | 50 | 31.5101 | 0.7826 | 1.0321 | 0.1608 | 0.4600 | 0.0873 | `20260317_172300_six_model_final` |  |
| 완료 | gpt-4o-mini-transcribe (api) | 50 | 2.3201 | 1.0512 | 1.8980 | 0.2160 | 0.6800 | 0.0693 | `20260317_172300_six_model_final` |  |
