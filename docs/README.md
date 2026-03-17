# Robot Voice Commander - 개발 문서 허브

## 문서 운영 원칙

- `docs/project_overview.md`: 프로젝트 목적, 범위, 구현 상태, 학습 결과를 한 번에 보는 통합 문서
- `docs/jetson_transition_plan.md`: Jetson 단계에서 wake word 실기 튜닝과 wake word+VAD 연동으로 넘어가기 위한 계획
- `docs/개발방침.md`: 현재 프로젝트의 최종 의사결정과 공통 원칙
- `docs/research/*.md`: 요소기술별 조사 결과와 선택 근거
- `docs/research/openwakeword_reference.md`: 삭제한 upstream clone 대신, openWakeWord 원본 출처와 현재 이관 범위 기록
- `docs/research/stt.md`: Jetson 기준 온디바이스 STT v1 선택 근거와 다음 검토 후보
- `docs/research/tts.md`: Jetson 기준 TTS v1 방향과 API/온디바이스 후보 선택 근거
- `stt/README.md`: STT recorder, benchmark, 직접 실행 명령, API 사용 로그 위치
- `docs/envs/wake_word_env.md`: Linux 서버(A100) 학습 환경
- `docs/envs/jetson_wake_word_env.md`: Jetson runtime venv, wake word/VAD demo 기준 ONNX Runtime CUDA 검증 절차
- `docs/envs/wake_word_train_smoke_env.md`: Jetson 학습 smoke venv, torch/librosa/feature extraction/train/export 검증 절차
- `docs/status.md`: 현재 시점의 최신 상태
- `docs/decisions.md`: 중요한 의사결정 이력
- `docs/logbook.md`: 시간순 작업 로그
- 1분 이상 걸릴 수 있는 실행 코드는 `docs/개발방침.md`의 장시간 실행 로그 원칙을 따른다

중복을 줄이기 위해 최신 상태, 의사결정 이력, 작업 로그의 역할을 분리한다.

## 디렉토리 구조

```
docs/
├── README.md        ← 이 파일 (전체 개요)
├── project_overview.md ← 프로젝트 전체 설명과 현재 구현 상태 통합
├── jetson_transition_plan.md ← Jetson 이관 및 실기 검증 계획
├── 개발방침.md       ← 개발 원칙, 기술 결정, 현황 통합
├── status.md        ← 최신 상태
├── decisions.md     ← 의사결정 로그
├── logbook.md       ← 작업 로그
├── assets/          ← 문서용 스크린샷과 정적 자산
├── envs/            ← 환경 세팅 기록
└── research/        ← 요소기술별 기술 조사 결과
    ├── wake_word.md
    ├── negative_datasets.md
    ├── tts_korean.md
    ├── stt.md
    ├── llm.md        (예정)
    └── tts.md
```

추가로 학습 산출물은 `wake_word/models/hi_popo/runs/<run_name>/` 단위로 보관하며, baseline과 이후 성능 개선 실험을 분리 추적한다.

현재 Jetson 데모 스크린샷은 `docs/assets/screenshots/jetson_demos/` 아래에 두고, 각 모듈 README에서 직접 보여준다.

## 우선 참고 순서

1. `docs/project_overview.md`
2. `docs/status.md`
3. `docs/개발방침.md`
4. `docs/jetson_transition_plan.md`
5. `docs/envs/jetson_wake_word_env.md`
6. `docs/decisions.md`
7. `docs/logbook.md`
8. `docs/research/wake_word.md`
9. `docs/research/openwakeword_reference.md`
10. `docs/research/negative_datasets.md`
11. `docs/research/tts_korean.md`
12. `docs/research/tts.md`
13. `docs/envs/wake_word_train_smoke_env.md`
14. `docs/envs/wake_word_env.md`

## 개발 방법론: PDCA 사이클

```
       ┌─────────────────────────────────────────┐
       ↓                                         ↑
  [Plan] 계획      →    [Do] 실행     →    [Check] 검토    →    [Act] 개선
목표 설정, 방법 수립    실제 구현/실험       데이터 분석, 평가      개선 후 표준화
```

| 단계 | 내용 | 현재 상태 |
|------|------|-----------|
| **Plan** | wake word 기술 선정, 데이터 전략 수립 | ✅ 완료 |
| **Do** | wake word/VAD 요소기술 구현, ONNX export, Jetson demo 검증 | ✅ 완료 |
| **Check** | wake word 실기 튜닝, hard negative/FAR 점검, wake word+VAD 연동 검토 | 🔄 진행 중 |
| **Act** | 오탐/미탐 결과 기반 데이터 보강, SDK 확장, STT 연결 | ⏳ 대기 |

## 시스템 파이프라인

```
[마이크]
   ↓
[Wake Word]  ← "하이 포포" 감지
   ↓
[VAD]        ← 음성 구간 감지
   ↓
[STT]        ← 음성 → 텍스트
   ↓
[LLM]        ← 명령 해석 및 응답 생성
   ↓
[TTS]        ← 텍스트 → 음성 출력
```

## 하드웨어

- **Jetson** = Jetson Orin Nano Developer Kit 8GB (SD카드 OS)
- Ubuntu 22.04, ROS2 Humble, Linux 5.15.148-tegra
- 추론: onnxruntime-gpu 1.23.0 + TensorRT 10.3.0
