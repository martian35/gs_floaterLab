# recipe D 모체 파일럿 — release D vs 우리 arm(D shim) (3090, seed 0, aria1253·TUM; stage 13, 2026-10-13)

목적: 논문 표는 5090 최신 baseline(D = C + scale cap .5 + 덮인 출생 opacity .02) 위에서 내야 한다. D의 덮인 출생 .02는 우리가 지우는 신생 floater 집단과
겹치므로, 5090 캠페인 전에 (1) floaterlab의 `--recipe-base D` 경로가 release D와 같은 숫자를 내는지 (2) D에서 base의 floater가 얼마나 남고 우리 효과가 유지되는지 봤다.
사전등록: [PREREG.md](../PREREG.md) stage 13. 원자료: `results/campaigns/07_floater_mechanism/{aria,tum_rgbd}/*/{releaseD_s0, cc_s0_probe, base_s0_probe}` (floaterlab_D root).

| run | PSNR | Gaussian | export floater (‰) | 학습 지도 floater | TUM GT floater |
|---|---|---|---|---|---|
| release D (`launch.py --recipe D` = run_d.py + audit) aria1253 | 27.412 | 110,347 | — | — | — |
| cc on D (shim + floaterlab, probe ON) aria1253 | 27.407 | 111,684 | **1 (.009)** | 78 | — |
| base on D (= D − SEW3 − FM) aria1253 | 27.394 | 112,156 | 16 (.145) | 197 | — |
| release D TUM fr1_desk | 19.911 | 46,784 | — | — | — |
| cc on D TUM | 19.952 | 47,021 | **0 (.000)** | 8 | 289 |
| base on D TUM | 19.959 | 46,638 | 5 (.118) | 15 | 295 |
| (참고) C base / cc aria1253 | 27.010 / 27.014 | 178k | 44 (.26) / 3 (.02) | 619 / 500 | — |
| (참고) C base / cc TUM | 19.900 / 19.917 | 104k | 16 (.20) / 3 (.04) | 90 / 92 | 384 / 385 |

## 판정

1. **패리티.** aria: PSNR Δ −.005 dB(통과), Gaussian +1.2%(기준 ±1%, 경계). TUM: PSNR +.041(기준 ±.03, 경계 밖), Gaussian +.5%.
   덮인 출생 수(111 / 86)는 release D와 우리 경로가 같다 → shim의 두 patch는 동일하게 적용됐다. 남은 후보: (a) 작은 장면의 run 간 변동(이 하네스 base 두 run .017 dB, C 재현 .3%),
   (b) probe ON/OFF, (c) run_d.py는 vendor 폴더를 sys.path 맨 앞에, shim 단독 실행은 맨 뒤에 둔다(vendor의 옛 `selected_mapping_check.py`가 release 경로에서만 앞설 수 있음).
   → 5090에서는 같은 seed로 release D와 cc_D를 한 번 더 비교하고, 필요하면 probe 없이도 비교한다. **D 경로 자체는 동작한다.**
2. **D는 base의 floater를 2.7~3배 줄인다** (44 → 16, 16 → 5; 비율 .26 → .145‰, .20 → .118‰). 예측대로 덮인 출생 .02가 신생 floater를 흡수한다.
3. **우리 효과는 D에서도 유지된다**: cc_D/base_D = 1/16, 0/5(≤ 절반 기준 통과), PSNR ±.01. 학습 지도에서도 197 → 78, 15 → 8.
   다만 절대 수가 작다(aria 15개, TUM 5개 차이). 논문 표는 seed 3개와 장면 추가(table_06, ETH3D)가 있어야 한다. TUM은 base_D 5개로 "D가 이미 대부분 해결" 경계에 있다.
4. TUM GT 라벨(한쪽만 셈)은 289 vs 295로 차이 없음 — C에서와 같다.
