# 문서 허브

이 디렉토리는 역할이 겹치지 않는 문서 구조를 유지하기 위한 허브다. 현재 상태는 `status`, 안정된 원칙은 `개발방침`, 최근 기록은 `logbook`, 오래된 상세 이력은 `archive`로 분리한다.

## 새 에이전트 시작 절차

새 세션에서 에이전트에게는 기본적으로 아래 한 줄만 지시하면 된다.

`먼저 docs/README.md만 읽고, 여기에 적힌 시작 절차에 따라 필요한 문서와 관련 코드만 확인해.`

그 다음 절차는 아래로 고정한다.

1. `docs/status.md`를 먼저 읽고 현재 상태를 파악한다.
2. 이번 작업과 직접 관련된 모듈 `README.md`만 읽는다.
3. `docs/개발방침.md`를 읽고 그 규칙에 맞게 행동한다.
4. 필요할 때만 `docs/decisions.md`, `docs/research/`, `docs/envs/`, `docs/reports/`를 추가로 읽는다.
5. 과거 맥락이 꼭 필요할 때만 `docs/logbook.md`와 `docs/archive/`를 읽는다.
6. 코드는 작업과 관련된 디렉토리만 읽고, 레포 전체를 처음부터 끝까지 훑지 않는다.

## 기본적으로 생략해도 되는 것

- `docs/archive/`
- `stt/eval_results/` 같은 자동 생성 결과물
- `secrets/` 아래 로컬 문서
- 현재 작업과 무관한 모듈의 코드와 README

## Single Source of Truth

| 문서 | 역할 | 여기에 써야 하는 것 | 여기서 빼야 하는 것 |
|---|---|---|---|
| `README.md` | 레포 진입점 | 프로젝트 소개, 모듈 링크, 문서 진입점 | 상세 상태, 긴 이력 |
| `docs/status.md` | 현재 상태 기준 | 지금 완료된 것, 고정 기준, 다음 작업 | 오래된 실험 로그 |
| `docs/개발방침.md` | 안정된 원칙 | 개발/문서 운영 규칙 | 일시적인 진행 상황 |
| `docs/decisions.md` | 핵심 결정 | 현재도 유효한 의사결정 | 세세한 작업 메모 |
| `docs/logbook.md` | 최근 로그 | 최근 세션의 작업 흐름 | 오래된 전체 히스토리 |
| `docs/archive/` | 보관 문서 | 이전 상세 문서, 오래된 로그 | 현재 기준 문서 역할 |
| `docs/research/` | 조사 문서 | 후보 비교, 선택 배경 | 최신 진행 상태 |
| `docs/envs/` | 환경 문서 | 설치, 검증, 재현 절차 | 프로젝트 현황 요약 |
| `docs/reports/` | 승격된 결과 요약 | 사람이 읽는 결과 보고서 | 자동 생성 원본 산출물 |

## 추천 읽는 순서

1. `docs/status.md`
2. 관련 모듈 `README.md`
3. `docs/개발방침.md`
4. `docs/decisions.md`
5. 필요 시 `docs/research/`, `docs/envs/`, `docs/reports/`
6. 과거 맥락이 더 필요할 때만 `docs/logbook.md`와 `docs/archive/`

## 디렉토리 메모

```text
docs/
├── README.md
├── status.md
├── 개발방침.md
├── decisions.md
├── logbook.md
├── project_overview.md
├── jetson_transition_plan.md
├── archive/
├── envs/
├── research/
├── reports/
└── assets/
```

- `project_overview.md`는 빠른 배경 설명용 얇은 문서다.
- `jetson_transition_plan.md`는 Jetson 연동 체크리스트만 유지한다.
- `stt/eval_results/**/*.md` 같은 자동 생성 결과물은 공식 문서가 아니라 실행 산출물로 본다.

## 운영 규칙

- 같은 상태 설명을 여러 상위 요약 문서에 반복하지 않는다.
- 현재 상태를 바꿨다면 우선 `docs/status.md`를 갱신한다.
- 원칙이 바뀌었을 때만 `docs/개발방침.md`를 갱신한다.
- 오래된 상세 기록은 지우지 말고 `docs/archive/`로 내린다.
- 자동 생성 결과물은 모듈 출력 디렉토리에 두고, 사람이 계속 읽어야 할 요약만 `docs/reports/`로 승격한다.
- 재현에 필요 없는 시행착오 산출물은 `md` 요약으로 승격한 뒤 삭제한다.
- 대용량 실행 파일이나 체크포인트를 남기지 않기로 결정했다면, 문서에는 `보관 여부`, `재현 경로`, `남겨둔 이유`를 함께 적는다.

## 문서 수정 체크리스트

1. 이번 변경의 최종 기준 문서가 `status`, `개발방침`, `README`, `reports` 중 어디인지 먼저 정한다.
2. 같은 내용을 두 곳 이상에 쓰지 않고, 다른 문서에는 링크만 남긴다.
3. 실행 결과를 숫자로 기록할 때는 code-generated 산출물이나 계산식 기반 값만 사용한다.
4. 시행착오 산출물을 지웠다면 `logbook`에 한 줄로 정리하고, 필요한 재현 절차만 `envs`나 모듈 `README`에 남긴다.
