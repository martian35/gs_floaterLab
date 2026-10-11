# Recipe D with vs without dense frames on UTMM — PREREG (2026-10-11, user approved)

**Question.** In recipe D, do dense (non-keyframe) RGB frames help at the same training budget?
**Arms.** D = colin's UTMM C reference-start runner (`mapper_reference_start/run_custom_c_reference_start.py`, 6N,
dense pool 1024 / recent 512) + scale cap 0.5 + selective births 0.5/0.02 (`d_recipe_shim.py`).
D-nodense = D with `auxiliary_mode=kf_native` (shim env B_AUX_MODE): the dense third of each unified batch (quota 3:3:6)
is filled with keyframes under their native loss, so no dense frame is rendered (and no dense-depth loss); total renders
stay 6N.
**Scenes.** UTMM all 8 (author-reference 6N inputs), seed 0, local RTX 5070 Ti; runner `run_d_dense_utmm.py`;
output `results/campaigns/gain_attribution/d_dense_utmm/v1/`. 16 runs. Evaluation/audit: colin's evaluate_run.py and
audit_custom_c_large_pool_6n.py unchanged. Read-out: PSNR/SSIM/LPIPS/Gaussians per scene, D-nodense − D; colin UTMM C
(`utmm_custom_c_reference_start_20261009_v1`) shown for reference only.

## Result (2026-10-11) — 16/16 runs, all audits passed
First launch stopped at import (raw `/home/intern` string on sys.path is not relocated locally); fixed to a Path; no run lost.
Verified per run: D roles `window/keyframe/dense`, D-nodense roles `window/keyframe/keyframe_native`, same 6N renders.
| scene | D PSNR / SSIM / LPIPS / Gaussians | D-nodense − D: PSNR / SSIM / LPIPS / Gaussians | D − colin C PSNR / Gaussians |
|---|---|---|---|
| fast-straight | 21.305 / 0.719 / 0.309 / 22,846 | −0.14 / −0.017 / +0.048 / +1.3% | +0.22 / −9% |
| slow-straight-1 | 18.830 / 0.678 / 0.314 / 17,195 | −0.69 / −0.024 / +0.049 / −0.4% | +0.02 / −1% |
| slow-straight-2 | 21.661 / 0.749 / 0.282 / 22,120 | −0.68 / −0.032 / +0.036 / +2.5% | −0.04 / −5% |
| square-1 | 20.063 / 0.660 / 0.367 / 62,315 | −0.82 / −0.054 / +0.073 / −3.9% | +0.13 / −35% |
| square-2 | 20.100 / 0.667 / 0.362 / 66,833 | −0.41 / −0.033 / +0.055 / −1.2% | +0.05 / −30% |
| ego-centric-1 | 20.638 / 0.726 / 0.282 / 53,279 | −0.60 / −0.049 / +0.087 / −2.1% | +0.09 / −27% |
| ego-centric-2 | 21.049 / 0.717 / 0.314 / 51,669 | −0.54 / −0.043 / +0.052 / +2.4% | +0.04 / −30% |
| ego-drive | 19.486 / 0.617 / 0.411 / 49,544 | −0.51 / −0.040 / +0.073 / −2.6% | +0.39 / −40% |
| mean | | **−0.55 / −0.037 / +0.059 / −0.5%** (8/8 worse) | +0.11 / −23% |
**Reading.** At the same 6N renders, removing dense frames from D costs 0.55 dB PSNR on average (−0.14…−0.82, 8/8),
SSIM −0.037 and LPIPS +0.059, with the same map size: dense frames are a large part of D's quality on UTMM. Side result:
D on UTMM is +0.11 dB over colin's C with 23 % fewer Gaussians (C from colin's RTX 5090 run; reference only).
