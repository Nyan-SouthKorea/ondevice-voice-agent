# TTS Training Feasibility Audit

> 마지막 업데이트: 2026-03-19
> 목적: `Piper`, `Kokoro`를 한국어 custom training 후보 관점에서 다시 비교하고, 어떤 스택을 먼저 파야 하는지 좁힌다.

## 한 줄 결론

- 현재 기준으로는 `Piper`가 한국어 custom training 실험의 1순위 후보다.
- `Kokoro`는 Jetson runtime 후보로는 강하지만, 공식 training/fine-tune 경로가 불명확해 현재는 `runtime 우선, training 후순위`로 둔다.
- 따라서 다음 custom training 실험은 `OpenVoice V2 synthetic dataset -> Piper pilot training` 순서로 잡는 것이 가장 현실적이다.

## 판단 기준

- 공식 또는 재현 가능한 training 경로가 있는가
- dataset 전처리 형식이 명확한가
- export 후 Jetson 배포 경로가 있는가
- 한국어 text frontend를 붙일 현실적인 여지가 있는가
- 유지보수 상태와 리스크가 어떤가

## Piper

### 확인된 점

- archived 저장소지만 `TRAINING.md`가 남아 있고, 아래 단계가 모두 문서화돼 있다.
  - `piper_train.preprocess`
  - `python3 -m piper_train`
  - `python3 -m piper_train.export_onnx`
- 공식 문서가 `fine-tuning an existing model or training from scratch`를 모두 허용한다.
- 공식 문서는 “대부분의 경우 기존 모델 fine-tune을 권장하지만, 같은 언어일 필요는 없고 sample rate / quality가 맞으면 된다”고 적는다.
- export 결과가 바로 `onnx` + `onnx.json`이므로 Jetson runtime 경로와 자연스럽게 이어진다.
- single-speaker / multi-speaker 전처리 포맷도 명확하다.

### 리스크

- `rhasspy/piper` 저장소는 archived 상태다.
- training stack이 Python 3.10, old dependency, `espeak-ng`, `piper-phonemize` 등 옛 의존성에 묶여 있다.
- 공식 한국어 voice가 없고, 현재 확인한 서드파티 한국어 model 품질은 무효였다.
- 즉 “training path는 있다”와 “한국어에서 바로 잘 된다”는 별개다.

### 현재 판단

- `Piper`는 custom training feasibility를 실제로 시험해볼 가치가 충분하다.
- 특히 `pilot synthetic dataset`으로 빠르게 small run을 돌리고, export 후 Jetson runtime까지 이어지는지 보기 좋다.
- 다만 처음부터 transfer learning으로 고정하지 않고, pilot에서 scratch / fine-tune 모두 비교할 여지를 남긴다.

## Kokoro

### 확인된 점

- 공식 GitHub 저장소는 inference library 성격이 강하다.
- 공식 README는 `KPipeline`, `misaki` 기반 사용법과 language/voice usage 중심이다.
- 공식 model card는 `82M`, `Apache-2.0`, `few hundred hours`, `A100 80GB GPU hours 1000` 같은 training facts는 공개한다.
- Hugging Face model tree상 finetunes / adapters는 보이지만, 공식 training/fine-tune 재현 문서는 현재 확인하지 못했다.

### 리스크

- 공식 README에 training / fine-tune / dataset format / export workflow가 없다.
- `Finetuning Kokoro` 이슈가 열려 있지만, 현재 확인 기준으로 공식 답변이나 템플릿이 없다.
- 실제 custom training을 하려면 `StyleTTS2 + ISTFTNet + misaki frontend` 수준의 추가 엔지니어링이 필요할 가능성이 높다.
- 즉 runtime candidate로는 좋지만, 지금 단계에서 한국어 custom training 메인 스택으로 잡으면 리스크가 크다.

### 현재 판단

- `Kokoro`는 지금 당장 training main track으로 올리지 않는다.
- 우선은 Jetson runtime winner 후보로만 유지한다.
- `Piper`가 막히거나 품질이 끝까지 부족할 때만, `Kokoro custom training`을 별도 연구 트랙으로 연다.

## 현재 권장 우선순위

1. `Piper`
   - OpenVoice V2 synthetic dataset로 `1~3시간` pilot
   - preprocessing / pilot training / export / Jetson smoke
2. `Kokoro`
   - runtime winner 재검증 유지
   - training은 문서/재현 경로가 명확해질 때만 진입

## 즉시 다음 작업

1. `Piper` training 환경과 재현 절차를 별도 env 문서로 고정
2. 한국어 text-only corpus 후보 정리
3. OpenVoice V2 audition -> active reference 확정
4. `1~3시간` pilot synthetic dataset 생성
5. `Piper` pilot training

## 참고한 1차 근거

- `rhasspy/piper` archived `TRAINING.md`
- `rhasspy/piper` issue `#822`
- `rhasspy/piper` discussion `#581`
- `hexgrad/kokoro` official GitHub README
- `hexgrad/Kokoro-82M` model card
- `hexgrad/kokoro` issue `#207`
