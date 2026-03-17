"""
wake word + VAD + STT 통합 GUI 데모.
"""

import argparse
import gc
import queue
import sys
import threading
import time
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import scrolledtext
from tkinter import ttk

import numpy as np
import sounddevice as sd

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber
from vad import VADDetector
from wake_word import HiPopoWakeWordRealtime
from wake_word.detector import STREAM_CHUNK_SAMPLES, TARGET_SR


GUI_REFRESH_MS = 50
WAKE_LAMP_HOLD_SEC = 1.0
MAX_LISTEN_WAIT_SEC = 5.0
MIN_UTTERANCE_SEC = 0.4
MAX_UTTERANCE_SEC = 10.0
PRE_SPEECH_SEC = 0.30

STT_MODEL_OPTIONS = [
    {
        "key": "whisper_tiny_cuda",
        "label": "whisper tiny fp16 (cuda)",
        "model": "whisper",
        "model_name": "tiny",
        "device": "cuda",
    },
    {
        "key": "whisper_base_cuda",
        "label": "whisper base fp16 (cuda)",
        "model": "whisper",
        "model_name": "base",
        "device": "cuda",
    },
    {
        "key": "whisper_base_trt",
        "label": "whisper base fp16e_fp16w (trt, legacy)",
        "model": "whisper_trt",
        "model_name": "base",
        "device": None,
        "checkpoint_path": Path("stt/models/whisper_trt_base_ko_ctx64_fp16e_fp16w_legacy/whisper_trt_split.pth"),
        "workspace_mb": 128,
        "max_text_ctx": 64,
    },
    {
        "key": "whisper_small_trt_safe",
        "label": "whisper small fp16e_fp32w (trt, nano safe)",
        "model": "whisper_trt",
        "model_name": "small",
        "device": None,
        "checkpoint_path": Path("stt/models/whisper_trt_small_ko_ctx64_fp16e_fp32w_nano_safe/whisper_trt_split.pth"),
        "workspace_mb": 64,
        "max_text_ctx": 64,
    },
    {
        "key": "whisper_small_trt_unsafe",
        "label": "whisper small fp16e_fp32w (trt, agx cross-device)",
        "model": "whisper_trt",
        "model_name": "small",
        "device": None,
        "checkpoint_path": Path("stt/models/whisper_trt_small_ko_ctx64_fp16e_fp32w_agx_cross_device/whisper_trt_split.pth"),
        "workspace_mb": 128,
        "max_text_ctx": 64,
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
    - 통합 GUI 데모 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse 네임스페이스를 반환한다.
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
    - 입력 장치 인자를 실제 sounddevice 장치 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 입력 장치 인자.

    반환:
    - 실제 실행에 사용할 장치 값을 반환한다.
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
    - 선택한 입력 장치 정보를 사람이 읽기 쉬운 문자열로 만든다.

    입력:
    - `device`: 실행에 사용할 장치 식별자.

    반환:
    - 입력 장치 설명 문자열을 반환한다.
    """
    info = sd.query_devices(device, "input")
    return (
        f"{info['name']} | sr={int(info['default_samplerate'])}Hz | "
        f"input_channels={info['max_input_channels']}"
    )


def compute_audio_level(audio_chunk):
    """
    기능:
    - 오디오 청크의 RMS 기준 입력 레벨을 계산한다.

    입력:
    - `audio_chunk`: float32 mono 오디오 청크.

    반환:
    - 0.0~1.0 범위의 입력 레벨 값을 반환한다.
    """
    audio = np.asarray(audio_chunk, dtype=np.float32)
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


class MetricBar(ttk.Frame):
    def __init__(self, master, title):
        """
        기능:
        - 제목, progress bar, 값 라벨을 가진 간단한 지표 위젯을 만든다.

        입력:
        - `master`: 부모 Tk 위젯.
        - `title`: 지표 제목 문자열.

        반환:
        - 없음.
        """
        super().__init__(master)
        self.title_label = ttk.Label(self, text=title)
        self.title_label.pack(anchor="w")
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", maximum=100.0)
        self.progress.pack(fill="x", pady=(4, 2))
        self.value_label = ttk.Label(self, text="0.0%")
        self.value_label.pack(anchor="e")

    def update_value(self, value):
        """
        기능:
        - 현재 지표 값을 progress bar와 라벨에 반영한다.

        입력:
        - `value`: 0.0~1.0 범위의 지표 값.

        반환:
        - 없음.
        """
        clamped = max(0.0, min(1.0, float(value)))
        self.progress["value"] = clamped * 100.0
        self.value_label.configure(text=f"{clamped * 100.0:5.1f}%")


class PhaseLamp(ttk.Frame):
    def __init__(self, master, title):
        """
        기능:
        - 단계별 진행 상태를 표시하는 램프 위젯을 만든다.

        입력:
        - `master`: 부모 Tk 위젯.
        - `title`: 단계 제목 문자열.

        반환:
        - 없음.
        """
        super().__init__(master, padding=6)
        top = master.winfo_toplevel()
        background = top.cget("background")
        self.canvas = tk.Canvas(self, width=24, height=24, highlightthickness=0, background=background)
        self.canvas.pack(side="left")
        self.title_label = ttk.Label(self, text=title, font=("Helvetica", 11, "bold"))
        self.title_label.pack(side="left", padx=(8, 0))
        self.detail_label = ttk.Label(self, text="비활성", foreground="#64748b")
        self.detail_label.pack(side="left", padx=(10, 0))
        self.set_active(False)

    def set_active(self, active, detail_text=""):
        """
        기능:
        - 단계 램프의 활성 여부와 상세 문구를 갱신한다.

        입력:
        - `active`: 현재 단계 활성 여부.
        - `detail_text`: 단계 옆에 보여줄 상세 문자열.

        반환:
        - 없음.
        """
        lamp_color = "#ef4444" if active else "#334155"
        title_color = "#111827" if active else "#475569"
        detail = detail_text if detail_text else ("진행 중" if active else "비활성")
        self.canvas.delete("all")
        self.canvas.create_oval(2, 2, 22, 22, fill=lamp_color, outline="")
        self.title_label.configure(foreground=title_color)
        self.detail_label.configure(text=detail, foreground=("#b91c1c" if active else "#64748b"))


class VoicePipelineGuiDemo:
    def __init__(self, args):
        """
        기능:
        - 통합 GUI 데모에 필요한 모듈, 상태값, 스레드, 위젯을 초기화한다.

        입력:
        - `args`: 실행 인자 객체.

        반환:
        - 없음.
        """
        self.args = args
        self.input_device = resolve_input_device(args.input_device)
        self.input_device_label = describe_input_device(self.input_device)

        self.wake_detector = HiPopoWakeWordRealtime(
            model_path=args.wake_model,
            metadata_path=args.wake_metadata,
            threshold=args.wake_threshold,
            feature_device=args.feature_device,
            cooldown_sec=args.wake_cooldown_sec,
        )
        self.vad_detector = VADDetector(
            model="silero",
            speech_threshold=args.vad_threshold,
            min_speech_frames=args.min_speech_frames,
            min_silence_frames=args.min_silence_frames,
        )

        self.model_options = {item["key"]: item for item in STT_MODEL_OPTIONS}
        self.pipeline_state = "IDLE"
        self.active_model_key = None
        self.active_model_label = "-"
        self.active_transcriber = None
        self.loading_model_key = None

        self.stop_event = threading.Event()
        self.audio_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        self.pipeline_thread = None
        self.stream = None
        self.stream_running = False

        self.audio_level = 0.0
        self.wake_score = 0.0
        self.vad_score = 0.0
        self.vad_status = False
        self.wake_lamp_until = 0.0
        self.listening_started_at = 0.0
        self.speech_started = False
        self.last_stt_text = ""
        self.api_call_count = 0
        self.session_transcribe_count = 0

        self.pre_speech_max_chunks = max(1, int((PRE_SPEECH_SEC * TARGET_SR) / self.vad_detector.chunk_samples))
        self.pre_speech_chunks = deque(maxlen=self.pre_speech_max_chunks)
        self.vad_pending_audio = np.zeros((0,), dtype=np.float32)
        self.utterance_chunks = []
        self.utterance_samples = 0

        self.root = tk.Tk()
        self.root.title("Wake Word + VAD + STT 통합 데모")
        self.root.geometry("960x720")
        self.root.minsize(860, 660)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.model_var = tk.StringVar(master=self.root, value=args.default_stt_model)
        self.status_var = tk.StringVar(value="준비 중")
        self.detail_var = tk.StringVar(value="STT 모델 로딩 대기")
        self.model_state_var = tk.StringVar(value="STT 모델 준비 안 됨")
        self.api_count_var = tk.StringVar(value="API 호출 0회")
        self.record_var = tk.StringVar(value="대기")
        self.wake_runtime_var = tk.StringVar(value="wake total: 0.00 ms")
        self.vad_runtime_var = tk.StringVar(value="vad conf: 0.0%")
        self.listen_indicator_var = tk.StringVar(value="마이크 대기")

        self._build_ui()
        self._request_model_load(args.default_stt_model)
        self.root.after(GUI_REFRESH_MS, self._refresh_ui)

    def _build_ui(self):
        """
        기능:
        - 통합 GUI 레이아웃과 위젯을 생성한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        root_frame = ttk.Frame(self.root, padding=12)
        root_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(root_frame, text="Wake Word + VAD + STT 통합 데모", font=("Helvetica", 17, "bold"))
        title_label.pack(anchor="w")
        ttk.Label(root_frame, text=f"입력 장치: {self.input_device_label}").pack(anchor="w", pady=(4, 0))

        top_frame = ttk.Frame(root_frame)
        top_frame.pack(fill="x", pady=(10, 8))
        top_frame.columnconfigure(0, weight=3)
        top_frame.columnconfigure(1, weight=2)

        left_column = ttk.Frame(top_frame)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_column = ttk.Frame(top_frame)
        right_column.grid(row=0, column=1, sticky="nsew")

        model_frame = ttk.LabelFrame(left_column, text="STT 모델", padding=10)
        model_frame.pack(fill="x", pady=(0, 8))

        self.model_combo = ttk.Combobox(
            model_frame,
            state="readonly",
            values=[item["label"] for item in STT_MODEL_OPTIONS],
            width=34,
        )
        self.model_combo.pack(side="left")
        self.model_combo.current([item["key"] for item in STT_MODEL_OPTIONS].index(self.args.default_stt_model))
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        self.reload_button = ttk.Button(model_frame, text="다시 로드", command=self._on_reload_clicked)
        self.reload_button.pack(side="left", padx=(8, 0))
        ttk.Label(model_frame, textvariable=self.model_state_var).pack(side="left", padx=(12, 0))

        control_frame = ttk.LabelFrame(left_column, text="제어", padding=10)
        control_frame.pack(fill="x", pady=(0, 8))

        self.start_button = ttk.Button(control_frame, text="마이크 시작", command=self._start_stream)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(control_frame, text="마이크 중지", command=self._stop_stream)
        self.stop_button.pack(side="left", padx=(8, 0))
        self.clear_button = ttk.Button(control_frame, text="기록 지우기", command=self._clear_history)
        self.clear_button.pack(side="left", padx=(8, 0))
        ttk.Label(control_frame, textvariable=self.record_var).pack(side="left", padx=(18, 0))

        state_frame = ttk.LabelFrame(left_column, text="상태", padding=10)
        state_frame.pack(fill="x", pady=(0, 0))

        ttk.Label(state_frame, textvariable=self.status_var, font=("Helvetica", 11, "bold")).pack(anchor="w")
        ttk.Label(state_frame, textvariable=self.detail_var).pack(anchor="w", pady=(2, 0))
        ttk.Label(state_frame, textvariable=self.api_count_var).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            state_frame,
            textvariable=self.listen_indicator_var,
            font=("Helvetica", 14, "bold"),
            foreground="#b91c1c",
        ).pack(anchor="w", pady=(6, 0))

        lamp_row = ttk.Frame(state_frame)
        lamp_row.pack(anchor="w", pady=(6, 0))
        ttk.Label(lamp_row, text="Wake 감지 램프").pack(side="left")
        self.lamp_canvas = tk.Canvas(lamp_row, width=28, height=28, highlightthickness=0, background=self.root.cget("background"))
        self.lamp_canvas.pack(side="left", padx=(8, 0))

        phase_frame = ttk.LabelFrame(right_column, text="프로세스 램프", padding=10)
        phase_frame.pack(fill="x", pady=(0, 8))
        self.phase_idle = PhaseLamp(phase_frame, "Wake Word 대기")
        self.phase_idle.pack(anchor="w", fill="x")
        self.phase_listening = PhaseLamp(phase_frame, "듣는 중")
        self.phase_listening.pack(anchor="w", fill="x", pady=(4, 0))
        self.phase_stt = PhaseLamp(phase_frame, "STT 처리 중")
        self.phase_stt.pack(anchor="w", fill="x", pady=(4, 0))
        self.phase_done = PhaseLamp(phase_frame, "출력 완료")
        self.phase_done.pack(anchor="w", fill="x", pady=(4, 0))

        metrics_frame = ttk.LabelFrame(right_column, text="실시간 지표", padding=10)
        metrics_frame.pack(fill="x", pady=(0, 0))

        self.level_bar = MetricBar(metrics_frame, "마이크 입력 레벨")
        self.level_bar.pack(fill="x")
        self.wake_bar = MetricBar(metrics_frame, "Wake score")
        self.wake_bar.pack(fill="x", pady=(6, 0))
        self.vad_bar = MetricBar(metrics_frame, "VAD confidence")
        self.vad_bar.pack(fill="x", pady=(6, 0))
        ttk.Label(metrics_frame, textvariable=self.wake_runtime_var).pack(anchor="w", pady=(6, 0))
        ttk.Label(metrics_frame, textvariable=self.vad_runtime_var).pack(anchor="w", pady=(2, 0))

        history_frame = ttk.LabelFrame(root_frame, text="인식 결과", padding=10)
        history_frame.pack(fill="both", expand=True)

        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            wrap="word",
            state="disabled",
            font=("NanumGothicCoding", 9),
        )
        self.history_text.pack(fill="both", expand=True)

        self.stop_button.state(["disabled"])
        self.start_button.state(["disabled"])

    def _on_model_selected(self, _event=None):
        """
        기능:
        - 사용자가 STT 모델 선택을 바꿨을 때 백그라운드 로드를 요청한다.

        입력:
        - `_event`: Tk 이벤트 객체.

        반환:
        - 없음.
        """
        selected_label = self.model_combo.get()
        selected_key = self._find_model_key_by_label(selected_label)
        if selected_key is None:
            return
        if self.pipeline_state == "STT_RUNNING":
            self._set_status("STT 실행 중", "현재 전사가 끝난 뒤 다시 시도하세요.")
            self._sync_combo_to_active_model()
            return
        self._request_model_load(selected_key)

    def _on_reload_clicked(self):
        """
        기능:
        - 현재 선택된 STT 모델을 다시 로드한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        selected_key = self._find_model_key_by_label(self.model_combo.get())
        if selected_key is None:
            return
        if self.pipeline_state == "STT_RUNNING":
            self._set_status("STT 실행 중", "현재 전사가 끝난 뒤 다시 시도하세요.")
            return
        self._request_model_load(selected_key, force=True)

    def _find_model_key_by_label(self, label):
        """
        기능:
        - 화면 라벨에 대응하는 내부 모델 키를 찾는다.

        입력:
        - `label`: GUI에 보이는 모델 라벨 문자열.

        반환:
        - 모델 키 문자열을 반환한다.
        """
        for item in STT_MODEL_OPTIONS:
            if item["label"] == label:
                return item["key"]
        return None

    def _request_model_load(self, model_key, force=False):
        """
        기능:
        - STT 모델을 백그라운드 스레드에서 로드하도록 요청한다.

        입력:
        - `model_key`: 로드할 STT 모델 키.
        - `force`: 현재와 같아도 다시 로드할지 여부.

        반환:
        - 없음.
        """
        if not force and model_key == self.active_model_key:
            self._set_status("이미 선택된 모델입니다.", self.active_model_label)
            return
        if self.loading_model_key is not None:
            self._set_status("모델 로딩 중입니다.", "현재 로딩이 끝난 뒤 다시 시도하세요.")
            return

        self.loading_model_key = model_key
        self.model_state_var.set(f"로딩 중: {self.model_options[model_key]['label']}")
        self.start_button.state(["disabled"])
        self.reload_button.state(["disabled"])
        loader_thread = threading.Thread(target=self._load_model_worker, args=(model_key,), daemon=True)
        loader_thread.start()

    def _load_model_worker(self, model_key):
        """
        기능:
        - 기존 STT 모델을 정리하고 새 STT 모델을 백그라운드에서 로드한다.

        입력:
        - `model_key`: 로드할 STT 모델 키.

        반환:
        - 없음.
        """
        old_transcriber = self.active_transcriber
        self.active_transcriber = None
        self.active_model_key = None
        self.active_model_label = "-"

        try:
            if old_transcriber is not None:
                old_transcriber.close()
            gc.collect()
            transcriber = self._build_transcriber_for_key(model_key)
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

    def _build_transcriber_for_key(self, model_key):
        """
        기능:
        - 모델 키에 맞는 STTTranscriber를 생성한다.

        입력:
        - `model_key`: 생성할 STT 모델 키.

        반환:
        - STTTranscriber 인스턴스를 반환한다.
        """
        model_info = self.model_options[model_key]
        kwargs = {
            "model": model_info["model"],
            "model_name": model_info["model_name"],
            "language": "ko",
            "device": model_info["device"],
            "usage_purpose": "voice_pipeline_gui_demo",
        }
        if model_info["model"] == "whisper_trt":
            kwargs["checkpoint_path"] = model_info["checkpoint_path"]
            kwargs["workspace_mb"] = model_info["workspace_mb"]
            kwargs["max_text_ctx"] = model_info["max_text_ctx"]
        return STTTranscriber(**kwargs)

    def _start_stream(self):
        """
        기능:
        - 기본 입력 마이크 스트림과 파이프라인 처리 스레드를 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.stream_running:
            return
        if self.loading_model_key is not None or self.active_transcriber is None:
            self._set_status("STT 모델 준비 중", self.model_state_var.get())
            return

        self.stop_event.clear()
        self.audio_queue = queue.Queue()
        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()

        self.stream = sd.InputStream(
            samplerate=TARGET_SR,
            blocksize=STREAM_CHUNK_SAMPLES,
            channels=1,
            dtype="float32",
            device=self.input_device,
            callback=self._audio_callback,
        )
        self.stream.start()
        self.stream_running = True
        self.record_var.set("마이크 실행 중")
        self._reset_listening_state()
        self._set_pipeline_state("IDLE", "호출어 대기 중")
        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.model_combo.state(["disabled"])
        self.reload_button.state(["disabled"])

    def _stop_stream(self):
        """
        기능:
        - 마이크 스트림과 파이프라인 처리 스레드를 종료한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.stop_event.set()
        self.stream_running = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.record_var.set("대기")
        self.start_button.state(["!disabled"] if self.active_transcriber is not None and self.loading_model_key is None else ["disabled"])
        self.stop_button.state(["disabled"])
        self.model_combo.state(["!disabled"])
        self.reload_button.state(["!disabled"])
        self._set_pipeline_state("STOPPED", "마이크 중지")

    def _audio_callback(self, indata, _frames, _time_info, status):
        """
        기능:
        - 마이크에서 들어오는 오디오 청크를 파이프라인 큐로 넘긴다.

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
        self.audio_queue.put(mono)

    def _pipeline_worker(self):
        """
        기능:
        - wake word, VAD, STT 상태기계를 순차 실행하는 통합 파이프라인 루프를 돌린다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        while not self.stop_event.is_set():
            try:
                audio_chunk = self.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            self.audio_level = compute_audio_level(audio_chunk)

            if self.pipeline_state == "STT_RUNNING":
                continue

            if self.pipeline_state == "IDLE":
                self._handle_idle_chunk(audio_chunk)
            elif self.pipeline_state in ("LISTENING", "RECORDING"):
                self._handle_listening_chunk(audio_chunk)

    def _handle_idle_chunk(self, audio_chunk):
        """
        기능:
        - 호출어 대기 상태에서 wake word score와 감지를 처리한다.

        입력:
        - `audio_chunk`: 현재 80ms 오디오 청크.

        반환:
        - 없음.
        """
        predictions = self.wake_detector.process_audio(audio_chunk, threshold=self.args.wake_threshold)
        if not predictions:
            return

        latest = predictions[-1]
        self.wake_score = float(latest.score)
        self.gui_queue.put(
            {
                "type": "wake_update",
                "score": self.wake_score,
                "detected": bool(any(item.detected for item in predictions)),
                "runtime_ms": self.wake_detector.last_runtime_stats["total_ms"],
            }
        )

        if any(item.detected for item in predictions):
            self.wake_lamp_until = time.monotonic() + WAKE_LAMP_HOLD_SEC
            self._activate_listening()

    def _activate_listening(self):
        """
        기능:
        - wake word 감지 후 VAD 기반 발화 대기 상태로 전환한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.wake_detector.reset()
        self.vad_detector.reset()
        self.pipeline_state = "LISTENING"
        self.listening_started_at = time.monotonic()
        self.speech_started = False
        self.pre_speech_chunks.clear()
        self.vad_pending_audio = np.zeros((0,), dtype=np.float32)
        self.utterance_chunks = []
        self.utterance_samples = 0
        self.vad_score = 0.0
        self.vad_status = False
        self.gui_queue.put(
            {
                "type": "state_update",
                "status": "호출어 감지",
                "detail": "명령 대기 중",
            }
        )

    def _handle_listening_chunk(self, audio_chunk):
        """
        기능:
        - VAD 청크 단위로 speech 시작/종료를 판단하고 발화 버퍼를 관리한다.

        입력:
        - `audio_chunk`: 현재 wake word 이후 오디오 청크.

        반환:
        - 없음.
        """
        self.vad_pending_audio = np.concatenate([self.vad_pending_audio, np.asarray(audio_chunk, dtype=np.float32)])
        now = time.monotonic()

        while self.vad_pending_audio.shape[0] >= self.vad_detector.chunk_samples:
            frame = self.vad_pending_audio[: self.vad_detector.chunk_samples]
            self.vad_pending_audio = self.vad_pending_audio[self.vad_detector.chunk_samples :]

            previous_status = bool(self.vad_detector.status)
            current_status = bool(self.vad_detector.infer(frame))
            self.vad_status = current_status
            self.vad_score = float(self.vad_detector.last_score)
            self.gui_queue.put(
                {
                    "type": "vad_update",
                    "status": self.vad_status,
                    "score": self.vad_score,
                }
            )

            if not self.speech_started:
                self.pre_speech_chunks.append(frame.copy())
                if now - self.listening_started_at > MAX_LISTEN_WAIT_SEC:
                    self._reset_listening_state()
                    self.gui_queue.put(
                        {
                            "type": "state_update",
                            "status": "대기 중",
                            "detail": "명령 대기 시간 초과",
                        }
                    )
                    return

                if current_status:
                    self.speech_started = True
                    self.pipeline_state = "RECORDING"
                    self.utterance_chunks = list(self.pre_speech_chunks)
                    self.utterance_samples = sum(chunk.shape[0] for chunk in self.utterance_chunks)
                    self.pre_speech_chunks.clear()
                    self.gui_queue.put(
                        {
                            "type": "state_update",
                            "status": "듣는 중",
                            "detail": "사용자 발화 수집 중",
                        }
                    )
                continue

            self.utterance_chunks.append(frame.copy())
            self.utterance_samples += frame.shape[0]
            utterance_sec = float(self.utterance_samples) / TARGET_SR

            if utterance_sec >= MAX_UTTERANCE_SEC:
                self._finalize_utterance("최대 발화 길이 도달")
                return

            if previous_status and not current_status:
                self._finalize_utterance("발화 종료 감지")
                return

    def _finalize_utterance(self, reason_text):
        """
        기능:
        - 수집된 발화를 STT 대상으로 확정하고 전사 스레드를 시작한다.

        입력:
        - `reason_text`: 발화 종료 이유 설명 문자열.

        반환:
        - 없음.
        """
        audio = np.concatenate(self.utterance_chunks, axis=0) if self.utterance_chunks else np.zeros((0,), dtype=np.float32)
        audio_sec = float(audio.shape[0]) / TARGET_SR if audio.size else 0.0

        self.pre_speech_chunks.clear()
        self.vad_pending_audio = np.zeros((0,), dtype=np.float32)
        self.utterance_chunks = []
        self.utterance_samples = 0

        if audio_sec < MIN_UTTERANCE_SEC:
            self._reset_listening_state()
            self.gui_queue.put(
                {
                    "type": "state_update",
                    "status": "대기 중",
                    "detail": f"{reason_text} | 발화가 너무 짧아 STT 생략",
                }
            )
            return

        self.pipeline_state = "STT_RUNNING"
        self.gui_queue.put(
            {
                "type": "state_update",
                "status": "STT 실행 중",
                "detail": f"{self.active_model_label} | {audio_sec:.2f}s",
            }
        )

        worker = threading.Thread(
            target=self._stt_worker,
            args=(audio, audio_sec, self.active_model_key, self.active_model_label, self.active_transcriber),
            daemon=True,
        )
        worker.start()

    def _stt_worker(self, audio, audio_sec, model_key, model_label, transcriber):
        """
        기능:
        - 수집된 발화를 별도 스레드에서 STT로 전사한다.

        입력:
        - `audio`: 발화 전체 오디오 배열.
        - `audio_sec`: 발화 길이(초).
        - `model_key`: 현재 STT 모델 키.
        - `model_label`: 현재 STT 모델 라벨.
        - `transcriber`: 사용할 STTTranscriber 인스턴스.

        반환:
        - 없음.
        """
        try:
            text = transcriber.transcribe(audio)
            self.gui_queue.put(
                {
                    "type": "stt_done",
                    "audio_sec": audio_sec,
                    "stt_sec": float(transcriber.last_duration_sec),
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

    def _reset_listening_state(self):
        """
        기능:
        - wake/VAD listening 상태를 초기화하고 다시 idle로 돌린다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.pipeline_state = "IDLE"
        self.speech_started = False
        self.listening_started_at = 0.0
        self.pre_speech_chunks.clear()
        self.vad_pending_audio = np.zeros((0,), dtype=np.float32)
        self.utterance_chunks = []
        self.utterance_samples = 0
        self.vad_detector.reset()
        self.vad_status = False
        self.vad_score = 0.0

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

    def _set_pipeline_state(self, state_name, detail_text):
        """
        기능:
        - 내부 파이프라인 상태와 화면 상태 문구를 함께 갱신한다.

        입력:
        - `state_name`: 새 파이프라인 상태 문자열.
        - `detail_text`: 화면에 표시할 상세 설명 문자열.

        반환:
        - 없음.
        """
        self.pipeline_state = state_name
        self._set_status(state_name, detail_text)

    def _update_phase_lamps(self):
        """
        기능:
        - 현재 파이프라인 상태를 단계별 램프와 청취 표시로 반영한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        is_idle = self.stream_running and self.pipeline_state == "IDLE"
        is_listening = self.pipeline_state in ("LISTENING", "RECORDING")
        is_stt = self.pipeline_state == "STT_RUNNING"
        is_done = self.pipeline_state in ("DONE",)

        self.phase_idle.set_active(is_idle, "호출어 감시 중" if is_idle else "")
        self.phase_listening.set_active(
            is_listening,
            "명령을 듣고 있습니다" if is_listening else "",
        )
        self.phase_stt.set_active(is_stt, "음성을 텍스트로 변환 중" if is_stt else "")
        self.phase_done.set_active(is_done, "결과 표시 완료" if is_done else "")

        if is_listening:
            self.listen_indicator_var.set("마이크가 켜져 있고 현재 명령을 듣고 있습니다")
        elif is_stt:
            self.listen_indicator_var.set("듣기 종료, STT 처리 중")
        elif is_done:
            self.listen_indicator_var.set("처리 완료, 다시 호출어 대기")
        elif self.stream_running:
            self.listen_indicator_var.set("마이크 켜짐, 호출어 대기 중")
        else:
            self.listen_indicator_var.set("마이크 대기")

    def _append_history(self, message):
        """
        기능:
        - 화면의 결과 히스토리에 텍스트 블록을 추가한다.

        입력:
        - `message`: 기록할 문자열.

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
        - 결과 히스토리 텍스트를 비운다.

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
        - 드롭다운 선택값을 현재 활성 STT 모델과 동기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.active_model_key is None:
            return
        self.model_combo.set(self.model_options[self.active_model_key]["label"])

    def _refresh_ui(self):
        """
        기능:
        - 백그라운드 큐 이벤트와 실시간 표시 요소를 주기적으로 반영한다.

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
                self.wake_runtime_var.set(f"wake total: {item['runtime_ms']:.2f} ms")
                if item["detected"]:
                    self.wake_lamp_until = time.monotonic() + WAKE_LAMP_HOLD_SEC

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
                self._append_history(
                    f"[{timestamp}] {item['model_label']}\n"
                    f"- audio_sec: {item['audio_sec']:.2f}\n"
                    f"- stt_sec: {item['stt_sec']:.3f}\n"
                    f"- text: {item['text']}"
                )
                self._set_pipeline_state("DONE", "전사 완료")
                self.root.after(1200, self._finish_done_phase)

            elif item["type"] == "stt_error":
                timestamp = time.strftime("%H:%M:%S")
                self._append_history(
                    f"[{timestamp}] {item['model_label']}\n"
                    f"- error: {item['error']}"
                )
                self._set_pipeline_state("DONE", "STT 실패 후 대기 복귀")
                self.root.after(1200, self._finish_done_phase)

        self.level_bar.update_value(self.audio_level)
        self.wake_bar.update_value(self.wake_score)
        self.vad_bar.update_value(self.vad_score)
        self._draw_lamp(time.monotonic() < self.wake_lamp_until)
        self._update_phase_lamps()
        self.root.after(GUI_REFRESH_MS, self._refresh_ui)

    def _finish_done_phase(self):
        """
        기능:
        - 출력 완료 단계 표시 후 다시 호출어 대기 상태로 복귀시킨다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.pipeline_state != "DONE":
            return
        self._reset_listening_state()
        self._set_status("대기 중", "호출어 대기 중")

    def _draw_lamp(self, detected):
        """
        기능:
        - wake 감지 램프를 현재 상태에 맞게 그린다.

        입력:
        - `detected`: 감지 상태 여부.

        반환:
        - 없음.
        """
        color = "#ef4444" if detected else "#334155"
        self.lamp_canvas.delete("all")
        self.lamp_canvas.create_oval(4, 4, 24, 24, fill=color, outline="")

    def _close(self):
        """
        기능:
        - 스트림, 스레드, STT 모델을 정리하고 GUI를 종료한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.stop_event.set()
        self.stream_running = False
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
        - Tk 메인 루프를 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.root.mainloop()


def main():
    """
    기능:
    - 통합 GUI 데모를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    app = VoicePipelineGuiDemo(args)
    app.run()


if __name__ == "__main__":
    main()
