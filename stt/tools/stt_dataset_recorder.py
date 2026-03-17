"""
STT 고정 문장 데이터셋 녹음 GUI.

50개 기준 문장을 순서대로 읽으면서 같은 파일명의 wav를 저장한다.
"""

import argparse
from pathlib import Path
import wave

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk


SAMPLE_RATE = 16000
STT_ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    """
    기능:
    - STT 녹음 GUI 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=STT_ROOT / "datasets" / "korean_eval_50",
        help="기준 txt와 녹음 wav를 같이 둘 데이터셋 디렉토리",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="입력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--output-device",
        default=None,
        help="재생 장치 index 또는 이름",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="시작할 문장 번호(1부터 시작)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="오디오 장치 목록만 출력하고 종료",
    )
    return parser.parse_args()


def print_devices():
    """
    기능:
    - 현재 사용할 수 있는 오디오 장치 목록을 출력한다.

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
    - 입력 장치 인자를 sounddevice가 사용할 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 입력 장치 인자.

    반환:
    - 실제 실행에 사용할 입력 장치 값을 반환한다.
    """
    if device_arg is not None:
        if str(device_arg).isdigit():
            return int(device_arg)
        return device_arg

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        raise RuntimeError("기본 입력 마이크가 설정되어 있지 않습니다.")
    return int(default_input)


def resolve_output_device(device_arg):
    """
    기능:
    - 출력 장치 인자를 sounddevice가 사용할 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 출력 장치 인자.

    반환:
    - 실제 실행에 사용할 출력 장치 값을 반환한다.
    """
    if device_arg is not None:
        if str(device_arg).isdigit():
            return int(device_arg)
        return device_arg

    default_output = sd.default.device[1]
    if default_output is None or default_output < 0:
        return None
    return int(default_output)


def list_prompt_files(dataset_dir):
    """
    기능:
    - 데이터셋 디렉토리에서 기준 문장 txt 파일 목록을 번호 순으로 읽는다.

    입력:
    - `dataset_dir`: 기준 txt 파일들이 들어 있는 디렉토리.

    반환:
    - 정렬된 txt 파일 경로 목록을 반환한다.
    """
    prompt_files = []
    for txt_path in sorted(dataset_dir.glob("*.txt")):
        if txt_path.stem.isdigit():
            prompt_files.append(txt_path)
    if not prompt_files:
        raise RuntimeError("데이터셋 디렉토리에 번호형 txt 파일이 없습니다.")
    return prompt_files


def read_text_file(text_path):
    """
    기능:
    - 기준 문장 txt 파일의 내용을 읽는다.

    입력:
    - `text_path`: 읽을 txt 파일 경로.

    반환:
    - 파일 내용을 문자열로 반환한다.
    """
    return text_path.read_text(encoding="utf-8").strip()


def read_wav_file(wav_path):
    """
    기능:
    - PCM16 mono 16kHz wav 파일을 float32 배열로 읽는다.

    입력:
    - `wav_path`: 읽을 wav 파일 경로.

    반환:
    - float32 mono 오디오 배열을 반환한다.
    """
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    if channels != 1:
        raise ValueError("wav 파일은 mono여야 합니다.")
    if sample_rate != SAMPLE_RATE:
        raise ValueError("wav 파일은 16kHz여야 합니다.")
    if sample_width != 2:
        raise ValueError("wav 파일은 PCM16이어야 합니다.")

    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return np.clip(audio, -1.0, 1.0)


def write_wav_file(wav_path, audio):
    """
    기능:
    - float32 mono 오디오 배열을 PCM16 mono 16kHz wav로 저장한다.

    입력:
    - `wav_path`: 저장할 wav 파일 경로.
    - `audio`: 저장할 float32 mono 오디오 배열.

    반환:
    - 없음.
    """
    pcm16 = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm16 * 32767.0).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm16.tobytes())


class STTDatasetRecorderApp:
    def __init__(self, root, dataset_dir, input_device, output_device, start_index):
        """
        기능:
        - 고정 문장 녹음 GUI의 상태와 위젯을 초기화한다.

        입력:
        - `root`: Tk 루트 객체.
        - `dataset_dir`: 기준 txt와 wav를 함께 둘 디렉토리.
        - `input_device`: 사용할 입력 장치.
        - `output_device`: 사용할 출력 장치.
        - `start_index`: 처음 열 문장 번호.

        반환:
        - 없음.
        """
        self.root = root
        self.dataset_dir = dataset_dir
        self.input_device = input_device
        self.output_device = output_device
        self.prompt_files = list_prompt_files(dataset_dir)
        self.current_index = max(0, min(len(self.prompt_files) - 1, start_index - 1))

        self.input_stream = None
        self.recorded_chunks = []
        self.current_audio = None
        self.current_level = 0.0
        self.is_recording = False

        self.progress_var = tk.StringVar()
        self.prompt_var = tk.StringVar()
        self.file_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.saved_var = tk.StringVar()
        self.duration_var = tk.StringVar()
        self.level_var = tk.DoubleVar(value=0.0)

        self._build_ui()
        self._load_prompt(self.current_index)
        self._update_level_loop()

    def _build_ui(self):
        """
        기능:
        - 녹음용 GUI 위젯을 배치한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.root.title("STT 데이터셋 녹음기")
        self.root.geometry("900x520")
        self.root.configure(bg="#f4f4f1")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f4f4f1")
        style.configure("TLabel", background="#f4f4f1", foreground="#1f2a2e")
        style.configure("Title.TLabel", font=("Malgun Gothic", 16, "bold"))
        style.configure("Info.TLabel", font=("Malgun Gothic", 11))
        style.configure("Prompt.TLabel", font=("Malgun Gothic", 18, "bold"))
        style.configure("TButton", font=("Malgun Gothic", 11), padding=10)
        style.configure("Level.Horizontal.TProgressbar", troughcolor="#d7ddd6", background="#d54e4e")

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        header_label = ttk.Label(main_frame, text="한국어 STT 평가용 50문장 녹음", style="Title.TLabel")
        header_label.pack(anchor="w")

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(12, 8))

        ttk.Label(info_frame, textvariable=self.progress_var, style="Info.TLabel").pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.file_var, style="Info.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(info_frame, textvariable=self.saved_var, style="Info.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(info_frame, textvariable=self.duration_var, style="Info.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(info_frame, textvariable=self.status_var, style="Info.TLabel").pack(anchor="w", pady=(4, 0))

        prompt_frame = ttk.Frame(main_frame, padding=20)
        prompt_frame.pack(fill="both", expand=True, pady=(8, 12))

        prompt_title = ttk.Label(prompt_frame, text="읽을 문장", style="Info.TLabel")
        prompt_title.pack(anchor="w")

        prompt_label = ttk.Label(
            prompt_frame,
            textvariable=self.prompt_var,
            style="Prompt.TLabel",
            wraplength=820,
            justify="left",
        )
        prompt_label.pack(anchor="w", pady=(16, 0))

        level_frame = ttk.Frame(main_frame)
        level_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(level_frame, text="입력 레벨", style="Info.TLabel").pack(anchor="w")
        level_bar = ttk.Progressbar(
            level_frame,
            variable=self.level_var,
            maximum=100.0,
            style="Level.Horizontal.TProgressbar",
        )
        level_bar.pack(fill="x", pady=(8, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="이전 문장", command=self._go_prev).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="다음 문장", command=self._go_next).pack(side="left", padx=(0, 20))
        ttk.Button(button_frame, text="녹음 시작", command=self._start_recording).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="녹음 정지", command=self._stop_recording).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="들어보기", command=self._play_audio).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="재시도", command=self._retry_recording).pack(side="left", padx=(0, 8))
        ttk.Button(button_frame, text="녹음 완료", command=self._complete_recording).pack(side="left")

    def _load_prompt(self, index):
        """
        기능:
        - 현재 문장을 불러오고 저장 상태와 기존 녹음 여부를 갱신한다.

        입력:
        - `index`: 불러올 문장 인덱스.

        반환:
        - 없음.
        """
        self.current_index = index
        self.recorded_chunks = []
        self.current_level = 0.0
        self.level_var.set(0.0)

        prompt_path = self.prompt_files[self.current_index]
        wav_path = prompt_path.with_suffix(".wav")
        self.prompt_var.set(read_text_file(prompt_path))
        self.file_var.set(f"기준 파일: {prompt_path.name} | 녹음 파일: {wav_path.name}")

        if wav_path.exists():
            self.current_audio = read_wav_file(wav_path)
            self.saved_var.set("저장 상태: 기존 녹음 있음")
            self.duration_var.set(f"녹음 길이: {self._audio_duration_text(self.current_audio)}")
        else:
            self.current_audio = None
            self.saved_var.set("저장 상태: 아직 녹음 없음")
            self.duration_var.set("녹음 길이: -")

        self.status_var.set("상태: 대기 중")
        self.progress_var.set(self._build_progress_text())

    def _build_progress_text(self):
        """
        기능:
        - 현재 문장 번호와 완료 개수를 문자열로 만든다.

        입력:
        - 없음.

        반환:
        - 진행 상태 문자열을 반환한다.
        """
        total_count = len(self.prompt_files)
        completed_count = 0
        for prompt_path in self.prompt_files:
            if prompt_path.with_suffix(".wav").exists():
                completed_count += 1
        return f"진행: {self.current_index + 1} / {total_count} | 완료: {completed_count} / {total_count}"

    def _audio_duration_text(self, audio):
        """
        기능:
        - 오디오 배열 길이를 초 단위 문자열로 바꾼다.

        입력:
        - `audio`: float32 mono 오디오 배열.

        반환:
        - 사람이 읽기 쉬운 길이 문자열을 반환한다.
        """
        duration_sec = float(len(audio)) / float(SAMPLE_RATE)
        return f"{duration_sec:.2f}초"

    def _update_level_loop(self):
        """
        기능:
        - 현재 입력 레벨을 주기적으로 GUI에 반영한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.level_var.set(min(self.current_level * 220.0, 100.0))
        if not self.is_recording:
            self.level_var.set(0.0)
        self.root.after(50, self._update_level_loop)

    def _audio_callback(self, indata, frames, time_info, status):
        """
        기능:
        - 실시간 마이크 입력을 수집하고 현재 입력 레벨을 계산한다.

        입력:
        - `indata`: 입력 오디오 버퍼.
        - `frames`: 현재 프레임 개수.
        - `time_info`: sounddevice 시간 정보.
        - `status`: 콜백 상태 정보.

        반환:
        - 없음.
        """
        del frames
        del time_info
        del status
        mono = np.asarray(indata[:, 0], dtype=np.float32).copy()
        self.recorded_chunks.append(mono)
        if mono.size:
            self.current_level = float(np.sqrt(np.mean(np.square(mono))))

    def _start_recording(self):
        """
        기능:
        - 현재 문장에 대한 새 녹음을 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            return

        self.current_audio = None
        self.recorded_chunks = []
        self.current_level = 0.0
        self.input_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=self.input_device,
            callback=self._audio_callback,
        )
        self.input_stream.start()
        self.is_recording = True
        self.saved_var.set("저장 상태: 새 녹음 진행 중")
        self.duration_var.set("녹음 길이: 녹음 중")
        self.status_var.set("상태: 녹음 중")

    def _stop_recording(self):
        """
        기능:
        - 현재 진행 중인 녹음을 멈추고 메모리 오디오로 확정한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if not self.is_recording:
            return

        self.input_stream.stop()
        self.input_stream.close()
        self.input_stream = None
        self.is_recording = False

        if self.recorded_chunks:
            self.current_audio = np.concatenate(self.recorded_chunks).astype(np.float32)
            self.duration_var.set(f"녹음 길이: {self._audio_duration_text(self.current_audio)}")
            self.saved_var.set("저장 상태: 메모리에서 확인 중, 아직 저장 전")
            self.status_var.set("상태: 녹음 정지")
        else:
            self.current_audio = None
            self.duration_var.set("녹음 길이: -")
            self.saved_var.set("저장 상태: 녹음 데이터 없음")
            self.status_var.set("상태: 녹음 데이터 없음")

    def _play_audio(self):
        """
        기능:
        - 현재 메모리 오디오 또는 이미 저장된 wav를 재생한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            return

        audio = self.current_audio
        if audio is None:
            wav_path = self.prompt_files[self.current_index].with_suffix(".wav")
            if wav_path.exists():
                audio = read_wav_file(wav_path)
                self.current_audio = audio

        if audio is None or not len(audio):
            self.status_var.set("상태: 재생할 녹음이 없음")
            return

        sd.play(audio, SAMPLE_RATE, device=self.output_device)
        self.status_var.set("상태: 녹음 재생 중")

    def _retry_recording(self):
        """
        기능:
        - 현재 메모리 녹음을 버리고 같은 문장을 다시 녹음할 수 있게 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            self._stop_recording()

        self.current_audio = None
        self.recorded_chunks = []
        self.current_level = 0.0
        self.saved_var.set("저장 상태: 새로 다시 녹음 가능")
        self.duration_var.set("녹음 길이: -")
        self.status_var.set("상태: 재시도 준비")

    def _complete_recording(self):
        """
        기능:
        - 현재 메모리 녹음을 wav로 저장하고 다음 문장으로 자동 이동한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            self._stop_recording()

        if self.current_audio is None or not len(self.current_audio):
            self.status_var.set("상태: 저장할 녹음이 없음")
            return

        wav_path = self.prompt_files[self.current_index].with_suffix(".wav")
        write_wav_file(wav_path, self.current_audio)
        self.saved_var.set("저장 상태: 저장 완료")
        self.status_var.set(f"상태: {wav_path.name} 저장 완료")
        self.progress_var.set(self._build_progress_text())

        if self.current_index < len(self.prompt_files) - 1:
            self.root.after(250, self._go_next)

    def _go_prev(self):
        """
        기능:
        - 이전 문장으로 이동한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            return
        if self.current_index <= 0:
            return
        self._load_prompt(self.current_index - 1)

    def _go_next(self):
        """
        기능:
        - 다음 문장으로 이동한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.is_recording:
            return
        if self.current_index >= len(self.prompt_files) - 1:
            self.status_var.set("상태: 마지막 문장까지 완료")
            return
        self._load_prompt(self.current_index + 1)


def main():
    """
    기능:
    - STT 평가용 문장 녹음 GUI를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    dataset_dir = args.dataset_dir.resolve()
    input_device = resolve_input_device(args.input_device)
    output_device = resolve_output_device(args.output_device)

    root = tk.Tk()
    STTDatasetRecorderApp(
        root=root,
        dataset_dir=dataset_dir,
        input_device=input_device,
        output_device=output_device,
        start_index=args.start_index,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
