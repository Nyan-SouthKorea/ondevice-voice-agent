# STT 평가 개요

- 결과 디렉토리: `/home/everybot/workspace/ondevice-voice-agent/project/repo/stt/eval_results/korean_eval_50`
- 생성 시각: `2026-03-17 08:59:20`
- 원본 산출물: 각 run 디렉토리의 `summary.json`
- 자동 선택 규칙:
  - 정확도 우선: `Normalized Exact Match` 내림차순, `Normalized CER` 오름차순, `Mean STT (s)` 오름차순
  - 오류율 우선: `Normalized CER` 오름차순, `Normalized Exact Match` 내림차순, `Mean STT (s)` 오름차순
  - 지연 우선: `Mean STT (s)` 오름차순, `P95 STT (s)` 오름차순, `Mean RTF` 오름차순

## 지표 설명

- `상태 (Status)`: 해당 모델 조합에 대해 summary 산출물이 존재하는지 나타낸다.
- `모델 (Label)`: 평가한 모델 이름과 실행 장치 조합이다.
- `샘플 수 (Samples)`: 실제 평가에 사용된 문장 수다.
- `Load (s)`: 모델을 메모리에 올리는 데 걸린 시간이다. warm-up 이전 1회 비용이다.
- `Mean STT (s)`: warm-up을 제외한 문장별 STT 처리 시간 평균이다.
- `P95 STT (s)`: warm-up을 제외한 문장별 STT 처리 시간의 95퍼센타일이다. 느린 구간 체감에 가깝다.
- `Mean RTF`: 평균 실시간비다. `처리 시간 / 오디오 길이`로 계산하며, 1.0 이하면 오디오 길이보다 빠르게 처리한 것이다.
- `Normalized Exact Match`: 정규화 후 기준 문장과 예측 문장이 완전히 같은 비율이다. 공백, 일부 기호 차이를 줄인 뒤 비교한다.
- `Normalized CER`: 정규화 후 문자 오류율이다. 낮을수록 좋다.
- `원본 run (Source)`: 수치를 읽어온 run 디렉토리 이름이다.

## 규칙 기반 자동 선택

| 항목 | 모델 | 원본 run | Normalized Exact Match | Normalized CER | Mean STT (s) | Mean RTF |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 정확도 우선 | gpt-4o-mini-transcribe (api) | `20260316_180115` | 0.7000 | 0.0669 | 0.8874 | 0.1824 |
| 오류율 우선 | gpt-4o-mini-transcribe (api) | `20260316_180115` | 0.7000 | 0.0669 | 0.8874 | 0.1824 |
| 지연 우선 | tiny (cuda) | `20260316_180025` | 0.0400 | 0.4753 | 0.6355 | 0.1306 |

## 전체 평가 표

| 상태 | 모델 | 샘플 수 | Load (s) | Mean STT (s) | P95 STT (s) | Mean RTF | Normalized Exact Match | Normalized CER | 원본 run |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 완료 | tiny (cuda) | 50 | 6.2438 | 0.6355 | 0.8203 | 0.1306 | 0.0400 | 0.4753 | `20260316_180025` |
| 완료 | base (cuda) | 50 | 5.2179 | 0.7428 | 0.9637 | 0.1526 | 0.1800 | 0.1653 | `20260316_172552` |
| summary 없음 | small (cuda) | - | - | - | - | - | - | - | `-` |
| 완료 | tiny (cpu) | 50 | 5.3554 | 4.6160 | 5.7325 | 0.9487 | 0.0400 | 0.4740 | `20260316_172715` |
| 완료 | base (cpu) | 50 | 1.3013 | 9.3706 | 11.6535 | 1.9258 | 0.1800 | 0.1661 | `20260316_172715` |
| 완료 | small (cpu) | 50 | 7.7633 | 24.6712 | 31.1793 | 5.0702 | 0.4200 | 0.0901 | `20260316_172715` |
| 완료 | gpt-4o-mini-transcribe (api) | 50 | 1.4875 | 0.8874 | 1.6442 | 0.1824 | 0.7000 | 0.0669 | `20260316_180115` |
