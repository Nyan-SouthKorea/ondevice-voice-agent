# Wake Word 기술 조사

> 작성일: 2026-03-12
> 상태: 조사 완료

## 결론 요약

- **채택**: openWakeWord
- **라이선스**: Apache 2.0 (상업적 사용 가능)
- **학습**: PyTorch → ONNX export
- **추론**: Jetson에서 onnxruntime-gpu

---

## 후보 비교

| 모델 | ONNX | 커스텀학습 | 라이선스 | 비고 |
|------|------|-----------|---------|------|
| **openWakeWord** | ✅ 네이티브 | ✅ | Apache 2.0 | **채택** |
| Mycroft Precise | 변환 필요 | ✅ | Apache 2.0 | 관리 소홀 |
| Porcupine | ❌ | 제한적 | 상용 | |
| Snowboy | ❌ | ✅ | 개발 중단 | |

---

## openWakeWord 구조

```
마이크 입력
    ↓
[Google Speech Embedding ONNX]  ← Apache 2.0, frozen (건드리지 않음)
    ↓
[이진 분류기 ONNX]              ← 커스텀 학습 대상
    ↓
0.0 ~ 1.0 (wake word 확률)
```

- Google Speech Embedding: YouTube 2억 개 오디오로 학습된 범용 음성 임베딩
- 분류기: FC 2레이어(32유닛), binary cross-entropy, 이진 분류

---

## 라이선스 상세

| 컴포넌트 | 라이선스 | 상업적 사용 |
|---|---|---|
| Google Speech Embedding | Apache 2.0 | ✅ |
| openWakeWord 코드 | Apache 2.0 | ✅ |
| 기본 제공 wake word 모델 (hey_jarvis 등) | CC BY-NC-SA 4.0 | ❌ |
| HuggingFace 학습 데이터셋 | CC BY-NC-SA 4.0 | ❌ (PoC 한정 사용) |

→ 커스텀 학습 필수. 사전 제공 모델 사용 불가.

---

## 기존 레포 노트북 분석

| 노트북 | TTS | 증강 | Negative 다운로드 | ONNX export |
|--------|-----|------|------------------|-------------|
| `automatic_model_training.ipynb` | ✅ Piper (Linux 전용, 영어만) | ✅ | ✅ HuggingFace | ✅ 자동 |
| `training_models.ipynb` | ❌ | ✅ | ✅ 직접 다운로드 | ❌ |

→ 한국어 미지원 → 커스텀 파이프라인 작성 필요

**채택 방식**: `training_models.ipynb` 흐름을 참고하되, TTS는 Edge TTS로 대체한 커스텀 파이프라인 작성

### 분류기 아키텍처 (`training_models.ipynb` 기준)

```python
nn.Sequential(
    nn.Flatten(),
    nn.Linear(timesteps * features, 32),
    nn.LayerNorm(32),
    nn.ReLU(),
    nn.Linear(32, 32),
    nn.LayerNorm(32),
    nn.ReLU(),
    nn.Linear(32, 1),
    nn.Sigmoid()
)
# 입력: Google Speech Embedding (3초 윈도우, 28 timesteps)
# 출력: 0.0 ~ 1.0 (wake word 확률)
```

---

## 학습 환경 (Linux PC)

| 항목 | 내용 |
|------|------|
| GPU | NVIDIA A100 80GB PCIe |
| CUDA | 11.8 |
| cuDNN | 8.9 |
| Python | 3.10 |
| PyTorch | 2.7.1+cu118 |
| conda 환경 | `wake_word` |
| 세팅 상세 | `docs/envs/wake_word_env.md` |

> ⚠️ PyTorch는 반드시 pip으로 설치. conda install 시 `iJIT_NotifyEvent` 심볼 에러 발생.

### 학습 파이프라인 구조

```
wake_word/
├── openWakeWord/          ← git clone (레포 원본)
├── train/
│   ├── 01_generate_positive.py   ← Edge TTS 한국어 positive 샘플 생성
│   ├── 02_augment.py             ← librosa 증강 (피치/속도/노이즈)
│   ├── 03_prepare_negative.py    ← AI Hub/MUSAN/FSD50K negative 데이터 준비
│   ├── 04_extract_features.py    ← Google Speech Embedding 사전 추출
│   ├── 05_train.py               ← 분류기 학습 (PyTorch)
│   └── 06_export_onnx.py         ← ONNX export → Jetson 배포
├── data/
│   ├── positive/          ← TTS 생성 + 실제 녹음 원본
│   ├── positive_aug/      ← 증강 후
│   ├── negative/          ← negative 오디오
│   └── features/          ← 사전 추출 embedding (.npy)
└── models/                ← hi_popo.onnx
```

---

## 데이터 전략

### Positive 샘플
| 소스 | 개수 | 방법 |
|------|------|------|
| Edge TTS | ~150개 | 10개 목소리 × 5속도 × 3피치 |
| 실제 녹음 | ~100개 | 팀원 8명 × 12~15회 |
| librosa 증강 | 3~5배 확장 | 피치 시프트, 타임 스트레치, 노이즈 추가 |
| **합계** | **1,000~2,000개** | |

### Negative 샘플
- **현재 기준**: AI Hub 자유대화 음성(일반남여) + MUSAN + FSD50K
- 한국어 일상 발화 데이터는 AI Hub를 우선 사용
- 환경 잡음 다양성은 MUSAN, FSD50K로 보강
- 세부 수집 절차와 재현성 기준은 `docs/research/negative_datasets.md` 참고
