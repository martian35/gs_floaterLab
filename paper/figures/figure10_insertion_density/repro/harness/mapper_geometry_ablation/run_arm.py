"""TUM cumulative mapper/geometry ablation with shared causal frontend packets.

Derived from the bounded Custom C 6N adapter. Production sources are unchanged;
arm settings, immediate membership, initialization and export stages are explicit.
Intermediate PLYs are omitted; quota barriers and causal poses are retained.
"""
import argparse
from collections import deque
import copy
import json
from pathlib import Path
import random
import shutil
import sys
import time
from types import MethodType

ABLATION = Path(__file__).resolve().parent
HERE = ABLATION.parent / 'mapper_equal_render'
sys.path.insert(0, str(HERE))
V2 = HERE.parent / 'mapper_baselines/v2'
sys.path.insert(0, str(V2))
from custom_common import (verify_recipe, recipe_setup, options, WorkAudit,
                           install_reference_pose_adapter, camera_poses, write, sha,
                           finish_selected_topology)
from render_quota import RenderQuota
sys.path.insert(0, '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping')
import ablation_support as geometry_c
from frontend_tape import FrontendTape


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene-contract', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--arm', required=True)   # LOCAL: any arm defined in the plan
    p.add_argument('--frontend-cache', type=Path, required=True)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--dense-capacity', type=int, default=1024)
    p.add_argument('--recent-rgb-capacity', type=int, default=512)
    args = p.parse_args()
    arm = geometry_c.configure(args.arm)
    if args.capture and args.arm != 'R4':
        p.error('Capture is prespecified on R4 only')
    if min(args.dense_capacity, args.recent_rgb_capacity) <= 0:
        p.error('RGB capacities must be positive')
    from gpu_admission import require_idle_gpu
    require_idle_gpu()
    import numpy as np
    import torch
    import yaml
    from scipy.spatial.transform import Rotation
    from lietorch import SE3
    from packet_archive import open_archive, sensor_intrinsics
    from pose_alignment import global_alignment
    from vigs_sensor_config import prepare
    from custom_optional_imu import install as install_optional_imu
    import vigs as module
    import gs_backend
    import track_frontend
    from online_mapper_runtime import OnlineMapperRuntime
    from bounded_rgb_pool import BoundedRGBStore
    from bounded_cached_rgb import BoundedRGBController
    import bounded_cached_rgb, rgb_residency, rgb_residency_compact, bounded_pool_memory
    import bounded_rgb_pool
    from protected_opacity_prune import ProtectedOpacityPrune

    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    start = time.monotonic()
    tracker = runtime = None
    contract = json.loads(args.scene_contract.read_text())
    rpi = int(__import__('os').environ.get('ABLATION_RPI', '6'))   # LOCAL: renders per training input (default 6N)
    if contract['renders_per_training_input'] != rpi or contract['input_frame_cap'] is not None:
        raise ValueError(f'Full-input {rpi}N contract required')
    archive = open_archive(contract['archive'])
    if archive.events or archive.manifest['shared_geometry_replay_allowed']:
        raise ValueError('Shared geometry is forbidden')
    oracle = {int(r['uid']): r['c2w'] for r in json.loads(Path(contract['reference_pose_file']).read_text())}
    train = tuple(contract['training_uids'])
    training = set(train)
    excluded = archive.heldout_uids | {int(f['frame_uid']) for f in archive.arrivals if oracle.get(int(f['frame_uid'])) is None}
    quota = RenderQuota(train, frozenset(contract['heldout_uids']), renders_per_input=rpi)
    if quota.total != contract['render_budget'] or list(quota.checkpoints) != contract['snapshot_renders']:
        raise ValueError('Quota differs from common contract')
    k = sensor_intrinsics(archive)
    lock, source = verify_recipe(args.output)
    frozen = args.output / 'harness_source'
    frozen.mkdir()
    for file in (Path(__file__), HERE/'audit_custom_c_large_pool_6n.py', HERE/'render_quota.py', HERE/'vigs_sensor_config.py', HERE/'custom_optional_imu.py', V2/'custom_common.py', V2/'packet_archive.py', V2/'pose_alignment.py'):
        shutil.copy2(file, frozen/file.name)
    locks = {str(f.resolve()): sha(f) for f in (Path(__file__), HERE/'audit_custom_c_large_pool_6n.py', HERE/'render_quota.py', HERE/'vigs_sensor_config.py', HERE/'custom_optional_imu.py', V2/'custom_common.py', args.scene_contract, Path(contract['reference_pose_file']))}
    locks[str(Path(bounded_rgb_pool.__file__).resolve())] = sha(bounded_rgb_pool.__file__)
    shutil.copy2(bounded_rgb_pool.__file__, frozen/'bounded_rgb_pool.py')
    for extra in (bounded_cached_rgb, rgb_residency, rgb_residency_compact, bounded_pool_memory):
        locks[str(Path(extra.__file__).resolve())] = sha(extra.__file__)
        shutil.copy2(extra.__file__, frozen/Path(extra.__file__).name)
    for extra in (ABLATION/'ablation_support.py', ABLATION/'frontend_tape.py', ABLATION/'audit_arm.py', ABLATION/'evaluate_stages.py'):
        locks[str(extra)] = sha(extra)
        shutil.copy2(extra, frozen/extra.name)
    config, ma, _ = recipe_setup(archive)
    geometry_c.install_initialization(arm, args.output)
    locks.update(geometry_c.install(args.output))
    sensor, measurements = prepare(archive, Path('/home/intern/VIGS-SLAM-custom'), args.output)
    config['IMU'] = yaml.safe_load(Path(sensor['native_config']).read_text())['IMU']
    config['Training']['parallel'] = False
    config['Training']['background_polish'] = False
    config['Training']['gs_dedicated_stream'] = False
    ma.imus = measurements
    ma.imagedir = sensor['input_image_directory']
    ma.imufile = sensor['canonical_imu']
    ma.output = ma.save_dir = str(args.output)
    ma.config = sensor['native_config']
    ma.seed = args.seed
    ma.buffer = 1200
    ma.gsmapping = True
    ma.gsvis = False
    ma.pure_online = True
    ma.gs_dedicated_stream = False
    ma.mapping_replay_deadline_guard = False
    # LOCAL: ABLATION_REFERENCE_START=1 = colin's UTMM reference-start policy (map before IMU init; poses come from the reference adapter)
    ma.mapping_after_imu_init = measurements is not None and __import__('os').environ.get('ABLATION_REFERENCE_START') != '1'
    ma.IMU_poseinit_after = 20
    ma.frontend_iters1 = 4
    ma.frontend_iters2 = 2
    ma.final_ba_inertial = False
    locks.update(sensor['source_locks'])
    write(args.output/'source_locks.json', locks)
    write(args.output/'effective_mapper_config.json', config)
    write(args.output/'effective_args.json', {key: value for key, value in vars(ma).items() if key != 'imus'})
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.reset_peak_memory_stats()
    module.load_config = lambda path: copy.deepcopy(config)
    optional_imu_adapter = install_optional_imu(module, track_frontend, frozen)
    install_reference_pose_adapter(oracle)
    tracked, used, emitted = set(), set(), set()
    last_uid = -1
    packets = deque()
    alignments, packet_events, snapshots, resets, rescales = [], [], [], [], []
    mapper_seconds = 0.
    service_active = False
    phase = 'track'
    tape = FrontendTape(args.frontend_cache, capture=args.capture, contract=args.scene_contract)
    try:
        tracker = module.VIGS(ma)
        if tracker._gs_parallel:
            raise RuntimeError('Unexpected concurrent mapper')
        tracker._gs_stream = None
        tracker._queue_causal_dense_interval = lambda *a, **kw: None
        mapper = tracker.gs
        topology = ProtectedOpacityPrune(mapper, threshold=.1, every_renders=300)
        bounded_store = BoundedRGBStore(heldout=excluded, recent_capacity=args.recent_rgb_capacity, dense_capacity=args.dense_capacity)
        geometry_c.install_membership()
        runtime = OnlineMapperRuntime(tracker, {**options(excluded, renders=40), **geometry_c.policy_options(arm), 'store': bounded_store})
        if not arm['dense_supervision']:
            runtime._offer_arrived_intervals = lambda: None
        rgb_controller = BoundedRGBController(runtime, args.dense_capacity)
        bounded_pool_memory.install(mapper.gaussians)
        runtime.guard.reject_if_unsafe('setup')  # synchronous mapper owner
        # Dispatch admits native observations only; service() owns all 6N work.
        class AdmissionOnly:
            completed = 0
            target = 0
            def start_arrival(self, uid): pass
            def sync(self): pass
            def report(self): return {'policy': 'external_6N', 'KF_cap_enforced': False}
        runtime.unified_budget = AdmissionOnly()
        tracker.video.use_imu_cpp = False
        all_imus = tracker.args.imus.copy() if tracker.args.imus is not None else None
        if all_imus is not None and np.any(np.diff(all_imus[:, 0]) <= 0):
            raise ValueError('IMU clock must strictly increase')
        tracker.video.imus = tracker.args.imus = all_imus[:0] if all_imus is not None else None
        runners = {
            'fnet': getattr(tracker.filterx.feature_encoder_trt, 'runner', None),
            'depth': getattr(tracker.filterx.omnidata_trt, 'depth_runner', None),
            'normal': getattr(tracker.filterx.omnidata_trt, 'normal_runner', None),
            'frontend_update': getattr(tracker.frontend.update_op, 'runner', None),
            'pgba_update': getattr(getattr(getattr(tracker.video, 'pgobuf', None), 'update_op', None), 'runner', None)}
        engines = {key: value is not None for key, value in runners.items()}
        if not all(engines.values()):
            raise ValueError('Selected native Custom requires five TRT engines: '+str(engines))
        audit = WorkAudit(gs_backend, mapper)
        original_render = gs_backend.render
        def checked_render(view, *a, **kw):
            if torch.is_grad_enabled():
                uid = int(view.uid)
                if not service_active or uid not in tracked or uid > last_uid:
                    raise RuntimeError('Training outside causal budget service')
                if quota.reserve((uid,)) != (uid,):
                    raise RuntimeError('Render beyond granted 6N budget')
            return original_render(view, *a, **kw)
        gs_backend.render = checked_render
        original_step = mapper._step_mapper_optimizer
        def checked_step(optimizer):
            before = audit.completed
            result = original_step(optimizer)
            if audit.completed != before + 1:
                raise RuntimeError('Selected C must complete one loss render per Adam')
            quota.commit(actual_renders=1, actual_adam_steps=1, mapper_seconds=0., whole_seconds=time.monotonic()-start)
            used.add(audit.rows[-1]['uid'])
            return result
        mapper._step_mapper_optimizer = checked_step

        def rescale(self, scale):
            if args.capture:
                tape.record(last_uid, phase, 'rescale', float(scale))
            rescales.append({'available_through_uid': last_uid, 'native_scale': float(scale), 'reference_mapper_changed': False})
        mapper.rescale = MethodType(rescale, mapper)
        original_reset = runtime._native_controls['mapper_reset']
        def reset(self):
            if args.capture:
                tape.record(last_uid, phase, 'reset', None)
            pending = len(packets)
            packets.clear()
            result = original_reset()
            resets.append({'available_through_uid': last_uid, 'completed_renders': quota.completed, 'pending_discarded': pending})
            return result
        mapper.remove_all_gaussians = MethodType(reset, mapper)

        def alignment():
            n = tracker.video.counter.value
            uids = tracker.video.tstamp[:n].detach().cpu().long().tolist()
            indices = [i for i, u in enumerate(uids) if u in training]
            valid = [uids[i] for i in indices]
            if not set(valid).issubset(tracked) or any(u > last_uid for u in valid):
                raise ValueError('Future camera used in gauge alignment')
            if len(valid) < 3:
                return None
            pred = SE3(tracker.video.poses[indices].detach().clone()).inv().matrix().cpu().numpy()
            try:
                result = global_alignment(pred, [oracle[u] for u in valid])
            except ValueError:
                return None
            alignments.append(dict(result, available_through_uid=last_uid, uids=valid))
            return result

        def drain():
            while packets:
                packet, gauge = packets[0]
                if gauge is None:
                    gauge = alignment()
                    if gauge is None:
                        return
                packets.popleft()
                packet['depths'] *= gauge['scale']
                before = audit.completed
                # Native frontend calls call_gs inside no_grad; packet birth
                # stays there, while all differentiable work is in service().
                if args.capture:
                    tape.record(last_uid, phase, 'packet', packet)
                runtime.dispatch({'_mapping_events': [packet], '_arrival_uid': last_uid})
                rgb_controller.compact_native_payloads(packet['tstamp'].tolist())
                if audit.completed != before:
                    raise RuntimeError('Observation admission performed unbudgeted training')

        def own_packet(self, viz_idx, dposes=None, dscale=None, final=False, update_idx=None, blocking=False):
            if final:
                raise RuntimeError('Final refinement forbidden')
            all_uids = self.video.tstamp[viz_idx].detach().cpu().long().tolist()
            if not set(all_uids).issubset(tracked) or any(u > last_uid for u in all_uids):
                raise ValueError('Unarrived native packet')
            eligible = [int(i) for i, u in zip(viz_idx.cpu().tolist(), all_uids) if u in training]
            if not eligible:
                return
            ids = torch.tensor(eligible, device='cuda', dtype=torch.long)
            cpu_ids = ids.cpu()
            uids = self.video.tstamp[ids].detach().cpu().long().tolist()
            transforms = np.stack([np.linalg.inv(oracle[u]) for u in uids])
            packet = {'viz_idx': cpu_ids, 'tstamp': self.video.tstamp[ids].detach().cpu().clone(),
                'images': self.video.images[cpu_ids], 'normals': self.video.normals[cpu_ids],
                'depths': 1./self.video.disps_up[cpu_ids],
                'intrinsics': self.video.intrinsics[ids].detach().cpu().clone()*8,
                'poses': torch.tensor(np.concatenate((transforms[:, :3, 3], Rotation.from_matrix(transforms[:, :3, :3]).as_quat()), axis=1), dtype=torch.float32),
                'pose_updates': None, 'scale_updates': None, 'update_idx': None, 'final': False}
            packets.append((packet, alignment()))
            emitted.update(uids)
            packet_events.append({'uids': uids, 'available_through_uid': last_uid, 'native_correction': dposes is not None})
            drain()
        tracker.call_gs = MethodType(own_packet, tracker)

        def replay_events(event_phase):
            for kind, payload, grad_enabled in tape.events(last_uid, event_phase):
                with torch.set_grad_enabled(grad_enabled):
                    if kind == 'packet':
                        uids = payload['tstamp'].long().tolist()
                        if not set(uids) <= training & tracked or any(u > last_uid for u in uids):
                            raise RuntimeError('Noncausal replay packet')
                        emitted.update(uids)
                        packet_events.append({'uids': uids, 'available_through_uid': last_uid, 'replayed': True})
                        before = audit.completed
                        runtime.dispatch({'_mapping_events': [payload], '_arrival_uid': last_uid})
                        rgb_controller.compact_native_payloads(uids)
                        if audit.completed != before:
                            raise RuntimeError('Replay dispatch trained outside service')
                    elif kind == 'reset':
                        reset(mapper)
                    elif kind == 'rescale':
                        rescale(mapper, payload)
                    elif kind != 'service_rng':
                        raise ValueError(kind)

        def save_snapshot():
            path = args.output/'snapshots'/f'renders_{quota.completed:09d}.ply'
            path.parent.mkdir(exist_ok=True)
            # Intermediate PLYs intentionally omitted in endpoint-only ablation.
            poses = path.with_suffix('.causal_poses.json')
            write(poses, camera_poses(mapper))
            snapshots.append({'ply': str(path.relative_to(args.output)), 'ply_sha256': None, 'materialized': False,
                'causal_pose_file': str(poses.relative_to(args.output)), 'available_through_uid': last_uid,
                'completed_renders': quota.completed, 'completed_steps': quota.adam_steps,
                'mapper_seconds': mapper_seconds, 'wall_seconds': time.monotonic()-start,
                'gaussian_count': len(mapper.gaussians.get_xyz), 'terminal_prune_applied': False})
            quota.mark_snapshot(quota.completed, poses)

        def service():
            nonlocal service_active, mapper_seconds, phase
            phase = 'service'
            if args.capture:
                tape.record(last_uid, phase, 'service_rng', None)
                drain()
            else:
                replay_events(phase)
            while quota.available:
                before = audit.completed
                began = time.monotonic()
                service_active = True
                try:
                    result = mapper.online_view_trainer.step(max_views=min(12, quota.available))
                finally:
                    service_active = False
                torch.cuda.synchronize()
                mapper_seconds += time.monotonic()-began
                if not result:
                    if audit.completed != before:
                        raise RuntimeError('Work completed with false service result')
                    break
                if audit.completed != quota.completed or audit.completed != runtime.guard.main_gaussian_steps_completed:
                    raise RuntimeError('Physical render/Adam/credit disagreement')
                topology.after_packet(audit.completed, last_uid)
                if quota.snapshot_due:
                    save_snapshot()
            bounded_pool_memory.release_free_heap()
            progress = {'uid': last_uid, 'tracked': len(tracked), 'admitted': quota.admitted,
                'renders': quota.completed, 'granted': quota.granted, 'gaussians': len(mapper.gaussians.get_xyz), 'bounded_rgb': rgb_controller.report()}
            write(args.output/'progress.json', progress)
            print(json.dumps(progress), flush=True)
            phase = 'track'

        for frame in archive.arrivals:
            last_uid = int(frame['frame_uid'])
            if frame['held_out']:
                continue
            stamp = float(frame['sensor_timestamp'])
            rgb = archive.load_rgb(last_uid)
            # Reference-missing frames are tracked but cannot supervise mapping.
            if last_uid in training:
                runtime.store.append_rgb(last_uid, stamp, rgb)
            tracked.add(last_uid)
            if all_imus is not None:
                count = int(np.searchsorted(all_imus[:, 0], stamp, side='right'))
                tracker.video.imus = tracker.args.imus = all_imus[:count]
            if tracker.video.counter.value >= ma.buffer-1:
                raise RuntimeError('Native frontend buffer exhausted')
            if args.capture:
                tracker.track(last_uid, stamp, rgb[None], intrinsics=torch.tensor(k, dtype=torch.float32)[None], is_last=False)
            else:
                replay_events('track')
            if last_uid in training:
                quota.admit(last_uid)
                if quota.admitted % 64 == 0 and quota.admitted < len(train):
                    service()
        service()
        completion = quota.close()
        expected = {int(f['frame_uid']) for f in archive.arrivals if not f['held_out']}
        mapped = set(mapper.viewpoints)
        overlap = sorted((mapped | used | tracked) & archive.heldout_uids)
        if tracked != expected or overlap or not (mapped | used).issubset(training):
            raise RuntimeError('Full-input/heldout contract failed')
        frontend_record = tape.finish()
        c_training = geometry_c.training_report(audit.completed)
        runtime.close()
        with runtime.guard.export_topology():
            c_export = geometry_c.finish(topology, args.output, training, archive.heldout_uids, audit, runtime.guard)
        terminal = c_export['terminal_opacity']
        write(args.output/'geometry_c.json', {'training': c_training, 'export': c_export})
        write(args.output/'causal_native_keyframe_poses.json', camera_poses(mapper))
        np.save(args.output/'intrinsics.npy', k)
        changed = [p for p, digest in {**locks, **source['sources']}.items() if sha(p) != digest]
        if changed:
            raise RuntimeError('Source changed during run: '+str(changed))
        report = runtime.report()
        report.update(schema='equal_render_native_mapper_v1', system='custom', recipe_variant='mapper_geometry_ablation', ablation_arm=arm, frontend_tape=frontend_record, bounded_rgb=rgb_controller.report(),
            geometry_c_training=c_training, geometry_c_export=c_export, final_map_stage='after_terminal_opacity_and_FM' if arm['carving'] else 'training_endpoint', dataset=contract['dataset'],
            scene=contract['scene'], pose_mode='gt', reference_kind=contract['reference_kind'],
            GT_pose_file=contract['reference_pose_file'], GT_pose_sha256=sha(contract['reference_pose_file']),
            budget='equal_render_6N', render_budget=quota.total, completed_training_renders=audit.completed,
            completed_adam_steps=quota.adam_steps, completed_training_pixels=audit.completed_pixels,
            training_renders_attempted=audit.attempted, input_frames=len(archive.arrivals), tracked_input_count=len(tracked),
            training_input_count=len(train), input_drop_count=0, heldout_overlap=overlap,
            mapping_camera_uids=sorted(mapped), loss_camera_uids=sorted(used),
            own_frontend='Current Custom recorded once; identical causal full packets replayed across ablation arms',
            sensor_mode=sensor['sensor_mode'], optional_imu_adapter=optional_imu_adapter,
            sensor_measurement_count=sensor['measurement_count'], fake_IMU_provided=False,
            TensorRT_engines_loaded=engines, GT_pose_provided_to_frontend=False, GT_depth_used=False,
            shared_geometry_packets_used=not args.capture, frontend_capture=args.capture, native_whole_system_benchmark=False, online_pgba_enabled=tracker.pgba,
            work_policy='equal_render_6N', kf_render_cap_enforced=False,
            mapper_seconds=mapper_seconds, whole_seconds=time.monotonic()-start,
            peak_allocated_vram_bytes=torch.cuda.max_memory_allocated(),
            peak_reserved_vram_bytes=torch.cuda.max_memory_reserved(),
            gaussian_count=len(mapper.gaussians.get_xyz),
            cumulative_gaussian_births=sum(v['after']-v['before'] for v in topology.births),
            recipe=source, source_locks=locks,
            geometry_alignment_records=alignments, native_packet_events=packet_events,
            native_map_resets=resets, fixed_mapper_rescale_requests=rescales,
            pending_packets=len(packets), snapshots=snapshots, topology=topology.report(), terminal_prune=terminal,
            auxiliary_nontraining_render_count=len(audit.no_grad_rows),
            quota_completion=completion, final_ba=False, final_refinement=False,
            post_refinement_optimizer_updates=0, native_terminate_called=False,
            render_and_input_contract_verified=True, benchmark_completed=False,
            quality_validation_completed=False, geometry_validation_completed=False)
        write(args.output/'render_work.json', audit.rows)
        write(args.output/'render_ledger.json', {'events': quota.events, 'completion': completion})
        write(args.output/'runtime.json', report)
        print('ABLATION_6N_RENDER_CONTRACT_PASS', audit.completed, flush=True)
    except Exception as error:
        write(args.output/'failure.json', {'exception': repr(error), 'completed_renders': quota.completed,
            'tracked_inputs': len(tracked), 'last_uid': last_uid})
        raise
    finally:
        if runtime is not None:
            runtime.close()
        if tracker is not None and tracker.pgba:
            tracker.video.pgobuf.stop()
            if tracker.mp_backend is not None:
                tracker.mp_backend.join(timeout=5)
                if tracker.mp_backend.is_alive():
                    raise RuntimeError('Owned PGBA did not stop')


if __name__ == '__main__':
    main()
