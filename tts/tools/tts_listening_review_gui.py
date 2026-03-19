"""
TTS listening review GUI.

benchmark listening sample을 Jetson에서 직접 듣고 점수를 남기기 위한 GUI다.
"""

import argparse
import csv
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk

import sounddevice as sd
import soundfile as sf


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent
A100_WORKSPACE_ROOT = Path("/data2/iena/260318_ondevice-voice-agent")
DEFAULT_REVIEW_ROOT = (
    WORKSPACE_ROOT
    / "results"
    / "tts"
    / "benchmark_full_v1_20260318"
    / "listening_review_20260319"
)

COMMON_FIELDS = ["language", "order", "prompt_id", "category", "text"]
SCORE_SUFFIXES = [
    "_audio_path",
    "_overall_10",
    "_naturalness_10",
    "_voice_appeal_10",
    "_pronunciation_10",
    "_notes",
]
MODEL_LABELS = {
    "melotts_ko": "MeloTTS (KO)",
    "openvoice_v2_ko": "OpenVoice V2 (KO)",
    "edge_tts_ko": "Edge TTS (KO)",
    "openai_api_ko": "OpenAI API TTS (KO)",
    "melotts_en": "MeloTTS (EN)",
    "openvoice_v2_en": "OpenVoice V2 (EN)",
    "piper_en": "Piper (EN)",
    "kokoro_en": "Kokoro (EN)",
    "edge_tts_en": "Edge TTS (EN)",
    "openai_api_en": "OpenAI API TTS (EN)",
}


def parse_args():
    """
    기능:
    - GUI 실행 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--review-root",
        type=Path,
        default=DEFAULT_REVIEW_ROOT,
        help="listening review pack 루트 경로",
    )
    parser.add_argument(
        "--output-device",
        default=None,
        help="출력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--start-language",
        default="ko",
        choices=["ko", "en"],
        help="시작 언어 탭",
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
    - 현재 오디오 출력 장치를 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    print("default_device", sd.default.device)
    for index, device in enumerate(sd.query_devices()):
        if device["max_output_channels"] > 0:
            print(
                f"[{index}] {device['name']} | "
                f"out={device['max_output_channels']} | "
                f"default_sr={int(device['default_samplerate'])}"
            )


def resolve_output_device(device_arg):
    """
    기능:
    - 출력 장치 인자를 sounddevice용 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 장치 인자.

    반환:
    - 장치 index 또는 이름을 반환한다.
    """
    if device_arg is not None:
        if str(device_arg).isdigit():
            return int(device_arg)
        return device_arg
    default_output = sd.default.device[1]
    if default_output is None or default_output < 0:
        return None
    return int(default_output)


def load_grouped_sheet(sheet_path):
    """
    기능:
    - grouped score sheet TSV를 읽는다.

    입력:
    - `sheet_path`: TSV 파일 경로.

    반환:
    - `(fieldnames, rows, model_keys)`를 반환한다.
    """
    with sheet_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    model_keys = []
    for field in fieldnames:
        if field.endswith("_audio_path"):
            model_keys.append(field[: -len("_audio_path")])
    return fieldnames, rows, model_keys


def save_grouped_sheet(sheet_path, fieldnames, rows):
    """
    기능:
    - grouped score sheet TSV를 저장한다.

    입력:
    - `sheet_path`: 저장할 TSV 경로.
    - `fieldnames`: 컬럼 목록.
    - `rows`: 저장할 행 목록.

    반환:
    - 없음.
    """
    with sheet_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def remap_audio_path(audio_path):
    """
    기능:
    - 저장된 절대경로를 현재 워크스페이스 경로로 보정한다.

    입력:
    - `audio_path`: 원본 오디오 경로 문자열.

    반환:
    - 현재 장비에서 실제로 열 수 있는 경로 문자열을 반환한다.
    """
    path = Path(audio_path)
    if path.is_file():
        return str(path)

    try:
        relative = path.relative_to(A100_WORKSPACE_ROOT)
    except ValueError:
        return str(path)

    remapped = WORKSPACE_ROOT / relative
    if remapped.is_file():
        return str(remapped)
    return str(path)


class ListeningReviewApp:
    def __init__(self, args):
        """
        기능:
        - listening review GUI를 초기화한다.

        입력:
        - `args`: 실행 인자 객체.

        반환:
        - 없음.
        """
        self.args = args
        self.review_root = args.review_root.resolve()
        self.sheet_paths = {
            "ko": self.review_root / "ko_grouped_score_sheet.tsv",
            "en": self.review_root / "en_grouped_score_sheet.tsv",
        }
        self.flat_export_path = self.review_root / "human_scores_flat.tsv"
        self.output_device = resolve_output_device(args.output_device)
        self.play_thread = None
        self.playback_lock = threading.Lock()
        self.current_language = args.start_language
        self.current_index = {"ko": 0, "en": 0}
        self.output_devices = []

        self.sheet_data = {}
        for language, sheet_path in self.sheet_paths.items():
            fieldnames, rows, model_keys = load_grouped_sheet(sheet_path)
            for row in rows:
                for model_key in model_keys:
                    audio_field = f"{model_key}_audio_path"
                    row[audio_field] = remap_audio_path(row[audio_field])
            self.sheet_data[language] = {
                "path": sheet_path,
                "fieldnames": fieldnames,
                "rows": rows,
                "model_keys": model_keys,
            }

        self.root = tk.Tk()
        self.root.title("TTS Listening Review")
        self.root.geometry("1380x920")
        self.root.minsize(1220, 820)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.language_var = tk.StringVar(value=self.current_language)
        self.prompt_meta_var = tk.StringVar(value="-")
        self.text_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="준비")
        self.output_device_var = tk.StringVar(value="")
        self.playing_var = tk.StringVar(value="재생 중인 파일 없음")

        self.model_widgets = {}

        self._build_ui()
        self._refresh_output_devices()
        self._render_current_prompt()

    def _build_ui(self):
        """
        기능:
        - GUI 위젯을 배치한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        root_frame = ttk.Frame(self.root, padding=16)
        root_frame.pack(fill="both", expand=True)

        title = ttk.Label(
            root_frame,
            text="TTS Listening Review",
            font=("Helvetica", 20, "bold"),
        )
        title.pack(anchor="w")

        top_bar = ttk.Frame(root_frame)
        top_bar.pack(fill="x", pady=(12, 10))

        ttk.Label(top_bar, text="언어").pack(side="left")
        for language, label in [("ko", "한국어"), ("en", "영어")]:
            ttk.Radiobutton(
                top_bar,
                text=label,
                value=language,
                variable=self.language_var,
                command=self._on_language_changed,
            ).pack(side="left", padx=(8, 6))

        ttk.Separator(top_bar, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Button(top_bar, text="이전", command=self._go_prev_prompt).pack(side="left")
        ttk.Button(top_bar, text="다음", command=self._go_next_prompt).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(top_bar, text="저장", command=self._save_current_state).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(top_bar, text="정지", command=self._stop_audio).pack(
            side="left", padx=(6, 0)
        )

        ttk.Separator(top_bar, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Label(top_bar, text="출력 장치").pack(side="left")
        self.output_device_combo = ttk.Combobox(top_bar, state="readonly", width=52)
        self.output_device_combo.pack(side="left", padx=(8, 6))
        self.output_device_combo.bind("<<ComboboxSelected>>", self._on_output_device_changed)
        ttk.Button(top_bar, text="새로고침", command=self._refresh_output_devices).pack(
            side="left"
        )

        meta_frame = ttk.LabelFrame(root_frame, text="현재 문장", padding=12)
        meta_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(meta_frame, textvariable=self.prompt_meta_var).pack(anchor="w")
        ttk.Label(
            meta_frame,
            textvariable=self.text_var,
            wraplength=1280,
            font=("Helvetica", 14),
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        playing_frame = ttk.Frame(root_frame)
        playing_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(playing_frame, textvariable=self.playing_var).pack(anchor="w")

        self.canvas = tk.Canvas(root_frame, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, side="left")
        scroll = ttk.Scrollbar(root_frame, orient="vertical", command=self.canvas.yview)
        scroll.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scroll.set)

        self.cards_frame = ttk.Frame(self.canvas)
        self.cards_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")

        status_frame = ttk.Frame(root_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor="w")

    def _refresh_output_devices(self):
        """
        기능:
        - 출력 장치 목록을 다시 읽어 콤보박스를 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.output_devices = []
        labels = []
        default_output = sd.default.device[1]
        selected_index = None
        for index, device in enumerate(sd.query_devices()):
            if device["max_output_channels"] <= 0:
                continue
            label = f"[{index}] {device['name']} | sr={int(device['default_samplerate'])}"
            self.output_devices.append((index, label))
            labels.append(label)
            if self.output_device == index:
                selected_index = len(labels) - 1
            elif self.output_device is None and default_output == index:
                self.output_device = index
                selected_index = len(labels) - 1

        self.output_device_combo["values"] = labels
        if selected_index is not None:
            self.output_device_combo.current(selected_index)
            self.output_device_var.set(labels[selected_index])
        elif labels:
            self.output_device_combo.current(0)
            self.output_device = self.output_devices[0][0]
            self.output_device_var.set(labels[0])
        self.status_var.set(
            f"출력 장치 준비 완료: {self.output_device if self.output_device is not None else '기본값 없음'}"
        )

    def _on_output_device_changed(self, _event):
        """
        기능:
        - 출력 장치 변경 이벤트를 처리한다.

        입력:
        - `_event`: Tk 이벤트 객체.

        반환:
        - 없음.
        """
        current = self.output_device_combo.current()
        if current < 0:
            return
        self.output_device = self.output_devices[current][0]
        self.status_var.set(f"출력 장치를 {self.output_device}로 변경했습니다.")

    def _on_language_changed(self):
        """
        기능:
        - 언어 탭 변경을 처리한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._capture_ui_to_row()
        self.current_language = self.language_var.get()
        self._render_current_prompt()

    def _go_prev_prompt(self):
        """
        기능:
        - 이전 prompt로 이동한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._capture_ui_to_row()
        if self.current_index[self.current_language] > 0:
            self.current_index[self.current_language] -= 1
        self._render_current_prompt()

    def _go_next_prompt(self):
        """
        기능:
        - 다음 prompt로 이동한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._capture_ui_to_row()
        max_index = len(self.sheet_data[self.current_language]["rows"]) - 1
        if self.current_index[self.current_language] < max_index:
            self.current_index[self.current_language] += 1
        self._render_current_prompt()

    def _current_row(self):
        """
        기능:
        - 현재 언어/인덱스의 행을 반환한다.

        입력:
        - 없음.

        반환:
        - 현재 row dict를 반환한다.
        """
        return self.sheet_data[self.current_language]["rows"][
            self.current_index[self.current_language]
        ]

    def _render_current_prompt(self):
        """
        기능:
        - 현재 선택된 prompt와 모델 카드들을 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        row = self._current_row()
        total = len(self.sheet_data[self.current_language]["rows"])
        self.prompt_meta_var.set(
            f"{self.current_language.upper()} | "
            f"{self.current_index[self.current_language] + 1}/{total} | "
            f"{row['prompt_id']} | {row['category']}"
        )
        self.text_var.set(row["text"])

        for child in self.cards_frame.winfo_children():
            child.destroy()
        self.model_widgets.clear()

        model_keys = self.sheet_data[self.current_language]["model_keys"]
        for column, model_key in enumerate(model_keys):
            frame = ttk.LabelFrame(
                self.cards_frame,
                text=MODEL_LABELS.get(model_key, model_key),
                padding=10,
            )
            frame.grid(row=column // 2, column=column % 2, sticky="nsew", padx=8, pady=8)
            self.cards_frame.columnconfigure(column % 2, weight=1)

            audio_path = Path(row[f"{model_key}_audio_path"])
            ttk.Label(
                frame,
                text=audio_path.name,
                font=("Helvetica", 10, "bold"),
            ).pack(anchor="w")
            ttk.Label(
                frame,
                text=str(audio_path),
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(4, 8))

            controls = ttk.Frame(frame)
            controls.pack(fill="x", pady=(0, 8))
            ttk.Button(
                controls,
                text="재생",
                command=lambda p=audio_path, label=MODEL_LABELS.get(model_key, model_key): self._play_audio(
                    p, label
                ),
            ).pack(side="left")
            ttk.Button(controls, text="정지", command=self._stop_audio).pack(
                side="left", padx=(6, 0)
            )

            overall_var = tk.StringVar(value=row.get(f"{model_key}_overall_10", ""))
            naturalness_var = tk.StringVar(value=row.get(f"{model_key}_naturalness_10", ""))
            appeal_var = tk.StringVar(value=row.get(f"{model_key}_voice_appeal_10", ""))
            pronunciation_var = tk.StringVar(
                value=row.get(f"{model_key}_pronunciation_10", "")
            )
            notes_var = tk.StringVar(value=row.get(f"{model_key}_notes", ""))

            self._add_score_row(frame, "Overall", overall_var)
            self._add_score_row(frame, "Naturalness", naturalness_var)
            self._add_score_row(frame, "Voice appeal", appeal_var)
            self._add_score_row(frame, "Pronunciation", pronunciation_var)

            ttk.Label(frame, text="Notes").pack(anchor="w", pady=(8, 0))
            notes_entry = ttk.Entry(frame, textvariable=notes_var, width=60)
            notes_entry.pack(fill="x")

            self.model_widgets[model_key] = {
                "overall": overall_var,
                "naturalness": naturalness_var,
                "voice_appeal": appeal_var,
                "pronunciation": pronunciation_var,
                "notes": notes_var,
            }

        self.status_var.set("현재 문장을 불러왔습니다. 재생 후 점수를 입력하고 저장하세요.")

    def _add_score_row(self, parent, label, variable):
        """
        기능:
        - 점수 입력 행을 추가한다.

        입력:
        - `parent`: 부모 위젯.
        - `label`: 라벨 텍스트.
        - `variable`: 연결할 문자열 변수.

        반환:
        - 없음.
        """
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, text=label, width=16).pack(side="left")
        spin = ttk.Spinbox(row, from_=1, to=10, textvariable=variable, width=6)
        spin.pack(side="left")

    def _capture_ui_to_row(self):
        """
        기능:
        - 현재 UI에 입력된 값을 현재 row dict에 반영한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if not self.model_widgets:
            return
        row = self._current_row()
        for model_key, widgets in self.model_widgets.items():
            row[f"{model_key}_overall_10"] = widgets["overall"].get().strip()
            row[f"{model_key}_naturalness_10"] = widgets["naturalness"].get().strip()
            row[f"{model_key}_voice_appeal_10"] = widgets["voice_appeal"].get().strip()
            row[f"{model_key}_pronunciation_10"] = widgets["pronunciation"].get().strip()
            row[f"{model_key}_notes"] = widgets["notes"].get().strip()

    def _save_current_state(self):
        """
        기능:
        - 현재 입력값을 TSV로 저장하고 flat summary도 함께 갱신한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        try:
            self._capture_ui_to_row()
            for language, data in self.sheet_data.items():
                save_grouped_sheet(data["path"], data["fieldnames"], data["rows"])
            self._export_flat_scores()
            self.status_var.set("점수를 저장했습니다.")
        except Exception as error:
            messagebox.showerror("저장 실패", str(error))
            self.status_var.set(f"저장 실패: {error}")

    def _export_flat_scores(self):
        """
        기능:
        - grouped sheet를 flat score TSV로 내보낸다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        fieldnames = [
            "language",
            "order",
            "prompt_id",
            "category",
            "text",
            "entry_id",
            "display_name",
            "audio_path",
            "overall_10",
            "naturalness_10",
            "voice_appeal_10",
            "pronunciation_10",
            "notes",
        ]
        rows = []
        for language, data in self.sheet_data.items():
            for row in data["rows"]:
                for model_key in data["model_keys"]:
                    rows.append(
                        {
                            "language": language,
                            "order": row["order"],
                            "prompt_id": row["prompt_id"],
                            "category": row["category"],
                            "text": row["text"],
                            "entry_id": model_key,
                            "display_name": MODEL_LABELS.get(model_key, model_key),
                            "audio_path": row[f"{model_key}_audio_path"],
                            "overall_10": row.get(f"{model_key}_overall_10", ""),
                            "naturalness_10": row.get(f"{model_key}_naturalness_10", ""),
                            "voice_appeal_10": row.get(
                                f"{model_key}_voice_appeal_10", ""
                            ),
                            "pronunciation_10": row.get(
                                f"{model_key}_pronunciation_10", ""
                            ),
                            "notes": row.get(f"{model_key}_notes", ""),
                        }
                    )
        with self.flat_export_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

    def _play_audio(self, audio_path, label):
        """
        기능:
        - 선택한 오디오를 출력 장치로 재생한다.

        입력:
        - `audio_path`: 재생할 wav 경로.
        - `label`: 표시용 모델 라벨.

        반환:
        - 없음.
        """
        audio_path = Path(audio_path)
        if not audio_path.is_file():
            messagebox.showerror("재생 실패", f"파일을 찾지 못했습니다: {audio_path}")
            return

        self._stop_audio()
        self.playing_var.set(f"재생 중: {label} | {audio_path.name}")

        def _worker():
            try:
                audio, sample_rate = sf.read(str(audio_path), always_2d=False)
                with self.playback_lock:
                    sd.play(audio, sample_rate, device=self.output_device)
                    sd.wait()
                self.root.after(
                    0,
                    lambda: self.playing_var.set("재생 완료"),
                )
            except Exception as error:
                self.root.after(
                    0,
                    lambda: messagebox.showerror("재생 실패", str(error)),
                )
                self.root.after(0, lambda: self.playing_var.set(f"재생 실패: {error}"))

        self.play_thread = threading.Thread(target=_worker, daemon=True)
        self.play_thread.start()

    def _stop_audio(self):
        """
        기능:
        - 현재 재생 중인 오디오를 중지한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        try:
            sd.stop()
            self.playing_var.set("재생 중지")
        except Exception:
            self.playing_var.set("재생 중인 파일 없음")

    def _close(self):
        """
        기능:
        - 종료 전에 현재 점수를 저장하고 GUI를 닫는다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._save_current_state()
        self._stop_audio()
        self.root.destroy()

    def run(self):
        """
        기능:
        - 메인 이벤트 루프를 실행한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.root.mainloop()


def main():
    """
    기능:
    - listening review GUI를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return
    app = ListeningReviewApp(args)
    app.run()


if __name__ == "__main__":
    main()
