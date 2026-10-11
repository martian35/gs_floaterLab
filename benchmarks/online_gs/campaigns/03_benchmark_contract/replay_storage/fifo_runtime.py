"""Runtime adapter for D: unbounded membership and unified FIFO mapper RGB.

No vendor, sampling, admission credit, losses or frontend buffer modifications.
"""
from types import MethodType
import torch
from tiered_rgb import FIFORGBTiers

_camera_types = {}


def share(camera, tiers):
    if hasattr(camera, '_fifo_rgb'):
        return
    uid = int(camera.uid)
    expected = tiers.cpu(uid)['float']
    original = camera.original_image
    if not torch.equal(original.detach().cpu(), expected):
        raise ValueError(f'CPU RGB differs for {uid}; refusing changed supervision')
    target = camera.original_image_gpu
    if target is not None and not torch.equal(target.detach().cpu(), expected):
        raise ValueError(f'GPU RGB differs for {uid}; refusing changed supervision')
    base = type(camera)
    if base not in _camera_types:
        def cpu(self):
            return None if self._fifo_cleaned else self._fifo_rgb.cpu(int(self.uid))['float']
        def gpu(self):
            return None if self._fifo_cleaned else self._fifo_rgb.image(int(self.uid))
        def setter(self, value):
            if value is not None:
                raise RuntimeError('FIFO camera RGB is immutable')
            self._fifo_cleaned = True
        _camera_types[base] = type('FIFORGB' + base.__name__, (base,), {
            'original_image': property(cpu, setter), 'original_image_gpu': property(gpu, setter)})
    camera.__dict__.pop('original_image', None)
    camera.__dict__.pop('original_image_gpu', None)
    camera._fifo_rgb, camera._fifo_cleaned = tiers, False
    camera.__class__ = _camera_types[base]
    tiers.stats['cameras_exact_pixels_checked'] += 1


def install(config):
    import bounded_rgb_pool as pool
    import bounded_cached_rgb as cached
    from arrived_sensor_store import ArrivedSensorStore
    from rgb_residency_compact import ExactRGBResidency
    original_store, original_controller = pool.BoundedRGBStore, cached.BoundedRGBController

    class Store(original_store):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.tiers = FIFORGBTiers(config['directory'], config['gpu_capacity'], config['ram_capacity'])
        def append_rgb(self, uid, timestamp, image):
            with self._lock:
                accepted = ArrivedSensorStore.append_rgb(self, uid, timestamp, image)
                if accepted:
                    self.tiers.add(int(uid), self._rgb[int(uid)])
                    self._rgb[int(uid)] = None  # membership metadata only
                return accepted
        def load_rgb(self, uid):
            with self._lock:
                uid = int(uid)
                if uid not in self._rgb or uid in self.heldout_uids:
                    raise ValueError('RGB has not arrived or is held-out')
                return self.tiers.cpu(uid)['raw']
        def pin(self, uids):
            if not set(uids) <= self._rgb.keys():
                raise ValueError('Unarrived training member')
            self.pinned = set(uids)
        def report(self):
            t = self.tiers.report()
            return {**ArrivedSensorStore.report(self), 'storage':'unbounded_logical_FIFO_tiers',
                    'tiers':t, 'expired_rgb':0, 'image_spill_reads':t.get('ssd_reads',0),
                    'image_spill_writes':t.get('ssd_writes',0)}

    class Policy(pool.BoundedUnifiedTrainingSet):
        def __init__(self, **kwargs):
            # Preserve the original admission/event boundaries, remove only cap.
            kwargs['dense_capacity'] = float('inf')
            capacity = kwargs.pop('dense_capacity')
            super().__init__(dense_capacity=1, **kwargs)
            self.dense_capacity = capacity
        def snapshot(self):
            result = super().snapshot()
            result.update(dense_capacity=None, dense_replacement='none_full_admitted_pool')
            return result

    class Controller(pool.BoundedRGBController):
        def __init__(self, runtime, dense_capacity):
            super().__init__(runtime, dense_capacity)
            self.trainer.policy_class = Policy
            self.trainer.policy = Policy(**self.trainer.options)
            self.compacted_payloads = self.payload_bytes = self.parent_bytes_at_compaction = 0
            original = self.mapper.register_causal_dense_views
            def register(mapper, records):
                records = list(records)
                result = original(records)
                for record in records:
                    camera = mapper.polish_viewpoints.get(int(record[0]))
                    if camera is not None: share(camera, self.store.tiers)
                return result
            self.mapper.register_causal_dense_views = MethodType(register, self.mapper)
            original_view = self.mapper._training_viewpoint
            def view(mapper, camera):
                result = original_view(camera)
                if result is not camera:
                    raise ValueError('D FIFO adapter requires native training resolution')
                return result
            self.mapper._training_viewpoint = MethodType(view, self.mapper)
            original_step = self.mapper._step_mapper_optimizer
            def step(mapper, *args, **kwargs):
                result = original_step(*args, **kwargs)
                self.store.tiers.clear_scratch()
                return result
            self.mapper._step_mapper_optimizer = MethodType(step, self.mapper)
        def compact_native_payloads(self, uids):
            uids = list(uids)
            ExactRGBResidency.compact_native_payloads(self, uids)
            for uid in uids:
                camera = self.mapper.viewpoints.get(int(uid))
                if camera is not None: share(camera, self.store.tiers)
            self.store.tiers.clear_scratch()
        def report(self):
            self.maintain()
            return dict(variant='D_FIFO_replay_storage', membership_changed=False,
                        keyframes_capped=False, dense_capacity=None, replacement='none_full_admitted_pool',
                        rgb_store=self.store.report(), dense_cameras=len(self.mapper.polish_viewpoints),
                        peak_dense_cameras=self.peak_cameras, compacted_payloads=self.compacted_payloads,
                        compacted_payload_bytes=self.payload_bytes, sampling_changed=False,
                        frontend_buffers_changed=False)

    class RAMStore(original_store):
        def append_rgb(self, uid, timestamp, image):
            return ArrivedSensorStore.append_rgb(self, uid, timestamp, image)
        load_rgb = ArrivedSensorStore.load_rgb
        def pin(self, uids):
            if not set(uids) <= self._rgb.keys(): raise ValueError('Unarrived member')
            self.pinned = set(uids)
        def report(self):
            return {**ArrivedSensorStore.report(self), 'storage':'unbounded_logical_legacy_RAM',
                    'expired_rgb':0, 'image_spill_reads':0, 'image_spill_writes':0}

    class RAMController(original_controller):
        def __init__(self, runtime, dense_capacity):
            super().__init__(runtime, dense_capacity)
            self.trainer.policy_class = Policy
            self.trainer.policy = Policy(**self.trainer.options)
        def report(self):
            result = super().report()
            result.update(variant='D_unbounded_legacy_storage', membership_changed=False,
                          dense_capacity=None, replacement='none_full_admitted_pool',
                          sampling_changed=False, frontend_buffers_changed=False)
            return result

    if config.get('mode') == 'full_ram':
        pool.BoundedRGBStore, cached.BoundedRGBController = RAMStore, RAMController
    else:
        pool.BoundedRGBStore, cached.BoundedRGBController = Store, Controller
    def restore():
        pool.BoundedRGBStore, cached.BoundedRGBController = original_store, original_controller
    return restore
