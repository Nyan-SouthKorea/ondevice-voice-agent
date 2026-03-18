# VAD Models

이 디렉토리는 VAD ONNX 모델 파일을 두는 위치다.

현재 기준:

- 기본 파일명: `silero_vad.onnx`
- 기본 경로: `vad/models/silero_vad.onnx`
- 공식 Silero VAD ONNX 파일을 기본 자산으로 함께 관리한다

공식 다운로드 예시:

```bash
cd /home/everybot/workspace/ondevice-voice-agent/repo
mkdir -p vad/models
curl -L \
  https://raw.githubusercontent.com/snakers4/silero-vad/v6.2.1/src/silero_vad/data/silero_vad.onnx \
  -o vad/models/silero_vad.onnx
```

실행 예시:

```bash
source /home/everybot/workspace/ondevice-voice-agent/env/wake_word_jetson/bin/activate
python vad/vad_demo.py --model silero
```

참고:

- 공식 저장소: https://github.com/snakers4/silero-vad
- 모델 파일은 공식 ONNX를 그대로 사용한다.
