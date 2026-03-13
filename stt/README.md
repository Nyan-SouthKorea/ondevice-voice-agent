# STT

이 디렉토리는 speech-to-text 모듈 자리다.

## 목적

- wake word 이후 사용자의 실제 명령 발화를 텍스트로 변환

## 현재 계획

- 온디바이스 경로와 API 경로를 래퍼 구조로 통합
- 후보 방향:
  - Whisper 기반 온디바이스
  - API 기반 STT

## 현재 상태

- 파일 구조만 준비됨
- 실제 구현은 아직 시작하지 않음

## 파일

- [`stt_whisper.py`](stt_whisper.py)
- [`stt_api.py`](stt_api.py)
- [`stt_demo.py`](stt_demo.py)

## 관련 문서

- [프로젝트 통합 개요](../docs/project_overview.md)
- [개발 방침](../docs/개발방침.md)
