# TTS Custom Training Plan V1

> 마지막 업데이트: 2026-03-19
> 목적: Jetson Orin Nano에서 실제로 쓸 수 있는 영어 runtime 후보를 먼저 확정하고, OpenVoice V2를 데이터 생성용으로 사용해 한국어 custom TTS 학습 파이프라인을 연다.

## 한 줄 결론

- `Piper`, `Kokoro`는 우선 `Jetson runtime 후보`로 본다.
- `OpenVoice V2`는 최종 runtime이 아니라 `voice audition + synthetic dataset 생성기`로 본다.
- 한국어 custom training은 바로 대규모로 가지 않고, `1~3시간 pilot dataset -> 파일럿 학습 -> 확대` 순서로 간다.
- `runtime winner`와 `training winner`는 같다고 가정하지 않는다.

## 현재 전제

- 최종 배포 타깃은 `Jetson Orin Nano Developer Kit 8GB`다.
- `10초 이상` 걸리는 TTS 응답은 제품 runtime 후보로는 의미가 없다고 본다.
- `Piper`, `Kokoro`는 영어 local runtime 후보로 유지한다.
- `MeloTTS`, `OpenVoice V2`는 현재 Nano에서 기능 성공 경로는 있으나, runtime 기본 후보로는 무겁다.
- `OpenVoice V2`는 원하는 목소리 확인과 synthetic 음성 데이터 생성용으로만 사용한다.
- YouTube 등 외부 음성은 기술 검토용 audition까지는 허용하되, 최종 제품 voice로 갈 때는 권리/동의 검토가 필요하다.

## 왜 이렇게 나누는가

- Jetson에서 잘 도는 모델과, 한국어 custom training에 유리한 모델은 다를 수 있다.
- 특히 한국어는 text normalization, phoneme/G2P, 숫자/영문 혼합 처리 때문에 단순히 영어 checkpoint가 잘 돈다고 해서 학습까지 쉬운 것이 아니다.
- 따라서 아래 두 트랙을 분리한다.
  - runtime 트랙: `Piper`, `Kokoro`
  - data / training 트랙: `OpenVoice V2` + 이후 선택할 training stack

## Track A. 영어 runtime winner 확정

### 목적

- `Piper`, `Kokoro` 중 Jetson Orin Nano에서 실제로 가장 실용적인 영어 local runtime을 고른다.

### 해야 할 일

1. 대표 영어 응답 문장셋을 길이별로 다시 정리한다.
   - short reply
   - normal reply
   - long 안내문
2. Jetson Nano에서 `cold / warm / mean / p95`를 다시 측정한다.
3. 메모리와 장치 점유를 다시 측정한다.
4. 생성 음성을 직접 들어 품질도 확인한다.

### 성공 기준

- 1~2문장 응답에서 지연이 충분히 짧고,
- 메모리 점유가 다른 파이프라인과 동시 구동 가능한 수준이며,
- 청취 품질도 받아들일 만한 엔진 1개를 고른다.

### 중단 조건

- 둘 다 지연/품질/메모리 조건을 만족하지 못하면, 영어 runtime winner 확정 없이 다음 대안을 검토한다.

## Track B. 학습 가능성 audit

### 목적

- `Piper`, `Kokoro`가 한국어 custom training 후보로 실제 가치가 있는지 따진다.

### 확인 항목

- 공식 또는 재현 가능한 training 경로 존재 여부
- dataset 포맷 요구사항
- text frontend / phonemizer / G2P 교체 가능성
- ONNX export 가능성
- Jetson 배포 경로 존재 여부
- 라이선스
- 유지보수 상태

### 현재 판단

- `Piper`는 archived 상태지만, training / fine-tuning / ONNX export 경로는 문서상 존재한다.
- `Kokoro`는 현재 기준으로는 runtime 쪽 정보가 더 강하고, training 경로는 별도 확인이 필요하다.

### 중단 조건

- training 경로가 불명확하거나 한국어 frontend 변경 비용이 지나치게 크면, 해당 엔진은 `runtime 전용 후보`로만 유지한다.

## Track C. OpenVoice V2 voice audition pipeline

### 목적

- 사용자가 주는 레퍼런스 음성을 실제로 들어보고, synthetic dataset 생성에 쓸 voice를 고른다.

### 입력 소스

- 사용자가 제공하는 `mp4` 또는 음성 파일
- 필요 시 여러 후보를 병렬로 비교

### 처리 절차

1. 음성 추출
2. 무음 제거 / 레벨 정리 / 길이 trimming
3. OpenVoice V2로 고정 문장 발화
4. 사용자가 청취
5. 승인된 reference만 active voice로 승격

### 좋은 reference 기준

- 6~15초
- 단일 화자
- 배경음/음악 최소
- 감정 과도하지 않음
- 발음 또렷함
- 리버브 적음

### 산출물

- candidate reference 목록
- audition output
- 승인된 active reference manifest

## Track D. 한국어 text-only corpus 구축

### 목적

- synthetic 음성 생성용 한국어 텍스트 코퍼스를 만든다.

### 원칙

- 음성보다 텍스트가 중요하다.
- 공개 한국어 TTS/ASR corpus에서 텍스트만 추출한다.
- 음성은 저장하지 않거나 버린다.

### 정리 항목

- 중복 제거
- 너무 긴 문장 제거
- 숫자/시간/금액/주소/영문 혼합 유지
- 존댓말/명령문/안내문/짧은 응답 분포 유지

### 권장 메타데이터

- `text_id`
- `source_corpus`
- `category`
- `language`
- `normalization_version`

## Track E. synthetic dataset 1차 생성

### 목적

- OpenVoice V2로 한국어 synthetic dataset을 먼저 소규모로 만든다.

### 1차 목표량

- `1~3시간`

### 이유

- feasibility 확인용이다.
- teacher artifact, 발음 붕괴, prosody 이상을 먼저 걸러야 한다.
- 이 단계에서 문제가 있으면 대규모 생성은 시간 낭비다.

### 필수 필터

- `Whisper large-v3` 역전사
- CER / normalized exact match
- 금지 패턴 규칙
- 샘플 청취

### 메타데이터

- `utterance_id`
- `text_id`
- `reference_id`
- `generation_model`
- `generation_settings`
- `stt_filter_score`
- `accepted`

## Track F. pilot 학습

### 목적

- 실제로 한국어 custom TTS가 가능성이 있는지 빠르게 검증한다.

### 전략

- 처음부터 대규모 full training으로 가지 않는다.
- 작은 pilot run으로 먼저 아래를 확인한다.
  - scratch가 나은지
  - transfer가 나은지
  - 학습이 끝나도 Jetson 후보로 볼 가치가 있는지

### 현재 가이드

- 리소스 때문에 transfer learning을 고집하지 않는다.
- 다만 scratch와 transfer 중 무엇이 더 낫는지는 pilot으로 판단한다.
- 필요한 경우 full training도 허용한다.

### 성공 기준

- A100에서 baseline 대비 의미 있는 voice identity 또는 품질 개선이 보인다.
- 자동 역전사 기준으로 문장 보존성이 무너지지 않는다.

### 중단 조건

- pilot에서 발음/자연스러움이 baseline보다 나쁘고,
- Jetson 배포 가능성도 낮으면 해당 스택은 중단한다.

## Track G. 확대 학습

### pilot 이후 조건부 확대

- pilot 검증이 통과한 뒤에만 `5~10시간`, 필요하면 `15~30시간`으로 확장한다.

### 데이터 규모 가이드

- `1~3시간`: feasibility
- `5~10시간`: demo급
- `15~30시간`: 꽤 안정적인 단일 화자 모델을 기대할 수 있는 구간

## Track H. 평가와 기존 benchmark 연결

### 원칙

- 기존 6-backend benchmark 결과는 다시 돌리지 않는다.
- 새로 학습한 모델만 canonical prompt에 대해 합성한다.
- 기존 결과와 나란히 비교한다.

### 평가 항목

- `Whisper large-v3` 역전사
- 기존 benchmark와 동일 prompt
- 사람 listening
- Jetson latency / memory

## GPU 사용 원칙

- 현재 A100 `80GB x 2`를 적극 사용한다.
- 다만 처음부터 복잡한 multi-GPU training을 강제하지 않는다.
- 우선 아래처럼 독립 작업을 병렬화한다.
  - GPU0: data generation / STT filtering
  - GPU1: pilot training / eval
- 대규모 확대 단계에서만 multi-GPU training 필요 여부를 다시 판단한다.

## 리포/로컬 구조 원칙

- 리포 안에는 계획, 스크립트, README, 메타데이터 포맷만 둔다.
- 실제 생성 음성과 학습 산출물은 `../results`와 로컬 asset 경로에 둔다.

권장 로컬 구조:

```text
../results/tts_custom/
├── references/
├── audition/
├── corpora/
├── synthetic_dataset/
│   ├── pilot_v1/
│   └── full_v1/
├── training/
│   ├── pilot/
│   └── full/
└── evaluation/
```

## 현재 즉시 실행 순서

1. `Piper`, `Kokoro` runtime 재검증
2. `Piper`, `Kokoro` 학습 가능성 audit
3. OpenVoice V2 audition pipeline 정리
4. 한국어 text-only corpus 후보 정리
5. synthetic dataset `1~3시간` 생성
6. pilot 학습
7. 새 모델만 기존 benchmark와 비교

## 공식/준공식 참고 메모

- Piper training/fine-tune/onnx export 경로는 archived 문서 기준으로 존재한다.
  - dataset preprocessing
  - `piper_train`
  - fine-tuning from existing checkpoint
  - `export_onnx`
- 다만 공식 저장소가 archived 상태이므로, runtime 후보성과 training 후보성은 분리해서 본다.

