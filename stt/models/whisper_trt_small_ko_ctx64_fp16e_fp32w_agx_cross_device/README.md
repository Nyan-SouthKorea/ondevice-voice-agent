# WhisperTRT Small KO ctx64 fp16e fp32w AGX cross device

이 디렉토리는 AGX Orin에서 생성 검증했던 한국어 `WhisperTRT small` 교차 장치 기준 메모 경로다.

핵심:

- 엔진 dtype: `fp16`
- 빌드 가중치 dtype: `fp32`
- 장비: `Jetson AGX Orin`

주의:

- AGX Orin에서 한 번에 빌드한 checkpoint다.
- Orin Nano에서도 로드는 될 수 있지만, TensorRT가 교차 장치 engine 경고를 낼 수 있다.
- 따라서 운영 기본값으로는 이 경로보다 `nano_safe` 모델을 우선 사용한다.

보관 정책:

- 이 경로는 AGX에서 한 번에 빌드가 가능했다는 사실과 사용 조건만 남긴다.
- checkpoint 파일은 상시 보관하지 않는다.
- 필요하면 AGX Orin에서 같은 조건으로 다시 생성한다.
