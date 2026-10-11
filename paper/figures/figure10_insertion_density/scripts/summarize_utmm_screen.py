#!/usr/bin/env python3
"""Summarise a finished UTMM insertion x density screen (F10 data). Reads evaluation/quality.json only; never trains.

  python summarize_utmm_screen.py --run-root <suite output> --out-dir <dir> [--reference <runs csv>]

Writes <out-dir>/runs.csv (one row per scene and arm) and <out-dir>/mean_by_arm.csv (scene-mean change against
uniform insertion at density 1, `R2@1`). With --reference, prints the per-run PSNR difference against another runs.csv
(e.g. colin reproduction vs the local 5070 Ti runs in ../analysis/).
"""
import argparse
import csv
import glob
import json
from pathlib import Path
from statistics import mean

SCENES = ['square-1', 'square-2', 'ego-centric-1', 'ego-centric-2', 'ego-drive',
          'fast-straight', 'slow-straight-1', 'slow-straight-2']
ARMS = ['R2@0.5', 'R2-I@0.5', 'R2@0.75', 'R2-I@0.75', 'R2@1', 'R2-I@1', 'R2@1.5', 'R2-I@1.5']


def load(root):
    rows = []
    for q in sorted(glob.glob(str(Path(root) / 'trials/*/*/*/seed0/evaluation/quality.json'))):
        p = Path(q).parts
        scene, arm = p[-5], p[-4]
        if arm not in ARMS:
            continue
        j = json.loads(Path(q).read_text())
        method, density = arm.split('@')
        rows.append(dict(scene=scene, arm=arm, method='uniform' if method == 'R2' else 'content_aware',
                         density=float(density), psnr=j['mean_psnr'], ssim=j['mean_ssim'], lpips=j['mean_lpips'],
                         gaussians=j['gaussian_count'], heldout_views=j['view_count'], run=str(Path(q).parents[1])))
    return rows


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--run-root', required=True); a.add_argument('--out-dir', required=True)
    a.add_argument('--reference')
    x = a.parse_args()
    rows = load(x.run_root)
    out = Path(x.out_dir); out.mkdir(parents=True, exist_ok=True)
    with open(out / 'runs.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    by = {(r['scene'], r['arm']): r for r in rows}
    scenes = [s for s in SCENES if all((s, arm) in by for arm in ARMS)]
    means = []
    for arm in ARMS:
        d = [(by[(s, arm)], by[(s, 'R2@1')]) for s in scenes]
        dp = [r['psnr'] - b['psnr'] for r, b in d]
        means.append(dict(arm=arm, method=by[(scenes[0], arm)]['method'], density=float(arm.split('@')[1]), scenes=len(d),
                          dpsnr_db_mean=mean(dp), dpsnr_db_min=min(dp), dpsnr_db_max=max(dp),
                          dgauss_pct_mean=100 * mean(r['gaussians'] / b['gaussians'] - 1 for r, b in d),
                          dssim_mean=mean(r['ssim'] - b['ssim'] for r, b in d),
                          dlpips_mean=mean(r['lpips'] - b['lpips'] for r, b in d),
                          scenes_psnr_ge_baseline=sum(v >= 0 for v in dp)))
    with open(out / 'mean_by_arm.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(means[0])); w.writeheader(); w.writerows(means)
    for m in means:
        print(f"{m['arm']:10s} n={m['scenes']} dPSNR {m['dpsnr_db_mean']:+.3f} [{m['dpsnr_db_min']:+.2f},{m['dpsnr_db_max']:+.2f}] "
              f"Gaussians {m['dgauss_pct_mean']:+.1f}% dLPIPS {m['dlpips_mean']:+.4f} ({m['scenes_psnr_ge_baseline']}/{m['scenes']} >= U1)")
    if x.reference:
        ref = {(r['scene'], r['arm']): float(r['psnr']) for r in csv.DictReader(open(x.reference))}
        diff = [by[k]['psnr'] - v for k, v in ref.items() if k in by]
        print(f'vs reference: {len(diff)} runs, PSNR difference mean {mean(diff):+.3f}, max |d| {max(map(abs, diff)):.3f} dB')


if __name__ == '__main__':
    main()
