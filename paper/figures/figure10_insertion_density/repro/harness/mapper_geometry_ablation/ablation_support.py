"""Isolated cumulative ablation: never edits production B/C sources or defaults."""
import inspect
import json
import os
from pathlib import Path
import shutil
import textwrap

HERE = Path(__file__).resolve().parent
PLAN = Path(os.environ.get('ABLATION_PLAN', '/home/intern/gs_floaterLab/results/campaigns/03_benchmark_contract/mapper_geometry_ablation_20261009_v1/plan.json'))  # LOCAL: overridable
ARM = None


def configure(name):
    global ARM
    ARM = next(a for a in json.loads(PLAN.read_text())['arms'] if a['arm'] == name)
    os.environ['FIXED40_KF_LOSS'] = 'd3_normal' if ARM['normal_loss'] else 'd3'
    os.environ['FIXED40_DENSE_DEPTH'] = 'geo' if ARM['dense_depth_loss'] else 'off'
    scale = float(ARM.get('density_scale', 1.0))
    if scale != 1.0:                       # LOCAL: same lower birth density for every arm that sets it
        install_density_scale(scale)
    return ARM


def install_density_scale(scale):
    """Multiply pcd_downsample / pcd_downsample_init by 1/scale for every birth (scale 0.5 -> half the points)."""
    import gaussian.scene.gaussian_model as gm
    original = gm.GaussianModel.create_pcd_from_image_and_depth

    def density_scaled(self, *args, **kwargs):
        ds = self.config['Dataset']; keep = (ds['pcd_downsample'], ds['pcd_downsample_init'])
        ds['pcd_downsample'] = keep[0] / scale; ds['pcd_downsample_init'] = keep[1] / scale
        try:
            return original(self, *args, **kwargs)
        finally:
            ds['pcd_downsample'], ds['pcd_downsample_init'] = keep
    gm.GaussianModel.create_pcd_from_image_and_depth = density_scaled


def policy_options(arm):
    return dict(membership='immediate', batch_quotas=tuple(arm['batch_quotas']),
                auxiliary_mode=arm['auxiliary_mode'])


def install_initialization(arm, output):
    if arm['initialization'] != 'fixed_density_uniform':
        return
    import gaussian.scene.gaussian_model as gm
    bound = gm.GaussianModel.create_pcd_from_image_and_depth
    # LOCAL FIX (2026-10-09, 5070 Ti copy): recipe_setup already wrapped the method (online-density with_frame_uid),
    # so patch the wrapped original inside the closure and keep the wrapper.
    cell = None
    fn = bound
    while 'original' in fn.__code__.co_freevars:   # wrappers (density scale, online-density) -> innermost method
        cell = fn.__closure__[fn.__code__.co_freevars.index('original')]
        fn = cell.cell_contents
    original = fn
    source = textwrap.dedent(inspect.getsource(original))
    old = 'w = sob[rows, cols].astype(np.float64)\n            w = w + w.mean() * 0.1 + 1e-6\n            w /= w.sum()'
    if source.count(old) != 1:
        raise RuntimeError('Uniform initialization patch no longer matches locked upstream method')
    source = source.replace(old, 'w = np.full(len(rows), 1.0 / len(rows), dtype=np.float64)')
    path = Path(output) / 'harness_source/uniform_initialization_method.py'
    path.write_text(source)
    namespace = {}
    exec(compile(source, str(path), 'exec'), original.__globals__, namespace)
    if cell is not None:
        cell.cell_contents = namespace[original.__name__]
    else:
        gm.GaussianModel.create_pcd_from_image_and_depth = namespace[original.__name__]
    gm.content_multiplier = lambda *args, **kwargs: 2.5


def install_membership():
    import bounded_rgb_pool as bounded
    base = bounded.BoundedUnifiedTrainingSet

    class ImmediateBoundedTrainingSet(base):
        def __init__(self, **kwargs):
            if kwargs.get('membership') != 'immediate':
                raise ValueError('All ablation arms must use immediate membership')
            kwargs = dict(kwargs, membership='growth')
            super().__init__(**kwargs)
            self.membership = 'immediate'

        def _admit(self):
            if self._pending is not None:
                return
            waiting = self.offered.keys() - self.admitted - self.retired - self.keyframes
            for uid in sorted(waiting):
                victim = min(self.admitted) if len(self.admitted) >= self.dense_capacity else None
                if victim is not None:
                    if uid <= victim:
                        self.retired.add(uid)
                        continue
                    self.admitted.remove(victim)
                    self.retired.add(victim)
                    self.evictions.append(dict(uid=victim, replacement=uid, rgb_steps=self.rgb_steps_completed))
                self.admitted.add(uid)
                self.counts.setdefault(uid, 0)
                self.photometric_counts.setdefault(uid, 0)
                self.admission_ledger.append(dict(uid=uid, rgb_steps=self.rgb_steps_completed,
                    generation=self.generation, pool_size_after=len(self.keyframes | self.admitted),
                    keyframe_count=len(self.keyframes), dense_count=len(self.admitted)))
            self.peak_dense = max(self.peak_dense, len(self.admitted))
            assert len(self.admitted) <= self.dense_capacity

    bounded.BoundedUnifiedTrainingSet = ImmediateBoundedTrainingSet


def install(output):
    import runtime as native
    import fixed40_geometry as geometry
    import fixed40_dense_depth as dense
    if geometry.CFG['mode'] != ('d3_normal' if ARM['normal_loss'] else 'd3'):
        raise RuntimeError('Wrong normal-loss arm')
    if dense.CFG['mode'] != ('geo' if ARM['dense_depth_loss'] else 'off'):
        raise RuntimeError('Wrong dense-depth arm')
    if ARM['carving']:
        import fixed40_floater as floater
        floater.install()
        floater._carve_ext()
    paths = native.verify_sources()
    paths[str(HERE / 'ablation_support.py')] = native.digest(__file__)
    paths[str(PLAN)] = native.digest(PLAN)
    frozen = Path(output) / 'geometry_c_source'
    frozen.mkdir()
    for path, digest in paths.items():
        shutil.copy2(path, frozen / (digest[:12] + '_' + Path(path).name))
    return paths


def training_report(completed):
    import fixed40_geometry as geometry
    import fixed40_dense_depth as dense
    stats = {}
    if ARM['carving']:
        import fixed40_floater as floater
        stats = floater.stats()
        if stats.get('self_grad_views') != completed or stats.get('evi_grad_steps') != completed:
            raise RuntimeError('Carve gradient missing on training views')
    return dict(variant='mapper_geometry_ablation', arm=ARM, keyframe_loss=dict(geometry.CFG),
                dense_depth=dict(dense.CFG), dense_depth_stats=dense.stats(),
                carve_stats=stats, training_renders=completed)


def finish(topology, output, training_uids, heldout_uids, audit, guard):
    import runtime as native
    if ARM['carving']:
        mapper = topology.mapper
        if os.environ.get('ABLATION_FM_SKIP_NODEPTH') != '1':
            return native.finish(topology, output, training_uids, heldout_uids, audit, guard)
        # LOCAL (2026-10-10): FM export requires depth on every mapper keyframe; on new RGB-only sequences some keyframes
        # carry none or are flagged mapping_eval_excluded. Export over the remaining keyframes and record the skipped ones.
        keep = mapper.viewpoints
        skipped = sorted(u for u, v in keep.items() if (lambda w: w.depth is None or getattr(w, 'mapping_eval_excluded', False))(mapper._training_viewpoint(v)))
        mapper.viewpoints = {u: v for u, v in keep.items() if u not in skipped}
        try:
            out = native.finish(topology, output, training_uids, heldout_uids, audit, guard)
        finally:
            mapper.viewpoints = keep
        out['fm_skipped_keyframes_without_depth'] = skipped
        (Path(output) / 'fm_skipped_keyframes.json').write_text(json.dumps(dict(skipped=skipped, total=len(keep))))
        return out
    path = Path(output) / 'online_map.ply'
    model = topology.mapper.gaussians
    model.save_ply(str(path))
    return dict(terminal_opacity=dict(enabled=False, removed=0, optimizer_updates=0),
                fm=dict(enabled=False, optimizer_updates=0), optimizer_updates=0,
                extra_training_renders=0, postprocessing_renders=0,
                stages=[dict(ply=path.name, sha256=native.digest(path), gaussians=len(model.get_xyz))])
