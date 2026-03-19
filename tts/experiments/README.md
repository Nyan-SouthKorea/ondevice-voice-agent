# TTS Experiments

이 디렉토리는 후보 TTS 엔진별 실험 구조를 분리해 두는 자리다.

운영 원칙:

- 공통 SDK형 진입점은 `tts/tts.py`와 `tts/backends/`에서 유지한다.
- 엔진별 설치 메모, 실험 계획, smoke 기준, 리스크는 여기 하위 폴더에 분리한다.
- 대용량 체크포인트와 설치 산출물은 리포에 넣지 않는다.
- 실행 결과와 벤치마크 산출물은 로컬 `../results/tts/` 아래에 둔다.

현재 A100 비교 대상:

- `melotts/`
- `openvoice_v2/`
- `piper/`
- `kokoro/`
- `custom_training/`

보조 reference backend:

- `edge_tts/`
- `openai_api/`

3단계 목표:

1. A100에서 각 엔진을 GPU 가속 기준으로 쉽게 import 가능한 backend 형태로 정리
2. 공통 문장셋과 평가 기준으로 음질/지연/메모리 비교
3. Jetson에서 같은 기준으로 다시 측정해 최종 후보를 좁힘

현재 후속 R&D 트랙:

- `Piper`, `Kokoro`를 Jetson runtime winner 후보로 다시 검증
- `OpenVoice V2`는 voice audition + synthetic dataset 생성기로 사용
- 한국어 custom training은 `1~3시간 pilot dataset -> pilot 학습 -> 확대` 순서로 진행
