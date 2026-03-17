# TTS 기술 조사

> 마지막 업데이트: 2026-03-17
> 목적: Jetson Orin Nano 기준 TTS v1 선택과 구현 순서를 정리한다.

## 현재 결론

- 기본 아키텍처:
  - 공통 래퍼 `TTSSynthesizer`
  - 빠른 end-to-end 확인용 API 경로
  - 온디바이스 기본 후보는 `MeloTTS`
- v1 구현 순서:
  1. 공통 TTS 인터페이스 확정
  2. OpenAI API TTS로 최소 동작 경로 확보
  3. MeloTTS 온디바이스 경로를 Jetson에서 붙여 기본값 후보 검증
  4. 재생/캐시/LLM 연결

## 선택 이유

### 1. OpenAI API TTS

- 공식 Audio API `audio/speech` endpoint 사용 가능
- 현재 공식 지원 모델:
  - `gpt-4o-mini-tts`
  - `tts-1`
  - `tts-1-hd`
- 장점:
  - 구현 속도가 가장 빠름
  - 스트리밍 파일 저장 경로가 명확함
  - 말투 지시와 속도 조절 지원
  - 한국어 입력도 지원 문서에 포함
- 한계:
  - 네트워크 의존
  - 음성은 현재 영어 최적화가 중심
  - 온디바이스 목표와는 거리가 있음

### 2. MeloTTS

- 공식 저장소 기준 한국어 지원
- MIT 라이선스
- 다국어/다화자 구조
- README 기준 `CPU real-time inference`를 강조
- 현재 프로젝트 목표와 가장 잘 맞는 점:
  - 온디바이스 가능성
  - 상업적 사용 가능
  - 한국어 지원이 명시적

### 3. OpenVoice V2

- 공식 저장소 기준 한국어 지원
- MIT 라이선스
- 강점:
  - 음성 복제까지 포함한 확장성
- 현재 보류 이유:
  - 지금 단계에서는 voice cloning이 요구사항이 아님
  - 기본 TTS보다 시스템 복잡도가 커짐

### 4. Piper / Kokoro

- Piper:
  - 로컬 추론과 MIT 라이선스 측면은 좋다
  - 현재 한국어 기본 채택 근거는 MeloTTS보다 약하다
- Kokoro:
  - Apache 2.0은 장점
  - 현재 한국어 운영 기준으로 바로 채택할 근거가 부족하다

## 현재 결정

- 제품 지향 기본 후보: `MeloTTS`
- 즉시 구현 경로: `OpenAI API TTS`
- 즉, 지금은 인터페이스와 상위 파이프라인을 먼저 열고, 온디바이스 기본값은 다음 단계에서 MeloTTS로 붙인다.

## v1 인터페이스

- 공통 진입점:
  - `tts/tts.py`
- 공통 사용 방식:
  - `TTSSynthesizer(model="api")`
  - `synthesize_to_file(text, output_path)`

예시:

```python
from tts import TTSSynthesizer

synthesizer = TTSSynthesizer(
    model="api",
    model_name="gpt-4o-mini-tts",
    voice="alloy",
    response_format="wav",
)
synthesizer.synthesize_to_file("안녕하세요. 테스트를 시작합니다.", "out.wav")
```

## 단계별 개발 계획

### Phase 1. 인터페이스와 API 경로

- 목표:
  - TTS 자리를 코드상으로 열어 둔다
  - LLM 또는 규칙 응답 텍스트를 파일로 바로 합성 가능하게 만든다
- 범위:
  - `TTSSynthesizer`
  - `OpenAIAPITTSModel`
  - `tts_demo.py`
  - usage log 기록

### Phase 2. MeloTTS 온디바이스 검증

- 목표:
  - Jetson에서 한국어 TTS 기본 경로를 확보한다
- 범위:
  - `MeloTTSModel` 추가
  - Jetson 전용 env 문서 추가
  - `wav/pcm` 출력 형식과 실제 합성 속도 측정
  - 화자/속도/음질 비교

### Phase 3. 재생과 캐시

- 목표:
  - 반복 문구는 재합성 없이 재사용
  - 오디오 플레이백까지 연결
- 범위:
  - output cache key
  - `synthesize_to_bytes()` 또는 `play()` 보강
  - 응답 문장 길이 제한 및 chunking 기준

### Phase 4. 상위 파이프라인 통합

- 목표:
  - LLM 텍스트 응답을 TTS로 넘기고 재생
- 범위:
  - LLM 출력 텍스트 -> TTS -> speaker output
  - 실패 시 fallback 정책
  - latency budget 정리

## 현재 바로 볼 파일

- `tts/tts.py`
- `tts/tts_api.py`
- `tts/tts_demo.py`
- `tts/README.md`

## 참고 출처

- OpenAI Audio / Speech 공식 문서
- OpenAI Text-to-Speech 공식 가이드
- OpenAI Audio API Reference
- `myshell-ai/MeloTTS` 공식 GitHub README
- `myshell-ai/OpenVoice` 공식 GitHub README
