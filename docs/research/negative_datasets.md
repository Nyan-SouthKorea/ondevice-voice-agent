# Negative 데이터셋 기준

> 작성일: 2026-03-12
> 목적: "하이 포포" Wake Word 학습용 Negative 샘플 수집 기준 정리

---

## 결론

- **최종 선택**: AI Hub 자유대화 음성(일반남여) + MUSAN + FSD50K
- **핵심 이유**: 한국어 일상 발화는 AI Hub 품질이 가장 중요하고, 환경 다양성은 MUSAN/FSD50K가 보강
- **출력 경로 기준**: `data/hi_popo/negative/`

---

## 비율 설계

| 구분 | 수량 | 비율 |
|------|------|------|
| Positive (증강 후) | 11,250 | 1 |
| Negative (목표) | 112,500 | 10 |

- 학습 시 `BCELoss(pos_weight=10.0)` 적용
- Hard negative와 환경 다양성을 함께 확보하는 것이 핵심

---

## 데이터소스 구성

| 소스 | 목표 클립 수 | 비중 | 역할 |
|------|-------------|------|------|
| AI Hub 자유대화 음성(일반남여) | 72,500 | 64% | 한국어 일상 발화 방어 |
| MUSAN | 20,000 | 18% | 음악, 소음, 다국어 음성 |
| FSD50K | 20,000 | 18% | 생활 환경음 보강 |
| 합계 | 112,500 | 100% | |

---

## 데이터셋 상세

### 1. AI Hub 자유대화 음성(일반남여)

| 항목 | 내용 |
|------|------|
| 출처 | AI Hub |
| 라이선스 | 비상업적 연구 무료 |
| 포맷 | WAV |
| 특징 | 한국어 자유대화, 전문 구축 데이터 |
| 다운로드 | 수동 신청 및 웹 다운로드 |

다운로드 절차:

1. AI Hub 접속 후 회원가입 및 인증
2. "자유대화 음성(일반남여)" 데이터 신청
3. 승인 후 train split 다운로드

### 2. MUSAN

| 항목 | 내용 |
|------|------|
| 출처 | OpenSLR |
| 라이선스 | CC BY 4.0 |
| 포맷 | WAV, 16kHz |
| 특징 | 장음원 위주, 3초 단위 청킹 필요 |

다운로드:

```bash
DLDIR="wake_word/data/hi_popo/_tmp_download"
mkdir -p "$DLDIR"
wget -q -O "$DLDIR/musan.tar.gz" https://www.openslr.org/resources/17/musan.tar.gz
cd "$DLDIR" && tar xzf musan.tar.gz
```

### 3. FSD50K

| 항목 | 내용 |
|------|------|
| 출처 | Zenodo |
| 라이선스 | CC BY 4.0 |
| 포맷 | WAV, 44.1kHz |
| 특징 | 생활 환경음 카테고리 다양, 16kHz 모노 변환 필요 |

다운로드:

```bash
DLDIR="wake_word/data/hi_popo/_tmp_download/fsd50k_parts"
mkdir -p "$DLDIR"
BASE="https://zenodo.org/records/4060432/files"

for f in FSD50K.dev_audio.z01 FSD50K.dev_audio.z02 FSD50K.dev_audio.z03 \
          FSD50K.dev_audio.z04 FSD50K.dev_audio.z05 FSD50K.dev_audio.zip \
          FSD50K.eval_audio.z01 FSD50K.eval_audio.zip \
          FSD50K.ground_truth.zip FSD50K.metadata.zip; do
  wget -q -c -O "$DLDIR/$f" "$BASE/$f?download=1" &
done
wait
```

---

## 파이프라인 기준

```text
[다운로드] AI Hub (수동) + MUSAN (wget) + FSD50K (wget)
    ↓
[변환] 모든 파일 → 16kHz 모노 WAV
    ↓
[청킹] 장음원 3초 단위 분할, 0.5초 미만 제거
    ↓
[샘플링] seed=42 랜덤 샘플링
    ↓
[저장] data/hi_popo/negative/
```

출력 디렉토리:

```text
data/hi_popo/negative/
├── aihub_free_conversation/
├── musan/
└── fsd50k/
```

---

## 재현성

- `SEED = 42`
- MUSAN URL 고정: `openslr.org/resources/17/musan.tar.gz`
- FSD50K 레코드 고정: `zenodo.org/records/4060432`
- AI Hub 동일 데이터셋 버전 사용
- 클립 필터 조건 유지: 유효 길이 `> 0.5초`

---

## 관련 문서

- `docs/개발방침.md`
- `docs/research/wake_word.md`
