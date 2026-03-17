"""Jetson TRT 실험을 위한 하드웨어/소프트웨어 프로파일 수집 스크립트."""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from importlib import metadata
import platform
import sys


def run_command(command, cwd=None, timeout_sec=20):
    """
    기능:
    - 외부 명령을 실행하고 stdout/stderr를 수집한다.

    입력:
    - `command`: 실행할 쉘 명령 문자열
    - `cwd`: 명령 실행 폴더
    - `timeout_sec`: 타임아웃 초 (기본 20초)

    반환:
    - 실행 결과 딕셔너리
    """
    try:
        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            cwd=cwd,
        )
        return {
            "return_code": int(completed.returncode),
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover - 예외는 환경 의존성
        return {
            "return_code": -1,
            "stdout": "",
            "stderr": str(exc),
        }


def read_file(path):
    """
    기능:
    - 파일을 텍스트로 읽어온다.

    입력:
    - `path`: 대상 파일 경로 문자열

    반환:
    - 파일 내용 문자열, 없으면 빈 문자열
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            return file.read().strip()
    except Exception:
        return ""


def package_versions():
    """
    기능:
    - TRT/음성 파이프라인 실행에 필요한 패키지 버전을 수집한다.

    입력:
    - 없음.

    반환:
    - 패키지명-버전 딕셔너리
    """
    names = [
        "torch",
        "onnx",
        "onnxruntime",
        "onnxruntime-gpu",
        "whisper",
        "whisper_trt",
        "torch2trt",
        "numpy",
        "sounddevice",
        "psutil",
        "librosa",
        "openai",
    ]
    versions = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except Exception:
            versions[name] = None
    return versions


def collect_profile():
    """
    기능:
    - jetson TRT 빌드에 필요한 하드웨어/소프트웨어 정보를 한 번에 수집한다.

    입력:
    - 없음.

    반환:
    - 프로파일 딕셔너리
    """
    return {
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": {
            "binary": sys.executable,
            "version": sys.version.splitlines()[0],
            "platform": platform.platform(),
        },
        "os": {
            "uname": run_command("uname -a"),
            "lsb_release": run_command("lsb_release -a"),
            "nv_tegra_release": read_file("/etc/nv_tegra_release"),
            "device_tree_model": read_file("/proc/device-tree/model"),
            "cpuinfo": read_file("/proc/cpuinfo"),
            "meminfo": read_file("/proc/meminfo"),
            "modules": run_command("lsmod | head -n 40"),
        },
        "storage": {
            "df_root": run_command("df -h /"),
            "df_tmp": run_command("df -h /tmp"),
        },
        "power": {
            "nvpmodel": run_command("nvpmodel -q"),
            "jetson_clocks_show": run_command("jetson_clocks --show"),
            "tegra_gpu_clk": run_command("cat /sys/devices/gpu.0/devfreq/57000000.gv11b/devfreq_cur_freq"),
        },
        "cuda_tensorrt": {
            "nvidia_smi": run_command("nvidia-smi -L"),
            "nvidia_smi_queries": run_command("nvidia-smi -q -d MEMORY,POWER -x"),
            "tegra_stats_one": run_command("tegrastats --interval 1000 --count 1"),
        },
        "package_versions": package_versions(),
        "python_check": {
            "torch_is_available": run_command("python - <<'PY'\nimport torch\nprint(torch.__version__)\nprint(torch.cuda.is_available())\nprint(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')\nPY"),
            "ort_providers": run_command("python - <<'PY'\nimport onnxruntime as ort\nprint(ort.__version__)\nprint(ort.get_available_providers())\nPY"),
        },
        "environment": {
            "PATH": run_command("echo $PATH"),
            "LD_LIBRARY_PATH": run_command("echo $LD_LIBRARY_PATH"),
            "CUDA_VISIBLE_DEVICES": run_command("echo $CUDA_VISIBLE_DEVICES"),
            "TRT_PATH": read_file("/etc/ld.so.conf"),
            "python_path": run_command("python - <<'PY'\nimport sys\nprint('::'.join(sys.path))\nPY", timeout_sec=10),
        },
    }


def write_profile(profile, output_dir, tag):
    """
    기능:
    - 수집한 프로파일을 json 파일로 저장하고 latest 링크를 만든다.

    입력:
    - `profile`: 수집 데이터
    - `output_dir`: 저장 폴더
    - `tag`: 파일명 태그

    반환:
    - 저장된 json 경로
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_dir / f"jetson_trt_profile_{tag}_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(profile, handle, ensure_ascii=False, indent=2)

    latest = output_dir / f"jetson_trt_profile_{tag}_latest.json"
    latest.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

    return str(file_path), str(latest)


def parse_args():
    """
    기능:
    - 프로파일 수집 CLI 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - argparse 네임스페이스
    """
    parser = argparse.ArgumentParser(
        description="Jetson TRT 실험용 하드웨어/소프트웨어 프로파일 수집"
    )
    parser.add_argument(
        "--output-dir",
        default="/home/everybot/workspace/ondevice-voice-agent/project/results/jetson_trt_profiles",
        help="json 결과를 저장할 폴더",
    )
    parser.add_argument(
        "--tag",
        default="agx_orin",
        help="출력 파일명 태그 (기본: agx_orin)",
    )
    return parser.parse_args()


def main():
    """
    기능:
    - 프로파일링을 실행하고 저장 경로를 터미널에 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    profile = collect_profile()
    json_path, latest_path = write_profile(profile, args.output_dir, args.tag)
    print(f"jetson_trt_profile_saved: {json_path}")
    print(f"jetson_trt_profile_latest: {latest_path}")


if __name__ == "__main__":
    main()
