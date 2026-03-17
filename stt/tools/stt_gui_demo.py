"""
STT 전용 GUI 데모.
"""

import argparse
import gc
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext
from tkinter import ttk

import numpy as np
import sounddevice as sd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber


TARGET_SR = 16000
BLOCK_SIZE = 1600
GUI_REFRESH_MS = 50
MIN_RECORD_SEC = 0.4

MODEL_OPTIONS = [
    {
        "key": "whisper_tiny_cuda",
        "label": "whisper tiny (cuda)",
        "model": "whisper",
        "model_name": "tiny",
        "device": "cuda",
    },
    {
        "key": "whisper_base_cuda",
        "label": "whisper base (cuda)",
        "model": "whisper",
        "model_name": "base",
        "device": "cuda",
    },
    {
        "key": "whisper_base_trt",
        "label": "whisper base (trt)",
        "model": "whisper_trt",
        "model_name": "base",
        "device": None,
    },
    {
        "key": "api_gpt4o_mini",
        "label": "gpt-4o-mini-transcribe (api)",
        "model": "api",
        "model_name": "gpt-4o-mini-transcribe",
        "device": None,
    },
]


def parse_args():
    """
    기능:
    - STT GUI 데모 실행 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스를 반환한다.
    """
    parser = argparse.ArgumentParser()
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
        "--default-model",
        default="whisper_base_cuda",
        choices=[item["key"] for item in MODEL_OPTIONS],
        help="시작 시 선택할 기본 STT 모델",
    )
    parser.add_argument(
        "--trt-checkpoint",
        type=Path,
        default=Path("stt/models/whisper_trt_base_ko_ctx64/whisper_trt_split.pth"),
        help="WhisperTRT checkpoint 경로",
    )
    return parser.parse_args()


def print_devices():
    """
    기능:
    - 현재 시스템의 오디오 장치 목록을 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    for index, device in enumerate(sd.query_devices()):
        print(
            f"[{index}] {device['name']} | "
            f"in={device['max_input_channels']} | out={device['max_output_channels']} | "
            f"default_sr={int(device['default_samplerate'])}"
        )


def resolve_input_device(device_arg):
    """
    기능:
    - 입력 장치 인자를 sounddevice에서 사용할 실제 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 장치 인자.

    반환:
    - 장치 index 또는 이름을 반환한다.
    """
    if device_arg is not None:
        if str(device_arg).isdigit():
            return int(device_arg)
        return device_arg

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        raise RuntimeError("기본 입력 마이크가 설정되어 있지 않습니다.")
    return int(default_input)


def describe_input_device(device):
    """
    기능:
    - 선택한 입력 장치를 사람이 읽기 쉬운 문자열로 만든다.

    입력:
    - `device`: sounddevice 장치 식별자.

    반환:
    - 장치 설명 문자열을 반환한다.
    """
    info = sd.query_devices(device, "input")
    return (
        f"{info['name']} | sr={int(info['default_samplerate'])}Hz | "
        f"input_channels={info['max_input_channels']}"
    )


class STTGuiDemo:
    def __init__(self, args):
        """
        기능:
        - STT GUI 데모에 필요한 상태와 위젯을 초기화한다.

        입력:
        - `args`: 실행 인자 객체.

        반환:
        - 없음.
        """
        self.args = args
        self.input_device = resolve_input_device(args.input_device)
        self.input_device_label = describe_input_device(self.input_device)
        self.model_options = {item["key"]: item for item in MODEL_OPTIONS}

        self.root = tk.Tk()
        self.root.title("STT GUI 데모")
        self.root.geometry("920x780")
        self.root.minsize(860, 720)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.gui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.audio_chunks = []
        self.audio_level = 0.0
        self.record_started_at = None
        self.last_audio = None

        self.active_model_key = None
        self.active_model_label = "-"
        self.active_transcriber = None
        self.loading_model_key = None
        self.recording = False
        self.transcribing = False
        self.api_call_count = 0
        self.session_transcribe_count = 0

        self.model_var = tk.StringVar(value=args.default_model)
        self.status_var = tk.StringVar(value="모델 로딩 대기")
        self.detail_var = tk.StringVar(value="준비 중")
        self.record_var = tk.StringVar(value="녹음 대기")
        self.model_state_var = tk.StringVar(value="모델 준비 안 됨")
        self.api_notice_var = tk.StringVar(value="")
        self.level_var = tk.DoubleVar(value=0.0)
        self.record_sec_var = tk.StringVar(value="0.00초")
        self.api_count_var = tk.StringVar(value="API 호출 0회")

        self.stream = None

        self._build_ui()
        self._request_model_load(args.default_model)
        self.root.after(GUI_REFRESH_MS, self._refresh_ui)

    def _build_ui(self):
        """
        기능:
        - 메인 GUI 레이아웃과 위젯을 생성한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        root_frame = ttk.Frame(self.root, padding=16)
        root_frame.pack(fill="both", expand=True)

        top_frame = ttk.Frame(root_frame)
        top_frame.pack(fill="x")

        title_label = ttk.Label(top_frame, text="STT GUI 데모", font=("Helvetica", 20, "bold"))
        title_label.pack(anchor="w")

        device_label = ttk.Label(top_frame, text=f"입력 장치: {self.input_device_label}")
        device_label.pack(anchor="w", pady=(6, 0))

        model_frame = ttk.LabelFrame(root_frame, text="모델 선택", padding=12)
        model_frame.pack(fill="x", pady=(14, 10))

        self.model_combo = ttk.Combobox(
            model_frame,
            state="readonly",
            values=[item["label"] for item in MODEL_OPTIONS],
            width=32,
        )
        self.model_combo.pack(side="left")
        self.model_combo.current([item["key"] for item in MODEL_OPTIONS].index(self.args.default_model))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        self.reload_button = ttk.Button(model_frame, text="다시 로드", command=self._on_reload_clicked)
        self.reload_button.pack(side="left", padx=(8, 0))

        ttk.Label(model_frame, textvariable=self.model_state_var).pack(side="left", padx=(16, 0))

        control_frame = ttk.LabelFrame(root_frame, text="녹음 제어", padding=12)
        control_frame.pack(fill="x", pady=(0, 10))

        self.start_button = ttk.Button(control_frame, text="녹음 시작", command=self._start_recording)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(control_frame, text="녹음 정지", command=self._stop_recording)
        self.stop_button.pack(side="left", padx=(8, 0))
        self.clear_button = ttk.Button(control_frame, text="기록 지우기", command=self._clear_history)
        self.clear_button.pack(side="left", padx=(8, 0))

        ttk.Label(control_frame, textvariable=self.record_var).pack(side="left", padx=(18, 0))
        ttk.Label(control_frame, textvariable=self.record_sec_var).pack(side="left", padx=(12, 0))

        meter_frame = ttk.LabelFrame(root_frame, text="상태", padding=12)
        meter_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(meter_frame, textvariable=self.status_var, font=("Helvetica", 12, "bold")).pack(anchor="w")
        ttk.Label(meter_frame, textvariable=self.detail_var).pack(anchor="w", pady=(4, 0))
        ttk.Label(meter_frame, textvariable=self.api_notice_var, foreground="#b91c1c").pack(anchor="w", pady=(4, 0))
        ttk.Label(meter_frame, textvariable=self.api_count_var).pack(anchor="w", pady=(4, 0))

        ttk.Label(meter_frame, text="입력 레벨").pack(anchor="w", pady=(10, 2))
        self.level_bar = ttk.Progressbar(
            meter_frame,
            orient="horizontal",
            maximum=100.0,
            variable=self.level_var,
            mode="determinate",
        )
        self.level_bar.pack(fill="x")

        history_frame = ttk.LabelFrame(root_frame, text="전사 결과", padding=12)
        history_frame.pack(fill="both", expand=True)

        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            wrap="word",
            state="disabled",
            font=("NanumGothicCoding", 12),
        )
        self.history_text.pack(fill="both", expand=True)

        self.stop_button.state(["disabled"])
        self.start_button.state(["disabled"])

    def _on_model_selected(self, _event=None):
        """
        기능:
        - 사용자가 모델 선택을 바꿨을 때 백그라운드 로드를 시작한다.

        입력:
        - `_event`: Tk 이벤트 객체.

        반환:
        - 없음.
        """
        selected_label = self.model_combo.get()
        selected_key = self._find_model_key_by_label(selected_label)
        if selected_key is None:
            return
        if self.recording or self.transcribing:
            self._set_status("현재 작업 중에는 모델을 바꿀 수 없습니다.", "녹음 또는 전사 종료 후 다시 시도하세요.")
            self._sync_combo_to_active_model()
            return
        self._request_model_load(selected_key)

    def _on_reload_clicked(self):
        """
        기능:
        - 현재 선택된 모델을 다시 로드한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        selected_key = self._find_model_key_by_label(self.model_combo.get())
        if selected_key is None:
            return
        if self.recording or self.transcribing:
            self._set_status("현재 작업 중에는 다시 로드할 수 없습니다.", "녹음 또는 전사 종료 후 다시 시도하세요.")
            return
        self._request_model_load(selected_key, force=True)

    def _find_model_key_by_label(self, label):
        """
        기능:
        - 모델 표시 라벨에 대응하는 내부 키를 찾는다.

        입력:
        - `label`: GUI에 보이는 모델 라벨.

        반환:
        - 모델 키를 반환한다.
        """
        for item in MODEL_OPTIONS:
            if item["label"] == label:
                return item["key"]
        return None

    def _request_model_load(self, model_key, force=False):
        """
        기능:
        - 선택한 모델을 백그라운드에서 로드하도록 요청한다.

        입력:
        - `model_key`: 로드할 모델 키.
        - `force`: 현재와 같아도 다시 로드할지 여부.

        반환:
        - 없음.
        """
        if not force and model_key == self.active_model_key:
            self._set_status("이미 선택된 모델입니다.", self.active_model_label)
            self._update_api_notice(model_key)
            return
        if self.loading_model_key is not None:
            self._set_status("모델 로딩 중입니다.", "현재 로딩이 끝난 뒤 다시 시도하세요.")
            return

        self.loading_model_key = model_key
        model_label = self.model_options[model_key]["label"]
        self.model_state_var.set(f"로딩 중: {model_label}")
        self.start_button.state(["disabled"])
        self.reload_button.state(["disabled"])
        loader_thread = threading.Thread(
            target=self._load_model_worker,
            args=(model_key,),
            daemon=True,
        )
        loader_thread.start()

    def _load_model_worker(self, model_key):
        """
        기능:
        - 별도 스레드에서 기존 모델을 정리하고 새 모델을 로드한다.

        입력:
        - `model_key`: 로드할 모델 키.

        반환:
        - 없음.
        """
        model_info = self.model_options[model_key]
        old_transcriber = self.active_transcriber
        self.active_transcriber = None
        self.active_model_key = None
        self.active_model_label = "-"

        try:
            if old_transcriber is not None:
                old_transcriber.close()
            gc.collect()

            kwargs = {
                "model": model_info["model"],
                "model_name": model_info["model_name"],
                "language": "ko",
                "device": model_info["device"],
                "usage_purpose": "stt_gui_demo",
            }
            if model_key == "whisper_base_trt":
                kwargs["checkpoint_path"] = self.args.trt_checkpoint
                kwargs["workspace_mb"] = 128
                kwargs["max_text_ctx"] = 64

            transcriber = STTTranscriber(**kwargs)
            self.gui_queue.put(
                {
                    "type": "model_loaded",
                    "model_key": model_key,
                    "transcriber": transcriber,
                }
            )
        except Exception as exc:
            self.gui_queue.put(
                {
                    "type": "model_error",
                    "model_key": model_key,
                    "error": str(exc),
                }
            )

    def _start_recording(self):
        """
        기능:
        - 기본 마이크 입력을 열고 실시간 녹음을 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.loading_model_key is not None or self.active_transcriber is None:
            self._set_status("모델 준비가 끝난 뒤 녹음할 수 있습니다.", self.model_state_var.get())
            return
        if self.recording or self.transcribing:
            return

        self.audio_chunks = []
        self.audio_level = 0.0
        self.record_started_at = time.time()
        self.recording = True
        self.record_var.set("녹음 중")
        self._set_status("녹음 중", f"모델: {self.active_model_label}")
        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.model_combo.state(["disabled"])
        self.reload_button.state(["disabled"])

        self.stream = sd.InputStream(
            samplerate=TARGET_SR,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            device=self.input_device,
            callback=self._audio_callback,
        )
        self.stream.start()

    def _audio_callback(self, indata, _frames, _time_info, status):
        """
        기능:
        - 녹음 중 들어오는 오디오 청크를 저장하고 입력 레벨을 갱신한다.

        입력:
        - `indata`: 입력 오디오 프레임.
        - `_frames`: 프레임 수.
        - `_time_info`: 시간 정보.
        - `status`: sounddevice 상태.

        반환:
        - 없음.
        """
        if status:
            self.gui_queue.put({"type": "stream_error", "error": str(status)})

        mono = np.asarray(indata[:, 0], dtype=np.float32).copy()
        if self.recording:
            self.audio_chunks.append(mono)
        self.audio_level = float(np.max(np.abs(mono))) if mono.size else 0.0

    def _stop_recording(self):
        """
        기능:
        - 녹음을 종료하고 비동기 STT를 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if not self.recording:
            return

        self.recording = False
        self.record_var.set("녹음 종료")
        self.stop_button.state(["disabled"])
        self.level_var.set(0.0)

        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_chunks:
            self._finish_idle("녹음 데이터가 없습니다.")
            return

        audio = np.concatenate(self.audio_chunks, axis=0)
        self.audio_chunks = []
        audio_sec = float(len(audio)) / TARGET_SR
        self.last_audio = audio

        if audio_sec < MIN_RECORD_SEC:
            self._finish_idle(f"녹음이 너무 짧아 전사를 생략했습니다. ({audio_sec:.2f}s)")
            return

        self.transcribing = True
        self._set_status("STT 분석 중", f"{self.active_model_label} | 길이 {audio_sec:.2f}s")
        worker = threading.Thread(
            target=self._transcribe_worker,
            args=(audio, audio_sec, self.active_model_key, self.active_model_label, self.active_transcriber),
            daemon=True,
        )
        worker.start()

    def _transcribe_worker(self, audio, audio_sec, model_key, model_label, transcriber):
        """
        기능:
        - 녹음된 오디오를 별도 스레드에서 전사한다.

        입력:
        - `audio`: 녹음된 float32 mono 오디오.
        - `audio_sec`: 오디오 길이.
        - `model_key`: 현재 모델 키.
        - `model_label`: 현재 모델 라벨.
        - `transcriber`: 사용할 STTTranscriber 객체.

        반환:
        - 없음.
        """
        try:
            text = transcriber.transcribe(audio)
            self.gui_queue.put(
                {
                    "type": "transcribe_done",
                    "text": text,
                    "audio_sec": audio_sec,
                    "stt_sec": transcriber.last_duration_sec,
                    "model_key": model_key,
                    "model_label": model_label,
                }
            )
        except Exception as exc:
            self.gui_queue.put(
                {
                    "type": "transcribe_error",
                    "error": str(exc),
                    "model_label": model_label,
                }
            )

    def _finish_idle(self, detail_text):
        """
        기능:
        - 현재 작업을 끝내고 대기 상태 UI를 복구한다.

        입력:
        - `detail_text`: 상태 상세 문자열.

        반환:
        - 없음.
        """
        self.transcribing = False
        self.recording = False
        self.record_var.set("녹음 대기")
        self.record_sec_var.set("0.00초")
        self.start_button.state(["!disabled"] if self.active_transcriber is not None and self.loading_model_key is None else ["disabled"])
        self.stop_button.state(["disabled"])
        self.model_combo.state(["!disabled"])
        self.reload_button.state(["!disabled"])
        self._set_status("대기 중", detail_text)

    def _set_status(self, status_text, detail_text):
        """
        기능:
        - 상단 상태 문구를 갱신한다.

        입력:
        - `status_text`: 요약 상태 문자열.
        - `detail_text`: 상세 상태 문자열.

        반환:
        - 없음.
        """
        self.status_var.set(status_text)
        self.detail_var.set(detail_text)

    def _append_history(self, message):
        """
        기능:
        - 전사 결과 히스토리에 한 줄을 추가한다.

        입력:
        - `message`: 추가할 문자열.

        반환:
        - 없음.
        """
        self.history_text.configure(state="normal")
        self.history_text.insert("end", message + "\n\n")
        self.history_text.see("end")
        self.history_text.configure(state="disabled")

    def _clear_history(self):
        """
        기능:
        - 화면의 전사 결과 히스토리를 비운다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        self.history_text.configure(state="disabled")

    def _sync_combo_to_active_model(self):
        """
        기능:
        - 드롭다운 선택값을 현재 활성 모델에 맞춘다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.active_model_key is None:
            return
        self.model_combo.set(self.model_options[self.active_model_key]["label"])

    def _update_api_notice(self, model_key):
        """
        기능:
        - API 모델 선택 여부에 따라 경고 문구를 갱신한다.

        입력:
        - `model_key`: 현재 선택 또는 활성 모델 키.

        반환:
        - 없음.
        """
        if model_key == "api_gpt4o_mini":
            self.api_notice_var.set("주의: API 모델은 실제 과금이 발생합니다. 짧은 녹음은 자동으로 생략됩니다.")
        else:
            self.api_notice_var.set("")

    def _refresh_ui(self):
        """
        기능:
        - GUI 큐 이벤트와 실시간 표시 요소를 주기적으로 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        while True:
            try:
                item = self.gui_queue.get_nowait()
            except queue.Empty:
                break

            if item["type"] == "model_loaded":
                self.active_model_key = item["model_key"]
                self.active_model_label = self.model_options[self.active_model_key]["label"]
                self.active_transcriber = item["transcriber"]
                self.loading_model_key = None
                self.model_state_var.set(f"준비됨: {self.active_model_label}")
                self._sync_combo_to_active_model()
                self._update_api_notice(self.active_model_key)
                self._finish_idle(f"현재 모델: {self.active_model_label}")

            elif item["type"] == "model_error":
                self.loading_model_key = None
                self.model_state_var.set("모델 로드 실패")
                self._finish_idle(item["error"])
                self._sync_combo_to_active_model()

            elif item["type"] == "stream_error":
                self._set_status("오디오 스트림 경고", item["error"])

            elif item["type"] == "transcribe_done":
                self.session_transcribe_count += 1
                if item["model_key"] == "api_gpt4o_mini":
                    self.api_call_count += 1
                timestamp = time.strftime("%H:%M:%S")
                self.api_count_var.set(f"API 호출 {self.api_call_count}회")
                self._append_history(
                    f"[{timestamp}] {item['model_label']}\n"
                    f"- audio_sec: {item['audio_sec']:.2f}\n"
                    f"- stt_sec: {item['stt_sec']:.3f}\n"
                    f"- text: {item['text']}"
                )
                self._finish_idle(f"전사 완료 | {item['model_label']}")

            elif item["type"] == "transcribe_error":
                self._append_history(
                    f"[{time.strftime('%H:%M:%S')}] {item['model_label']}\n"
                    f"- error: {item['error']}"
                )
                self._finish_idle("전사 실패")

        if self.recording and self.record_started_at is not None:
            elapsed = time.time() - self.record_started_at
            self.record_sec_var.set(f"{elapsed:.2f}초")

        self.level_var.set(min(100.0, self.audio_level * 100.0))
        self.root.after(GUI_REFRESH_MS, self._refresh_ui)

    def _close(self):
        """
        기능:
        - 열린 스트림과 모델을 정리하고 GUI를 종료한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.stop_event.set()
        self.recording = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if self.active_transcriber is not None:
            self.active_transcriber.close()
            self.active_transcriber = None
        self.root.destroy()

    def run(self):
        """
        기능:
        - STT GUI 메인 루프를 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.root.mainloop()


def main():
    """
    기능:
    - STT GUI 데모를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    app = STTGuiDemo(args)
    app.run()


if __name__ == "__main__":
    main()
