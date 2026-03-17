# Status

> 마지막 업데이트: 2026-03-17

## 현재 목표

- wake word와 VAD 요소기술을 실제 Jetson 마이크 환경 기준으로 마무리 검증한다.
- wake word threshold와 input gain 기본값을 현장 기준으로 확정한다.
- wake word와 VAD를 연결해 STT 입력 구간 절단 기준을 정리한다.
- STT는 고정 문장 50개 직접 녹음 데이터셋으로 속도와 정확도를 비교한 뒤 기본 경로를 정한다.
- TTS는 공통 래퍼와 최소 합성 경로를 먼저 열고, 이후 Jetson 온디바이스 기본값을 확정한다.

## 현재 최종 기준

- wake word: `하이 포포`
- negative 데이터 최종 기준: `AI Hub + MUSAN + FSD50K`
- mixed positive 증강: 원본 positive 기반
- 학습 환경: Linux 서버 + A100
- 추론 타깃: Jetson Orin Nano Developer Kit 8GB
- VAD 기본 backend: `silero`
- STT 기본 backend 방향: `Whisper`
- TTS 기본 방향: `MeloTTS` 검증 + API 경로 병행

## 현재 상태

- 요소기술 완료 상태
  - wake word: 학습, 평가, ONNX export, Jetson 실시간 추론, openWakeWord 의존성 제거, Jetson 학습 smoke 검증까지 완료
  - VAD: dual backend, 공통 `VADDetector`, 기본 backend `silero`, 기본 마이크 demo 검증까지 완료
- negative 데이터셋 3종 준비 완료
  - `negative/musan`: `20,000`
  - `negative/fsd50k`: `20,000`
  - `negative/aihub_free_conversation`: `72,500`
- positive 증강 구조 정리 완료
  - `clean`: `11,250`
  - `mixed_noise`: `281`
  - `mixed_speech`: `281`
- feature 추출 완료
  - `positive_features_train.npy`: `(10631, 28, 96)`
  - `positive_features_test.npy`: `(1181, 28, 96)`
  - `negative_features_train.npy`: `(101250, 28, 96)`
  - `negative_features_test.npy`: `(11250, 28, 96)`
- baseline 학습과 grid search 완료
- 현재 best full-data run은 `final_full_best_trial40`
  - run dir: `wake_word/models/hi_popo/runs/final_full_best_trial40`
  - `lr=0.0005`
  - `negative_weight=5.0`
  - `layer_dim=64`
  - `n_blocks=2`
  - epoch 8 기준:
    - `val_recall 0.9966`
    - `val_accuracy 0.9926`
    - `val_fp_rate 0.0114`
    - `threshold 0.80`
- 분리 평가 스크립트 추가
  - `wake_word/train/05c_evaluate.py`
  - 저장된 checkpoint 기준 재평가 결과:
    - positive-only recall: `1177 / 1181 = 0.9966`
    - negative-only false positive rate: `128 / 11250 = 0.0114`
    - negative-only specificity: `11122 / 11250 = 0.9886`
- ONNX export 완료
  - `wake_word/models/hi_popo/hi_popo_classifier.onnx`
  - `wake_word/models/hi_popo/hi_popo_classifier_onnx.json`
- feature backbone ONNX 로컬화 완료
  - `wake_word/assets/feature_models/melspectrogram.onnx`
  - `wake_word/assets/feature_models/embedding_model.onnx`
  - `wake_word/features.py`로 feature extraction 로컬 구현 완료
  - `wake_word/openWakeWord/` clone 의존성 제거 완료
- classifier ONNX 추론 래퍼는 `(16, 96)` window와 `(T, 96)` clip feature 입력을 모두 지원한다.
- Jetson 실시간 GUI demo 완료
  - file: `wake_word/wake_word_gui_demo.py`
  - input: 기본 마이크
  - display: audio level gauge, wake score gauge, threshold slider, input gain slider
  - detection UI: 1초 유지 램프, 최근 감지 시각, 3초 유지 최고점
  - timing: `melspectrogram.onnx`, `embedding_model.onnx`, `hi_popo_classifier.onnx` 실행 시간 표시
  - resource: `tegrastats` 기반 CPU/RAM/GPU 텍스트 표시
  - user validation: Jetson에서 실제 실행 확인 완료
- Jetson runtime venv 생성 완료
  - path: `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson`
  - ORT source: `/home/everybot/.local/lib/python3.10/site-packages`
  - `onnxruntime-gpu 1.23.0`
  - `wake_word/train/check_onnx_gpu.py` 결과: `GPU_OK`
- Jetson 학습 smoke venv 생성 완료
  - path: `/home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_train_smoke`
  - PyTorch: `2.8.0`
  - librosa: `0.11.0`
  - torch CUDA 확인:
    - `torch.cuda.is_available() = True`
    - device: `Orin`
  - ORT source: `/home/everybot/.local/lib/python3.10/site-packages`
  - feature extraction smoke:
    - zero clip 기준 output shape `(1, 28, 96)`
    - provider `['CUDAExecutionProvider', 'CPUExecutionProvider']`
  - train smoke:
    - `wake_word/train/05_train.py` 1 epoch를 `cuda:0`에서 실행 확인
  - export smoke:
    - `wake_word/train/06_export_onnx.py` 실행 확인
  - 비고:
    - smoke용 synthetic feature와 run artifact는 검증 직후 제거함
- VAD 요소기술 구현 완료
  - 공통 진입점: `vad/detector.py`
  - 백엔드 1: `vad/model_webrtcvad.py`
  - 백엔드 2: `vad/model_silero.py`
  - 공통 사용 방식: `infer(audio_chunk) -> bool`
  - 기본 백엔드: `silero`
  - 기본 filtering:
    - `min_speech_frames=3`
    - `min_silence_frames=10`
  - 간단 데모: `vad/vad_demo.py`
  - GUI 데모: `vad/vad_gui_demo.py`
  - 데모 출력:
    - 최종 `status`
    - 마이크 입력 레벨 `level`
    - `silero`일 때 `conf`
    - `webrtcvad`일 때 `voiced_ratio`
  - GUI 표시:
    - 빨간 감지 램프
    - `말하는 중 / 대기 중` 상태
    - 입력 레벨 게이지
    - confidence 게이지
    - `silero` 기준 threshold 슬라이더
  - 검증 상태:
    - `webrtcvad` 기본 마이크 demo 동작 확인
    - `silero` 공식 ONNX 다운로드 및 기본 마이크 demo 동작 확인
- VAD 기본 ONNX 모델 경로
  - `vad/models/silero_vad.onnx`
- 현재 통합 전 단계
  - wake word와 VAD는 각각 독립적으로 검증 완료
  - 아직 둘을 연결한 utterance segmentation 단계는 시작 전
- STT 초기 구조 구현 완료
  - 공통 진입점: `stt/transcriber.py`
  - 백엔드 1: `stt/stt_whisper.py`
  - 백엔드 2: `stt/stt_api.py`
  - 최소 데모: `stt/stt_demo.py`
  - 녹음 GUI: `stt/stt_dataset_recorder.py`
  - 비교 평가: `stt/stt_benchmark.py`
  - 기준 데이터셋: `stt/datasets/korean_eval_50/`
  - 데이터셋 관리:
    - 기준 txt와 사용자 직접 녹음 wav를 함께 리포에 포함
  - 현재 기준:
    - 기본 backend는 `whisper`
    - 기본 Whisper 모델값은 현재 `tiny` 잠정값
    - 입력은 `16kHz mono` wav 또는 float32 mono 배열
    - 목적은 `짧은 utterance -> text` 기본 경로 확보와 비교 평가 기준 마련
  - Jetson smoke:
    - env: `wake_word_train_smoke`
    - `openai-whisper 20250625`, `openai 2.28.0`
    - `tiny + cuda` 기준 예시 샘플 전사 결과: `하이포포`
    - elapsed: 약 `3.031 sec`
  - 다음 비교 기준:
    - 사용자가 직접 읽은 50개 고정 문장 기준으로 `tiny / base / small`과 필요 시 API 경로 비교
    - 속도 지표와 normalized exact match, normalized CER를 함께 기록
- TTS 초기 구조 구현 시작
  - 공통 진입점: `tts/tts.py`
  - 백엔드 1: `tts/tts_api.py`
  - 최소 데모: `tts/tts_demo.py`
  - 현재 구현 범위:
    - 텍스트를 오디오 파일로 저장하는 최소 API 경로 확보
    - `TTSSynthesizer(model="api")` 공통 사용 방식 정리
    - OpenAI Audio Speech API 호출 결과를 로컬 usage log에 기록
  - 현재 방향:
    - 빠른 통합 경로는 `OpenAI API TTS`
    - 온디바이스 기본 후보는 `MeloTTS`
  - 다음 단계:
    - Jetson에서 `MeloTTS` 설치/실행 검증
    - playback / cache / LLM 연결 추가
- Jetson synthetic chunk 기준 간단 timing 확인
  - chunk size: `1280 samples = 80 ms`
  - classifier window: `16 frames = 1.28 s`
  - avg `melspectrogram.onnx`: `1.52 ms`
  - avg `embedding_model.onnx`: `4.59 ms`
  - avg `hi_popo_classifier.onnx`: `1.03 ms`
  - avg total pipeline: `8.35 ms`
- `wake_word/models/`의 대용량 학습 산출물은 계속 git 제외 대상이다.
- 다만 현재 runtime에 직접 필요한 최종 classifier ONNX와 metadata는 리포에 함께 둔다.
- `vad/models/silero_vad.onnx`도 기본 runtime 자산으로 리포에 함께 둔다.
- wake word 예시 샘플 경로를 `wake_word/examples/audio_samples/`로 정리했다.
- 루트 `README.md`, `wake_word/README.md`, `vad/README.md`를 현재 진입 문서로 사용한다.
- Jetson 환경 세팅 절차와 유지 기준은 `docs/envs/jetson_wake_word_env.md`에 정리돼 있다.
- `_tmp_download` 원본 보관 구조를 3개 폴더로 정리했다.
  - `1_aihub_free_conversation`
  - `2_fsd50k`
  - `3_musan`

## 중요 메모

- 현재 서버 환경에서는 ONNX feature 추출이 실제로는 GPU가 아니라 CPU로 동작했다.
- 원인은 `onnxruntime-gpu==1.23.2`의 CUDA 12 의존성과 현재 서버의 CUDA 11.8 조합 불일치다.
- PyTorch 학습은 사용자 셸에서 GPU 사용 가능했다.
- 현재 evaluation 비율은 대략 positive:negative = `1:10`이다.
- 이 비율은 모델 비교와 학습 선택에는 유효하지만, 실제 배치 성능을 바로 의미하지는 않는다.
- 현재 코드에서는 이름이 `test`인 split을 best epoch와 threshold 선택에 사용하므로, 엄밀히는 held-out validation에 가깝다.
- 현재 runtime 구조는 80ms마다 score를 갱신하고, 최초 유효 score는 약 1.28초 warm-up 뒤부터 나온다.
- Jetson에서도 학습 코드를 전혀 못 보는 상태는 아니고, `feature extraction -> train -> export` smoke 수준까지는 재현 가능하다.
- `openWakeWord` 로컬 clone 없이도 추론 smoke와 학습 smoke가 다시 통과했다.

## 다음 작업

1. 실제 현장 오디오 기준으로 threshold와 input gain 기본값을 확정
2. `하이 보보`, `하이 뽀뽀`, `굿바이 포포` 같은 hard negative 문구와 일반 대화 오탐 패턴을 정리
3. false accepts per hour 관점으로 연속 배경 오디오를 점검
4. wake word 감지 뒤에 VAD를 연결하고 speech start / speech end / utterance cut 기준을 정리
5. STT 50문장 직접 녹음 데이터셋을 만든 뒤 `tiny / base / small`과 API 경로를 비교
6. 비교 결과를 바탕으로 STT 기본 backend와 모델값을 확정
7. wake word와 VAD를 연결하고 utterance cut 기준을 먼저 확정
8. 성능이 충분하면 wake word와 VAD를 상위 SDK 첫 모듈로 정리
9. TTS 온디바이스 backend 후보를 Jetson에서 검증하고 상위 출력 모듈 구조를 정리
