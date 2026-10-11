# F10 결과 스냅샷

수집 시각: **2026-10-11**. 정적 기록이며 이후 진행 상황을 자동 반영하지 않는다.
모든 run은 로컬 RTX 5070 Ti(16 GB), colin 2026-10-09 코드 상태(아래 provenance)와 패치된 geometry-ablation 하네스.
PSNR/SSIM/LPIPS는 held-out 프레임 평균(평가 프레임은 학습에 쓰지 않음), Gaussians는 최종 저장 지도의 개수.
U = 균등 삽입(R2, fixed_density_uniform), I = 내용 기반 삽입(R2-I, online_rank_gradient_weighted). 숫자 뒤 배율은 생성 밀도.

## 1. 정본 — UTMM 8장면, 2N, reference start (`utmm_2N_reference_start/`)

장면별 기준(U1) 대비 ΔPSNR (dB) / ΔGaussians:

| scene | U1 PSNR (dB) | U1 Gaussians | U0.5 | U0.75 | U1.5 | I0.5 | I0.75 | I1 | I1.5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| square-1 | 18.628 | 141,898 | -0.33 / -49% | -0.13 / -24% | +0.10 / +48% | -0.19 / -57% | +0.05 / -37% | +0.14 / -16% | +0.23 / +24% |
| square-2 | 18.883 | 128,760 | -0.30 / -49% | -0.08 / -25% | +0.14 / +49% | -0.06 / -54% | +0.11 / -32% | +0.18 / -9% | +0.27 / +36% |
| ego-centric-1 | 19.276 | 105,241 | -0.27 / -49% | -0.10 / -25% | +0.10 / +49% | -0.05 / -52% | +0.08 / -28% | +0.16 / -5% | +0.25 / +42% |
| ego-centric-2 | 19.625 | 115,756 | -0.30 / -49% | -0.12 / -25% | +0.13 / +49% | -0.04 / -53% | +0.10 / -30% | +0.20 / -7% | +0.32 / +39% |
| ego-drive | 18.245 | 138,041 | -0.13 / -48% | -0.04 / -24% | +0.03 / +48% | -0.02 / -55% | +0.02 / -34% | +0.04 / -14% | +0.08 / +28% |
| fast-straight | 19.435 | 38,918 | -0.24 / -50% | -0.09 / -25% | +0.14 / +50% | +0.54 / -57% | +0.64 / -36% | +0.67 / -15% | +0.66 / +28% |
| slow-straight-1 | 17.370 | 20,758 | -0.24 / -50% | -0.12 / -25% | +0.11 / +50% | +0.21 / -53% | +0.30 / -29% | +0.31 / -5% | +0.27 / +42% |
| slow-straight-2 | 20.152 | 33,733 | -0.34 / -50% | -0.12 / -25% | +0.05 / +50% | +0.26 / -56% | +0.37 / -34% | +0.41 / -12% | +0.37 / +31% |

8장면 평균은 [mean_by_arm.csv](utmm_2N_reference_start/mean_by_arm.csv)와 [계획](../plan/CURRENT.md) 표.
I0.75: Gaussian −32.6%, PSNR +0.207 dB(8/8 ≥ 기준), SSIM +0.007, LPIPS −0.006.
파일럿 통과: square-1 tape capture 19.281 dB / 재생 19.278 dB, Gaussians 116,957 / 116,993, 같은 tape·loss view 순서·render 수.

## 2. 재현 확인 — 같은 설계, IMU 초기화 뒤 지도 시작 (`utmm_2N_imu_gated/`, 5장면)

직선 주행 3장면은 IMU 초기화가 끝나지 않아 지도가 없었다(이후 reference start로 해결).
같은 5장면에서 두 실행의 I0.75 − U1 차이는 0.05 dB 이내로 같았다. 절대 PSNR은 실행 간 평균 +0.126 dB(최대 |차이| 0.260) 달라서,
그림은 절대값이 아니라 같은 실행 안의 기준 대비 변화만 쓴다.

| scene | U1 PSNR (dB) | U1 Gaussians | U0.5 | U0.75 | U1.5 | I0.5 | I0.75 | I1 | I1.5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| square-1 | 18.603 | 139,371 | -0.33 / -49% | -0.09 / -24% | +0.11 / +49% | -0.22 / -57% | +0.01 / -37% | +0.10 / -16% | +0.19 / +24% |
| square-2 | 19.105 | 125,562 | -0.27 / -49% | -0.09 / -25% | +0.12 / +49% | -0.02 / -54% | +0.13 / -32% | +0.20 / -10% | +0.27 / +35% |
| ego-centric-1 | 19.510 | 98,704 | -0.29 / -49% | -0.10 / -24% | +0.12 / +49% | -0.06 / -51% | +0.08 / -28% | +0.17 / -4% | +0.27 / +42% |
| ego-centric-2 | 19.830 | 109,409 | -0.30 / -49% | -0.14 / -25% | +0.15 / +49% | -0.08 / -53% | +0.10 / -30% | +0.18 / -7% | +0.30 / +39% |
| ego-drive | 18.230 | 137,444 | -0.10 / -48% | -0.03 / -24% | +0.02 / +49% | -0.01 / -55% | +0.04 / -34% | +0.07 / -13% | +0.10 / +29% |

## 3. 다른 데이터셋 (그림 제외, 근거)

`other_tests_runs.csv`. I의 효과(밀도 1)와 균등 삽입의 개수 민감도:

| 실험 | 데이터셋/장면 | 예산 | 균등 1 PSNR, Gaussians | I1 − U1 PSNR / LPIPS | 균등 저밀도 − U1 PSNR | 균등 1.5 − U1 PSNR |
|---|---|---|---|---:|---:|---:|
| density_x_budget | aria 0416_301-305 | 1N | 25.86, 319k | +0.05 / -0.011 | -0.33 (0.25) |  |
| density_x_budget | aria 0416_301-305 | 2N | 27.21, 297k | -0.03 / -0.007 | -0.51 (0.25) |  |
| density_x_budget | aria 0416_301-305 | 3N | 28.01, 282k | +0.02 / -0.005 | -0.65 (0.25) |  |
| density_x_budget | eth3d sofa_1 | 1N | 24.32, 245k | +0.09 / -0.008 | +0.04 (0.25) |  |
| density_x_budget | eth3d sofa_1 | 2N | 25.86, 221k | +0.08 / -0.002 | +0.18 (0.25) |  |
| density_x_budget | eth3d sofa_1 | 3N | 26.73, 201k | +0.10 / -0.006 | +0.21 (0.25) |  |
| density_x_budget | rpng table_01 | 1N | 21.37, 676k | +0.00 / -0.005 | -0.24 (0.25) |  |
| density_x_budget | rpng table_01 | 2N | 21.68, 304k | +0.02 / -0.004 | -0.23 (0.25) |  |
| density_x_budget | rpng table_01 | 3N | 21.87, 280k | +0.01 / +0.000 | -0.25 (0.25) |  |
| density_x_budget | tum_rgbd rgbd_dataset_freiburg1_desk | 1N | 18.92, 226k | +0.01 / -0.003 | -0.04 (0.25) |  |
| density_x_budget | tum_rgbd rgbd_dataset_freiburg1_desk | 2N | 19.18, 187k | +0.10 / -0.001 | +0.09 (0.25) |  |
| density_x_budget | tum_rgbd rgbd_dataset_freiburg1_desk | 3N | 19.50, 178k | +0.02 / -0.005 | +0.04 (0.25) |  |
| density_x_budget | utmm square-1 | 1N | 18.20, 146k | +0.09 / -0.022 | -0.95 (0.25) |  |
| density_x_budget | utmm square-1 | 2N | 18.59, 139k | +0.12 / -0.026 | -0.97 (0.25) |  |
| density_x_budget | utmm square-1 | 3N | 18.76, 136k | +0.13 / -0.022 | -1.02 (0.25) |  |
| density_x_budget RPNG table_02 | rpng table_02 | 1N | 19.17, 592k | -0.00 / +0.005 | -0.10 (0.25) |  |
| density_x_budget RPNG table_02 | rpng table_02 | 2N | 19.61, 471k | +0.02 / +0.007 | -0.12 (0.25) |  |
| density_x_budget RPNG table_02 | rpng table_02 | 3N | 20.01, 428k | -0.00 / +0.010 | -0.15 (0.25) |  |
| new datasets | mipnerf360 bicycle | 2N | 15.04, 373k | -0.04 / -0.004 | +0.10 (0.5) | -0.23 |
| new datasets | statichikes forest1 | 2N | 15.32, 193k | +0.05 / -0.003 | -0.06 (0.5) | +0.03 |
| new datasets | statichikes forest2 | 2N | 19.65, 162k | -0.05 / +0.007 | -0.46 (0.5) | +0.17 |
| new datasets | statichikes university2 | 2N | 18.39, 226k | +0.04 / -0.017 | -0.15 (0.5) | +0.02 |
| new datasets | tandt train | 2N | 15.10, 403k | -0.25 / +0.001 | -0.16 (0.5) | +0.08 |
| new datasets | tandt truck | 2N | 17.03, 368k | -0.01 / -0.016 | -0.41 (0.5) | -0.11 |

요약: UTMM 외에서는 I1 − U1 PSNR이 −0.25…+0.10 dB이고, StaticHikes·MipNeRF360·T&T에서는 균등 1.5도 PSNR을 올리지 않는다(평균 −0.01 dB).
저밀도 손실은 UTMM square-1(약 −1 dB)과 Aria(−0.33…−0.65 dB)에서 크지만, I가 PSNR 이득을 내는 것은 UTMM뿐이다.
MipNeRF360 garden은 tracking 실패(frame 162)로 제외. UTMM square-1 행(밀도×예산)은 IMU 초기화 뒤 지도 시작 조건이다.

## 4. 이미지 디테일 집중도 (GPU 없음, `content_concentration.json`)

학습 프레임 40장, 640 px 폭, Sobel 크기의 Gini와 평평한 영역 비율(95백분위의 10% 미만).

| 장면 | Gini | 평평한 비율 |
|---|---:|---:|
| utmm/ego-centric-1 | 0.709 | 0.631 |
| utmm/ego-centric-2 | 0.708 | 0.625 |
| utmm/slow-straight-2 | 0.698 | 0.603 |
| utmm/fast-straight | 0.695 | 0.599 |
| utmm/slow-straight-1 | 0.689 | 0.584 |
| tum_rgbd/rgbd_dataset_freiburg1_desk | 0.688 | 0.609 |
| utmm/square-2 | 0.670 | 0.562 |
| utmm/ego-drive | 0.664 | 0.553 |
| utmm/square-1 | 0.662 | 0.546 |
| aria/0416_301-305 | 0.622 | 0.386 |
| rpng/table_01 | 0.588 | 0.439 |
| rpng/table_02 | 0.535 | 0.357 |
| eth3d/sofa_1 | 0.510 | 0.187 |
