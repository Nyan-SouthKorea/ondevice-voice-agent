"""
Jetson용 TTS 텍스트 입력 GUI.

PyQt5 기반으로 한국어 IME 입력을 안정적으로 받고,
기존 Piper SDK 경로로 합성한 뒤 바로 재생한다.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent

DEFAULT_ENV_ROOT = WORKSPACE_ROOT / "env"
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
DEFAULT_OUTPUT_ROOT = (
    WORKSPACE_ROOT / "results" / "tts" / "jetson_demo" / "piper_ko_text_input_gui"
)


def resolve_default_model_path():
    """
    기능:
    - 우선순위에 따라 기본 Piper ONNX 경로를 고른다.

    입력:
    - 없음.

    반환:
    - 기본으로 사용할 모델 경로를 반환한다.
    """
    for candidate in [
        DEFAULT_LOCAL_MODEL_PATH,
        DEFAULT_RESULTS_MODEL_PATH,
        DEFAULT_RESULTS_MODEL_PATH_FLAT,
    ]:
        if candidate.is_file():
            return candidate
    return DEFAULT_RESULTS_MODEL_PATH


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
        "--env-root",
        type=Path,
        default=DEFAULT_ENV_ROOT,
        help="Jetson env 루트 경로",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=resolve_default_model_path(),
        help="기본으로 사용할 Piper ONNX 경로",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="합성 wav 저장 루트",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Piper 실행 device. Jetson Nano 기본값은 cpu",
    )
    return parser.parse_args()


class SynthesisWorker(QThread):
    """
    기능:
    - Piper 합성을 백그라운드 스레드에서 수행한다.

    입력:
    - 생성자에서 실행 경로와 텍스트를 받는다.

    반환:
    - `completed`, `failed` 시그널로 결과를 전달한다.
    """

    completed = pyqtSignal(str, str, str)
    failed = pyqtSignal(str)

    def __init__(self, env_python, model_path, device, output_root, text):
        super().__init__()
        self.env_python = env_python
        self.model_path = model_path
        self.device = device
        self.output_root = output_root
        self.text = text

    def run(self):
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        history_output = self.output_root / f"{timestamp}.wav"
        command = [
            str(self.env_python),
            str(REPO_ROOT / "tts" / "tts_demo.py"),
            "--model",
            "piper",
            "--model-name",
            str(self.model_path),
            "--device",
            self.device,
            "--text",
            self.text,
            "--output",
            str(history_output),
        ]
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self.failed.emit(result.stderr or result.stdout or "합성 실패")
            return

        model_load = "-"
        elapsed = "-"
        for line in (result.stdout or "").splitlines():
            if line.startswith("model_load_sec:"):
                model_load = line.split(":", 1)[1].strip()
            elif line.startswith("elapsed_sec:"):
                elapsed = line.split(":", 1)[1].strip()

        self.completed.emit(str(history_output), model_load, elapsed)


class TextInputTtsWindow(QMainWindow):
    """
    기능:
    - 한국어 입력과 Piper 합성/재생을 담당하는 메인 GUI를 제공한다.

    입력:
    - 실행 인자.

    반환:
    - 없음.
    """

    def __init__(self, args):
        super().__init__()
        self.args = args
        self.env_python = args.env_root / DEFAULT_PIPER_ENV / "bin" / "python"
        self.model_path = args.model_path
        self.output_root = args.output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.latest_output = self.output_root / "latest.wav"

        self.play_process = None
        self.worker = None

        self.setWindowTitle("Jetson Korean Piper TTS Demo")
        self.resize(980, 680)
        self.setMinimumSize(860, 580)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Jetson Korean Piper TTS Demo")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            "한글 입력기로 문장을 입력한 뒤 '합성 후 재생'을 누르면 "
            "한국어 Piper ONNX로 읽어줍니다."
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        info_group = QGroupBox("실행 정보")
        info_layout = QGridLayout(info_group)
        info_layout.addWidget(QLabel("모델 경로"), 0, 0)
        self.model_label = QLabel(str(self.model_path))
        self.model_label.setWordWrap(True)
        self.model_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self.model_label, 0, 1)

        info_layout.addWidget(QLabel("출력 파일"), 1, 0)
        self.output_label = QLabel(str(self.latest_output))
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self.output_label, 1, 1)
        root.addWidget(info_group)

        root.addWidget(QLabel("입력 텍스트"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("여기에 읽을 한국어 문장을 입력하세요.")
        self.text_edit.setPlainText(
            "안녕하세요. Jetson에서 한국어 Piper TTS 데모를 테스트하고 있습니다."
        )
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setAttribute(Qt.WA_InputMethodEnabled, True)
        root.addWidget(self.text_edit, stretch=1)

        button_row = QHBoxLayout()
        self.synthesize_button = QPushButton("합성 후 재생")
        self.synthesize_button.clicked.connect(self.start_synthesize_and_play)
        button_row.addWidget(self.synthesize_button)

        self.play_button = QPushButton("다시 재생")
        self.play_button.clicked.connect(self.start_play_latest)
        button_row.addWidget(self.play_button)

        self.stop_button = QPushButton("정지")
        self.stop_button.clicked.connect(self.stop_playback)
        button_row.addWidget(self.stop_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        metric_row = QHBoxLayout()
        metric_row.addWidget(QLabel("model_load_sec"))
        self.model_load_label = QLabel("-")
        metric_row.addWidget(self.model_load_label)
        metric_row.addSpacing(24)
        metric_row.addWidget(QLabel("elapsed_sec"))
        self.elapsed_label = QLabel("-")
        metric_row.addWidget(self.elapsed_label)
        metric_row.addStretch(1)
        root.addLayout(metric_row)

        self.status_label = QLabel("준비")
        self.status_label.setStyleSheet("color: #157347; font-weight: 600;")
        root.addWidget(self.status_label)

    def set_busy(self, busy):
        """
        기능:
        - 합성 중 버튼 상태를 바꾼다.

        입력:
        - `busy`: busy 여부.

        반환:
        - 없음.
        """
        self.synthesize_button.setEnabled(not busy)

    def start_synthesize_and_play(self):
        """
        기능:
        - 백그라운드 스레드에서 합성 후 재생을 시작한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "입력 필요", "읽을 텍스트를 입력해 주세요.")
            return
        if not self.env_python.is_file():
            QMessageBox.critical(
                self,
                "env 누락",
                f"Piper env python을 찾지 못했습니다: {self.env_python}",
            )
            return
        if not self.model_path.is_file():
            QMessageBox.critical(
                self,
                "모델 누락",
                f"Piper ONNX를 찾지 못했습니다: {self.model_path}",
            )
            return

        self.stop_playback()
        self.set_busy(True)
        self.status_label.setText("합성 중...")
        self.worker = SynthesisWorker(
            self.env_python,
            self.model_path,
            self.args.device,
            self.output_root,
            text,
        )
        self.worker.completed.connect(self._handle_success)
        self.worker.failed.connect(self._handle_failure)
        self.worker.finished.connect(lambda: self.set_busy(False))
        self.worker.start()

    def _handle_failure(self, message):
        """
        기능:
        - 합성 실패를 UI에 반영한다.

        입력:
        - `message`: 오류 메시지.

        반환:
        - 없음.
        """
        self.status_label.setText("합성 실패")
        QMessageBox.critical(self, "합성 실패", message)

    def _handle_success(self, output_path, model_load, elapsed):
        """
        기능:
        - 합성 성공 결과를 반영하고 재생한다.

        입력:
        - `output_path`: 새로 생성한 wav 경로.
        - `model_load`: 모델 로드 시간.
        - `elapsed`: 합성 시간.

        반환:
        - 없음.
        """
        source = Path(output_path)
        if self.latest_output.exists():
            self.latest_output.unlink()
        source.replace(self.latest_output)
        self.output_label.setText(str(self.latest_output))
        self.model_load_label.setText(model_load)
        self.elapsed_label.setText(elapsed)
        self.status_label.setText("합성 완료, 재생 시작")
        self._play_file(self.latest_output)

    def start_play_latest(self):
        """
        기능:
        - 최신 wav를 다시 재생한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if not self.latest_output.is_file():
            QMessageBox.warning(self, "출력 없음", "먼저 한 번 합성해 주세요.")
            return
        self._play_file(self.latest_output)

    def stop_playback(self):
        """
        기능:
        - 현재 재생 중인 오디오를 정지한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        if self.play_process and self.play_process.poll() is None:
            self.play_process.terminate()
            self.status_label.setText("재생 정지")

    def _play_file(self, path):
        """
        기능:
        - aplay로 wav 파일을 재생한다.

        입력:
        - `path`: 재생할 wav 경로.

        반환:
        - 없음.
        """
        self.stop_playback()
        self.status_label.setText("재생 중...")
        self.play_process = subprocess.Popen(
            ["aplay", "-q", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def closeEvent(self, event):
        """
        기능:
        - 창 종료 시 재생 프로세스를 정리한다.

        입력:
        - `event`: Qt close event.

        반환:
        - 없음.
        """
        self.stop_playback()
        super().closeEvent(event)


def main():
    """
    기능:
    - GUI 앱을 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    app = QApplication(sys.argv)
    window = TextInputTtsWindow(args)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
