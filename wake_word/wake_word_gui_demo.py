"""
Jetson용 실시간 wake word GUI demo.

기능:
- 기본 입력 마이크 사용
- 실시간 audio level 표시
- 실시간 wake score 게이지 표시
- threshold 슬라이더로 현장 튜닝
- DETECTED / IDLE 상태 표시

예시:
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/bin/activate
python wake_word/wake_word_gui_demo.py
"""

import argparse
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import numpy as np
import sounddevice as sd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wake_word import HiPopoWakeWordRealtime
from wake_word.detector import STREAM_CHUNK_SAMPLES, TARGET_SR


GUI_REFRESH_MS = 50
GAUGE_WIDTH = 560
GAUGE_HEIGHT = 26
DETECTION_LAMP_HOLD_SEC = 1.0
PEAK_SCORE_HOLD_SEC = 3.0
TEGRASTATS_INTERVAL_MS = 1000


def parse_args():
    """
    기능:
    - 명령행 인자를 정의하고 파싱한다.
    
    입력:
    - 없음.
    
    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier.onnx"),
        help="ONNX classifier path",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier_onnx.json"),
        help="Export metadata path",
    )
    parser.add_argument(
        "--providers",
        type=str,
        default=None,
        help="Comma-separated classifier providers, e.g. cuda,cpu",
    )
    parser.add_argument(
        "--feature-device",
        choices=["cpu", "gpu"],
        default="gpu",
        help="Device for openWakeWord feature extraction",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="Input device index or name. Default is the current system default input.",
    )
    parser.add_argument(
        "--cooldown-sec",
        type=float,
        default=1.0,
        help="Minimum seconds between DETECTED events",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Initial threshold override",
    )
    parser.add_argument(
        "--input-gain",
        type=float,
        default=1.0,
        help="Software input gain multiplier",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    return parser.parse_args()


def parse_providers(raw):
    """
    기능:
    - 쉼표로 구분된 provider 문자열을 리스트로 변환한다.
    
    입력:
    - `raw`: 쉼표로 구분된 원본 입력 문자열.
    
    반환:
    - 파싱된 값 또는 리스트를 반환한다.
    """
    if raw is None:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


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
        if device_arg.isdigit():
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
    - `device`: 실행에 사용할 장치 또는 장치 식별자.
    
    반환:
    - 문자열 결과를 반환한다.
    """
    info = sd.query_devices(device, "input")
    return (
        f"{info['name']} | sr={int(info['default_samplerate'])}Hz | "
        f"input_channels={info['max_input_channels']}"
    )


def print_devices():
    """
    기능:
    - 현재 시스템에서 사용할 수 있는 오디오 장치 목록을 출력한다.
    
    입력:
    - 없음.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    for index, device in enumerate(sd.query_devices()):
        print(
            f"[{index}] {device['name']} | "
            f"in={device['max_input_channels']} | out={device['max_output_channels']} | "
            f"default_sr={int(device['default_samplerate'])}"
        )


def parse_tegrastats_line(line):
    """
    기능:
    - tegrastats 한 줄에서 GUI에 표시할 리소스 요약 정보를 뽑는다.

    입력:
    - `line`: tegrastats 원본 출력 한 줄.

    반환:
    - CPU, RAM, GPU 표시용 문자열 딕셔너리를 반환한다.
    """
    ram_match = re.search(r"RAM (\d+)/(\d+)MB", line)
    cpu_match = re.search(r"CPU \[([^\]]+)\]", line)
    gpu_match = re.search(r"GR3D_FREQ (\d+)%", line)

    ram_used = 0
    ram_total = 0
    ram_percent = 0.0
    if ram_match:
        ram_used = int(ram_match.group(1))
        ram_total = int(ram_match.group(2))
        if ram_total > 0:
            ram_percent = ram_used / ram_total * 100.0

    cpu_values = []
    if cpu_match:
        for item in cpu_match.group(1).split(","):
            item = item.strip()
            percent_match = re.match(r"(\d+)%", item)
            if percent_match:
                cpu_values.append(int(percent_match.group(1)))

    cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
    gpu_percent = int(gpu_match.group(1)) if gpu_match else 0
    cpu_core_text = ", ".join(f"{value}%" for value in cpu_values) if cpu_values else "-"

    return {
        "cpu_text": f"CPU 평균 {cpu_avg:.1f}%",
        "ram_text": f"RAM {ram_used}/{ram_total}MB ({ram_percent:.1f}%)",
        "gpu_text": f"GPU {gpu_percent}%",
        "detail": f"CPU 코어: {cpu_core_text}",
    }


class GaugeBar(ttk.Frame):
    def __init__(self, master, title, color):
        """
        기능:
        - 게이지 UI 위젯의 기본 상태와 표시 요소를 준비한다.
        
        입력:
        - `master`: Tkinter 부모 위젯.
        - `title`: 게이지 제목 문자열.
        - `color`: 게이지에 사용할 색상 코드.
        
        반환:
        - 없음.
        """
        super().__init__(master)
        self.title_label = ttk.Label(self, text=title)
        self.title_label.pack(anchor="w")

        self.canvas = tk.Canvas(
            self,
            width=GAUGE_WIDTH,
            height=GAUGE_HEIGHT,
            background="#0f172a",
            highlightthickness=0,
        )
        self.canvas.pack(fill="x", expand=True, pady=(4, 2))
        self.value_label = ttk.Label(self, text="0.0%")
        self.value_label.pack(anchor="e")
        self.color = color

    def update_value(self, value, threshold=None, held_peak=None):
        """
        기능:
        - 게이지 막대와 표시 값을 현재 상태에 맞게 갱신한다.
        
        입력:
        - `value`: 게이지에 표시할 현재 값.
        - `threshold`: 검출 기준값. `None`이면 기본 threshold를 사용한다.
        - `held_peak`: 잠시 유지해서 표시할 최고점 값.

        반환:
        - 함수 실행 결과를 반환한다.
        """
        clamped = max(0.0, min(1.0, value))
        width = int(GAUGE_WIDTH * clamped)

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, GAUGE_WIDTH, GAUGE_HEIGHT, fill="#1f2937", outline="")
        self.canvas.create_rectangle(0, 0, width, GAUGE_HEIGHT, fill=self.color, outline="")
        if threshold is not None:
            x = int(GAUGE_WIDTH * max(0.0, min(1.0, threshold)))
            self.canvas.create_line(x, 0, x, GAUGE_HEIGHT, fill="#f8fafc", width=2)
        if held_peak is not None:
            peak_x = int(GAUGE_WIDTH * max(0.0, min(1.0, held_peak)))
            self.canvas.create_line(peak_x, 0, peak_x, GAUGE_HEIGHT, fill="#f97316", width=3)
            self.value_label.configure(
                text=f"현재 {clamped * 100.0:5.1f}% | 유지 최고 {held_peak * 100.0:5.1f}%"
            )
            return
        self.value_label.configure(text=f"{clamped * 100.0:5.1f}%")


class WakeWordGuiDemo:
    def __init__(self, args):
        """
        기능:
        - 실시간 GUI 데모에 필요한 detector, queue, stream, 상태값을 준비한다.
        
        입력:
        - `args`: 명령행에서 파싱된 실행 인자 객체.
        
        반환:
        - 없음.
        """
        self.args = args
        self.providers = parse_providers(args.providers)
        self.input_device = resolve_input_device(args.input_device)

        self.detector = HiPopoWakeWordRealtime(
            model_path=args.model,
            metadata_path=args.metadata,
            threshold=args.threshold,
            providers=self.providers,
            feature_device=args.feature_device,
            cooldown_sec=args.cooldown_sec,
        )

        self.input_device_label = describe_input_device(self.input_device)
        self.classifier_providers = ", ".join(self.detector.classifier.session.get_providers())
        self.feature_provider = str(self.detector.feature_execution_provider)

        self.root = tk.Tk()
        self.root.title("하이 포포 웨이크워드 데모")
        self.root.geometry("820x860")
        self.root.minsize(780, 780)
        self.root.configure(background="#e5e7eb")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.threshold_var = tk.DoubleVar(value=self.detector.threshold)
        self.input_gain_var = tk.DoubleVar(value=args.input_gain)
        self.current_threshold = float(self.detector.threshold)
        self.current_input_gain = float(args.input_gain)
        self.current_score = 0.0
        self.current_audio_level = 0.0
        self.current_status = "대기 중"
        self.last_detected_at = "-"
        self.stream_status = "정상"
        self.detection_lamp_until = 0.0
        self.held_peak_score = 0.0
        self.held_peak_until = 0.0
        self.resource_stats = {
            "cpu_text": "CPU 평균 확인 중",
            "ram_text": "RAM 확인 중",
            "gpu_text": "GPU 확인 중",
            "detail": "CPU 코어: -",
        }
        self.resource_process = None

        self.audio_queue = queue.Queue(maxsize=8)
        self.gui_queue = queue.Queue(maxsize=32)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.resource_thread = threading.Thread(target=self._resource_loop, daemon=True)

        self._build_ui()

        self.stream = sd.InputStream(
            samplerate=TARGET_SR,
            blocksize=STREAM_CHUNK_SAMPLES,
            channels=1,
            dtype="float32",
            device=self.input_device,
            callback=self._audio_callback,
        )

    def _build_ui(self):
        """
        기능:
        - Tkinter GUI 레이아웃과 위젯을 구성한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Status.TLabel", font=("TkDefaultFont", 22, "bold"))
        style.configure("Meta.TLabel", font=("TkDefaultFont", 11))

        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="하이 포포 웨이크워드", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Jetson 마이크 실시간 데모", style="Meta.TLabel").pack(anchor="w", pady=(0, 14))

        info = ttk.Frame(frame)
        info.pack(fill="x", pady=(0, 12))
        self.device_label = ttk.Label(info, text=f"입력 장치: {self.input_device_label}", style="Meta.TLabel")
        self.device_label.pack(anchor="w")
        ttk.Label(info, text=f"분류기 실행 프로바이더: {self.classifier_providers}", style="Meta.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"특징 추출 프로바이더: {self.feature_provider}", style="Meta.TLabel").pack(anchor="w")
        self.chunking_label = ttk.Label(
            info,
            text=(
                f"오디오 청크: {STREAM_CHUNK_SAMPLES} 샘플 "
                f"({self.detector.last_runtime_stats['chunk_ms']:.0f} ms) | "
                f"특징 갱신: 1 프레임 / {self.detector.last_runtime_stats['feature_step_ms']:.0f} ms | "
                f"분류 윈도우: {self.detector.last_runtime_stats['classifier_window_frames']} 프레임 "
                f"({self.detector.last_runtime_stats['classifier_window_ms']:.0f} ms)"
            ),
            style="Meta.TLabel",
        )
        self.chunking_label.pack(anchor="w")

        lamp_section = ttk.Frame(frame)
        lamp_section.pack(fill="x", pady=(0, 12))
        ttk.Label(lamp_section, text="감지 램프", style="Meta.TLabel").pack(anchor="w")
        lamp_body = ttk.Frame(lamp_section)
        lamp_body.pack(anchor="w", pady=(6, 0))
        self.lamp_canvas = tk.Canvas(
            lamp_body,
            width=96,
            height=96,
            background="#e5e7eb",
            highlightthickness=0,
        )
        self.lamp_canvas.pack(side="left")
        self.lamp_canvas.create_oval(10, 10, 86, 86, fill="#cbd5e1", outline="")
        lamp_text_frame = ttk.Frame(lamp_body)
        lamp_text_frame.pack(side="left", padx=(12, 0))
        self.lamp_status_label = ttk.Label(lamp_text_frame, text="꺼짐", style="Status.TLabel", foreground="#64748b")
        self.lamp_status_label.pack(anchor="w")
        ttk.Label(
            lamp_text_frame,
            text="감지되면 1초 동안 빨간 램프 유지",
            style="Meta.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        self.audio_gauge = GaugeBar(frame, "마이크 입력 레벨", "#38bdf8")
        self.audio_gauge.pack(fill="x", pady=(0, 12))

        self.score_gauge = GaugeBar(frame, "하이 포포 인식 점수", "#22c55e")
        self.score_gauge.pack(fill="x", pady=(0, 12))

        resource_frame = ttk.Frame(frame)
        resource_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(resource_frame, text="Jetson 리소스", style="Meta.TLabel").pack(anchor="w")
        self.resource_cpu_label = ttk.Label(resource_frame, text=self.resource_stats["cpu_text"], style="Meta.TLabel")
        self.resource_cpu_label.pack(anchor="w", pady=(6, 0))
        self.resource_ram_label = ttk.Label(resource_frame, text=self.resource_stats["ram_text"], style="Meta.TLabel")
        self.resource_ram_label.pack(anchor="w")
        self.resource_gpu_label = ttk.Label(resource_frame, text=self.resource_stats["gpu_text"], style="Meta.TLabel")
        self.resource_gpu_label.pack(anchor="w")
        self.resource_detail_label = ttk.Label(resource_frame, text=self.resource_stats["detail"], style="Meta.TLabel")
        self.resource_detail_label.pack(anchor="w")

        slider_frame = ttk.Frame(frame)
        slider_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(slider_frame, text="임계값", style="Meta.TLabel").pack(anchor="w")
        self.threshold_scale = ttk.Scale(
            slider_frame,
            from_=0.30,
            to=0.95,
            orient="horizontal",
            variable=self.threshold_var,
            command=self._on_threshold_changed,
        )
        self.threshold_scale.pack(fill="x")
        self.threshold_value_label = ttk.Label(slider_frame, text=f"{self.current_threshold:.2f}", style="Meta.TLabel")
        self.threshold_value_label.pack(anchor="e")

        gain_frame = ttk.Frame(frame)
        gain_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(gain_frame, text="마이크 입력 레벨 조절", style="Meta.TLabel").pack(anchor="w")
        self.input_gain_scale = ttk.Scale(
            gain_frame,
            from_=1.0,
            to=6.0,
            orient="horizontal",
            variable=self.input_gain_var,
            command=self._on_input_gain_changed,
        )
        self.input_gain_scale.pack(fill="x")
        self.input_gain_value_label = ttk.Label(
            gain_frame,
            text=f"{self.current_input_gain:.2f}x",
            style="Meta.TLabel",
        )
        self.input_gain_value_label.pack(anchor="e")

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill="x", pady=(10, 0))
        self.status_label = ttk.Label(status_frame, text="대기 중", style="Status.TLabel", foreground="#475569")
        self.status_label.pack(anchor="w")

        self.score_label = ttk.Label(status_frame, text="점수=0.0000", style="Meta.TLabel")
        self.score_label.pack(anchor="w", pady=(8, 0))
        self.last_detected_label = ttk.Label(status_frame, text="마지막 감지: -", style="Meta.TLabel")
        self.last_detected_label.pack(anchor="w")
        self.stream_label = ttk.Label(status_frame, text="오디오 스트림 상태: 정상", style="Meta.TLabel")
        self.stream_label.pack(anchor="w")
        self.onnx_timing_label = ttk.Label(
            status_frame,
            text="ONNX 시간(ms): 멜 0.00 (0) | 임베딩 0.00 (0) | 분류기 0.00 (0)",
            style="Meta.TLabel",
        )
        self.onnx_timing_label.pack(anchor="w")
        self.pipeline_timing_label = ttk.Label(
            status_frame,
            text="전체 처리 시간(ms): 0.00 | 이번 청크 생성 프레임: 0",
            style="Meta.TLabel",
        )
        self.pipeline_timing_label.pack(anchor="w")

    def _audio_callback(self, indata, _frames, _time_info, status):
        """
        기능:
        - 마이크 callback에서 받은 오디오 chunk를 worker queue에 넣는다.
        
        입력:
        - `indata`: sounddevice callback이 전달한 입력 오디오 버퍼.
        - `_frames`: callback에서 전달되는 frame 수 정보.
        - `_time_info`: callback 시점 정보.
        - `status`: audio stream 상태 정보.
        
        반환:
        - 없음.
        """
        if status:
            self.stream_status = str(status)

        chunk = indata[:, 0].copy()
        try:
            self.audio_queue.put_nowait(chunk)
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.audio_queue.put_nowait(chunk)
            except queue.Full:
                pass

    def _on_threshold_changed(self, value):
        """
        기능:
        - 임계값 슬라이더 변경을 메인 스레드 상태값과 라벨에 반영한다.

        입력:
        - `value`: Tkinter Scale이 전달한 현재 슬라이더 값 문자열.

        반환:
        - 없음.
        """
        self.current_threshold = float(value)
        self.threshold_value_label.configure(text=f"{self.current_threshold:.2f}")

    def _on_input_gain_changed(self, value):
        """
        기능:
        - 입력 증폭 슬라이더 변경을 메인 스레드 상태값과 라벨에 반영한다.

        입력:
        - `value`: Tkinter Scale이 전달한 현재 슬라이더 값 문자열.

        반환:
        - 없음.
        """
        self.current_input_gain = float(value)
        self.input_gain_value_label.configure(text=f"{self.current_input_gain:.2f}x")

    def _worker_loop(self):
        """
        기능:
        - 오디오 queue를 소비하며 실시간 추론 결과를 GUI queue로 전달한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        while not self.stop_event.is_set():
            try:
                chunk = self.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            input_gain = self.current_input_gain
            amplified_chunk = np.clip(chunk * input_gain, -1.0, 1.0)
            predictions = self.detector.process_audio(
                amplified_chunk,
                threshold=self.current_threshold,
            )
            if not predictions:
                continue

            latest = predictions[-1]
            update = {
                "score": latest.score,
                "audio_level": latest.audio_level,
                "threshold": latest.threshold,
                "detected": latest.detected,
                "timestamp": latest.timestamp,
                "stream_status": self.stream_status,
                "runtime_stats": dict(self.detector.last_runtime_stats),
            }

            try:
                self.gui_queue.put_nowait(update)
            except queue.Full:
                try:
                    self.gui_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.gui_queue.put_nowait(update)
                except queue.Full:
                    pass

    def _resource_loop(self):
        """
        기능:
        - tegrastats를 읽어 Jetson 리소스 상태 문자열을 주기적으로 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        try:
            self.resource_process = subprocess.Popen(
                ["tegrastats", "--interval", str(TEGRASTATS_INTERVAL_MS)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self.resource_stats = {
                "cpu_text": "CPU 평균: tegrastats 없음",
                "ram_text": "RAM: tegrastats 없음",
                "gpu_text": "GPU: tegrastats 없음",
                "detail": "CPU 코어: -",
            }
            return
        except Exception as exc:
            self.resource_stats = {
                "cpu_text": f"CPU 평균: tegrastats 실행 실패 ({type(exc).__name__})",
                "ram_text": "RAM: -",
                "gpu_text": "GPU: -",
                "detail": "CPU 코어: -",
            }
            return

        try:
            assert self.resource_process.stdout is not None
            for line in self.resource_process.stdout:
                if self.stop_event.is_set():
                    break
                self.resource_stats = parse_tegrastats_line(line)
        finally:
            if self.resource_process is not None and self.resource_process.poll() is None:
                self.resource_process.terminate()
            self.resource_process = None

    def _poll_gui_queue(self):
        """
        기능:
        - GUI queue의 결과를 읽어 화면 표시를 갱신한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        while True:
            try:
                update = self.gui_queue.get_nowait()
            except queue.Empty:
                break

            self.current_score = update["score"]
            self.current_audio_level = update["audio_level"]
            now = time.monotonic()
            current_threshold = self.current_threshold
            current_input_gain = self.current_input_gain
            if update["score"] >= current_threshold:
                if now >= self.held_peak_until:
                    self.held_peak_score = update["score"]
                else:
                    self.held_peak_score = max(self.held_peak_score, update["score"])
                self.held_peak_until = now + PEAK_SCORE_HOLD_SEC

            held_peak = None
            if now < self.held_peak_until:
                held_peak = self.held_peak_score
            else:
                self.held_peak_score = 0.0

            self.input_gain_value_label.configure(text=f"{current_input_gain:.2f}x")
            self.audio_gauge.update_value(update["audio_level"])
            self.score_gauge.update_value(
                update["score"],
                threshold=current_threshold,
                held_peak=held_peak,
            )
            if held_peak is not None:
                self.score_label.configure(
                    text=(
                        f"점수={update['score']:.4f} | 임계값={current_threshold:.2f} | "
                        f"3초 유지 최고점={held_peak:.4f}"
                    )
                )
            else:
                self.score_label.configure(text=f"점수={update['score']:.4f} | 임계값={current_threshold:.2f}")
            self.stream_label.configure(text=f"오디오 스트림 상태: {update['stream_status']}")
            runtime_stats = update["runtime_stats"]
            self.onnx_timing_label.configure(
                text=(
                    "ONNX 시간(ms): "
                    f"멜 {runtime_stats['melspectrogram_ms']:.2f} ({runtime_stats['melspectrogram_calls']}) | "
                    f"임베딩 {runtime_stats['embedding_ms']:.2f} ({runtime_stats['embedding_calls']}) | "
                    f"분류기 {runtime_stats['classifier_ms']:.2f} ({runtime_stats['classifier_calls']})"
                )
            )
            self.pipeline_timing_label.configure(
                text=(
                    f"전체 처리 시간(ms): {runtime_stats['total_ms']:.2f} | "
                    f"이번 청크 생성 프레임: {runtime_stats['feature_frames_emitted']}"
                )
            )

            if update["detected"]:
                self.current_status = "감지됨"
                self.last_detected_at = time.strftime("%H:%M:%S")
                self.detection_lamp_until = time.monotonic() + DETECTION_LAMP_HOLD_SEC
                self.status_label.configure(text="감지됨", foreground="#16a34a")
            else:
                self.current_status = "대기 중"
                self.status_label.configure(text="대기 중", foreground="#475569")

            self.last_detected_label.configure(text=f"마지막 감지: {self.last_detected_at}")

        if time.monotonic() < self.detection_lamp_until:
            self.lamp_canvas.delete("all")
            self.lamp_canvas.create_oval(10, 10, 86, 86, fill="#ef4444", outline="")
            self.lamp_status_label.configure(text="감지됨", foreground="#dc2626")
        else:
            self.lamp_canvas.delete("all")
            self.lamp_canvas.create_oval(10, 10, 86, 86, fill="#cbd5e1", outline="")
            self.lamp_status_label.configure(text="꺼짐", foreground="#64748b")

        resource_stats = dict(self.resource_stats)
        self.resource_cpu_label.configure(text=resource_stats["cpu_text"])
        self.resource_ram_label.configure(text=resource_stats["ram_text"])
        self.resource_gpu_label.configure(text=resource_stats["gpu_text"])
        self.resource_detail_label.configure(text=resource_stats["detail"])
        self.root.after(GUI_REFRESH_MS, self._poll_gui_queue)

    def run(self):
        """
        기능:
        - worker, 오디오 stream, GUI 이벤트 루프를 시작한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        self.worker_thread.start()
        self.resource_thread.start()
        self.stream.start()
        self.root.after(GUI_REFRESH_MS, self._poll_gui_queue)
        self.root.mainloop()

    def _close(self):
        """
        기능:
        - 오디오 stream과 GUI 자원을 정리하고 종료한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        self.stop_event.set()
        if self.resource_process is not None and self.resource_process.poll() is None:
            self.resource_process.terminate()
        try:
            self.stream.stop()
        finally:
            self.stream.close()
        self.root.destroy()


def main():
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    app = WakeWordGuiDemo(args)
    app.run()


if __name__ == "__main__":
    main()
