# Jetson TTS Env

> 목적: `OpenVoice V2`를 제외한 TTS 후보를 Jetson에서 검증하기 위한 env 구조와 실행 순서를 고정한다.

## 기본 원칙

- Jetson에서는 처음부터 모든 TTS 의존성을 한 env에 넣지 않는다.
- 먼저 backend별 smoke env를 분리해 실제 설치 가능성과 추론 가능성을 확인한다.
- 그 다음에만 최종 채택 후보를 상위 통합 env로 올린다.
- benchmark 코드는 A100 기준 per-backend env 구조를 유지하므로, Jetson 쪽도 같은 철학을 따른다.
- 공통 SDK 이름은 계속 `TTSSynthesizer`로 유지하되, backend import는 env 분리 친화적으로 정리한다.

## 이번 단계 범위

- 포함:
  - `MeloTTS`
  - `Piper`
  - `Kokoro`
  - `Edge TTS`
  - `OpenAI API TTS`
- 제외:
  - `OpenVoice V2`

## 왜 env를 나누는가

- 현재 TTS 후보는 의존성 차이가 크다.
- Jetson에서 가장 먼저 확인할 것은 "좋은 구조"가 아니라 "실제로 설치되고, 실제로 한 문장을 말할 수 있는가"다.
- `TTSSynthesizer`가 lazy import를 지원하면, 각 env는 자기 backend 의존성만 갖고도 같은 SDK 진입점을 쓸 수 있다.
- 이 방식이면 benchmark harness와 Jetson runtime 실험이 서로 덜 충돌한다.

## 권장 env 이름

- `../env/tts_network_jetson`
  - `Edge TTS`, `OpenAI API TTS`
- `../env/tts_melotts_jetson`
  - `MeloTTS`
- `../env/tts_piper_jetson`
  - `Piper`
- `../env/tts_kokoro_jetson`
  - `Kokoro`

## Jetson TTS 진행 순서

1. repo 최신화
2. TTS SDK lazy import 반영 여부 확인
3. `tts_network_jetson` 생성 후 `Edge TTS`, `OpenAI API TTS` smoke
4. `tts_melotts_jetson` 생성 후 한국어 smoke
5. `tts_piper_jetson` 생성 후 영어 smoke
6. `tts_kokoro_jetson` 생성 후 영어 smoke
7. 모델별 추론 시간, 메모리, 실패 원인 기록
8. 최종 채택 후보만 상위 voice pipeline 통합 대상으로 올림

## demo 원칙

- demo는 `tts/tts_demo.py` 공통 CLI를 유지한다.
- Jetson 전용 helper가 필요하면 wrapper script를 따로 두고, backend별 env python으로 `tts_demo.py`를 호출한다.
- 즉 demo wrapper는 추가할 수 있지만, backend 구현이나 benchmark 코드를 갈아엎지 않는다.

## 현재 기대 결과

- `Edge TTS`, `OpenAI API TTS`:
  - 네트워크 경로이므로 설치 난이도는 낮다.
- `MeloTTS`:
  - 한국어 주력 local 후보라 Jetson에서 가장 먼저 검증한다.
- `Piper`:
  - 영어 경량 후보로 검증 가치가 높다.
- `Kokoro`:
  - 영어 품질/속도 우수 후보지만 Jetson aarch64 설치 난이도는 직접 확인이 필요하다.

## 성공 기준

- 각 후보가 최소 1문장 이상 Jetson에서 실제 합성된다.
- 실패한 후보는 실패 원인이 문서화된다.
- 성공한 후보는 `TTSSynthesizer` 또는 thin demo wrapper로 바로 다시 실행할 수 있다.
- 다음 단계에서 어떤 후보를 상위 통합 env로 올릴지 판단할 수 있다.
