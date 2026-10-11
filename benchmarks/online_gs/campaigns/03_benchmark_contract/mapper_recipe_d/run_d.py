"""Apply the team's byte-identical D addon to the existing C benchmark runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
HERE=Path(__file__).resolve().parent
EQUAL=HERE.parent/'mapper_equal_render'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene-contract',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    p.add_argument('--pool-policy',choices=('legacy','temporal'),default='legacy')
    p.add_argument('--pool-capacity',type=int,default=512)
    p.add_argument('--pool-bin-width',type=int,default=64,
                   help='Fixed frame-UID accounting bin width; never a topology cutoff')
    p.add_argument('--pool-plan-renders',type=int,default=40,
                   help='Short planning horizon in single-view optimizer completions')
    p.add_argument('--replay-storage', choices=('legacy','full_ram','tiered_fifo'), default=None,
                   help='Default tiered_fifo for legacy pool; legacy for temporal pool')
    p.add_argument('--replay-gpu-capacity',type=int,default=512)
    p.add_argument('--replay-ram-capacity',type=int,default=1024)
    p.add_argument('--replay-ssd-directory',type=Path)
    p.add_argument('--dry-run',action='store_true',help='Print resolved launch without importing GPU code')
    return p

def launch_args(a, base, shim):
    capacity=a.pool_capacity if a.pool_policy=='temporal' else 1024
    return [str(shim),str(base),'--scene-contract',str(a.scene_contract),'--output',str(a.output),
            '--seed',str(a.seed),'--dense-capacity',str(capacity),'--recent-rgb-capacity','512']

def main():
    p=parser();a=p.parse_args()
    if min(a.pool_capacity,a.pool_bin_width,a.pool_plan_renders)<=0 or (a.pool_policy=='temporal' and a.pool_capacity<3):
        p.error('Positive pool settings required; temporal capacity must be at least 3')
    a.replay_storage = a.replay_storage or ('tiered_fifo' if a.pool_policy=='legacy' else 'legacy')
    if min(a.replay_gpu_capacity,a.replay_ram_capacity)<0:
        p.error('Storage capacities must be nonnegative')
    if a.pool_policy=='temporal' and a.replay_storage!='legacy':
        p.error('Tiered full replay is separate from the temporal retention experiment')
    storage_config=dict(mode=a.replay_storage,gpu_capacity=a.replay_gpu_capacity,
        ram_capacity=a.replay_ram_capacity,directory=str(a.replay_ssd_directory or a.output/'replay_images'))
    contract=json.loads(a.scene_contract.read_text())
    # Compare to the updated C on UTMM, and original C startup elsewhere.
    base=HERE.parent/'mapper_reference_start/run_custom_c_reference_start.py' if contract['dataset']=='utmm' else EQUAL/'run_custom_c_large_pool_6n.py'
    provenance=json.loads((HERE/'vendor/provenance.json').read_text())
    for name,h in provenance['files'].items():
        if sha(HERE/'vendor'/name)!=h:raise ValueError('Team D source modified: '+name)
    paths=[Path(__file__),HERE/'audit_d.py',HERE/'evaluate_d_stages.py',HERE/'vendor/provenance.json',*[HERE/'vendor'/n for n in provenance['files']]]
    if a.pool_policy=='temporal':
        paths.extend(HERE/n for n in ('temporal_pool.py','temporal_policy.py','temporal_runtime.py','temporal_depth.py','temporal_audit.py'))
    storage_dir=HERE.parent/'replay_storage'
    paths.extend(storage_dir/n for n in ('native_timing.py','storage_audit.py'))
    if a.replay_storage!='legacy':
        paths.extend(storage_dir/n for n in ('fifo_runtime.py','tiered_rgb.py'))
    payloads={str(f.resolve()):f.read_bytes() for f in paths}
    locks={p:hashlib.sha256(b).hexdigest() for p,b in payloads.items()}
    shim=HERE/'vendor/d_recipe_shim.py'
    argv=launch_args(a,base,shim)
    pool_config=dict(capacity=a.pool_capacity,bin_width=a.pool_bin_width,plan_renders=a.pool_plan_renders)
    if a.dry_run:
        print(json.dumps(dict(pool_policy=a.pool_policy,temporal_pool=pool_config if a.pool_policy=='temporal' else None,
            replay_storage=storage_config,argv=argv,base=str(base),vendor_verified=True,gpu_started=False),indent=2))
        return
    if a.output.exists():
        raise FileExistsError(a.output)
    restore=None
    if a.pool_policy=='temporal':
        sys.path[:0]=[str(HERE),'/home/intern/VIGS-SLAM-custom/vigs',
                      '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping']
        from temporal_runtime import install
        restore=install(pool_config)
    if a.replay_storage!='legacy':
        sys.path[:0]=[str(storage_dir),'/home/intern/VIGS-SLAM-custom/vigs',
            '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping']
        from fifo_runtime import install
        restore=install(storage_config)
    sys.path[:0]=[str(storage_dir),'/home/intern/VIGS-SLAM-custom/vigs',
        '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping']
    from native_timing import install as install_native_timing
    timing=install_native_timing()
    for name in ['B_COVERED_SCALE_CAP','B_WITH_REPLACEMENT','B_SELECTED_WORKER']:
        os.environ.pop(name,None)
    os.environ.update(B_SCALE_CAP='0.5',B_COVERED_OPACITY='0.02')
    sys.path.insert(0,str(HERE/'vendor'))
    sys.argv=argv
    try:
        runpy.run_path(str(shim),run_name='__main__')
        import scale_cap_patch,selop_patch
        assert Path(scale_cap_patch.__file__).resolve()==HERE/'vendor/scale_cap_patch.py'
        assert Path(selop_patch.__file__).resolve()==HERE/'vendor/selop_patch.py'
        assert selop_patch.OP==.02 and scale_cap_patch.SMALL['ids'] is None
        assert not selop_patch.STATE['stats'].get('error',0)
        assert all(sha(p)==h for p,h in locks.items())
        r=json.loads((a.output/'runtime.json').read_text())
        r['replay_storage_config']=storage_config
        r['mapper_additional_timing']=dict(timing)
        r['mapper_with_admission_seconds']=r['mapper_seconds']+sum(timing.values())
        r['mapper_with_admission_scope']='training service + image admission + mapper packet dispatch/birth + image adoption; excludes frontend, online topology outside service, export, IO snapshots'
        r['native_timing_synchronizes_boundaries']=True
        r['input_mapping_stream_seconds']=timing.stream_end-timing.stream_start
        r['input_mapping_stream_scope']='first RGB storage admission through last completed trainer call; includes frontend, interleaved input IO, mapper, intermediate snapshots/logs; excludes startup before first input and terminal export'
        r['training_pool_policy']=a.pool_policy
        r['recipe_configuration']=('D_'+a.replay_storage) if a.pool_policy=='legacy' else 'D_temporal_pool'
        if a.pool_policy=='temporal':
            from temporal_audit import audit_temporal
            r['temporal_pool_config']=pool_config
            r['temporal_pool_audit']=audit_temporal(r)
            (a.output/'temporal_pool_audit.json').write_text(json.dumps(r['temporal_pool_audit'],indent=2)+'\n')
        r.update(recipe_variant='D',recipe_d_provenance=provenance,
                 recipe_d=dict(scale_cap=.5,covered_opacity=.02,coverage_alpha=.6,depth_residual_multiplier=40.,
                    birth_count_and_positions_changed=False,optional_birth_probe_enabled=False,
                    extra_coverage_renders=int(selop_patch.STATE['stats'].get('births',0)),
                    C_backbone=str(base),UTMM_reference_start_fix=contract['dataset']=='utmm'))
        r['unified_scale_projection']['max_scale']=.5
        r['source_locks'].update(locks)
        (a.output/'runtime.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    finally:
        if restore is not None:
            restore()
        if a.output.exists():
            frozen=a.output/'recipe_d_source';frozen.mkdir(exist_ok=True)
            for path,b in payloads.items():(frozen/(locks[path][:12]+'_'+Path(path).name)).write_bytes(b)
            (a.output/'recipe_d_source_locks.json').write_text(json.dumps(locks,indent=2)+'\n')

if __name__=='__main__':main()
