# Wake Word Audio Samples

이 폴더는 공개 리포지토리에서 `wake_word` 구성을 이해할 수 있도록 넣어둔 소량 샘플만 포함한다.

## 포함 원칙

- 직접 생성한 `positive/tts` 샘플만 포함한다.
- `AI Hub`, `MUSAN`, `FSD50K` 등 third-party dataset 샘플은 포함하지 않는다.
- 실제 학습 전체 데이터셋은 리포에 포함하지 않는다.

## 현재 포함 샘플

- `positive_tts/pt-BR-ThalitaMultilingualNeural__pos0p__pos15hz.wav`
- `positive_tts/en-US-BrianMultilingualNeural__neg20p__pos5hz.wav`
- `positive_tts/ko-KR-InJoonNeural__pos8p__pos0hz.wav`

## 참고

- 전체 학습 데이터와 전처리 결과는 `wake_word/data/` 아래에 있고, 공개 리포에는 포함하지 않는다.
- 모델 산출물과 탐색 결과는 `wake_word/models/` 아래에서 관리되며, 공개 리포에는 포함하지 않는다.
