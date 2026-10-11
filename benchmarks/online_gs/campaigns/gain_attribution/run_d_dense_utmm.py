#!/usr/bin/env python3
"""Recipe D with and without dense frames on UTMM (reference start, 6N), local queue.

  python run_d_dense_utmm.py --output <dir> [--scenes a,b,...]

Arms: D (colin's UTMM C reference-start runner + scale cap 0.5 + selective births 0.5/0.02) and D-nodense (same, but
auxiliary_mode=kf_native: the dense third of every unified batch (quota 3:3:6) is filled with keyframes under their native
loss, so dense frames are never rendered; total renders stay 6N). Training goes through d_recipe_shim.py around
mapper_reference_start/run_custom_c_reference_start.py; evaluation and audit use colin's evaluate_run.py and
audit_custom_c_large_pool_6n.py unchanged. Needs ROGO_MACHINE_PROFILE + relocation hook (ROGO_CHAIN_SITECUSTOMIZE=1).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BENCH = Path('/home/intern/gs_floaterLab/benchmarks/online_gs/campaigns/03_benchmark_contract')   # relocated
INPUTS = Path('/ssd/intern/paperExperiments/runs/mapper_baselines/utmm_author_reference_6N_20261008_v1/inputs/utmm')
SCENES = ['fast-straight', 'slow-straight-1', 'slow-straight-2', 'square-2', 'ego-centric-2', 'ego-drive', 'ego-centric-1', 'square-1']
ARMS = {'D': {}, 'D-nodense': {'B_AUX_MODE': 'kf_native'}}


def main():
    a = argparse.ArgumentParser(); a.add_argument('--output', type=Path, required=True); a.add_argument('--scenes')
    x = a.parse_args(); out = x.output; out.mkdir(parents=True, exist_ok=True)
    scenes = x.scenes.split(',') if x.scenes else SCENES
    sys.path.insert(0, '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping')
    from run_c import c_environment
    py, cwd, env = c_environment()
    equal = Path(os.fspath(BENCH / 'mapper_equal_render'))
    env.update(CUSTOM_C_BENCHMARK_BOOTSTRAP='1', CUSTOM_C_GPU_EXCEPTION_FILE=str(out / 'gpu_exception.json'),
               B_SCALE_CAP='0.5', B_COVERED_OPACITY='0.02')
    env['PYTHONPATH'] = str(equal / 'queue_python_bootstrap') + ':' + str(equal) + ':' + env['PYTHONPATH']
    if not (out / 'gpu_exception.json').exists():
        (out / 'gpu_exception.json').write_text(json.dumps(dict(authorized_by='nobody: local queue, every other compute process blocks admission',
                                                               pid=-1, start_ticks=0, cmdline_sha256='', scope='local D dense ablation')))
    progress = out / 'progress.json'
    state = json.loads(progress.read_text()) if progress.exists() else dict(rows=[])
    done = {(r['scene'], r['arm']) for r in state['rows'] if r['status'] == 'completed'}

    def run(cmd, log, extra):
        e = dict(env); e.update(extra)
        log.parent.mkdir(parents=True, exist_ok=True)
        while True:
            with log.open('w') as f:
                code = subprocess.call([py, *cmd], cwd=cwd, env=e, stdout=f, stderr=subprocess.STDOUT)
            if code != 75:
                return code
            time.sleep(10)                       # GPU busy (admission); retry
    for scene in scenes:
        contract = INPUTS / scene / 'v1/scene_contract.json'
        for arm, extra in ARMS.items():
            if (scene, arm) in done:
                continue
            run_dir = out / 'trials' / scene / arm
            row = dict(scene=scene, arm=arm, run=str(run_dir), started_at=time.time(), status='training')
            state['rows'] = [r for r in state['rows'] if (r['scene'], r['arm']) != (scene, arm)] + [row]
            progress.write_text(json.dumps(state, indent=1))
            steps = []
            if not (run_dir / 'runtime.json').exists():
                steps.append(('training', [str(HERE / 'd_recipe_shim.py'), str(BENCH / 'mapper_reference_start/run_custom_c_reference_start.py'),
                                           '--scene-contract', str(contract), '--output', str(run_dir)]))
            steps += [('evaluation', [str(equal / 'evaluate_run.py'), '--scene-contract', str(contract), '--run', str(run_dir),
                                      '--config', str(run_dir / 'native_sensor_config.yaml'), '--output', str(run_dir / 'evaluation')]),
                      ('audit', [str(equal / 'audit_custom_c_large_pool_6n.py'), '--scene-contract', str(contract), '--run', str(run_dir),
                                 '--evaluation', str(run_dir / 'evaluation'), '--output', str(run_dir / 'audit.json')])]
            for stage, cmd in steps:
                row['status'] = stage; progress.write_text(json.dumps(state, indent=1))
                code = run(cmd, out / 'logs' / scene / arm / f'{stage}.log', extra)
                if code:
                    row.update(status='failed', failed_stage=stage, returncode=code); break
            else:
                row.update(status='completed', finished_at=time.time())
            progress.write_text(json.dumps(state, indent=1))
    state['finished_at'] = time.time(); progress.write_text(json.dumps(state, indent=1))


if __name__ == '__main__':
    main()
