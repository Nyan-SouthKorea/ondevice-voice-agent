"""
Jetson용 실시간 VAD GUI demo.

기능:
- 기본 입력 마이크 사용
- 실시간 음성 여부 표시
- 실시간 입력 레벨 표시
- 실시간 confidence 표시
- threshold 슬라이더로 현장 튜닝

예시:
source /home/everybot/workspace/ondevice-voice-agent/project/env/wake_word_jetson/bin/activate
python vad/vad_gui_demo.py
"""

import argparse
import queue
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

from vad import VADDetector


GUI_REFRESH_MS = 50
GAUGE_WIDTH = 560
GAUGE_HEIGHT = 26


def parse_args():
    """
    기능:
    - VAD GUI demo 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["webrtcvad", "silero"],
        default="silero",
        help="사용할 VAD 백엔드",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Silero ONNX 모델 경로",
    )
    parser.add_argument(
        "--mode",
        type=int,
        default=2,
        help="webrtcvad 공격성 모드(0~3)",
    )
    parser.add_argument(
        "--speech-threshold",
        type=float,
        default=0.5,
        help="Silero speech 판정 기준값",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="입력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--min-speech-frames",
        type=int,
        default=3,
        help="True 전환 전 필요한 연속 speech frame 수",
    )
    parser.add_argument(
        "--min-silence-frames",
        type=int,
        default=10,
        help="False 전환 전 필요한 연속 silence frame 수",
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
    - 현재 시스템에서 사용할 수 있는 오디오 장치 목록을 출력한다.

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
    - `device`: 실행에 사용할 장치 또는 장치 식별자.

    반환:
    - 문자열 결과를 반환한다.
    """
    info = sd.query_devices(device, "input")
    return (
        f"{info['name']} | sr={int(info['default_samplerate'])}Hz | "
        f"input_channels={info['max_input_channels']}"
    )


def compute_audio_level(audio_chunk):
    """
    기능:
    - 현재 오디오 청크의 마이크 입력 레벨을 RMS 기준으로 계산한다.

    입력:
    - `audio_chunk`: float32 mono 오디오 청크.

    반환:
    - 0.0~1.0 범위의 입력 레벨 값을 반환한다.
    """
    audio = np.asarray(audio_chunk, dtype=np.float32)
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


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

    def update_value(self, value, threshold=None):
        """
        기능:
        - 게이지 막대와 표시 값을 현재 상태에 맞게 갱신한다.

        입력:
        - `value`: 게이지에 표시할 현재 값.
        - `threshold`: 기준값. `None`이면 표시하지 않는다.

        반환:
        - 없음.
        """
        clamped = max(0.0, min(1.0, value))
        width = int(GAUGE_WIDTH * clamped)

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, GAUGE_WIDTH, GAUGE_HEIGHT, fill="#1f2937", outline="")
        self.canvas.create_rectangle(0, 0, width, GAUGE_HEIGHT, fill=self.color, outline="")
        if threshold is not None:
            x = int(GAUGE_WIDTH * max(0.0, min(1.0, threshold)))
            self.canvas.create_line(x, 0, x, GAUGE_HEIGHT, fill="#f8fafc", width=2)
        self.value_label.configure(text=f"{clamped * 100.0:5.1f}%")


class VadGuiDemo:
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
        self.input_device = resolve_input_device(args.input_device)
        self.detector = VADDetector(
            model=args.model,
            model_path=args.model_path,
            mode=args.mode,
            speech_threshold=args.speech_threshold,
            min_speech_frames=args.min_speech_frames,
            min_silence_frames=args.min_silence_frames,
        )
        self.input_device_label = describe_input_device(self.input_device)

        self.root = tk.Tk()
        self.root.title("VAD 실시간 데모")
        self.root.geometry("820x760")
        self.root.minsize(760, 700)
        self.root.configure(background="#e5e7eb")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.threshold_var = tk.DoubleVar(value=args.speech_threshold)
        self.current_threshold = float(args.speech_threshold)
        self.current_audio_level = 0.0
        self.current_score = 0.0
        self.current_status = False
        self.last_status_text = "대기 중"
        self.stream_status = "정상"

        self.audio_queue = queue.Queue(maxsize=8)
        self.gui_queue = queue.Queue(maxsize=32)
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)

        self._build_ui()

        self.stream = sd.InputStream(
            samplerate=self.detector.sample_rate,
            blocksize=self.detector.chunk_samples,
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

        ttk.Label(frame, text="VAD 실시간 데모", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Jetson 마이크 실시간 음성 구간 감지", style="Meta.TLabel").pack(anchor="w", pady=(0, 14))

        info = ttk.Frame(frame)
        info.pack(fill="x", pady=(0, 12))
        ttk.Label(info, text=f"입력 장치: {self.input_device_label}", style="Meta.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"백엔드: {self.detector.model}", style="Meta.TLabel").pack(anchor="w")
        ttk.Label(
            info,
            text=(
                f"오디오 청크: {self.detector.chunk_samples} 샘플 | "
                f"speech filter: {self.detector.min_speech_frames} | "
                f"silence filter: {self.detector.min_silence_frames}"
            ),
            style="Meta.TLabel",
        ).pack(anchor="w")

        lamp_section = ttk.Frame(frame)
        lamp_section.pack(fill="x", pady=(0, 16))
        ttk.Label(lamp_section, text="음성 감지 상태", style="Meta.TLabel").pack(anchor="w")
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
        self.lamp_status_label = ttk.Label(
            lamp_text_frame,
            text="대기 중",
            style="Status.TLabel",
            foreground="#64748b",
        )
        self.lamp_status_label.pack(anchor="w")
        self.lamp_detail_label = ttk.Label(
            lamp_text_frame,
            text="말하는 중 아님",
            style="Meta.TLabel",
        )
        self.lamp_detail_label.pack(anchor="w", pady=(6, 0))

        self.audio_gauge = GaugeBar(frame, "마이크 입력 레벨", "#38bdf8")
        self.audio_gauge.pack(fill="x", pady=(0, 12))

        confidence_title = "음성 confidence" if self.detector.model == "silero" else "음성 비율"
        self.confidence_gauge = GaugeBar(frame, confidence_title, "#ef4444")
        self.confidence_gauge.pack(fill="x", pady=(0, 12))

        slider_frame = ttk.Frame(frame)
        slider_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(slider_frame, text="Threshold", style="Meta.TLabel").pack(anchor="w")
        self.threshold_scale = ttk.Scale(
            slider_frame,
            from_=0.10,
            to=0.95,
            orient="horizontal",
            variable=self.threshold_var,
            command=self._on_threshold_changed,
        )
        self.threshold_scale.pack(fill="x")
        self.threshold_value_label = ttk.Label(slider_frame, text=f"{self.current_threshold:.2f}", style="Meta.TLabel")
        self.threshold_value_label.pack(anchor="e")
        if self.detector.model != "silero":
            self.threshold_scale.state(["disabled"])

        status_frame = ttk.Frame(frame)
        status_frame.pack(fill="x", pady=(12, 0))
        self.status_label = ttk.Label(status_frame, text="대기 중", style="Status.TLabel", foreground="#475569")
        self.status_label.pack(anchor="w")
        self.confidence_label = ttk.Label(status_frame, text="conf=0.0000", style="Meta.TLabel")
        self.confidence_label.pack(anchor="w", pady=(8, 0))
        self.raw_status_label = ttk.Label(status_frame, text="raw_status=False", style="Meta.TLabel")
        self.raw_status_label.pack(anchor="w")
        self.threshold_status_label = ttk.Label(
            status_frame,
            text="threshold=0.50",
            style="Meta.TLabel",
        )
        self.threshold_status_label.pack(anchor="w")
        self.stream_label = ttk.Label(status_frame, text="오디오 스트림 상태: 정상", style="Meta.TLabel")
        self.stream_label.pack(anchor="w")

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
        - threshold 슬라이더 변경을 메인 스레드 상태값과 라벨에 반영한다.

        입력:
        - `value`: Tkinter Scale이 전달한 현재 슬라이더 값 문자열.

        반환:
        - 없음.
        """
        self.current_threshold = float(value)
        self.threshold_value_label.configure(text=f"{self.current_threshold:.2f}")

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

            if hasattr(self.detector.backend, "speech_threshold"):
                self.detector.backend.speech_threshold = self.current_threshold

            audio_level = compute_audio_level(chunk)
            status = self.detector.infer(chunk)
            update = {
                "status": bool(status),
                "raw_status": bool(self.detector.raw_status),
                "score": float(self.detector.last_score),
                "audio_level": float(audio_level),
                "threshold": float(self.current_threshold),
                "stream_status": self.stream_status,
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

            self.current_audio_level = update["audio_level"]
            self.current_score = update["score"]
            self.current_status = update["status"]
            self.audio_gauge.update_value(update["audio_level"])

            threshold = update["threshold"] if self.detector.model == "silero" else None
            self.confidence_gauge.update_value(update["score"], threshold=threshold)

            score_key = "conf" if self.detector.model == "silero" else "voiced_ratio"
            self.confidence_label.configure(text=f"{score_key}={update['score']:.4f}")
            self.raw_status_label.configure(text=f"raw_status={update['raw_status']}")
            if self.detector.model == "silero":
                self.threshold_status_label.configure(text=f"threshold={update['threshold']:.2f}")
            else:
                self.threshold_status_label.configure(text="threshold=webrtcvad 미사용")
            self.stream_label.configure(text=f"오디오 스트림 상태: {update['stream_status']}")

            if update["status"]:
                self.last_status_text = "말하는 중"
                self.status_label.configure(text="말하는 중", foreground="#dc2626")
                self.lamp_status_label.configure(text="말하는 중", foreground="#dc2626")
                self.lamp_detail_label.configure(text="음성 감지됨")
                self.lamp_canvas.delete("all")
                self.lamp_canvas.create_oval(10, 10, 86, 86, fill="#ef4444", outline="")
            else:
                self.last_status_text = "대기 중"
                self.status_label.configure(text="대기 중", foreground="#475569")
                self.lamp_status_label.configure(text="대기 중", foreground="#64748b")
                self.lamp_detail_label.configure(text="말하는 중 아님")
                self.lamp_canvas.delete("all")
                self.lamp_canvas.create_oval(10, 10, 86, 86, fill="#cbd5e1", outline="")

        self.root.after(GUI_REFRESH_MS, self._poll_gui_queue)

    def _close(self):
        """
        기능:
        - 오디오 스트림과 worker를 정리하고 창을 종료한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.stop_event.set()
        try:
            self.stream.stop()
        except Exception:
            pass
        try:
            self.stream.close()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        """
        기능:
        - 오디오 스트림과 worker를 시작하고 Tkinter mainloop를 실행한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.stream.start()
        self.worker_thread.start()
        self.root.after(GUI_REFRESH_MS, self._poll_gui_queue)
        self.root.mainloop()


def main():
    """
    기능:
    - 명령행 인자를 읽고 VAD GUI demo를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    demo = VadGuiDemo(args)
    demo.run()


if __name__ == "__main__":
    main()
