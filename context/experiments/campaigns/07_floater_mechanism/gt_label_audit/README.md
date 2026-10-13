# 외부 기준(Kinect GT) floater 라벨은 무엇을 재는가 — TUM fr1_desk (stage 11, 2026-10-10)

## 배경

TUM에서 Kinect 깊이 기준 floater는 base 384, cc 385로 우리 방법이 아무것도 못 한 것처럼 보였고, SparseGS(150)·sensor carve(202)가 좋아 보였다.
사용자 지적: "BA depth가 GT와 정확히 안 맞으니 GT 기준으로는 지도 표면도 floater 취급될 수 있지 않나." → 직접 쟀다.

## 1. GT 라벨에 걸린 것의 정체

| 방법 | GT floater | 그중 지도 기준 '표면' | 지도 기준 'floater' |
|---|---|---|---|
| base | 384 | 86% | 9 |
| cc | 385 | 90% | 2 |
| sensor carve λ.2 | 202 | 92% | 3 |
| MonoGS | 131 | 95% | 1 |

GT 라벨은 대부분 **지도 표면이 Kinect보다 25% 넘게 앞에 놓인 곳**을 센다. 지도 기준 floater는 우리 방법이 이미 2개로 줄였다.

## 2. 지도 표면 vs Kinect (held-out 114 view, 렌더 median 깊이 / Kinect)

| 대상 | 10% 이내 일치 ↑ | 25% 넘게 앞 | 25% 넘게 뒤 |
|---|---|---|---|
| frontend 깊이 (학습 KF 77장, `base_depthdump`) | 81.5% | 1.71% | 3.62% |
| 지도 표면 base | 90.6% | 1.83% | 1.29% |
| 지도 표면 cc | 90.6% | 1.82% | 1.31% |
| sensor carve λ.2 | 90.5% | 1.58% | 1.46% |
| sensor carve λ3 | 89.0% | 1.10% | 2.34% |
| SparseGS | **87.6%** | **.97%** | **3.95%** |
| MonoGS | 90.2% | 1.93% | 1.46% |
| DNGaussian / CG-SLAM / GOF / GS-SLAM Eq.9 | 90.5 / 90.6 / 90.9 / 90.6% | 2.17 / 1.96 / 1.89 / 1.74% | 1.18 / 1.24 / 1.36 / 1.46% |

- frontend 깊이는 Kinect와 생각보다 덜 맞는다(81.5%; 예측 90% 이상은 **틀림**). 지도 표면이 자기 학습 깊이보다 Kinect에 더 가깝다.
- 앞에 놓인 픽셀(1.8%)의 위치: 물체 경계 19–23%, Kinect 구멍 근처 18–23%, 넓은 면 ~57%.
- **SparseGS는 오차를 줄인 게 아니라 옮겼다.** 앞 오차 절반, 뒤 오차 3배(앞 층을 벗겨내자 뒤의 틀린 표면이 드러남). 지도 크기 때문이 아니다(보이는 Gaussian 78k = base). GT 앞쪽 질량 1.97% → .99%, PSNR −2.8 dB.
- sensor carve도 같은 방향이지만 약하다(λ.2 일치율 그대로, λ3 하락).

## 결론

- GT floater 수(한쪽 지표)만 보고하면 표면을 뒤로 밀거나 벗겨내는 방법이 이긴다. **양방향 지표(10% 일치율, AbsRel 등)를 같이 낸다.** 양방향에서는 어떤 방법도 base를 넘지 못했다.
- 우리 방법은 깊이 정확도를 해치지 않으면서 지도가 스스로와 모순되는 floater를 지운다. 지도-센서 불일치는 고치지 않는다.
- 도구: VIGS `scripts/floaterlab/analysis/surface_vs_gt.py`(held-out 렌더, GPU), `frontend_vs_gt.py`(CPU, `kf_depth.npz` 필요), `methods/depth_dump.py`(학습 불변 기록 plugin; base와 PSNR 19.901 vs 19.900).
