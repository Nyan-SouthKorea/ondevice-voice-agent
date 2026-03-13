# VAD

이 디렉토리는 voice activity detection 모듈 자리다.

## 목적

- wake word 이후 실제 발화 구간만 잘라내기
- 이후 STT 입력 길이와 잡음 구간을 줄이기

## 현재 상태

- 구조만 잡혀 있음
- 구현은 아직 시작하지 않음
- 검토 후보: `webrtcvad`

## 파일

- [`vad.py`](vad.py)
- [`vad_demo.py`](vad_demo.py)

## 관련 문서

- [프로젝트 통합 개요](../docs/project_overview.md)
- [개발 방침](../docs/개발방침.md)
