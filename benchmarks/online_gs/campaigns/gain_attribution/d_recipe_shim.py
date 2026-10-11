"""Recipe D shim: C's run_custom_c_large_pool_6n.py with scale cap 0.5 and selective births 0.5/0.02.

usage: python d_recipe_shim.py <path/to/run_custom_c_large_pool_6n.py> <its args...>
Env: B_SCALE_CAP (e.g. 0.5), B_COVERED_OPACITY (e.g. 0.02), B_AUX_MODE (dense_rgb | kf_rgb | kf_native: what fills the
'dense' third of each unified batch; kf_native = keyframes with their native loss, i.e. no dense frames); unset = unchanged.
No C file is modified: the patches replace GSBackEnd._project_mapping_scales and wrap GaussianModel.extend_from_pcd
at runtime, then the original script runs as __main__. Writes <output>/recipe_d.json.
"""
import atexit
import json
import os
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent


def main():
    script = Path(sys.argv[1]).resolve()
    args = sys.argv[2:]
    sys.argv = [str(script), *args]
    sys.path[0] = str(script.parent)
    sys.path.append(str(HERE))          # appended: this folder holds an older selected_mapping_check.py
    info = {k: os.environ.get(k) for k in ('B_SCALE_CAP', 'B_COVERED_OPACITY')}
    if os.environ.get('B_SCALE_CAP'):
        import scale_cap_patch
        scale_cap_patch.install(os.environ['B_SCALE_CAP'])
        import gs_backend
        proj = gs_backend.GSBackEnd._project_mapping_scales

        def counted(self, *a, **k):
            info['projection_calls'] = info.get('projection_calls', 0) + 1
            return proj(self, *a, **k)
        gs_backend.GSBackEnd._project_mapping_scales = counted
    if os.environ.get('B_COVERED_OPACITY'):
        import selop_patch
        selop_patch.install(probe=False)
        import gs_backend                # also capture the mapper here (C dispatches through OnlineMapperRuntime too)
        ptd = gs_backend.GSBackEnd.process_track_data

        def keep(self, packet):
            selop_patch.STATE['mapper'] = self
            return ptd(self, packet)
        gs_backend.GSBackEnd.process_track_data = keep
    if os.environ.get('B_AUX_MODE'):            # e.g. kf_native: the 'dense' training role samples keyframes instead
        sys.path.insert(0, str(script.parent.parent / 'mapper_baselines/v2'))   # the runner adds the same path
        import custom_common
        original_options = custom_common.options

        def options(*a, **k):
            out = original_options(*a, **k)
            out['auxiliary_mode'] = os.environ['B_AUX_MODE']
            return out
        custom_common.options = options
        info['B_AUX_MODE'] = os.environ['B_AUX_MODE']
    output = Path(args[args.index('--output') + 1]) if '--output' in args else None

    def dump():
        if output and output.exists():
            if os.environ.get('B_COVERED_OPACITY'):
                import selop_patch
                info['selop'] = dict(selop_patch.STATE['stats'])
            (output / 'recipe_d.json').write_text(json.dumps(info, indent=1) + '\n')
    atexit.register(dump)
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    main()
