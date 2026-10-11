#!/usr/bin/env python3
"""Create the F10 UTMM suite directory on colin: 2N contracts for the 8 UTMM scenes, plan, scene selection, GPU receipt.

  python3 make_utmm_suite.py --output <new suite dir>

Contracts are copies of the audited UTMM author-reference 6N contracts with renders_per_training_input=2,
render_budget = 2 x training inputs, snapshot_renders every 384 renders + final. Archive, reference poses, held-out UIDs
and training UIDs are unchanged. CPU only; writes nothing outside --output.
"""
import argparse
import json
from pathlib import Path

INPUTS = Path('/ssd/intern/paperExperiments/runs/mapper_baselines/utmm_author_reference_6N_20261008_v1/inputs/utmm')
SCENES = ['square-1', 'square-2', 'ego-centric-1', 'ego-centric-2', 'ego-drive',
          'fast-straight', 'slow-straight-1', 'slow-straight-2']
HERE = Path(__file__).resolve().parent


def main():
    a = argparse.ArgumentParser(); a.add_argument('--output', type=Path, required=True); a.add_argument('--rpi', type=int, default=2)
    x = a.parse_args()
    if x.output.exists():
        raise FileExistsError(x.output)
    x.output.mkdir(parents=True)
    selection = []
    for scene in SCENES:
        c = json.loads((INPUTS / scene / 'v1/scene_contract.json').read_text())
        total = len(c['training_uids']) * x.rpi
        c.update(renders_per_training_input=x.rpi, render_budget=total,
                 snapshot_renders=list(range(384, total, 384)) + [total],
                 local_budget_note=f'F10 {x.rpi}N copy of {INPUTS / scene / "v1/scene_contract.json"}')
        d = x.output / 'contracts' / scene; d.mkdir(parents=True)
        (d / 'scene_contract.json').write_text(json.dumps(c, indent=1))
        selection.append(dict(dataset='utmm', scene=scene, scene_contract=str(d / 'scene_contract.json')))
    (x.output / 'scene_selection.json').write_text(json.dumps(dict(
        source=f'F10 UTMM 8-scene insertion x density screen, {x.rpi}N, reference start', selection=selection), indent=1))
    plan = json.loads((HERE / 'plan_utmm_2N.json').read_text()); plan['local_budget'] = f'{x.rpi}N'
    (x.output / 'plan.json').write_text(json.dumps(plan, indent=1))
    # Receipt that exempts no process: admission then requires an otherwise idle GPU (same as the local runs).
    (x.output / 'gpu_exception.json').write_text(json.dumps(dict(
        authorized_by='nobody: F10 reproduction has no exempt process; every other compute process blocks admission',
        pid=-1, start_ticks=0, cmdline_sha256='', scope='F10 UTMM insertion screen'), indent=1))
    print('prepared', x.output, [s['scene'] for s in selection])


if __name__ == '__main__':
    main()
