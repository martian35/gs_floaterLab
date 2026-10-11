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
