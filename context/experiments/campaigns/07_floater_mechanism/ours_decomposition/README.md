# 우리 방법 분해 — carve / FM / 기준 깊이 / 세기 / 조합 (stage 8–11, 2026-10-10)

숫자는 aria1253 / table_06 / TUM. ΔPSNR은 base(또는 명시한 대조군) 대비. 사전등록·판정: [PREREG.md](../PREREG.md) 결과 8–10.

## 1. 두 부품

| arm | ΔPSNR | export floater | 학습 직후 지도 floater | TUM GT floater |
|---|---|---|---|---|
| base | 27.01 / 23.66 / 19.90 dB | 44 / 6 / 16 | 619 / 381 / 90 | 384 |
| carve_only (학습 중 SEW3만, terminal prune) | +.01 / −.01 / +.02 | 8 / 0 / 8 | 499 / 144 / 90 | 363 |
| fm_only (base 학습 + FM) | −.02 / +.01 / +.01 | 11 / 0 / 2 | 597 / 381 / 73 | 388 |
| cc (둘 다 = C) | +.00 / +.01 / +.02 | 3 / 0 / 3 | 500 / 134 / 92 | 385 |

- 예측 (1) "fm_only ≈ cc"는 aria에서 틀림(11 vs 3), table·TUM 맞음. (2) "학습 지도 floater carve_only ≈ cc < base (aria·table), TUM 차이 없음" 맞음. (3) PSNR ±.05 맞음.
- carve는 **학습 중 지도**를 정리한다(SLAM이 도는 동안 보이는 지도; −19% / −62%). export 단계 없이도 44 → 8, 6 → 0. FM은 끝에 남은 것을 지운다. aria에서는 둘 다 필요, TUM은 FM이 대부분.
- fm_only 수치는 가장 순환적이다(FM은 학습 KF에서, 라벨은 held-out에서 같은 규칙).
- fm_only 1차 실행은 설정 실수(evidence capture hook 꺼짐 → "FM render buffers were not captured")로 실패해 `FIXED40_SELF=evidence, SELF_GRAD=0`으로 재실행했다. 방법 결과가 아니다.

## 2. 기준 깊이와 세기 (같은 gradient, 기준만 frontend BA 깊이로)

| arm | ΔPSNR | Gaussian | export floater | TUM GT (‰) | 표면 주입 크기 / 우리 |
|---|---|---|---|---|---|
| sensor carve λ .2 | −.15 / −.11 / +.01 | −7% / −8% / −3% | 18 / 3 / 6 | 202 (2.63) | ~250× |
| sensor carve λ 3 (= 우리 λ) | −1.63 / −1.73 / −.41 | −19% / −29% / −13% | 8 / 0 / 4 | 120 (1.74) | ~1,000× |
| cc | ±.02 | 0% | 3 / 0 / 3 | 385 (4.89) | 1 |

- 예측(TUM GT < 202; aria·table PSNR −.1 초과·지도 −10% 초과) 모두 맞음. frontend 깊이가 틀린 곳(Aria/RPNG)에서 같은 세기로 밀면 실제 표면이 지워진다.
- 센서가 정확한 TUM에서는 외부 기준 floater가 가장 낮다(대가 −.41 dB). **우리 방법의 한계로 정직하게 쓴다.**

## 3. 조합 (cc + sensor carve λ .2; 느린 evidence 경로라 대조군 cc_slow 동반)

| | PSNR | Gaussian | export floater | TUM GT ‰ |
|---|---|---|---|---|
| cc_slow (대조군) | 26.97 / 23.67 / 19.92 | 178k / 193k / 103k | 2 / 0 / 1 | 4.70 |
| cc_sensor02 | −.13 / −.12 / −.01 | −6.5% / −7.6% / −3.3% | 1 / 0 / 2 | **2.59** |

두 기준의 효과는 더해지고 비용은 sensor carve 단독과 같다. cc_slow vs cc(빠른 커널): −.04 / .00 / .00 dB, floater 2/0/1 vs 3/0/3 → 경로 차이는 잡음.
본문 방법이 아니라 ablation/discussion 후보.
