# OpenAI API TTS Experiment

목표:

- 네트워크 기반 TTS reference baseline을 공통 SDK형 backend로 유지한다.
- `api`, `openai_api`, `chatgpt_api` 이름으로 같은 backend를 호출할 수 있게 한다.

현재 상태:

- A100 env `../env/tts_openai_api` 생성 완료
- `TTSSynthesizer(model="api" | "openai_api" | "chatgpt_api")` alias 연결 완료
- 실제 API 호출 없이 client 초기화와 alias 인스턴스화까지 확인 완료

현재 메모:

- backend:
  - `tts/backends/openai_api.py`
- 현재 기본 모델:
  - `gpt-4o-mini-tts`
- 현재 기본 voice:
  - `alloy`
- alias 검증:
  - `openai_api -> OpenAIAPITTSModel`
  - `chatgpt_api -> OpenAIAPITTSModel`

현재 판단:

- 빠른 end-to-end 음성 응답 baseline으로 유지한다.
- A100 4개 로컬 후보 비교와는 별도로, 품질과 사용자 인상 reference 용도로 둔다.
- 불필요한 과금을 막기 위해 실제 smoke 호출은 필요할 때만 수행한다.
