"""
WhisperTRT 기반 온디바이스 STT 백엔드.
"""

from pathlib import Path
import time

import numpy as np

from stt.experiments.stt_trt_builder_experiment import prepare_builder


class WhisperTRTSTTModel:
    def __init__(
        self,
        checkpoint_path,
        model_name="base",
        language="ko",
        workspace_mb=128,
        max_text_ctx=64,
    ):
        """
        기능:
        - WhisperTRT checkpoint를 로드해 온디바이스 STT 백엔드를 초기화한다.

        입력:
        - `checkpoint_path`: WhisperTRT split checkpoint 경로.
        - `model_name`: 기록용 Whisper 모델 이름.
        - `language`: tokenizer 언어 코드.
        - `workspace_mb`: builder 기록용 workspace 크기.
        - `max_text_ctx`: checkpoint 빌드 시 사용한 최대 text context 길이.

        반환:
        - 없음.
        """
        try:
            import torch
            import whisper
            import whisper_trt.model as wm
        except Exception as exc:
            raise ImportError(
                "WhisperTRT STT를 사용하려면 `torch`, `whisper`, `whisper_trt`가 필요합니다."
            ) from exc

        checkpoint = Path(checkpoint_path).resolve()
        if not checkpoint.exists():
            raise FileNotFoundError(f"WhisperTRT checkpoint를 찾을 수 없습니다: {checkpoint}")

        self.model_name = model_name
        self.language = language
        self.workspace_mb = workspace_mb
        self.max_text_ctx = max_text_ctx
        self.checkpoint_path = checkpoint
        self._torch = torch
        self._whisper = whisper
        self._wm = wm

        builder = prepare_builder(
            wm=wm,
            whisper=whisper,
            model_name=model_name,
            language=language,
            workspace_mb=workspace_mb,
            max_text_ctx=max_text_ctx,
            verbose=False,
        )
        self.model = builder.load(str(checkpoint))
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0

    def transcribe(self, audio):
        """
        기능:
        - float32 mono 오디오를 WhisperTRT checkpoint로 전사한다.

        입력:
        - `audio`: float32 mono 16kHz numpy 배열.

        반환:
        - 전사된 텍스트를 문자열로 반환한다.
        """
        started_at = time.perf_counter()

        mel = self._whisper.audio.log_mel_spectrogram(
            audio,
            padding=self._whisper.audio.N_SAMPLES,
        )[None, ...].cuda()
        if int(mel.shape[2]) > self._whisper.audio.N_FRAMES:
            mel = mel[:, :, : self._whisper.audio.N_FRAMES]

        audio_features = self.model.embed_audio(mel)
        prompt = list(self.model.tokenizer.sot_sequence_including_notimestamps)
        tokens = self._torch.LongTensor(prompt).cuda()[None, ...]

        for _ in range(self.model.dims.n_text_ctx - len(prompt)):
            logits = self.model.logits(tokens, audio_features)
            next_tokens = logits.argmax(dim=-1)
            tokens = self._torch.cat([tokens, next_tokens[:, -1:]], dim=-1)
            if tokens[0, -1] == self.model.tokenizer.eot:
                break

        generated = tokens[:, len(prompt) :]
        if generated.shape[1] > 0 and generated[0, -1] == self.model.tokenizer.eot:
            generated = generated[:, :-1]

        text = self.model.tokenizer.decode([int(x) for x in generated.flatten()])
        self.last_duration_sec = time.perf_counter() - started_at
        self.last_text = str(text).strip()
        self.last_result = {
            "text": self.last_text,
            "model": "whisper_trt",
            "model_name": self.model_name,
            "language": self.language,
            "checkpoint_path": str(self.checkpoint_path),
        }
        return self.last_text

    def reset(self):
        """
        기능:
        - 마지막 STT 결과를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0

    def close(self):
        """
        기능:
        - TRT 모델을 정리하고 CUDA 캐시를 비운다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.model = None
        if self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()
