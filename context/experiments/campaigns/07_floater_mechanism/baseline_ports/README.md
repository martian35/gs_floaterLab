# 공식 코드 이식 — 출처·등급·변경점 (2026-10-09~10)

등급: **V** 공식 Python 그대로(입력만 교체) · **R** 공식 CUDA 또는 재구현을 같은 입력에서 수치 검증 · **P** 공개 코드 없음, 논문 식.
전체 변경점은 VIGS-SLAM-custom `scripts/floaterlab/methods/ORIGIN_<name>.md`에 줄 단위로 있다. 공식 clone(커밋 고정)은 3090 `official_baselines_20261009/`.

| 방법 | 저장소 @ 커밋 | 등급 | 그대로 쓴 것 | 바꾼 것 (왜) | 미공개라 추정한 값 |
|---|---|---|---|---|---|
| MonoGS prune | muskie82/MonoGS @6c9254c, slam_backend.py:288-304 | R | RGB-D 설정: opacity<.7 prune, 150 iteration마다 | iteration → training render; 가시성 prune은 단안 전용이라 원본대로 OFF; reset_opacity_nonvisible 미이식 | — |
| 3DGS opacity reset | graphdeco-inria/gaussian-splatting @54c035f, train.py:164-174, gaussian_model.py:258-261,452-465 | V | prune opacity<.005 /100, reset min(op,.01) 3000마다(<15000/30000) | 주기 → 6N 예산 비율(.1/.2/.3/.4); densify 미이식(하네스가 금지) | — |
| DNGaussian | Fictionarry/DNGaussian @22a588c, loss_utils.py:18-32,81-93, train_llff.py:93-140, gaussian_renderer:128-270 | V | normalize/patchify/margin_l2/smoothness 함수, hard(opacity .95, S/R 고정) / soft(opacity만), 가중치 .1/1/.1, patch 5–17, tol .00025 | 목표 = 단안 DPT → frontend BA 깊이(둘 다 깊이에 단조; patch 정규화라 스케일 무관); +inf 픽셀 patch 제거; 단계별 step → 같은 Adam step 합산(6N); KF view만; iteration → 예산 비율; 빈 mask NaN → 0 | — |
| GOF distortion | autonomousvision/gaussian-opacity-fields @5245b20 (rasterizer submodule 7b75ce3), train.py:162-188 | V/R | 공식 rasterizer 그대로 빌드(패키지 이름만 변경 + `#include <cstdint>`), λ 100, rendering[8].mean(), 15000/30000부터 | 학습 render마다 공식 rasterizer로 1회 추가 렌더(주 영상은 우리 렌더러); kernel_size 0; depth-normal 항 미추가(base에 normal 있음) | — |
| CG-SLAM | hjr37/CG-SLAM @a2df6d9 (rasterizer submodule 123b0c2), CG_SLAM.py:314-316, forward.cu:390-409 | R | 공식 rasterizer(depth 분산 CUDA) 그대로, .25·|mean−median| + .15·|var|, consis_loss 그대로 | KF view마다 1회 추가 렌더; gt_depth = frontend BA 깊이(비유한 픽셀 제외); pose 고정. τ=.025 reduce_opacity는 공식 코드에서 호출되지 않아 미이식 | — |
| DS-NeRF KL | dunbar12138/DSNeRF @cacad3c, loss.py:47-90 | P(+V 식) | −log(w+1e-5)·exp(−(z−D)²/2σ²) 식; opacity에 대한 정확한 gradient(T 결합 포함, autograd 대비 1e-16) | NeRF 샘플 간격 → 1; σ² = 1(정규화 단위) → σ = .25D m; 공식 설정은 KL을 끄고 MSE를 씀(명시) | 가중치 .1 (스윕 .01, .001) |
| SplatAD | carlinds/splatad @6e31ad7, rasterization.cu:2270-2275 | R | alpha_sum_until_points(D−.2 m보다 앞 Gaussian의 raw alpha 합)와 backward(v_opacity += v·G) | LiDAR → frontend 깊이; 손실은 neurad-studio에 있어 가중치 미공개 | 가중치 1 (스윕 .1, .01) |
| GS-SLAM Eq.9 | 논문 arXiv 2311.11700v4 §3.2 (yanchi-3dv/diff-gaussian-rasterization-for-gsslam @164d243는 rasterizer만, 식 없음) | P | Λ ← ηΛ if D − dist(X,P_uv) > γ, keyframe 추가 시 | D = KF frontend 깊이; 각 KF 첫 training render의 Adam step 직후 1회; dense view 제외 | η .01, γ .25D |
| Sheng 2026 | Displays 92:103349 §4.3 식 13–15 (공개 코드 없음) | P | 렌더 깊이 D̂(alpha 가중)와 중심 투영 깊이 비교 d < φD̂ − .1 m, ≥10 view, γ .01 | round = 현재 pool 각 view 1회 training render; 투표는 training render에서(추가 렌더 없음); LiDAR 미사용(논문도 surface loss에만) | φ .75 (민감도 .9) |
| SparseGS | ForMyCat/SparseGS @95e7aef, train.py:271-364, prune_utils.py:153-157, forward.cu:262-424 | V(+R) | calc_diff, dip test(diptest), percentile .98·exp(−7.5·dip) 하한 80, power −4, 첫 기여자~mode 삭제 | mode/alpha_depth/첫 기여자를 우리 커널로 계산(ray_sparsegs.cu; 공식 startIdx/endIdx는 fetch index를 써 의도된 list 위치로 수정); export 시 1회(공식: 20k iteration에 삭제 후 10k 추가 학습 — 온라인에 없음) | run.sh 값 사용 |

이식 검증: `tests/test_dngaussian_port.py` (공식 함수와 rtol 1e-3; std reduction 순서로 margin 원소가 뒤집혀 최대 8.5e-5), KL gradient autograd 대조 1e-16,
각 run의 `geometry_c.json → training.methods`에 plugin stats(적용 view 수 등)로 실제 작동 확인(29/29 run).

## 문헌 조사 정정 (공식 코드를 읽고 고친 것)

- SparseGS 임계는 .98 / 7.0(run.sh 7.5)이며 "0.97"은 코드에 없다.
- CG-SLAM의 τ=.025 opacity 감소(reduce_opacity)는 공식 코드에서 호출되지 않는다.
- GS-SLAM Eq.9는 공개 rasterizer 저장소에 없다(논문 식만).
- DS-NeRF 공식 설정은 KL을 끄고 depth MSE를 쓴다.
- MonoGS 가시성 prune은 단안 설정 전용이다(RGB-D에서는 opacity prune만).
