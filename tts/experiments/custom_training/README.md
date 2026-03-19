# TTS Custom Training Experiments

이 디렉토리는 영어 runtime winner 검증과 한국어 custom TTS 학습 파이프라인을 이어서 실험하는 자리다.

현재 active 방향:

1. `Piper`, `Kokoro`를 Jetson runtime 후보로 다시 검증
2. `OpenVoice V2`는 최종 runtime이 아니라 voice audition + synthetic dataset 생성기로 사용
3. 한국어 text-only corpus를 준비하고, synthetic dataset `1~3시간` pilot부터 시작
4. pilot 검증이 통과한 뒤에만 full training으로 확장
5. 현재 training 우선순위는 `Piper` 먼저, `Kokoro`는 runtime 우선 / training 후순위다.

관련 기준 문서:

- `docs/reports/tts_custom_training_plan_v1.md`
- `docs/reports/tts_training_feasibility_audit_20260319.md`
- `docs/status.md`

주의:

- 실제 생성 음성, 대규모 데이터셋, 체크포인트는 리포에 넣지 않는다.
- 리포 안에는 계획, 스크립트, 포맷, 얇은 실험 메모만 둔다.
