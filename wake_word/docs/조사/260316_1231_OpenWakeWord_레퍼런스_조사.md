# openWakeWord Reference Note

> 마지막 업데이트: 2026-03-16
> 목적: 삭제한 `wake_word/openWakeWord/` 로컬 clone 대신, 원본 출처와 현재 리포에 옮겨 쓴 범위를 기록한다.

## 1. 원본 소스 정보

- 원본 프로젝트: `openWakeWord`
- 저장소: https://github.com/dscripka/openWakeWord
- 라이선스: Apache 2.0

현재 이 리포에서 직접 보관하는 backbone ONNX는 아래 release asset 기준이다.

- `melspectrogram.onnx`
  - https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx
- `embedding_model.onnx`
  - https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx

## 2. 왜 로컬 clone을 제거했는가

이전에는 `wake_word/openWakeWord/`를 참고용으로 두었지만, 실제로는 아래 코드가 그 clone을 직접 import하고 있었다.

- `wake_word/detector.py`
- `wake_word/train/04_extract_features.py`
- `wake_word/train/check_onnx_gpu.py`

즉 참고용이 아니라 실행 의존성이었고, 이 상태는 아래 문제가 있었다.

- 로컬 clone이 없으면 코드가 바로 깨진다
- 문서만 읽어서는 숨은 설치 단계가 보이지 않는다
- SDK나 배포 구조로 갈수록 경계가 흐려진다

그래서 현재는 로컬 clone을 제거하고, 필요한 최소 기능만 이 리포 안으로 옮겼다.

## 3. 현재 리포로 옮긴 범위

현재 직접 사용하는 것은 딱 세 가지다.

1. feature backbone ONNX 2개
2. ONNX 호출 로직
3. streaming feature buffer 관리 로직

현재 위치:

- ONNX 자산:
  - `wake_word/assets/feature_models/melspectrogram.onnx`
  - `wake_word/assets/feature_models/embedding_model.onnx`
- 로컬 구현:
  - `wake_word/features.py`

## 4. 원본에서 참고한 모듈과 현재 대응 관계

기준 원본 파일:

- `openwakeword/utils.py`

이 파일에서 현재 리포로 옮겨 온 핵심은 아래다.

### 4-1. 모델 파일 준비

원본 개념:

- `download_models(...)`

현재 대응:

- `wake_word/features.py`
  - `ensure_feature_models(...)`

차이:

- 예전: local clone 안의 `resources/models/`를 기준으로 모델을 찾거나 다운로드
- 현재: 리포 안의 `assets/feature_models/`를 기준으로 고정

### 4-2. feature backbone ONNX 세션 초기화

원본 개념:

- `AudioFeatures.__init__(...)`

현재 대응:

- `wake_word/features.py`
  - `AudioFeatures.__init__(...)`

현재 유지한 요소:

- mel spectrogram ONNX 세션
- embedding ONNX 세션
- CPU / GPU provider 선택
- streaming buffer 초기 상태

### 4-3. mel spectrogram 계산

원본 개념:

- `_get_melspectrogram(...)`

현재 대응:

- `wake_word/features.py`
  - `_get_melspectrogram(...)`

현재 유지한 요소:

- PCM16 입력 정규화
- ONNX 출력 후 `x / 10 + 2` 변환

### 4-4. embedding 계산

원본 개념:

- `_get_embeddings(...)`
- `_get_embeddings_from_melspec(...)`
- `_get_embeddings_batch(...)`
- `embed_clips(...)`

현재 대응:

- `wake_word/features.py`
  - `_get_embeddings(...)`
  - `_get_embeddings_from_melspec(...)`
  - `_get_embeddings_batch(...)`
  - `embed_clips(...)`

현재 유지한 요소:

- `76` frame window
- `8` frame step
- 최종 embedding 차원 `96`
- clip batch 처리

### 4-5. realtime streaming buffer

원본 개념:

- `raw_data_buffer`
- `melspectrogram_buffer`
- `feature_buffer`
- `_buffer_raw_data(...)`
- `get_features(...)`

현재 대응:

- `wake_word/features.py`
  - 같은 이름의 buffer 상태와 helper 메서드 유지
- `wake_word/detector.py`
  - realtime 추론에서 위 buffer를 사용해 `80 ms` 단위 streaming 처리

## 5. 현재 사용하지 않는 openWakeWord 기능

아래는 현재 리포가 가져오지 않은 범위다.

- openWakeWord의 내장 wake word 모델들
- `openwakeword.Model`
- `openwakeword.train`
- verifier model 관련 기능
- openWakeWord가 포함하던 VAD 관련 기능
- 기타 예제, 테스트, benchmark 코드

즉 지금은 wake word custom pipeline에 필요한 최소 backbone 부분만 유지한다.

## 6. 지금 구조에서의 실행 경로

현재 wake word 실행 경로는 아래다.

1. `wake_word/assets/feature_models/melspectrogram.onnx`
2. `wake_word/assets/feature_models/embedding_model.onnx`
3. `wake_word/features.py`
4. `wake_word/detector.py`
5. `wake_word/train/04_extract_features.py`
6. `wake_word/train/check_onnx_gpu.py`

즉 `openWakeWord` 로컬 clone은 이제 실행 경로에 없다.

## 7. 다시 원본을 확인해야 할 때

다음 경우에만 원본 repo를 다시 보면 된다.

- backbone ONNX 버전을 바꾸고 싶을 때
- `utils.py`의 batch 처리 방식과 성능을 다시 비교하고 싶을 때
- openWakeWord의 학습 아이디어나 verifier 구조를 참고하고 싶을 때

다만 새로 clone을 실행 의존성으로 다시 붙이진 않는다. 필요하면 참고 후 로컬 구현으로 다시 옮긴다.
