# Korean Eval 50

고정 문장 50개를 기준으로 STT 속도와 정확도를 비교하기 위한 최소 평가 세트다.

관리 기준:

- `001.txt`부터 `050.txt`까지가 기준 문장이다.
- 각 문장에 대한 녹음은 같은 파일명으로 `001.wav`처럼 같은 디렉토리에 저장한다.
- txt는 리포에 포함한다.
- 사용자가 직접 녹음한 wav는 기본적으로 git 추적 대상에서 제외한다.

사용 흐름:

1. `python stt/stt_dataset_recorder.py --dataset-dir stt/datasets/korean_eval_50`
2. 1번부터 50번까지 순서대로 녹음
3. `python stt/stt_benchmark.py --dataset-dir stt/datasets/korean_eval_50 --config whisper:tiny`
4. 같은 데이터셋으로 다른 STT 모델도 같은 방식으로 비교

파일 예:

- `012.txt`
- `012.wav`

이 구조만 맞으면 recorder와 benchmark가 그대로 동작한다.
