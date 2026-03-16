# STT

이 디렉토리는 speech-to-text 계층 자리다.

현재 상태:

- 초기 구현 완료
- 온디바이스와 API 기반 STT를 같은 사용법으로 갈아끼울 수 있는 구조를 잡았다.
- 고정 문장 50개 기준 녹음 데이터셋과 비교 평가 흐름을 추가했다.

예상 역할:

- 발화 오디오를 텍스트로 변환
- Jetson 환경과 서버/API 환경을 모두 고려한 추상화 제공

현재 구현 구조:

- `transcriber.py`
  - 공통 진입점
  - `STTTranscriber(model="whisper" | "api")`
- `stt_whisper.py`
  - OpenAI Whisper 기반 온디바이스 백엔드
- `stt_api.py`
  - OpenAI Audio Transcriptions API 백엔드
- `stt_demo.py`
  - 기본 마이크 또는 wav 파일을 받아 텍스트를 출력하는 최소 데모
- `stt_dataset_recorder.py`
  - 기준 문장 50개를 순서대로 녹음하는 GUI
- `stt_benchmark.py`
  - 같은 데이터셋으로 여러 STT 설정을 비교하는 평가 스크립트
- `datasets/korean_eval_50/`
  - txt와 wav를 같은 파일명으로 관리하는 평가 세트

공통 사용 방식:

```python
from stt import STTTranscriber

transcriber = STTTranscriber(model="whisper", model_name="tiny")
text = transcriber.transcribe(audio)
print(text)
print(transcriber.last_duration_sec)
```

현재 v1 기준:

- 기본 온디바이스 backend는 `whisper`
- 기본 Whisper 모델값은 현재 `tiny` 잠정값
- API backend는 구조만 같이 맞춰 둠
- 입력은 `16kHz mono` wav 또는 float32 mono 배열 기준
- 현재 단계의 목적은 `짧은 utterance -> text` 기본 경로 확보와 비교 평가 기준 마련이다
- 기본 모델값은 감으로 정하지 않고, 직접 녹음한 50문장 세트로 속도와 정확도를 비교한 뒤 정한다

## 평가 데이터셋

- 경로: `stt/datasets/korean_eval_50/`
- 파일 구조:
  - `001.txt`
  - `001.wav`
  - `002.txt`
  - `002.wav`
- txt는 리포에 포함한다.
- 사용자가 직접 녹음한 wav는 기본적으로 git 추적 대상에서 제외한다.

이 구조를 택한 이유:

- 문장 기준과 녹음 결과가 1:1로 바로 대응된다.
- 사람이 폴더를 열어도 진행 상태를 즉시 이해할 수 있다.
- recorder와 benchmark가 같은 포맷을 그대로 사용한다.

## 녹음 GUI

```bash
cd /home/everybot/workspace/ondevice-voice-agent/project/repo
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke/bin/activate
python stt/stt_dataset_recorder.py --dataset-dir stt/datasets/korean_eval_50
```

현재 지원 버튼:

- `녹음 시작`
- `녹음 정지`
- `들어보기`
- `재시도`
- `녹음 완료`

`녹음 완료`를 누르면 현재 문장 번호의 wav를 저장하고 다음 문장으로 자동 이동한다.

## 비교 평가

```bash
cd /home/everybot/workspace/ondevice-voice-agent/project/repo
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke/bin/activate
python stt/stt_benchmark.py \
  --dataset-dir stt/datasets/korean_eval_50 \
  --config whisper:tiny \
  --config whisper:base \
  --config whisper:small \
  --device cuda
```

현재 비교 지표:

- 샘플별 전사 결과
- 샘플별 STT 시간
- 설정별 평균 처리 시간
- 설정별 normalized exact match
- 설정별 normalized CER

평가 결과는 `stt/eval_results/` 아래에 저장한다.

현재 참고 기준:

- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/project_overview.md`](../docs/project_overview.md)
