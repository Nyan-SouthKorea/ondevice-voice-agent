# Jetson 공격적 성능 설정 가이드

## 목적

이 문서는 Jetson Orin Nano / Orin Nano Super 계열에서 다음 상태를 만들기 위한 운영 문서다.

- `MAXN_SUPER` 유지
- 클럭은 동적으로 동작
- 팬은 자동 제어 유지
- 재부팅 후에도 설정 유지
- `jetson_clocks`를 부팅 시 자동 적용하지 않음

이 프로파일은 "실사용 가능한 가장 공격적인 설정"을 목표로 한다.

중요한 점:

- `MAXN_SUPER`는 NVIDIA가 공식적으로 허용한 최고 성능 모드다.
- `jetson_clocks`는 CPU/GPU/EMC를 계속 최고값에 고정한다.
- `jetson_clocks`를 계속 켜 두면 `System throttled due to over-current`가 더 자주 발생할 수 있다.

따라서 이 문서의 권장 상태는 다음과 같다.

- 공격적: `MAXN_SUPER`
- 안정성/실사용성: 동적 클럭 유지
- 소음/열/보호 로직: 팬 자동 제어 유지

## 최종 목표 상태

- `nvpmodel` 모드: `MAXN_SUPER`
- `/etc/nvpmodel.conf` 기본 모드: `2`
- `nvfancontrol.service`: `enabled`
- `nvpmodel.service`: `enabled`
- `jetson_clocks`: 현재 부팅 세션에 고정 적용되지 않은 상태

이 문서가 기준으로 삼는 이미지에서는 `MAXN_SUPER`가 `mode 2`다. 다른 BSP에서는 모드 번호가 다를 수 있으므로 먼저 확인해야 한다.

## 왜 이렇게 설정하는가

`MAXN_SUPER`만 켜도 이 BSP가 허용하는 CPU/GPU/EMC 최대 상한이 열린다.

하지만 `jetson_clocks`까지 적용하면:

- CPU 최소/최대가 모두 최고값으로 고정될 수 있음
- GPU 최소/최대가 모두 최고값으로 고정될 수 있음
- EMC가 최고값에 고정될 수 있음
- 순간 전력 피크가 커져 `over-current` throttling이 늘어날 수 있음

즉 벤치마크용으로는 더 공격적이지만, 장시간 실사용에는 불리할 수 있다.

그래서 운영 프로파일은 아래가 적절하다.

- `MAXN_SUPER`는 유지
- 클럭은 필요할 때만 올라가도록 둠
- 팬은 `nvfancontrol`이 자동으로 조절

## 적용 명령

아래 명령을 순서대로 실행한다.

```bash
sudo -S nvpmodel -m 2
sudo -S cp /etc/nvpmodel.conf /etc/nvpmodel.conf.bak.$(date +%F-%H%M%S)
sudo -S sed -i 's/^< PM_CONFIG DEFAULT=.*/< PM_CONFIG DEFAULT=2 >/' /etc/nvpmodel.conf
sudo -S systemctl enable nvpmodel nvfancontrol
sudo -S systemctl restart nvfancontrol
```

## 현재 부팅 세션에서 `jetson_clocks`가 이미 적용된 경우

이전에 누군가 `jetson_clocks`를 실행했다면, 현재 부팅 세션에서는 고정 클럭 상태가 남아 있을 수 있다.

백업 파일이 있으면 다음 명령으로 되돌린다.

```bash
sudo -S jetson_clocks --restore /home/everybot/jetson_clocks.before.conf
```

백업 파일이 없다면 다음을 직접 점검해야 한다.

- 커스텀 systemd 서비스
- `.bashrc`, `.profile`, 로그인 스크립트
- `cron`
- 별도 시작 스크립트

즉 `jetson_clocks`가 부팅 시 자동으로 실행되도록 만든 흔적이 없는지 확인해야 한다.

## 검증 명령

아래 명령으로 상태를 확인한다.

```bash
sudo -S bash -lc 'jetson_clocks --show; echo ---; nvpmodel -q; echo ---; systemctl is-enabled nvfancontrol nvpmodel'
```

정상이라면 대략 아래 패턴이 보여야 한다.

- `NV Power Mode: MAXN_SUPER`
- CPU `MinFreq`가 약 `729600`
- CPU `MaxFreq`가 약 `1728000`
- GPU `MinFreq`가 약 `306000000`
- GPU `MaxFreq`가 약 `1020000000`
- EMC에서 `FreqOverride=0`
- `FAN Dynamic Speed Control=nvfancontrol`
- `nvfancontrol`, `nvpmodel` 둘 다 `enabled`

이 의미는 다음과 같다.

- 최고 전력 모드는 유지됨
- 클럭은 동적 스케일링 중임
- 팬은 자동 제어 중임
- 재부팅 후에도 같은 전력 모드가 유지됨

## 과전류 이벤트 확인

`System throttled due to over-current`가 뜨는지 확인하려면:

```bash
grep '' /sys/class/hwmon/hwmon*/oc*_event_cnt 2>/dev/null
```

보통 다음처럼 해석한다.

- `oc1`: 저전압 계열
- `oc2`: 평균 입력 전력 초과 계열
- `oc3`: 순간 입력 전력 초과 계열

특히 `oc3`는 순간 피크라서 Jetson Power GUI나 `tegrastats`에서 잘 안 잡힐 수 있다.

## 롤백

기본 출하형에 가까운 상태로 되돌리려면:

```bash
sudo -S nvpmodel -m 1
sudo -S sed -i 's/^< PM_CONFIG DEFAULT=.*/< PM_CONFIG DEFAULT=1 >/' /etc/nvpmodel.conf
sudo -S systemctl restart nvfancontrol
```

이 이미지 기준으로 `mode 1`은 기본 `25W`다.

## 옆 Jetson에서 Codex에게 시킬 때 쓸 지시문 예시

아래처럼 말하면 된다.

```text
/home/everybot/workspace/ondevice-voice-agent/repo/docs/envs/jetson/JETSON_MAXN_SUPER_PERSISTENT_KO.md
이 문서를 읽고, 문서 기준대로 지금 Jetson을 설정해. 적용 후 검증 결과도 같이 정리해.
```

## Codex용 추가 지침

- 이 문서의 기본 목표는 `MAXN_SUPER + 동적 클럭 + 자동 팬`이다.
- 사용자가 명시적으로 원하지 않으면 `jetson_clocks`를 영구 적용하지 말 것.
- 다른 Jetson에서는 먼저 `/etc/nvpmodel.conf`에서 `MAXN_SUPER`의 모드 번호를 확인할 것.
- `MAXN_SUPER`가 없는 장비면 가장 공격적인 공식 모드를 대신 사용하되, 무엇이 달랐는지 보고할 것.

## English Summary

- Keep `MAXN_SUPER`
- Do not keep `jetson_clocks` pinned
- Keep automatic fan control
- Persist the default power mode in `/etc/nvpmodel.conf`
- Verify with `jetson_clocks --show`, `nvpmodel -q`, and `systemctl is-enabled`
