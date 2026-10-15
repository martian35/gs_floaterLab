# GEO — floater 억제 기존 방법은 왜 안 되고, Consensus Carving은 어떻게 푸는가

> 2026-10-09~11, RTX 3090, seed 0, 장면 3개. **벤치마크 수치가 아니라 기전 근거**를 모은 캠페인이다.
> 벤치마크 표는 5090에서 다시 낸다 ([5090에서 이어가기](HANDOFF_5090.md)).
> 코드: VIGS-SLAM-custom 브랜치 `handoff/floaterlab-baselines-20261013` → `scripts/floaterlab/`, 실행 안내 `docs/FLOATERLAB_BASELINES.md`.

Status: **EVIDENCE** (카테고리별 실패 지점과 우리 방법의 작용 차이 확정) / **OPEN** (seed 1개, 외부 기준 지표에서는 base와 동률).

## 한 줄 요약

같은 mapper(recipe C 실행기, 자체 frontend, 기준 pose, 6N) 위에 기존 floater 억제 방법 10가지를 공식 코드에서 이식해 켜고,
학습 중 gradient를 항별로 분해해 **floater와 표면 중 어느 쪽을 미는지** 쟀다. 기존 방법은 다섯 지점 중 하나에서 막힌다:
① opacity로는 floater와 표면이 구분되지 않는다 ② 앞/뒤 방향을 구분 못 해 지우지 않고 옮긴다 ③ 외부 깊이를 믿어 그 오차만큼 표면을 지운다
④ 지우는 세기와 지도를 지키는 세기가 양립하지 않는다 ⑤ 되돌릴 수 없는 삭제를 한다.
Consensus Carving은 지도 자신의 median 기준·앞쪽만·opacity만·지속성 gate·soft gradient로 다섯을 각각 피한다.
**gate 대조(stage 12, 2026-10-13):** cc에서 persistence gate만 끄면(λ3 그대로) 표면 주입이 6e-11 → 2.4e-8(aria)·1.7e-12 → 7.9e-9(table)·3e-10 → 2.7e-8(TUM)로 올라 sensor λ3(7.4e-8/2.0e-8/6.3e-8)의 1/3~1/2.5 수준이 되고, PSNR은 −2.23/−2.39/−.92 dB(sensor λ3 −1.63/−1.73/−.41)로 더 나쁘다. 즉 λ3에서 표면을 지키는 결정적 부품은 **persistence gate**이고, 기준 깊이(자기 median vs frontend)의 몫은 선택성 2~3배다. 같은 λ .2·gate 없음·FM 없음 조건의 기준 깊이 대조(stage 14): 자기 median이 frontend 기준보다 PSNR 손실 2.5~3배 작고 선택성 3~7배 높다 → 기준 깊이의 몫은 3~7배, gate의 몫은 100~1,000배.
표면에 가는 힘이 floater에 가는 힘의 1/10⁴–1/10⁶이고, PSNR·지도 크기·깊이 정확도는 그대로, floater는 44/6/16 → 3/0/3.

## 질문

1. 각 카테고리의 기존 방법은 **학습 중 어떤 Gaussian을 어느 방향으로** 미는가? (probe) → [mechanism_probe](mechanism_probe/README.md)
2. 그 결과 PSNR·지도 크기·floater가 어떻게 되는가? → [results_3scenes](results_3scenes/README.md)
3. 우리 방법의 두 부품(학습 중 carve / 끝의 FM)과 기준 깊이(자기 median / frontend)는 각각 무엇을 하는가? → [ours_decomposition](ours_decomposition/README.md)
4. 외부 기준(Kinect GT) floater 라벨은 실제로 무엇을 재는가? → [gt_label_audit](gt_label_audit/README.md)
5. 이식은 공식 코드와 얼마나 같은가? → [baseline_ports](baseline_ports/README.md)

사전등록과 단계별 판정: [PREREG.md](PREREG.md). 최신 baseline(D) 위의 파일럿: [results_D_pilot](results_D_pilot/README.md) — D는 base floater를 2.7~3배 줄이고 우리 효과는 유지(cc_D 1/0 vs base_D 16/5, PSNR ±.01). 이 캠페인까지의 geometry 연구 이력: [HISTORY.md](HISTORY.md).
확정 결론: [knowledge/floater_baseline_mechanisms.md](../../../knowledge/floater_baseline_mechanisms.md). 논문 §3.3 작성 브리프: [paper/notes/method/consensus_carving](../../../../paper/notes/method/consensus_carving/2026-10-15_sec3_3_writing_brief.md).

## 하네스와 arm

- base = recipe C − SEW3 − FM (KF RGB + metric depth .25 + normal, dense RGB + transported depth .25, 보호 prune, 종료 opacity<.1).
- cc = release C. 3090에서 팀원 C 재현 .005–.03 dB (aria1253 27.007 vs 27.004/27.029; 301_1253 25.264 vs 25.268).
- 장면: aria1253 (Aria, MPS pose, 6,216 renders), RPNG table_06 (12,996), TUM fr1_desk (GT pose + Kinect depth, 2,934). 예산은 팀원 계약과 동일.
- 지표: held-out PSNR; export floater = held-out view에서 기여의 80% 이상이 ray median 종료 깊이보다 25% 넘게 앞 (FM과 같은 규칙, 학습·FM이 안 쓰는 view);
  TUM GT floater = 같은 규칙을 Kinect 깊이 기준으로; probe = 10 render마다 opacity·위치 gradient를 RGB/geometry/inject로 분해, Gaussian ID별 누적(실제 .grad와 합 일치 ~1e-6).

## 카테고리별 판정 (카테고리 하나 = 한 행; 숫자는 aria1253 / table_06 / TUM)

| Category | 포함 Method | 판정 기준 | 작용 방식 | 카테고리 공통 문제점 (측정 근거) |
|---|---|---|---|---|
| 지도 관리 | MonoGS prune, 3DGS opacity reset, opacity 임계 .3/.5 | opacity가 낮은가 | 주기 삭제 / reset 후 재학습 | **opacity로는 floater와 표면이 구분되지 않는다.** 끝까지 남는 floater의 opacity(.15–.36)가 표면 분포 안에 있다. 임계 t에서 지워지는 비율(floater/표면): .2 → .32/.16, .3 → .70/.24, .5 → 1.0/.37, .7 → 1.0/.48. MonoGS floater 0/0/1이지만 지도 −67/−79/−81%, −1.22/−.69/−.39 dB. reset은 floater도 표면처럼 다시 자라게 해 학습 지도 floater 619 → 1,466. |
| frontend depth 정규화 | DNGaussian(공식), depth L1 ×4, DNG식 soft(opacity만)/hard(위치만) | 렌더 깊이 vs frontend 깊이 | depth loss gradient (opacity+위치) | **깊이 오차 크기만 줄일 뿐 앞쪽 floater와 뒤쪽 표면을 구분하지 않는다.** floater의 depth gradient가 6배 커도 opacity 방향은 중립(.54). hard는 위치 gradient의 72%가 뒤쪽이지만 실제 이동 3 cm(표면까지 12 cm 이상); soft는 표면 opacity를 키운다(.466). floater 43/32/11 (base 44/6/16). |
| 종료 분포 / ray 통계 | CG-SLAM(공식 rasterizer), GOF distortion(공식 rasterizer), DS-NeRF KL(식) | ray 위 질량의 퍼짐 | 분포 모양을 바꾸는 양방향 loss | **"분포가 좁고 일관되게"만 요구해 우회로가 생긴다.** CG-SLAM은 floater를 뒤로 옮기고(88%) 표면 opacity를 키워(.74 → .89) 지도 +9/+8/+13%; GOF는 위치 89–99% 뒤쪽이나 opacity 중립(.50), 이동 4.8 cm; KL은 floater/표면 힘 비율 1.2–7.3이라 지우는 세기면 지도가 무너진다(가중치 100배 낮춰도 table −8.7 dB). |
| 센서 free-space | GS-SLAM Eq.9(식), SplatAD(공식 커널), sensor carve(우리 carve gradient를 frontend 깊이 기준으로; KF view만, persistence gate 없음) | 센서/frontend 깊이보다 앞 = 빈 공간 | 앞쪽 opacity 감쇠 | **외부 깊이가 맞다고 가정해 그 오차만큼 표면을 지운다.** frontend 깊이는 Kinect와 10% 이내 일치 81.5%(지도 자신 90.6%보다 낮음). 같은 세기(λ3)의 sensor carve는 표면 주입이 우리의 ~1,000배 → −1.63/−1.73/−.41 dB, 지도 −19/−29/−13% — 단 이 차이의 대부분은 sensor arm에 gate가 없어서다(gate를 끈 우리 carve도 −2.2/−2.4/−.9 dB; stage 12). Eq.9 지도 −39/−39/−46%. SplatAD는 "효과 없음"(w .01: 49/11/14) 아니면 "붕괴"(w 1: −4.85 dB). 센서가 정확한 TUM에서만 외부 기준 이득. |
| 판정 후 삭제 | SparseGS(공식 판정), Sheng 2026(식) | 깊이 봉우리 둘인 픽셀 / Gaussian 중심의 다중 view 투표 | 한 번에 삭제 또는 opacity ×.01 | **판정 단위가 거칠고 되돌릴 수 없다.** SparseGS는 픽셀 앞쪽 전부(첫 기여자~최빈 깊이)를 지워 삭제의 95%가 표면, 화면 기여 24–33% 손실, −2.8 dB; 앞 오차를 뒤 오차로 바꿔 깊이 정확도 90.6 → 87.6%. Sheng은 중심 한 점·평균 깊이·기여 무시 → 지도 −17~−42%, 엄격히(φ.9) 하면 감쇠 4.7배. |
| **Ours** | Consensus Carving + FM | 지도 자신이 렌더한 median보다 앞 + 여러 view에서 지속 | 앞쪽 질량에만 opacity 내림 gradient(soft) + 끝에 누적 증거로 정리 | 선택성 1.1e4–6.1e6 (gate 없이는 646–1.8e3; sensor λ3 295–557, DNG 15–58, SplatAD 8–55, KL 1.2–7.3). PSNR ±.02, 지도 0%, 깊이 정확도 그대로. **한계:** 지도-센서 불일치는 못 고친다 (TUM GT 385 vs base 384). |

## 본문용 대표 결과 (TABLE_BASELINE_MAIN; 셀 = PSNR / floater‰)

| Category | Method | aria1253 | table_06 | TUM | TUM GT-front‰↓ | TUM Acc%↑ | #G ×base | time ×base |
|---|---|---|---|---|---|---|---|---|
| — | Base | 27.01 / 0.26 | 23.66 / 0.03 | 19.90 / 0.20 | 4.87 | 90.6 | 1.00 | 1.00 |
| Map maintenance | MonoGS prune | 25.79 / 0.00 | 22.97 / 0.00 | 19.51 / 0.05 | 7.19 | 90.2 | 0.24 | 0.85 |
| Depth regularization | DNGaussian | 26.75 / 0.26 | 23.56 / 0.17 | 19.73 / 0.13 | 5.34 | 90.5 | 1.03 | 1.50 |
| Ray statistics | CG-SLAM | 27.14 / 0.13 | 23.56 / 0.01 | 19.86 / 0.07 | 6.02 | 90.6 | 1.10 | 1.15 |
| Sensor free space | GS-SLAM Eq. 9 | 26.33 / 0.11 | 23.26 / 0.03 | 19.72 / 0.09 | 3.49 | 90.6 | 0.59 | 0.92 |
| Detect-and-delete | SparseGS | 24.22 / 0.21 | 21.04 / 0.07 | 17.10 / 0.45 | 1.91 | 87.6 | 0.94 | 1.00 |
| **Ours** | Consensus Carving | 27.01 / 0.02 | 23.67 / 0.00 | 19.92 / 0.04 | 4.89 | 90.6 | 1.00 | 1.14 |

floater‰ = held-out에서 보이는 Gaussian 1,000개당. GT-front‰ = Kinect 기준(앞쪽만). Acc = 렌더 깊이가 Kinect와 10% 안인 픽셀 비율(양방향).
TeX: [`results/campaigns/07_floater_mechanism/tables/TABLE_BASELINE_MAIN.tex`](../../../../results/campaigns/07_floater_mechanism/tables/TABLE_BASELINE_MAIN.tex).

## 반드시 같이 적을 한계

- **라벨 순환성.** floater‰는 학습에 안 쓴 view에서 재지만 판정 규칙이 우리 방법과 같다. 외부 기준(TUM GT-front, Acc)에서 우리는 base와 같다.
  주장은 "깊이 정확도와 화질을 해치지 않고 지도가 스스로와 모순되는 floater를 지운다"로 맞춘다.
- **GT-front는 한쪽만 센다.** 걸린 것의 86–95%가 지도 기준 표면. 표면을 뒤로 미는 방법이 유리해 보이므로 양방향 지표와 함께 낸다 ([gt_label_audit](gt_label_audit/README.md)). 양방향(10% 일치율)에서는 모든 arm이 base ±0.3 %p 안이거나 아래이며(GOF +0.26 %p가 최대), seed 1개라 어느 쪽도 판정하지 않는다.
- **sensor carve 비교는 단일 요소 비교가 아니다.** 기준 깊이 외에 view 집합(KF만)과 persistence gate 유무가 함께 다르다. 표면 주입 ~1,000배 차이를 기준 깊이만의 효과로 단정하지 않는다. **분리 결과(stage 12): 주원인은 gate.** **gate 대조(stage 12, 2026-10-13):** cc에서 persistence gate만 끄면(λ3 그대로) 표면 주입이 6e-11 → 2.4e-8(aria)·1.7e-12 → 7.9e-9(table)·3e-10 → 2.7e-8(TUM)로 올라 sensor λ3(7.4e-8/2.0e-8/6.3e-8)의 1/3~1/2.5 수준이 되고, PSNR은 −2.23/−2.39/−.92 dB(sensor λ3 −1.63/−1.73/−.41)로 더 나쁘다. 즉 λ3에서 표면을 지키는 결정적 부품은 **persistence gate**이고, 기준 깊이(자기 median vs frontend)의 몫은 선택성 2~3배다. 같은 λ .2·gate 없음·FM 없음 조건의 기준 깊이 대조(stage 14): 자기 median이 frontend 기준보다 PSNR 손실 2.5~3배 작고 선택성 3~7배 높다 → 기준 깊이의 몫은 3~7배, gate의 몫은 100~1,000배.
- seed 1개, 3090. ±.1 dB 이내는 판정하지 않는다. SparseGS는 공식의 삭제 후 10k 회복 학습이 없는 조건. GOF 시간 2.3–3×는 추가 렌더(이식) 비용.
- 미공개 하이퍼파라미터 추정: GS-SLAM η γ, Sheng φ, SplatAD 가중치, DS-NeRF σ.
- 부품 비교다(같은 mapper). 시스템 전체 비교가 아니다.

## 결과 파일

- 경량 번들(77 run, quality/label/mechanism JSON): [`results/campaigns/07_floater_mechanism/`](../../../../results/campaigns/07_floater_mechanism/README.md) — PLY·probe npz·로그는 3090 `vigs_aria_experiments/bcd_runs_20261009/floaterlab*`.
- 3090 작업 목록과 chain 스크립트: [`benchmarks/online_gs/campaigns/07_floater_mechanism/`](../../../../benchmarks/online_gs/campaigns/07_floater_mechanism/README.md).
