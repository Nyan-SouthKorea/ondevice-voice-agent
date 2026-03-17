# TTS

이 디렉토리는 text-to-speech 계층 자리다.

현재 상태:

- 초기 구조 시작
- 공통 TTS 래퍼와 API 기반 최소 합성 경로를 추가했다.
- 온디바이스 기본 후보는 `MeloTTS`로 보고 후속 검증을 진행한다.

예상 역할:

- LLM 또는 명령 처리 결과를 음성으로 변환
- 온디바이스 가능 여부와 라이선스를 함께 고려한 엔진 선택

현재 구현 구조:

- `tts.py`
  - 공통 진입점
  - `TTSSynthesizer(model="api")`
- `tts_api.py`
  - OpenAI Audio Speech API 백엔드
- `tts_demo.py`
  - 텍스트를 받아 오디오 파일로 저장하는 최소 데모

공통 사용 방식:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="api",
    model_name="gpt-4o-mini-tts",
    voice="alloy",
    response_format="wav",
)
path = synthesizer.synthesize_to_file("안녕하세요. 테스트를 시작합니다.", "tts_outputs/test.wav")
print(path)
print(synthesizer.last_duration_sec)
```

직접 실행:

```bash
cd /home/everybot/workspace/ondevice-voice-agent/project/repo
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke/bin/activate
python tts/tts_demo.py \
  --text "안녕하세요. TTS 테스트를 시작합니다." \
  --output tts_outputs/hello.wav \
  --response-format wav
```

현재 v1 방향:

- 빠른 end-to-end 연결용:
  - `OpenAI API TTS`
- 온디바이스 기본 후보:
  - `MeloTTS`

현재 단계 판정:

- TTS 구조 설계 시작
- 공통 인터페이스와 API 경로 확보
- 다음 단계는 Jetson 기준 온디바이스 backend 검증

다음 작업:

1. `MeloTTS` Jetson 실행 가능 여부와 설치 절차를 별도 env 문서로 정리
2. 공통 인터페이스에 온디바이스 backend를 추가
3. 오디오 playback과 cache 전략을 붙인다
4. 이후 LLM 출력과 연결한다

현재 참고 기준:

- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/project_overview.md`](../docs/project_overview.md)
- [`../docs/research/tts.md`](../docs/research/tts.md)
