# Agent Watchdog Plan

> 목적: 에이전트 모드에서 장시간 생성/학습/후처리 파이프라인이 세션과 분리되어도 끊기지 않게 만드는 범용 watchdog 기준을 정리한다.

## 목표

- 장시간 작업이 세션 종료, 컨텍스트 압축, 터미널 종료로 끊기지 않게 한다.
- 상태 파일만 남고 실제 프로세스는 죽어 있는 상황을 줄인다.
- watchdog 자신도 smoke test를 통과한 뒤에만 실전 파이프라인에 사용한다.

## 범위

- 생성
- 학습
- export / 변환
- 후처리
- smoke / benchmark
- 여러 단계를 자동 연결하는 detached pipeline

## 핵심 요구사항

### 1. 규칙 기반 core

- 프로세스 생존 여부는 `pid`와 `ps`로 판정한다.
- 진행 상황은 `progress`, `heartbeat`, `mtime`으로 판정한다.
- stale 여부는 정해진 `stale_sec` 기준으로 판정한다.
- 다음 단계 실행 여부는 명시적 규칙으로만 정한다.

### 2. 필수 산출물

- `job.spec.json`
- `job.pid`
- `status.local.md`
- `events.log`
- `stdout.log`
- `stderr.log`

### 3. smoke-first

- 실전 pipeline 전에 watchdog 자체를 먼저 시험한다.
- 최소 smoke 시나리오:
  1. 정상 종료 sample
  2. 실패 종료 sample
  3. heartbeat 멈춤 sample
- watchdog가 각 경우에 대해 아래를 남기는지 확인한다.
  - 상태 전이
  - 종료 코드
  - stale 판정
  - restart 또는 next-step 실행 여부

### 4. 단계별 운영

- generation이 끝났다고 해서 바로 다음 단계에 들어가지 않는다.
- watchdog가 `실제 본체 종료`와 `산출물 완결성`을 확인한 뒤 다음 단계로 넘긴다.
- monitor만 남고 본체가 죽은 경우는 `실패`로 기록한다.

## 권장 구조

### job spec 예시

- `job_name`
- `mode`: `observe` 또는 `act`
- `target_cmd`
- `expected_outputs`
- `heartbeat_files`
- `stale_sec`
- `on_success_cmd`
- `on_failure_cmd`
- `on_stale_cmd`

### 상태 파일 예시

- 현재 단계
- 마지막 heartbeat 시간
- target pid
- 마지막 이벤트
- 다음 단계 대기 여부

## 현재 프로젝트에 바로 적용할 기준

- `10분 이상` 또는 `다단계 자동 연결` 작업은 watchdog 대상
- watchdog smoke를 먼저 통과시키지 못하면 실전 실행 금지
- 장시간 작업은 `세션에 붙은 단순 shell loop`보다 `명시적 pid/status/events`를 남기는 detached 실행을 기본값으로 둔다

## 다음 구현 계획

1. `tools/agent_watchdog.py` 구현
2. sample job 3종 작성
3. smoke harness 작성
4. 실제 TTS 장시간 pipeline에 적용
