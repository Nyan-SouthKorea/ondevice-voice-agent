"""
wake word + VAD + STT + TTS 통합 GUI 데모.
"""

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

from voice_pipeline_gui_demo import (
    PhaseLamp,
    STT_MODEL_OPTIONS,
    VoicePipelineGuiDemo,
    describe_input_device,
    print_devices,
    resolve_input_device,
)


REPO_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = REPO_ROOT.parent

DEFAULT_PIPER_ENV = "tts_piper_jetson"
DEFAULT_LOCAL_MODEL_PATH = (
    REPO_ROOT
    / "tts"
    / "models"
    / "piper_ko_260319_공식파인튜닝"
    / "epoch=2183-step=1376858.onnx"
)
DEFAULT_RESULTS_MODEL_PATH = (
    WORKSPACE_ROOT
    / "results"
    / "tts_custom"
    / "training"
    / "260319_1440_Piper_한국어_공식_파인튜닝_v1"
    / "exported_onnx"
    / "epoch=2183-step=1376858"
    / "epoch=2183-step=1376858.onnx"
)
DEFAULT_RESULTS_MODEL_PATH_FLAT = (
    WORKSPACE_ROOT
    / "results"
    / "tts_custom"
    / "training"
    / "260319_1440_Piper_한국어_공식_파인튜닝_v1"
    / "exported_onnx"
    / "epoch=2183-step=1376858.onnx"
)


def parse_args():
    """
    기능:
    - 통합 GUI + TTS 데모 실행 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wake-model",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier.onnx"),
        help="wake word ONNX 모델 경로",
    )
    parser.add_argument(
        "--wake-metadata",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier_onnx.json"),
        help="wake word ONNX 메타데이터 경로",
    )
    parser.add_argument(
        "--wake-threshold",
        type=float,
        default=0.80,
        help="wake word 검출 threshold",
    )
    parser.add_argument(
        "--wake-cooldown-sec",
        type=float,
        default=1.0,
        help="wake word 재감지 최소 간격",
    )
    parser.add_argument(
        "--feature-device",
        choices=["cpu", "gpu"],
        default="gpu",
        help="wake word feature extractor 장치",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.50,
        help="silero VAD speech threshold",
    )
    parser.add_argument(
        "--min-speech-frames",
        type=int,
        default=3,
        help="speech 시작으로 보기 전 필요한 연속 speech frame 수",
    )
    parser.add_argument(
        "--min-silence-frames",
        type=int,
        default=10,
        help="speech 종료로 보기 전 필요한 연속 silence frame 수",
    )
    parser.add_argument(
        "--default-stt-model",
        default="whisper_small_trt_safe",
        choices=[item["key"] for item in STT_MODEL_OPTIONS],
        help="시작 시 사용할 기본 STT 모델 키",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="입력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="오디오 장치 목록 출력 후 종료",
    )
    parser.add_argument(
        "--tts-env-root",
        type=Path,
        default=WORKSPACE_ROOT / "env",
        help="Jetson TTS env 루트",
    )
    parser.add_argument(
        "--tts-model-path",
        type=Path,
        default=None,
        help="한국어 Piper ONNX 경로",
    )
    parser.add_argument(
        "--tts-device",
        default="cpu",
        help="TTS backend device. Jetson Nano 기본값은 cpu",
    )
    parser.add_argument(
        "--tts-prefix",
        default="{text}",
        help="STT 결과를 TTS로 읽을 때 사용할 응답 템플릿. {text} placeholder 사용 가능",
    )
    return parser.parse_args()


def resolve_default_tts_model_path():
    """
    기능:
    - Jetson용 한국어 Piper ONNX 기본 경로를 고른다.

    입력:
    - 없음.

    반환:
    - 사용할 ONNX 경로를 반환한다.
    """
    for candidate in [
        DEFAULT_LOCAL_MODEL_PATH,
        DEFAULT_RESULTS_MODEL_PATH,
        DEFAULT_RESULTS_MODEL_PATH_FLAT,
    ]:
        if candidate.is_file():
            return candidate
    return DEFAULT_RESULTS_MODEL_PATH


class VoicePipelineTtsGuiDemo(VoicePipelineGuiDemo):
    def __init__(self, args):
        """
        기능:
        - 기존 wake/VAD/STT GUI 위에 TTS 응답 단계를 추가한다.

        입력:
        - `args`: 실행 인자 객체.

        반환:
        - 없음.
        """
        self.args = args
        self.input_device = resolve_input_device(args.input_device)
        self.input_device_label = describe_input_device(self.input_device)
        self.tts_env_python = args.tts_env_root / DEFAULT_PIPER_ENV / "bin" / "python"
        self.tts_model_path = args.tts_model_path or resolve_default_tts_model_path()
        self.tts_output_root = WORKSPACE_ROOT / "results" / "tts" / "jetson_demo" / "voice_pipeline_tts"
        self.tts_output_root.mkdir(parents=True, exist_ok=True)
        self.tts_metrics_log_path = self.tts_output_root / "metrics.jsonl"
        self.tts_play_process = None
        self.last_tts_text = ""
        self.turn_index = 0
        self.current_turn_metrics = {}
        self.last_wake_runtime_ms = 0.0
        super().__init__(args)
        self.root.title("Wake Word + VAD + STT + TTS 통합 데모")

    def _build_ui(self):
        """
        기능:
        - 기존 UI를 만들고 TTS 표시 라벨만 추가한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        super()._build_ui()
        self.tts_info_var = type(self.status_var)(value=f"TTS 모델: {self.tts_model_path}")
        self.tts_runtime_var = type(self.status_var)(value="stt sec: - | tts sec: - | total sec: -")
        self.tts_stage_var = type(self.status_var)(value="TTS 상태: 대기")
        self.tts_log_var = type(self.status_var)(value=f"기록 파일: {self.tts_metrics_log_path}")
        from tkinter import ttk

        self.phase_tts = PhaseLamp(self.phase_done.master, "TTS 재생 중")
        self.phase_tts.pack(anchor="w", fill="x", pady=(4, 0), before=self.phase_done)

        history_frame = self.history_text.master
        root_frame = history_frame.master
        tts_frame = ttk.LabelFrame(root_frame, text="TTS 상태와 실행시간", padding=10)
        tts_frame.pack(fill="x", pady=(8, 8), before=history_frame)
        ttk.Label(tts_frame, textvariable=self.tts_info_var).pack(anchor="w")
        ttk.Label(tts_frame, textvariable=self.tts_stage_var).pack(anchor="w", pady=(4, 0))
        ttk.Label(tts_frame, textvariable=self.tts_runtime_var).pack(anchor="w", pady=(4, 0))
        ttk.Label(tts_frame, textvariable=self.tts_log_var).pack(anchor="w", pady=(4, 0))

    def _reset_turn_metrics(self):
        """
        기능:
        - 현재 turn의 실행시간 추적 상태를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.current_turn_metrics = {
            "turn_id": self.turn_index,
            "wake_detected_at": None,
            "stt_started_at": None,
            "stt_finished_at": None,
            "tts_started_at": None,
            "tts_finished_at": None,
            "wake_runtime_ms": self.last_wake_runtime_ms,
        }

    def _append_metrics_log(self, payload):
        """
        기능:
        - TTS 파이프라인 실행 지표를 JSONL 파일에 누적 저장한다.

        입력:
        - `payload`: 저장할 dict.

        반환:
        - 없음.
        """
        self.tts_metrics_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.tts_metrics_log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _activate_listening(self):
        """
        기능:
        - 새 turn 실행시간 추적을 시작하고 listening 상태로 전환한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.turn_index += 1
        self._reset_turn_metrics()
        self.current_turn_metrics["wake_detected_at"] = time.monotonic()
        self.tts_stage_var.set("TTS 상태: 호출어 감지, 새 turn 시작")
        self.tts_runtime_var.set("stt sec: - | tts sec: - | total sec: -")
        super()._activate_listening()

    def _finalize_utterance(self, reason_text):
        """
        기능:
        - STT 시작 시점을 기록하고 발화를 전사 대상으로 넘긴다.

        입력:
        - `reason_text`: 발화 종료 이유 설명 문자열.

        반환:
        - 없음.
        """
        self.current_turn_metrics["stt_started_at"] = time.monotonic()
        super()._finalize_utterance(reason_text)

    def _pipeline_worker(self):
        """
        기능:
        - STT/TTS 실행 중에는 추가 입력을 무시하도록 상태기를 확장한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        while not self.stop_event.is_set():
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
            except Exception:
                continue

            self.audio_level = float((audio_chunk**2).mean() ** 0.5) if audio_chunk.size else 0.0

            if self.pipeline_state in {"STT_RUNNING", "TTS_RUNNING"}:
                continue

            if self.pipeline_state == "IDLE":
                self._handle_idle_chunk(audio_chunk)
            elif self.pipeline_state in ("LISTENING", "RECORDING"):
                self._handle_listening_chunk(audio_chunk)

    def _format_tts_response(self, text):
        """
        기능:
        - STT 결과를 TTS용 발화 문자열로 정리한다.

        입력:
        - `text`: STT 결과 문자열.

        반환:
        - TTS로 읽을 최종 문자열을 반환한다.
        """
        clean = (text or "").strip()
        if not clean:
            return "인식된 문장이 없습니다."
        try:
            return self.args.tts_prefix.format(text=clean)
        except Exception:
            return clean

    def _tts_worker(self, response_text):
        """
        기능:
        - 한국어 Piper TTS로 응답 음성을 생성하고 재생한다.

        입력:
        - `response_text`: 읽어줄 최종 응답 문자열.

        반환:
        - 없음.
        """
        try:
            self.current_turn_metrics["tts_started_at"] = time.monotonic()
            timestamp = time.strftime("%y%m%d_%H%M%S")
            output_path = self.tts_output_root / f"{timestamp}.wav"
            command = [
                str(self.tts_env_python),
                str(REPO_ROOT / "tts" / "tts_demo.py"),
                "--model",
                "piper",
                "--model-name",
                str(self.tts_model_path),
                "--device",
                self.args.tts_device,
                "--text",
                response_text,
                "--output",
                str(output_path),
            ]
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            synth_wall_sec = time.monotonic() - self.current_turn_metrics["tts_started_at"]
            if result.returncode != 0:
                self.gui_queue.put(
                    {
                        "type": "tts_error",
                        "error": result.stderr or result.stdout or "TTS 합성 실패",
                    }
                )
                return

            model_load = "-"
            elapsed = "-"
            for line in (result.stdout or "").splitlines():
                if line.startswith("model_load_sec:"):
                    model_load = line.split(":", 1)[1].strip()
                elif line.startswith("elapsed_sec:"):
                    elapsed = line.split(":", 1)[1].strip()

            play_started_at = time.monotonic()
            self.tts_play_process = subprocess.Popen(
                ["aplay", "-q", str(output_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.tts_play_process.wait()
            play_sec = time.monotonic() - play_started_at
            self.current_turn_metrics["tts_finished_at"] = time.monotonic()
            self.gui_queue.put(
                {
                    "type": "tts_done",
                    "text": response_text,
                    "output_path": str(output_path),
                    "model_load_sec": model_load,
                    "tts_sec": elapsed,
                    "tts_wall_sec": synth_wall_sec,
                    "play_sec": play_sec,
                }
            )
        except Exception as exc:
            self.gui_queue.put({"type": "tts_error", "error": str(exc)})

    def _stt_worker(self, audio, audio_sec, model_key, model_label, transcriber):
        """
        기능:
        - STT 실행의 wall time까지 함께 기록한다.

        입력:
        - `audio`: 발화 전체 오디오 배열.
        - `audio_sec`: 발화 길이(초).
        - `model_key`: 현재 STT 모델 키.
        - `model_label`: 현재 STT 모델 라벨.
        - `transcriber`: 사용할 STTTranscriber 인스턴스.

        반환:
        - 없음.
        """
        started_at = time.monotonic()
        try:
            text = transcriber.transcribe(audio)
            finished_at = time.monotonic()
            self.current_turn_metrics["stt_finished_at"] = finished_at
            self.gui_queue.put(
                {
                    "type": "stt_done",
                    "audio_sec": audio_sec,
                    "stt_sec": float(transcriber.last_duration_sec),
                    "stt_wall_sec": finished_at - started_at,
                    "model_key": model_key,
                    "model_label": model_label,
                    "text": text,
                }
            )
        except Exception as exc:
            self.gui_queue.put(
                {
                    "type": "stt_error",
                    "model_label": model_label,
                    "error": str(exc),
                }
            )

    def _refresh_ui(self):
        """
        기능:
        - 기존 큐 처리에 TTS 완료/실패 이벤트를 추가한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        while True:
            try:
                item = self.gui_queue.get_nowait()
            except Exception:
                break

            if item["type"] == "model_loaded":
                self.active_model_key = item["model_key"]
                self.active_model_label = self.model_options[self.active_model_key]["label"]
                self.active_transcriber = item["transcriber"]
                self.loading_model_key = None
                self.model_state_var.set(f"준비됨: {self.active_model_label}")
                self._sync_combo_to_active_model()
                if not self.stream_running:
                    self.start_button.state(["!disabled"])
                    self.reload_button.state(["!disabled"])
                self._set_status("STT 모델 준비 완료", self.active_model_label)

            elif item["type"] == "model_error":
                self.loading_model_key = None
                self.model_state_var.set("STT 모델 로드 실패")
                self.start_button.state(["disabled"])
                self.reload_button.state(["!disabled"])
                self._set_status("모델 로드 실패", item["error"])
                self._sync_combo_to_active_model()

            elif item["type"] == "stream_error":
                self._set_status("오디오 스트림 경고", item["error"])

            elif item["type"] == "wake_update":
                self.wake_score = item["score"]
                self.last_wake_runtime_ms = float(item["runtime_ms"])
                self.current_turn_metrics["wake_runtime_ms"] = self.last_wake_runtime_ms
                self.wake_runtime_var.set(f"wake total: {item['runtime_ms']:.2f} ms")
                if item["detected"]:
                    self.wake_lamp_until = time.monotonic() + 1.0

            elif item["type"] == "vad_update":
                self.vad_status = item["status"]
                self.vad_score = item["score"]
                self.vad_runtime_var.set(
                    f"vad state: {'speech' if self.vad_status else 'idle'} | conf: {self.vad_score * 100.0:5.1f}%"
                )

            elif item["type"] == "state_update":
                self._set_status(item["status"], item["detail"])

            elif item["type"] == "stt_done":
                self.session_transcribe_count += 1
                if item["model_key"] == "api_gpt4o_mini":
                    self.api_call_count += 1
                self.api_count_var.set(f"API 호출 {self.api_call_count}회")
                timestamp = time.strftime("%H:%M:%S")
                self.last_stt_text = item["text"]
                response_text = self._format_tts_response(item["text"])
                self.last_tts_text = response_text
                wake_to_stt_done_sec = "-"
                wake_detected_at = self.current_turn_metrics.get("wake_detected_at")
                stt_finished_at = self.current_turn_metrics.get("stt_finished_at")
                if wake_detected_at and stt_finished_at:
                    wake_to_stt_done_sec = f"{stt_finished_at - wake_detected_at:.3f}"
                self.tts_stage_var.set("TTS 상태: STT 완료, 음성 합성 시작")
                self.tts_runtime_var.set(
                    f"stt sec: {item['stt_sec']:.3f} (wall {item['stt_wall_sec']:.3f}) | "
                    f"tts sec: - | total sec: {wake_to_stt_done_sec}"
                )
                self._append_history(
                    f"[{timestamp}] {item['model_label']}\n"
                    f"- audio_sec: {item['audio_sec']:.2f}\n"
                    f"- stt_sec: {item['stt_sec']:.3f}\n"
                    f"- stt_wall_sec: {item['stt_wall_sec']:.3f}\n"
                    f"- wake_runtime_ms: {self.current_turn_metrics.get('wake_runtime_ms', 0.0):.2f}\n"
                    f"- wake_to_stt_done_sec: {wake_to_stt_done_sec}\n"
                    f"- text: {item['text']}\n"
                    f"- tts_request: {response_text}"
                )
                self.pipeline_state = "TTS_RUNNING"
                self._set_status("TTS 실행 중", "전사 결과를 바로 읽는 중")
                threading.Thread(target=self._tts_worker, args=(response_text,), daemon=True).start()

            elif item["type"] == "stt_error":
                timestamp = time.strftime("%H:%M:%S")
                self._append_history(f"[{timestamp}] {item['model_label']}\n- error: {item['error']}")
                self._set_pipeline_state("DONE", "STT 실패 후 대기 복귀")
                self.root.after(1200, self._finish_done_phase)

            elif item["type"] == "tts_done":
                timestamp = time.strftime("%H:%M:%S")
                wake_detected_at = self.current_turn_metrics.get("wake_detected_at")
                stt_started_at = self.current_turn_metrics.get("stt_started_at")
                tts_finished_at = self.current_turn_metrics.get("tts_finished_at")
                total_sec = "-"
                stt_to_tts_done_sec = "-"
                if wake_detected_at and tts_finished_at:
                    total_sec = f"{tts_finished_at - wake_detected_at:.3f}"
                if stt_started_at and tts_finished_at:
                    stt_to_tts_done_sec = f"{tts_finished_at - stt_started_at:.3f}"
                self.tts_runtime_var.set(
                    f"stt sec: 완료 | tts sec: {item['tts_sec']} (wall {item['tts_wall_sec']:.3f}) | total sec: {total_sec}"
                )
                self.tts_stage_var.set("TTS 상태: 응답 재생 완료")
                self._append_history(
                    f"[{timestamp}] Piper Korean TTS\n"
                    f"- tts_sec: {item['tts_sec']}\n"
                    f"- tts_wall_sec: {item['tts_wall_sec']:.3f}\n"
                    f"- model_load_sec: {item['model_load_sec']}\n"
                    f"- play_sec: {item['play_sec']:.3f}\n"
                    f"- wake_to_tts_done_sec: {total_sec}\n"
                    f"- stt_to_tts_done_sec: {stt_to_tts_done_sec}\n"
                    f"- output: {item['output_path']}"
                )
                self._append_metrics_log(
                    {
                        "timestamp": timestamp,
                        "turn_id": self.current_turn_metrics.get("turn_id"),
                        "wake_runtime_ms": self.current_turn_metrics.get("wake_runtime_ms"),
                        "stt_text": self.last_stt_text,
                        "tts_text": item["text"],
                        "model_load_sec": item["model_load_sec"],
                        "tts_sec": item["tts_sec"],
                        "tts_wall_sec": round(float(item["tts_wall_sec"]), 6),
                        "play_sec": round(float(item["play_sec"]), 6),
                        "wake_to_tts_done_sec": total_sec,
                        "stt_to_tts_done_sec": stt_to_tts_done_sec,
                        "output_path": item["output_path"],
                    }
                )
                self._set_pipeline_state("DONE", "TTS 응답 완료")
                self.root.after(1200, self._finish_done_phase)

            elif item["type"] == "tts_error":
                timestamp = time.strftime("%H:%M:%S")
                self._append_history(f"[{timestamp}] Piper Korean TTS\n- error: {item['error']}")
                self.tts_stage_var.set("TTS 상태: 오류")
                self._append_metrics_log(
                    {
                        "timestamp": timestamp,
                        "turn_id": self.current_turn_metrics.get("turn_id"),
                        "wake_runtime_ms": self.current_turn_metrics.get("wake_runtime_ms"),
                        "stt_text": self.last_stt_text,
                        "tts_text": self.last_tts_text,
                        "error": item["error"],
                    }
                )
                self._set_pipeline_state("DONE", "TTS 실패 후 대기 복귀")
                self.root.after(1200, self._finish_done_phase)

        self.level_bar.update_value(self.audio_level)
        self.wake_bar.update_value(self.wake_score)
        self.vad_bar.update_value(self.vad_score)
        self._draw_lamp(time.monotonic() < self.wake_lamp_until)
        self._update_phase_lamps()
        self.root.after(50, self._refresh_ui)

    def _update_phase_lamps(self):
        """
        기능:
        - TTS 실행 단계를 포함해 램프 상태를 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        is_idle = self.stream_running and self.pipeline_state == "IDLE"
        is_listening = self.pipeline_state in ("LISTENING", "RECORDING")
        is_stt = self.pipeline_state == "STT_RUNNING"
        is_tts = self.pipeline_state == "TTS_RUNNING"
        is_done = self.pipeline_state == "DONE"

        self.phase_idle.set_active(is_idle, "호출어 대기 중" if is_idle else "")
        self.phase_listening.set_active(is_listening, "명령을 듣는 중" if is_listening else "")
        self.phase_stt.set_active(is_stt, "음성을 전사하는 중" if is_stt else "")
        self.phase_tts.set_active(is_tts, "전사 결과를 음성으로 재생 중" if is_tts else "")
        self.phase_done.set_active(is_done, "처리 완료" if is_done else "")

        if is_listening:
            self.listen_indicator_var.set("마이크가 켜져 있고 현재 명령을 듣고 있습니다")
        elif is_stt:
            self.listen_indicator_var.set("듣기 종료, STT 처리 중")
        elif is_tts:
            self.listen_indicator_var.set("TTS 응답 재생 중")
        elif is_done:
            self.listen_indicator_var.set("응답 완료, 다시 호출어 대기")
        elif is_idle:
            self.listen_indicator_var.set("마이크 켜짐, 호출어 대기 중")
        else:
            self.listen_indicator_var.set("마이크 대기")

    def _close(self):
        """
        기능:
        - TTS 재생 프로세스까지 함께 정리하고 종료한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.tts_play_process and self.tts_play_process.poll() is None:
            self.tts_play_process.terminate()
        super()._close()


def main():
    """
    기능:
    - wake/VAD/STT/TTS 통합 GUI 데모를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return
    app = VoicePipelineTtsGuiDemo(args)
    app.run()


if __name__ == "__main__":
    main()
