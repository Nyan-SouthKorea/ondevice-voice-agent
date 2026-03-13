# VAD

이 디렉토리는 voice activity detection 모듈 자리다.

현재 상태:

- 구현 시작 전
- wake word 이후 음성 구간 분리를 담당할 예정

예상 역할:

- wake word 이후 실제 발화 구간 검출
- STT 입력 구간 절단
- background noise 조건에서 불필요한 STT 호출 감소

현재 참고 기준:

- [`../docs/개발방침.md`](../docs/개발방침.md)
- [`../docs/project_overview.md`](../docs/project_overview.md)
