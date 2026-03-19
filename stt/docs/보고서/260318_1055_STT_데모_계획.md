# STT / 통합 데모 계획

## 목적

- STT 단독 GUI 데모를 먼저 만들어 `녹음 -> STT -> 결과 표시` 흐름과 모델 전환 UX를 검증한다.
- 이후 wake word, VAD, STT를 합친 통합 GUI 데모로 확장한다.
- 두 단계 모두 Jetson 실기 기준으로 동작하며, API 사용은 과금 보호 장치를 포함한다.

## 1단계: STT 전용 GUI 데모

### 목표

- 사용자가 `녹음 시작 / 녹음 정지` 버튼으로 직접 발화를 녹음한다.
- 정지 후 선택한 STT 모델로 전사한다.
- 결과 텍스트를 스크롤 가능한 히스토리로 남긴다.
- 모델 전환은 GUI를 멈추지 않고 백그라운드 로딩으로 처리한다.

### 지원 모델

- `whisper tiny fp16 (cuda)`
- `whisper base fp16 (cuda)`
- `whisper base fp16e_fp16w (trt, legacy)`
- `whisper small fp16e_fp32w (trt, nano safe)`
- `gpt-4o-mini-transcribe`

### 핵심 요구사항

- 모델 전환 시 메인 GUI가 멈추지 않는다.
- STT 실행 중 중복 녹음/중복 전사를 막는다.
- API 모델은 명시적으로 선택해야 하며, 세션 API 호출 횟수를 표시한다.
- 비교 모드는 최대 2개 모델만 선택해 순차 실행한다.
- 비교 대상이 아닌 모델은 메모리에 상주시켜 두지 않는다.
- 너무 짧은 녹음은 전사하지 않는다.
- 마지막 모델 로드 상태, 녹음 상태, STT 실행 상태를 화면에 표시한다.

### 1차 구현 범위

1. 모델 선택 드롭다운
2. 백그라운드 모델 로딩
3. `녹음 시작 / 녹음 정지 / 기록 지우기`
4. 실시간 입력 레벨 표시
5. 전사 결과 스크롤 히스토리
6. API 경고 문구와 세션 호출 횟수 표시
7. 선택한 최대 2개 모델 비교

## 2단계: wake word + VAD + STT 통합 GUI 데모

### 목표

- `하이 포포` 호출 후 wake word 감지를 시각화한다.
- 감지 후 VAD가 listening 상태로 들어가 실제 발화 구간만 자른다.
- 발화 종료 후 STT를 실행하고, 결과를 히스토리에 남긴다.

### 상태 흐름

- `IDLE`
- `WAKE_DETECTED`
- `LISTENING`
- `STT_RUNNING`
- `SHOW_RESULT`

### VAD 기본 방향

- backend는 `silero` 고정
- wake word 직후 짧은 grace 구간을 둔다
- speech start는 짧은 연속 speech 기준으로 확정한다
- speech end는 상용 서비스 수준의 silence 누적 기준으로 확정한다
- 발화가 너무 짧거나 speech가 없는 경우는 STT를 생략한다

### 2차 구현 범위

1. wake word 램프 및 score 표시
2. VAD listening 상태 표시
3. speech start / end 기반 utterance cut
4. STT 모델 선택 재사용
5. 결과 히스토리 재사용
6. API 보호 장치 재사용

## 현재 구현 순서

1. STT 전용 GUI 데모 구현
2. 직접 시연 후 UI/파라미터 보완
3. 통합 GUI 데모 구현
4. wake word / VAD / STT 연결 검증
