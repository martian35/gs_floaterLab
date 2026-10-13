# 기전 probe — 어느 항이 floater와 표면을 어느 방향으로 미는가 (aria1253 중심, 2026-10-09~11)

## 측정

- 10 render마다 opacity logit과 시선 방향 위치의 gradient를 **RGB / geometry(RGB 외 모든 loss: base의 normal·dense depth + loss형 방법) / inject(방법이 직접 넣은 opacity gradient)**로 분해해
  Gaussian ID(stable point id)별로 300 render 창에 누적. 실제 `.grad`와의 합 일치 최대 상대 오차 ~1e-6(모든 run).
- 종료 후 held-out 라벨로 집단을 나눔: **survivor** = export 지도에 남은 floater, **floater** = 학습 직후 지도의 floater, **surface** = held-out에서 보이고 앞쪽 기여 비율 < .2.
- fade share = opacity를 내리는 gradient 비율(.5 중립), deeper share = 카메라에서 멀어지는 방향 비율, per seen = 보인 probe render당 크기.
- 원자료: `results/campaigns/07_floater_mechanism/<dataset>/<scene>/<arm>_s0_probe/mechanism.json`, 표: `tables/ALL_RESULTS.md` §Mechanism, `tables/selectivity_table.md`.

## 1. 끝까지 남는 floater는 어떤 것인가 (base, aria1253)

| 성질 | 값 | 뜻 |
|---|---|---|
| 나이 | 마지막 10% 구간 출생 16% | 오래 산 Gaussian (학습 직후 floater 619개는 77%가 신생·opacity .013이라 terminal prune이 93% 지움) |
| opacity | 중앙값 .24 (10–90% .15–.36) | 표면 분포(.13–.99) 안 |
| RGB gradient | fade .49 (표면 .47) | photometric 침묵 |
| 기존 geometry 항 | fade .58 (표면 .53) | 거의 중립 |
| 표면까지 거리 | 중앙값 12 cm (25–75%: 8–29) aria / 5 cm TUM | 판정 margin(깊이의 25%)보다 훨씬 작은 이동으로는 못 닿음 |
| 학습 중 이동 | 3.1 cm (표면 3.5) | DNGaussian 3.2, GOF 4.8 — "뒤로 옮긴다"는 방향일 뿐 표면에 닿지 않음 |

→ 해결책에 필요한 성질: (P1) 선택성 (P2) 위치가 아닌 opacity, 내리는 방향 (P3) 외부 깊이 오차에 견고 (P4) 지도·PSNR·예산 보존.

## 2. 선택성 — 방법이 넣는 opacity gradient: floater / 표면 (per seen, 세 장면)

| 방법 | inject 크기 floater / 표면 (비율) aria | table_06 | TUM | floater fade / 표면 fade |
|---|---|---|---|---|
| **Ours (cc)** | 2.2e-5 / 6.1e-11 (**3.6e5**) | 1.1e-5 / 1.7e-12 (**6.1e6**) | 3.5e-6 / 3.1e-10 (**1.1e4**) | 1.0 / 1.0 (표면은 사실상 0) |
| carve_only | 2.2e-5 / 5.8e-11 (3.8e5) | 9.4e-6 / 1.5e-12 (6.1e6) | 3.9e-6 / 3.5e-10 (1.1e4) | 1.0 / 1.0 |
| cc_nogate (λ3, gate OFF) | 4.3e-5 / 2.4e-8 (1.8e3) | 1.0e-5 / 7.9e-9 (1.3e3) | 1.8e-5 / 2.7e-8 (646) | 1.0 / 1.0 — gate를 끄면 표면 주입 90~4,600배 |
| sensor carve λ3 | 4.1e-5 / 7.4e-8 (557) | 6.0e-6 / 2.0e-8 (295) | 2.0e-5 / 6.3e-8 (324) | 1.0 / 1.0 — 표면 주입이 우리의 ~1,000배 |
| carve λ.2 gate OFF, FM OFF (자기 median) | 2.8e-6 / 5.8e-9 (492) | 6.2e-7 / 7.0e-10 (883) | 7.3e-7 / 4.5e-9 (161) | 1.0 / 1.0 — sensor λ.2와 같은 조건에서 기준 깊이만 다름 |
| sensor carve λ.2 | 2.2e-6 / 1.6e-8 (143) | 4.6e-7 / 3.5e-9 (132) | 4.9e-7 / 1.2e-8 (40) | 1.0 / 1.0 |
| DNGaussian soft | 3.3e-6 / 1.8e-7 (18) | 1.6e-6 / 2.7e-8 (58) | 2.4e-6 / 1.7e-7 (15) | .77 / .47 (표면은 키움) |
| SplatAD w1 | 1.3e-5 / 6.4e-7 (21) | 3.6e-6 / 1.6e-7 (23) | 7.8e-6 / 1.4e-7 (55) | 1.0 / 1.0 |
| DS-NeRF KL w.1 | 4.2e-5 / 1.9e-5 (2.2) | 3.3e-5 / 1.0e-5 (3.1) | 1.1e-4 / 1.6e-5 (7.3) | .80 / .55 (표면도 지움) |
| DS-NeRF KL w.001 | 1.2e-6 / 3.0e-7 (4.1) | 3.2e-7 / 2.6e-7 (1.2) | 8.2e-7 / 4.0e-7 (2.0) | .97 / .93 |

loss형 방법(d4, GOF, CG-SLAM)은 inject가 없고 geometry 항에 섞인다. survivor 집단의 geometry 항 방향(aria): d4 fade .54 deeper .52, GOF fade .50 **deeper .99**, CG-SLAM fade .80 deeper .89, DNG hard deeper .72.

## 3. 지도 관리 임계와 reset

임계 t에서 지워지는 비율 (survivor / 표면, base aria): t .2 → .32 / .16, .3 → .70 / .24, .5 → 1.0 / .37, .7 → 1.0 / .48.
3DGS reset(min(op,.01) at 10/20/30/40%): reset 뒤 다시 자라는 힘이 RGB뿐이고 RGB는 floater에 중립이라 floater도 표면과 같이 회복 → 학습 지도 floater 619 → 1,466, export 44 → 68.

## 4. 삭제 정밀도 (export 단계 삭제; 삭제 직전 지도의 held-out 라벨로 채점)

| run | 단계 | 삭제 수 | floater 정밀도 | 표면 비율 | held-out 기여 손실 |
|---|---|---|---|---|---|
| table_06 SparseGS | 방법 삭제 | 21,876 | .016 | **.953** | **23.8%** |
| TUM SparseGS | 방법 삭제 | 6,155 | .003 | .905 | 33.2% |
| base / cc (모든 장면) | terminal opacity prune | 17–19k | .004–.033 | .62–.87 | .9–1.4% |

terminal prune이 지우는 것도 대부분 "표면"으로 분류되지만 held-out 기여 손실이 1% 안팎(opacity<.1 신생)인 반면, SparseGS는 무거운 앞쪽 Gaussian을 지운다.
Sheng 2026의 감쇠 정밀도는 미측정(학습 중 감쇠).
