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

## 2. 기준 깊이와 세기 (같은 carve gradient를 frontend BA 깊이 기준으로 — 단, KF view만·persistence gate 없음)

| arm | ΔPSNR | Gaussian | export floater | TUM GT (‰) | 표면 주입 크기 / 우리 |
|---|---|---|---|---|---|
| sensor carve λ .2 | −.15 / −.11 / +.01 | −7% / −8% / −3% | 18 / 3 / 6 | 202 (2.63) | ~250× |
| sensor carve λ 3 (= 우리 λ) | −1.63 / −1.73 / −.41 | −19% / −29% / −13% | 8 / 0 / 4 | 120 (1.74) | ~1,000× |
| cc | ±.02 | 0% | 3 / 0 / 3 | 385 (4.89) | 1 |

- 예측(TUM GT < 202; aria·table PSNR −.1 초과·지도 −10% 초과) 모두 맞음. [정정 2026-10-13, §4] "frontend 깊이가 틀린 곳에서 같은 세기로 밀면 표면이 지워진다"는 과장 — 같은 세기에서 표면을 지키는 부품은 gate이며, gate 없는 자기 median carve도 표면을 지운다.
- 센서가 정확한 TUM에서는 외부 기준 floater가 **지도를 유지한 arm 중** 가장 낮다(1.74‰, −.41 dB). 원시 개수가 더 낮은 KL w.1(40, 1.75‰)·SplatAD w1(62, 1.27‰)은 지도 −77%/−38%, PSNR −6.5/−.8 dB의 붕괴를 동반한다. **우리 방법의 한계로 정직하게 쓴다.**
- **교란 요인 (2026-10-13 5090 검토):** sensor arm은 우리와 기준 깊이만 다른 것이 아니다. BA 깊이가 KF에만 있어 KF view에서만 작동하고(우리는 모든 training render), persistence gate가 없다(BA 기준 경로에 gate 구현이 없음). 따라서 표면 주입 ~1,000배와 PSNR 손실을 기준 깊이만의 효과로 단정할 수 없다. 분리용 대조: `arms/cc_nogate.json`(cc에서 gate만 끔) — 결과는 §4에 추가한다.

## 3. 조합 (cc + sensor carve λ .2; 느린 evidence 경로라 대조군 cc_slow 동반)

| | PSNR | Gaussian | export floater | TUM GT ‰ |
|---|---|---|---|---|
| cc_slow (대조군) | 26.97 / 23.67 / 19.92 | 178k / 193k / 103k | 2 / 0 / 1 | 4.70 |
| cc_sensor02 | −.13 / −.12 / −.01 | −6.5% / −7.6% / −3.3% | 1 / 0 / 2 | **2.59** |

두 기준의 효과는 더해지고 비용은 sensor carve 단독과 같다. cc_slow vs cc(빠른 커널): −.04 / .00 / .00 dB, floater 2/0/1 vs 3/0/3 → 경로 차이는 잡음.
본문 방법이 아니라 ablation/discussion 후보.

## 4. gate 대조 — cc에서 persistence gate만 끔 (stage 12, λ3, FM 유지; 3장면 seed 0)

| arm | ΔPSNR(base) | Gaussian | export floater | 학습 지도 floater | 표면 주입/seen | 선택성 |
|---|---|---|---|---|---|---|
| cc (gate ON) | +.00 / +.01 / +.02 | 0% | 3 / 0 / 3 | 500 / 134 / 92 | 6.1e-11 / 1.7e-12 / 3.1e-10 | 3.6e5 / 6.1e6 / 1.1e4 |
| cc_nogate | **−2.23 / −2.39 / −.92** | −13 / −23 / −11% | 0 / 0 / 2 | 583 / 242 / 92 | 2.4e-8 / 7.9e-9 / 2.7e-8 | 1.8e3 / 1.3e3 / 646 |
| sensor λ3 (gate 없음, KF만, FM 없음) | −1.63 / −1.73 / −.41 | −19 / −29 / −13% | 8 / 0 / 4 | 536 / 294 / 116 | 7.4e-8 / 2.0e-8 / 6.3e-8 | 557 / 295 / 324 |

- 사전 규칙대로 판정: 표면 주입이 sensor λ3 수준(1/3~1/2.5)까지 올랐으므로 **1,000배 선택성 차이의 주원인은 gate**다. 기준 깊이의 몫은 남은 2~3배.
- gate 없는 자기 median carve는 판정-삭제 계열처럼 행동한다: TUM GT floater 194(cc 385), 양방향 10% 일치 87.2%(base 90.6, SparseGS 87.6), 앞 1.44% / 뒤 3.64%.
- 함의: 논문 서사에서 "자기 median 기준"보다 **"여러 view에서 지속적으로 앞에 있을 때만 민다"**(persistence gate)를 핵심 부품으로 둬야 한다. 기준 깊이의 독립 효과는 §5(stage 14)에서 분리했다: 3~7배.

## 5. 기준 깊이 대조 — 자기 median λ .2, gate 없음, FM 없음 (= S36 SEG2 운영점) vs sensor carve λ .2 (stage 14, 3장면 seed 0)

같은 λ·같은 gate 조건(없음)·같은 FM 조건(없음)에서 기준 깊이만 다르다. 남은 차이는 view 집합(우리는 모든 training render, sensor는 BA 깊이가 있는 KF만)이며 floater 주입 크기는 비슷하다(2.8e-6 vs 2.2e-6).

| arm | ΔPSNR(base) | Gaussian | export floater | 학습 지도 floater | 표면 주입/seen | 선택성 |
|---|---|---|---|---|---|---|
| carve_l02_nogate (자기 median) | **−.06 / −.04 / −.01** | −1.6 / −2.7 / −1.9% | 5 / 0 / 8 | 541 / 333 / 70 | 5.8e-9 / 7.0e-10 / 4.5e-9 | 492 / 883 / 161 |
| sensor_carve λ.2 (frontend 깊이) | −.15 / −.11 / +.01 | −6.6 / −7.9 / −3.4% | 18 / 3 / 6 | 609 / 398 / 81 | 1.6e-8 / 3.5e-9 / 1.2e-8 | 143 / 132 / 40 |
| (참고) carve_only = λ3 + gate, FM 없음 | +.01 / −.01 / +.02 | 0% | 8 / 0 / 8 | 499 / 144 / 90 | 5.8e-11 / 1.5e-12 / 3.5e-10 | 3.8e5 / 6.1e6 / 1.1e4 |

- 사전 규칙대로 판정: 자기 median의 PSNR 손실이 작고(2.5~3배) 표면 주입이 작으므로(2.7~5배) **기준 깊이도 선택성에 기여한다**(3~7배). TUM GT floater 271(base 384), 양방향 10% 일치 90.46%(base 90.59).
- 두 부품의 몫을 합치면: 기준 깊이 3~7배 + persistence gate 100~1,000배(§4). gate가 λ를 15배 올려도 PSNR 비용이 0이 되게 하고, 기준 깊이는 같은 λ에서 손실을 줄인다.
- export floater만 보면 λ.2·gate 없음(5/0/8)과 λ3·gate(8/0/8)가 비슷하다. gate의 이득은 학습 중 지도(table 333 → 144)와 PSNR 비용(−.04 → −.01)에서 나타난다.
