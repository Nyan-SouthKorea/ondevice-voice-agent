# Wake Word 학습 환경 세팅 (Linux PC)

> 작성일: 2026-03-12
> 목적: openWakeWord 커스텀 학습을 위한 conda 환경 구성

> Jetson runtime venv는 `docs/envs/jetson_wake_word_env.md`에서 별도로 관리한다.

---

## 환경 정보

- **OS**: Ubuntu (Linux PC)
- **GPU**: NVIDIA A100 80GB PCIe
- **CUDA**: 11.8
- **Python**: 3.10
- **PyTorch**: 2.7.1+cu118

---

## 설치 순서

### 1. conda 환경 생성

```bash
conda create -n wake_word python=3.10
conda activate wake_word
```

### 2. CUDA 툴킷 설치

```bash
conda install -c conda-forge cudatoolkit=11.8 cudnn=8.9
```

### 3. PyTorch 설치

> ⚠️ conda로 PyTorch를 설치하면 `iJIT_NotifyEvent` 심볼 에러 발생.
> **반드시 pip으로 설치할 것.**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 4. 추가 패키지 설치

```bash
pip install openwakeword
pip install edge-tts
pip install librosa soundfile
```

---

## 설치 확인

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
# 출력 예: True / NVIDIA A100 80GB PCIe
```
