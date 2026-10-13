> 3090 작업 폴더(aria-online-3dgs-bench `analysis/bcd_baselines_20261009/PREREG_MECHANISM_BASELINES.md`)의 사본, 2026-10-13. 경로는 3090 기준이며 코드 구조 §5는 계획 시점 초안이다(실제 구조는 VIGS `scripts/floaterlab/README.md`). 결과 1–12는 실행 순서대로 아래에 덧붙였다.

# 사전등록: baseline 방법이 왜 우리 목적에 안 맞는가 — 학습 중 기전 측정 (3090, 2026-10-09)

목적: 벤치마크 수치(5090에서 별도)가 아니라, **각 baseline이 floater를 못 지우는 이유를 학습 중에 직접 측정**해
가설을 확인/기각한다. 이론 예측 → 측정 신호 → 기각 조건을 실행 전에 고정한다.

## 1. 하네스와 기준(base)
- 팀원 release `765d55d` (`run_bcd.py`), 자체 frontend, 기준 pose, 6N 예산. 3090에서 빌드한 엔진.
- **base = C에서 carve·FM만 뺀 것**: KF depth L1 .25 + normal + dense depth .25 + 학습 중 보호 prune + 종료 opacity<.1 정리.
  모든 arm은 base 위에 방법 하나만 켠다. 우리 방법 arm = base + Consensus Carve(SEW3) + FM = C와 동일(패리티 검사).
- 비교는 같은 seed, 같은 frontend 산출물 조건에서. 1 seed로 기전을 보고, 판정이 경계에 걸리면 seed 1 추가.

## 2. 데이터 (3 장면)
| 장면 | 이유 | floater 판정 |
|---|---|---|
| **aria1253** (0416_301-1253, 1,311 RGB) | 개발 장면. BA 오류 출생 30%, 윤곽 spill, 끝 출생 잔여 — 지금까지 기전 데이터 대부분이 여기 | held-out 라벨(노랑∪파랑) |
| **RPNG table_06** | free-space 출생 58%(가장 높음): 센서 순환 가설의 최강 시험 | held-out 라벨 |
| **TUM fr1_desk** | 팀원 벤치마크 포함, **GT depth** 있음 → 우리 라벨과 무관한 floater 판정(held-out view에서 GT 표면보다 앞) | GT 라벨 + held-out 라벨(라벨 순환 검증) |

## 3. 공통 측정 (모든 arm, probe ON)
- Gaussian별 stable point ID로 수명 추적: 출생 render, opacity 궤적, 시선 방향 위치 변화(카메라 쪽 −).
- **항별 gradient 분해**(k=10 render마다): RGB / KF depth / normal / dense depth / **방법 항** 각각의 opacity-logit 및
  시선 방향 위치 gradient를 `autograd.grad`로 따로 계산해 Gaussian별 창(300 render) 누적: 합, |합|, 양수 비율.
- 화소 통계(같은 cadence): 렌더 평균 깊이 vs 중앙값 불일치 화소 비율, 불투명 화소의 종료 깊이 이동(layer stripping).
- 종료 시 라벨로 Gaussian을 floater / 표면 / 기타로 나눠 위 값을 집단별로 요약.

## 4. arm별 가설과 기각 조건
| arm | 카테고리 | 이론 예측(왜 안 되나) | 측정 신호 | 가설 기각 조건 |
|---|---|---|---|---|
| D4: depth L1 ×4 | Frontend depth 정규화 | floater는 BA 깊이에서 태어나 자기 화소의 D̄≈D → depth 항 gradient가 floater에서 작다 | floater/표면의 depth 항 |∂/∂opacity| 비; floater 화소 중 |D̄−D|<5%D 비율 | floater의 depth 항 gradient가 표면 이상이고 floater 수가 base 대비 ×0.7 미만 |
| DNGh: DNGaussian hard(위치) | 〃 | 위치 gradient 부호를 목표가 정함 → floater는 시선 방향으로 이동, 꺼지지 않음; 일부는 표면 통과 | floater의 시선 변위 분포, 중앙값 표면 통과 비율, opacity 변화 | floater opacity 하강이 위치 이동보다 크다 |
| DNGs: DNGaussian soft(opacity) | 〃 | depth 항의 opacity gradient는 표면 성장에 쓰이고 floater에는 부호가 섞임 | floater에서 depth 항 opacity gradient의 "키움" 비율 | floater에서 "낮춤"이 80% 이상 |
| GS9: GS-SLAM 식 9 | 센서 free-space | (a) 출생 view에서 벌점 0(순환) (b) BA가 뒤에 찍힌 곳에서 표면 박리 | floater별 벌점 view 수·첫 벌점까지 시간; 벌점 받은 표면 Gaussian 수; 박리 화소 비율 | floater의 출생 view 벌점 비율 > 50%, 박리가 base 수준 |
| KL: DS-NeRF KL | 종료 분포 손실 | D 근처 질량을 키움 → D에서 태어난 floater를 강화 | floater opacity gradient 부호(키움 비율), 위치 이동 | floater "낮춤" 우세 + floater 감소 |
| DIST: 2DGS distortion | 자기참조 ray 통계 | 분포를 지배 모드로 수축할 뿐 누가 틀렸는지 구분 못함 → 같은 ray의 표면도 함께 움직임 | 같은 ray에서 floater vs 표면 gradient 비; hole·PSNR 부수 피해 | floater에 표면의 3배 이상 집중 |
| SH26: Sheng 2026 | 판정 후 삭제 | (a) 평균 깊이 기준이 floater에 끌려 표시 누락 (b) 모순 view가 드물어 10표에 못 미침(끝 출생) (c) 삭제 정밀도 낮음 | 평균·중앙값 판정 불일치; floater별 표 수의 시간 궤적·임계 도달 시간; 삭제 집합의 정밀도/재현율 | 끝 5 KF 출생도 임계 도달, 정밀도 > 50% |
| SPG: SparseGS 사후 mode prune | 판정 후 삭제 | mode 앞을 전부 삭제 → 얇은·앞쪽 실제 구조 삭제 | 삭제 정밀도/재현율, PSNR | 정밀도 > 50% |
| RST: 3DGS opacity reset | 온라인 지도 관리 | reset 후 모순 view가 없으면 floater도 다시 자란다; 표면은 그동안 손상 | reset 전후 floater·표면 opacity 회복 속도 | floater 회복이 표면보다 확실히 느림 |
| **CC: Consensus Carve + FM (우리)** | 자기 합의 | 합의 앞 기여만, opacity만 | floater/표면 carve gradient 비, 흐려지기까지 시간, 끝 출생 잔여 | — (패리티: C와 같은 카운터) |

각 baseline의 주 가중치는 aria1253에서 3값 이하로 스윕하고, "PSNR ≥ base−.05 dB 중 floater 최소"로 고른 뒤 다른 장면에 고정한다.

## 5. 코드 구조 (`scripts/floaterlab/`, bcd worktree, 별도 브랜치 — push는 지시 시)
```
floaterlab/
  arms/                    # arm 하나 = JSON 하나 (켜고 끄기는 여기서만)
    base.json  cc.json  d4.json  dng_hard.json  dng_soft.json  gs9.json  kl.json  dist.json  sh26.json  spg.json  rst.json
  runtime.py               # install(arm) / training_report() / finish(): C의 geometry_c.runtime 자리를 대신함
  hooks.py                 # backend 3지점(KF 손실, dense 손실, optimizer step)을 한 번만 감싸고 켜진 플러그인을 순서대로 호출
  methods/
    base.py                # Plugin 인터페이스: loss_terms(), opacity_grad(), on_render(), on_window(), export_mask()
    depth_l1.py  dng.py  gs_slam_eq9.py  ds_kl.py  distortion.py  sheng2026.py  sparsegs.py  opacity_reset.py
    consensus_carve.py     # upstream fixed40_floater(SEW3) + FM를 감싸 C와 비트 단위 동일 동작
  probe/
    lifecycle.py  grad_split.py  ray_stats.py
  run_arm.py               # release C 실행기(run_custom_c_large_pool_6n.py)의 최소 포크: geometry_c → floaterlab.runtime
  campaign.py              # 작업 목록 → systemd-run 풀, 이미 끝난 출력은 건너뜀
  report.py                # 라벨 계산 + §4 가설별 판정표 생성
  tests/                   # 플러그인 끄면 base와 동일, CC arm이 C와 같은 카운터, gradient 분해 합 = 총 gradient
```
환경변수는 쓰지 않는다(release가 FIXED40_*를 지운다). 모든 run은 `run_manifest.json`에 arm JSON, 소스 SHA, 3090 엔진 지문을 남긴다.

## 결과 1 — aria1253 seed 0, 내부 ablation arm (공식 코드 이식 아님), 2026-10-09
출력: vigs_aria_experiments/bcd_runs_20261009/floaterlab/aria1253/*_probe, 표: mechanism_stage1_aria1253.md. probe 검사 1.1–1.8e-6 (전 arm 유효).
- export floater: base 36/44(2 run) · cc 3 · sensor_carve 18 (PSNR −.16, G −7%) · dng_hard 36 · dng_soft 54 (−.10) · d4 92 (−.85).
- 생존 floater(export) ≠ 학습 직후 floater: 생존은 오래 산(마지막 10% 출생 16%) opacity ~.2 집단, 학습 직후는 77%가 막 태어나 이미 opacity .013.
- RGB 항은 생존 floater에 중립(fade share .49 ≈ 표면 .47) → photometric 침묵 확인.
- D4 가설 **수정**: depth gradient는 floater에서 작지 않고 오히려 6배 크다(4.8e-5 vs base 7.5e-6), 그러나 opacity 방향이 중립(.54). 예측 기전(작은 gradient)은 기각, 결론(못 지움)은 유지 — "크지만 방향이 없다".
- DNGs 지지: 주입 opacity gradient의 fade share 생존 .54 ≈ 표면 .53 (구분 없음).
- DNGh 지지: 학습 직후 floater의 위치를 91% 더 깊게 민다; export 수 base와 동일.
- sensor_carve: 방향 1.0이나 floater 주입 크기 cc의 ~1/6; 출생 view 벌점 0 가설은 이번 probe로 미측정(view별 기록 필요).

## 결과 2 — 공식 DNGaussian 이식 (Fictionarry/DNGaussian@22a588c, ORIGIN_dngaussian.md), aria1253 seed 0
- PSNR 26.750 (base 27.01–27.03, −.27), export floater 43 (base 36/44) → 감소 없음. hard 3,138 KF view 전부, soft 2,588.
- 생존 floater: soft(opacity) fade share .573 (약함), 표면 .466(=키움) → soft 항은 표면 성장에 쓰임(9월 D3F와 일치).
  hard: 생존 floater 위치 '더 깊게' .717. 주입 opacity 크기 3.3e-6 vs cc floater 2.2e-5.
- 내부 근사(dng_soft 54 / dng_hard 36)와 같은 결론 → 기전 해석이 근사 방식에 의존하지 않음. 표: mechanism_stage2_dngaussian.md.

## 결과 3 — 지도 관리 계열 (MonoGS @6c9254c, 3DGS @54c035f 이식 + 임계 스윕), aria1253 seed 0 (ORIGIN_maintenance.md)
| arm | 임계 | export floater | PSNR | Gaussian |
|---|---|---|---|---|
| base | .1 | 36/44 | 27.01–27.03 | 178k |
| maint_t03 | .3 | 18 | 26.78 | 133k |
| maint_t05 | .5 | 9 | 26.49 | 109k |
| MonoGS | .7 /150 | 0 | 25.79 | 58k |
| 3DGS | .005 + reset .01 @10–40% | 68 | 26.91 | 176k |
| cc | .1 | 3 | 27.01 | 178k |
기전(base 학습 지도): 생존 floater opacity 분위 .146/.182/.243/.309/.363 (10–90%), 표면 .133/.308/.739/.957/.99.
임계 t에서 지워지는 비율(생존 / 표면): .2 → .32/.16, .3 → .70/.24, .5 → 1.0/.37, .7 → 1.0/.48.
→ opacity는 생존 floater와 표면을 가르지 못한다. 3DGS reset은 floater도 표면처럼 다시 자라 floater가 늘었다(68).

## 결과 4 — Sheng 2026 (논문 식, ORIGIN_sheng2026.md), aria1253 seed 0
- φ .75: export floater 20, PSNR 26.557 (−.46), G 128,928 (−28%), 47 round, 감쇠 8,851.
- φ .9 : export floater 5,  PSNR 26.531 (−.49), G 129,093 (−28%), 감쇠 41,998 (4.7배) → floater 15개 더 줄이려 정상 Gaussian 수만 개 감쇠.
- 미측정: 감쇠 집합의 정밀도(라벨 대조). 다음 단계에서 감쇠 시점 ID 기록 후 학습 지도 라벨과 대조.

## 결과 5 — SparseGS (ForMyCat/SparseGS@95e7aef 판정 로직, 커널 재구현; ORIGIN_sparsegs.md), aria1253 seed 0
- export 시 112 KF view, 평균 dip .0011 → 백분위 97.2, 표시 화소 353,120, 삭제 10,423 / 195,105.
- export floater 34 (base 36/44), PSNR 24.216 (−2.8 dB). 첫 기여자~mode 전체 삭제가 앞쪽 실제 물체를 지움.
- 정밀도 미측정(삭제 직전 PLY 미저장) → runtime 수정: export 훅 arm은 before_method_export.ply 저장.

## 결과 6 — KL / SplatAD 가중치 스윕 (aria1253, 사전 규칙: PSNR ≥ base−.05 중 floater 최소; 없으면 PSNR 최고를 '실패'로 보고)
base 27.010 / export floater 44.
| arm | 가중치 | PSNR | Gaussian | export floater |
|---|---|---|---|---|
| dsnerf_kl | .1 (기본) | 18.07 | 54k | 31 |
| dsnerf_kl_w01 | .01 | 20.99 | 71k | 26 |
| dsnerf_kl_w001 | .001 | 25.66 | 133k | 64 |
| splatad | 1 (기본) | 22.16 | 71k | 6 |
| splatad_w01 | .1 | 26.31 | 122k | 30 |
| splatad_w001 | .01 | 26.945 | 162k | 49 |
기준 통과 가중치 없음 → 규칙대로 PSNR 최고 KL .001, SplatAD .01 선택(둘 다 '실패' 표기). 이 가중치에서 floater는 base보다 많다
(64, 49 vs 44): 지도를 지키는 세기에서는 floater를 못 지우고, 지우는 세기에서는 지도가 무너진다. table_06·TUM 재실행 = stage 7.

## 사전등록 — stage 8: 우리 방법 분해 (carve_only = SEW3 학습만, fm_only = base 학습 + FM), 3장면 seed 0, 2026-10-10
질문: floater 감소가 학습 중 carve 덕인가, export finisher(FM) 덕인가.
예측: (1) export floater는 fm_only ≈ cc (FM이 마지막 정리). (2) 학습 지도 floater(before_terminal_prune)는 carve_only ≈ cc < base
(aria·table), TUM은 차이 없음(stage 3에서 cc 92 vs base 90). (3) PSNR 세 arm 모두 base ±.05.
판정: (1)이 맞고 (2)가 틀리면 "carve는 불필요, FM만으로 충분"으로 보고한다.

## 사전등록 — stage 9: 용량을 맞춘 sensor carve (sensor_carve_l3, λ 3 = cc와 같은 λ, KF view만, gate 없음), 3장면 seed 0
이유: sensor_carve(λ .2)의 floater 주입 크기가 cc의 1/10이라 "기준 깊이" 차이와 "세기" 차이가 섞여 있었다.
예측: TUM(센서 깊이 정확)에서는 GT floater가 더 준다(<202). aria·table(frontend 깊이 오차)에서는 PSNR이 base보다 .1 dB 넘게
떨어지거나 Gaussian이 10% 넘게 준다. 맞으면 "기준이 틀린 곳에서는 세게 밀수록 실제 표면을 지운다"를 지지한다.
틀리면(aria·table에서도 PSNR ±.05, floater ≤ cc) sensor 기준이 우리와 동등하다고 보고한다.

## 결과 7 — 선택 가중치 (KL .001, SplatAD .01) table_06·TUM
KL .001: ΔPSNR −8.67 (table) / −1.46 (TUM), Gaussian −66% / −63%, floater 65 / 12, TUM GT 153. 가중치를 100배 줄여도 table 지도 붕괴 (Adam 정규화 + −log 특이점).
SplatAD .01: ΔPSNR −.04 / +.03, floater 11 / 14 (base 6 / 16), TUM GT 276. PSNR을 지키는 세기에서는 floater 효과 없음.

## 결과 8 — 우리 방법 분해 (stage 8; fm_only는 capture hook 누락으로 1차 실패 → evidence on, λ 0으로 재실행)
export floater carve_only 8 / 0 / 8, fm_only 11 / 0 / 2, cc 3 / 0 / 3 (base 44 / 6 / 16). 학습 지도 floater carve_only 499 / 144 / 90, fm_only 597 / 381 / 73.
예측 (1) aria에서 틀림 (11 vs 3), table·TUM 맞음; (2) 맞음; (3) 맞음 → "carve 불필요" 아님. carve = 학습 중 지도 정리, FM = 끝 정리, aria에서 둘 다 필요; TUM은 FM이 대부분.

## 결과 9 — 용량 맞춘 sensor carve (stage 9, λ 3)
ΔPSNR −1.63 / −1.73 / −.41, Gaussian −19% / −29% / −13%, export floater 8 / 0 / 4, TUM GT 120. floater 주입 4.1e-5 (cc 2.2e-5), 표면 주입 7.4e-8 (cc 6e-11, ~1,000배).
예측 모두 맞음 → "기준 깊이가 틀린 곳에서 같은 세기로 밀면 실제 표면을 지운다" 지지. 센서 정확한 TUM에서는 지도를 유지한 arm 중 외부 기준 floater 최저 1.74‰ (대가 −.41 dB; KL w.1·SplatAD w1은 더 낮으나 지도 붕괴). sensor arm은 KF만·gate 없음이라 기준 깊이 단독 비교는 아님 [2026-10-13 정정].

## 사전등록 — stage 11: GT 라벨이 재는 것 + 우리 방법 × sensor carve 조합, 2026-10-10
배경: TUM GT floater의 86–95%가 지도 기준으로는 표면이다 (GT 라벨은 대부분 "지도 표면이 Kinect보다 앞" 을 센다).
SparseGS의 GT 감소는 지도 크기 때문이 아니다 (보이는 Gaussian 78k = base); 앞쪽 표면 층 삭제로 GT 앞쪽 질량 1.97% → .99%.
(a) frontend 깊이 vs Kinect (base_depthdump, 학습 불변): 예측 — 픽셀 90% 이상이 10% 이내 일치. 그렇다면 sensor carve의 TUM 이득은
    "sensor 기준 ≈ GT 기준"이라는 같은 기준 효과로 설명된다.
(b) 지도 표면 vs Kinect (held-out 렌더 median): base에서 25% 넘게 앞인 픽셀 1.8% (시험 실행), 그중 경계 19%, 구멍 근처 23%.
    예측 — SparseGS·sensor carve는 front 비율이 base보다 낮고, 우리 방법(cc)은 base와 같다.
(c) cc_sensor02 = cc(느린 evidence 경로) + sensor carve λ .2, 대조군 cc_slow = cc(느린 경로). 3장면.
    예측 — TUM GT 비율이 cc_slow보다 낮다 (≈ sensor_carve 2.6‰). aria·table PSNR은 cc_slow 대비 −.1 dB 안팎 (sensor carve 단독 비용).
    export floater는 cc_slow 이하. 이 셋이 맞으면 "두 기준은 다른 오류를 고치며 더할 수 있다"로 보고, PSNR 비용이 장면마다 다르면 그대로 보고.

## 결과 10 — stage 11 (2026-10-10)
(a) frontend 깊이 vs Kinect (TUM KF 77장): 10% 이내 81.5%, 25% 넘게 앞 1.71%, 25% 넘게 뒤 3.62%. 예측(≥90%) **틀림**.
    지도 표면(held-out 렌더 median)은 10% 이내 90.6% → 지도가 자신의 depth 감독보다 Kinect에 더 가깝다.
(b) 지도 표면 vs Kinect (held-out 114장, 앞 / 뒤 / 10% 이내):
    base 1.83% / 1.29% / .906, cc 1.82 / 1.31 / .906, sensor λ.2 1.58 / 1.46 / .905, sensor λ3 1.10 / 2.34 / .890,
    SparseGS .97 / 3.95 / .876, MonoGS 1.93 / 1.46 / .902, cc+sensor .2 1.60 / 1.46 / .907.
    앞쪽 어긋남의 위치: 물체 경계 19–23%, Kinect 구멍 근처 18–23%, 나머지 ~57%.
    예측 맞음 (SparseGS·sensor < base, cc = base). 그러나 SparseGS는 앞 오차를 줄인 만큼 뒤 오차가 3배 → 10% 이내 비율은 오히려 낮다.
    → GT floater 라벨은 한쪽(앞)만 센다. 표면을 뒤로 미는 방법이 좋아 보인다. 양쪽을 다 보는 지표(10% 이내)에서는 어떤 방법도 base를 넘지 못한다.
(c) cc_sensor02 vs cc_slow: ΔPSNR −.13 / −.12 / −.01, Gaussian −6.5% / −7.6% / −3.3%, export floater 1/0/2 vs 2/0/1, TUM GT 2.59‰ vs 4.70‰.
    예측 대부분 맞음 (TUM export 2 vs 1은 1개 차). 두 기준의 효과는 더해지고, 비용은 sensor carve 단독 비용(−.15/−.11, −7/−8%)과 같다.
    cc_slow vs cc (빠른 경로): ΔPSNR −.04 / .00 / .00, export 2/0/1 vs 3/0/3 → 경로 차이는 잡음 수준.
    base_depthdump vs base: PSNR 19.901 vs 19.900, 앞 1.84% vs 1.83% → 기록 plugin은 학습을 바꾸지 않음.

## 사전등록 — stage 12: cc_nogate (cc에서 persistence gate만 끔, SELF_GATE=0), 3장면 seed 0, 2026-10-13
이유(5090 검토): sensor_carve_l3와 cc는 기준 깊이 외에 KF-only·gate 유무가 함께 다르다. gate의 몫을 분리한다.
예측: gate를 끄면 표면 주입(per seen)이 cc보다 커지지만 sensor λ3(~7e-8)보다는 작게 남는다(선택성 1e3 이상); export floater는 cc ±3; PSNR ±.05.
판정: 표면 주입이 sensor λ3 수준까지 오르면 "1,000배 차이의 주원인은 gate"로, 그대로 작으면 "주원인은 기준 깊이"로 보고한다. 중간이면 둘 다로 보고한다.

## 사전등록 — stage 13: recipe D 모체 파일럿 (3090, aria1253·TUM, seed 0), 2026-10-13
이유: 논문 표는 5090 최신 baseline(D) 위에서 내야 하고, D의 덮인 출생 .02는 우리가 지우는 신생 floater 집단과 겹친다.
(1) 패리티: `--recipe-base D --arm cc.json` PSNR = release D(`--recipe D`) ±.03 dB, Gaussian 수 ±1%.
(2) 예측: D base의 export floater는 C base(44/16)보다 적다(출생 .02). 우리 효과(cc−base)는 유지되나 폭은 줄 수 있다.
판정: cc_D의 floater가 base_D 대비 절반 이하이면 "D에서도 유효"; base_D 자체가 ≤5개면 "D가 이미 대부분 해결, 우리 방법의 추가 가치는 작다"로 정직하게 보고한다.

## 결과 11 — stage 12 cc_nogate (λ3, persistence gate OFF, FM ON), 3장면 seed 0, 2026-10-13
| arm | ΔPSNR(base) | Gaussian | export floater | 학습 지도 floater | 표면 주입/seen | 선택성(floater/표면) |
|---|---|---|---|---|---|---|
| cc (gate ON) | +.00 / +.01 / +.02 | 0% | 3 / 0 / 3 | 500 / 134 / 92 | 6.1e-11 / 1.7e-12 / 3.1e-10 | 3.6e5 / 6.1e6 / 1.1e4 |
| cc_nogate | **−2.23 / −2.39 / −.92** | −13 / −23 / −11% | 0 / 0 / 2 | 583 / 242 / 92 | 2.4e-8 / 7.9e-9 / 2.7e-8 | 1.8e3 / 1.3e3 / 646 |
| sensor λ3 (gate 없음, KF만, FM 없음) | −1.63 / −1.73 / −.41 | −19 / −29 / −13% | 8 / 0 / 4 | 536 / 294 / 116 | 7.4e-8 / 2.0e-8 / 6.3e-8 | 557 / 295 / 324 |
판정(사전 규칙): gate를 끄자 표면 주입이 sensor λ3의 1/3~1/2.5 수준까지 올랐다 → **"1,000배 선택성 차이의 주원인은 gate"**. 기준 깊이의 몫은 남은 2~3배.
PSNR 손실은 gate 없는 자기 median carve가 sensor λ3보다 크다(dose는 다름: 우리는 모든 training render, sensor는 KF만).
TUM GT floater 194(cc 385, sensor λ3 120), 양방향 10% 일치 87.2%(base 90.6, SparseGS 87.6), 앞 1.44% / 뒤 3.64%: gate 없는 carve는 판정-삭제 계열처럼 표면을 벗겨 뒤 오차를 만든다.
**정정:** stage 9의 "frontend 깊이가 틀린 곳에서 같은 세기로 밀면 표면이 지워진다"는 과장. λ3에서 표면을 지키는 부품은 persistence gate이며, 기준 깊이의 효과는 아직 분리되지 않았다.

## 사전등록 — stage 14: carve_l02_nogate (자기 median, λ .2, gate OFF, FM OFF = S36 SEG2 운영점), 3장면 seed 0
목적: sensor_carve λ .2(gate 없음, FM 없음, KF만)와 같은 세기·같은 gate 조건에서 기준 깊이의 몫을 분리한다(남는 차이: view 집합).
예측: ΔPSNR ±.05(S36의 SEG2 −.02), export floater는 base(44/6/16)와 carve_only(8/0/8) 사이, 표면 주입은 sensor λ.2(1.6e-8/3.5e-9/1.2e-8)보다 작다.
판정: 자기 median λ.2의 PSNR 손실이 sensor λ.2(−.15/−.11/+.01)보다 작고 표면 주입이 작으면 "기준 깊이도 선택성에 기여"; 비슷하면 "λ.2에서는 기준 깊이 효과 미미, gate가 전부".

## 결과 12 — stage 13 D 파일럿 (3090, seed 0)
aria: release D 27.412/110,347 · cc_D 27.407/111,684 (export 1, trained 78) · base_D 27.394/112,156 (export 16, trained 197).
TUM: release D 19.911/46,784 · cc_D 19.952/47,021 (0, 8; GT 289) · base_D 19.959/46,638 (5, 15; GT 295).
(1) 패리티: PSNR aria 통과(−.005), TUM 경계 밖(+.041); G +1.2%/+.5%(경계). 덮인 출생 수 동일(111/86) → patch 적용은 같음; 후보 원인 run 변동·probe·run_d.py의 vendor sys.path 순서. 5090에서 재확인.
(2) base_D floater 16/5 < C base 44/16 (예측 맞음). (3) cc_D/base_D = 1/16, 0/5 → "D에서도 유효"; 단 절대 수 작음, TUM은 "D가 이미 대부분 해결" 경계. 카드: gs_floaterLab campaigns/07_floater_mechanism/results_D_pilot/README.md.
