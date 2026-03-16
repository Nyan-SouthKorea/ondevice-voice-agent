# hi_popo Model Artifacts

이 디렉토리는 `하이 포포` wake word 모델의 학습 결과와 실험 산출물을 보관한다.

## 구조

- `runs/<run_name>/`
  - 개별 학습 실행 단위 아카이브
  - 체크포인트, 학습 히스토리, 실행 메타데이터를 함께 보관
- `hi_popo_classifier.pt`
  - 가장 최근 실행 결과의 최신 체크포인트
- `hi_popo_classifier.onnx`
  - 가장 최근 export 결과의 최신 classifier ONNX
- `hi_popo_classifier_onnx.json`
  - 최신 ONNX export metadata
- `hi_popo_training_history.json`
  - 가장 최근 실행 결과의 최신 학습 히스토리
- `hi_popo_latest_run.json`
  - 가장 최근 실행 결과의 요약 메타데이터

run 디렉토리에도 필요하면 아래 파일을 함께 둔다.

- `runs/<run_name>/hi_popo_classifier.onnx`
- `runs/<run_name>/hi_popo_classifier_onnx.json`

## 운영 원칙

- baseline 학습과 성능 개선 실험은 모두 `runs/` 아래에 별도 디렉토리로 남긴다.
- 실험별 결과 비교는 `run_name` 기준으로 추적한다.
- 단순 로그북 기록을 넘어서, 실제 재현 가능한 설정과 산출물을 같이 보관한다.
- 현재 export 대상은 raw audio end-to-end 모델이 아니라 `classifier only` ONNX다.

## 권장 run 이름

- baseline: `YYYYMMDD_HHMMSS_baseline`
- threshold 조정: `YYYYMMDD_HHMMSS_threshold_tune`
- negative weight 변경: `YYYYMMDD_HHMMSS_negw10`
- mixed 비율 변경: `YYYYMMDD_HHMMSS_mixed_ratio_update`
