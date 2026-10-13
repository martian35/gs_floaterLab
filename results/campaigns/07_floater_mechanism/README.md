# GEO campaign — 경량 결과 번들 (3090, 2026-10-09~11)

`<dataset>/<scene>/<arm>_s0[_probe]/` 77 run. PLY·probe npz·render ledger·로그는 3090 `vigs_aria_experiments/bcd_runs_20261009/floaterlab*`에 남겨 두었다(약 29 GB).

| 파일 | 내용 |
|---|---|
| `quality.json` | release 평가기 출력 (mean_psnr/ssim/lpips, gaussian_count, completed_renders …) |
| `label_online_map.json`, `label_before_terminal_prune.json`, `label_before_method_export.json` | held-out floater 라벨(지도 median 기준): floaters, visible, heldout_views, rule |
| `label_gt_online_map.json` | TUM만: Kinect 기준 라벨 (앞쪽만 셈 — gt_label_audit 참조) |
| `mechanism.json` | probe × 라벨: survivor/floater/surface 집단별 fade·deeper share, per-seen 크기, 출생 시점, opacity |
| `geometry_c.json` | arm 설정, carve 적용 횟수, plugin stats(방법이 실제로 작동했는지), export 단계 Gaussian 수 |
| `floaterlab_export.json` | export 훅 방법(SparseGS, depth_dump)의 결과 |
| `surface_vs_gt.json`, `frontend_vs_gt.json` | TUM: 지도 표면 / frontend 깊이 vs Kinect 양방향 비교 |
| `probe_summary.json` | probe 설정과 .grad 일치 검사(check_max_rel) |
| `runtime_summary.json` | mapper/whole 초, VRAM, 입력 수, pose_mode, reference_kind |
| `launch.json` | arm 경로, seed, probe, scene contract |

`runs_index.json`: run별 (root, scene, dataset, arm, probe, psnr, ssim, lpips, gaussians, floaters_export/trained, gt_floaters_export, mapper_seconds, source_run).
`tables/`: ALL_RESULTS.{md,json}(summarize.py), FULL_PERFORMANCE.md, TABLE_BASELINE_MAIN.{md,tex}, selectivity_table.md, stage_table.md, deletion_precision_ours.json, mechanism_stage1/2.md.
aria1253 SparseGS run은 삭제 직전 PLY 저장 기능 이전에 돌아 mechanism.json이 없다(ALL_RESULTS.json의 mechanism_error).
