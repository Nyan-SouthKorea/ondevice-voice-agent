# MeloTTS Experiment

목표:

- A100에서 `MeloTTS`를 공통 TTS 인터페이스 아래에 붙인다.
- 한국어 baseline voice 품질과 지연 시간을 확인한다.

1차 산출물:

- `TTSSynthesizer(model="melotts", ...)` 형태로 import 가능한 backend
- 한국어 대표 문장셋 기준 출력 오디오와 latency 기록

현재 상태:

- A100 첫 연결 완료
- `cuda:0` 기준 한국어 smoke 합성 성공
- 확인된 speaker id:
  - `KR -> 0`

현재 검증 결과:

- env:
  - `../env/tts_melotts`
- 첫 smoke:
  - output: `../results/tts/20260318_melotts_smoke/hello_kr.wav`
  - `model_load_sec 3.700`
  - `elapsed_sec 16.515`
  - output length: `6.006 sec`
- 두 번째 새 프로세스 재실행:
  - `model_load_sec 2.713`
  - `elapsed_sec 5.972`

설치 메모:

- `/usr/bin/python3.10 -m venv` 기준으로 설치
- `pip install git+https://github.com/myshell-ai/MeloTTS.git`
- `python -m unidic download`
- `librosa 0.9.1`와 최신 `setuptools` 조합 때문에 `setuptools<81` pin 필요
- 첫 한국어 실행 시 `python-mecab-ko`와 dictionary가 자동 설치됐다

중점 평가:

- 한국어 발음 안정성
- 기본 voice 인상
- 짧은 응답문 latency
- Jetson 탑재 가능성
