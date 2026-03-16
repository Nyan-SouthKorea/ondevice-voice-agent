from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENWAKEWORD_ROOT = REPO_ROOT / "openWakeWord"
if str(OPENWAKEWORD_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENWAKEWORD_ROOT))


def main() -> int:
    """
    기능:
    - 현재 환경에서 ONNX Runtime CUDA provider가 실제로 동작하는지 확인한다.
    
    입력:
    - 없음.
    
    반환:
    - 검사 결과를 나타내는 종료 코드 정수를 반환한다.
    """
    import onnxruntime as ort
    from openwakeword.utils import download_models

    model_dir = OPENWAKEWORD_ROOT / "openwakeword" / "resources" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    melspec_path = model_dir / "melspectrogram.onnx"
    embedding_path = model_dir / "embedding_model.onnx"

    if not melspec_path.exists() or not embedding_path.exists():
        download_models(target_directory=str(model_dir), inference_framework="onnx")

    print("available_providers:", ort.get_available_providers())

    session_options = ort.SessionOptions()
    try:
        session = ort.InferenceSession(
            str(embedding_path),
            sess_options=session_options,
            providers=["CUDAExecutionProvider"],
        )
        actual_providers = session.get_providers()
        print("requested_provider: CUDAExecutionProvider")
        print("actual_session_providers:", actual_providers)
        if actual_providers and actual_providers[0] == "CUDAExecutionProvider":
            print("RESULT: GPU_OK")
            return 0
        print("RESULT: GPU_FALLBACK")
        return 2
    except Exception as exc:
        print("requested_provider: CUDAExecutionProvider")
        print("RESULT: GPU_FAILED")
        print(f"error_type: {type(exc).__name__}")
        print(f"error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
