"""Lossless FIFO RGB tiers. Reads never promote entries or change replay membership.

Capacities count images, including arrived candidates. One CPU bundle and one GPU
image may additionally be held as read scratch. OS page cache is not bypassed.
"""
from collections import OrderedDict, Counter
from pathlib import Path
import os
import time
import torch


def nbytes(bundle):
    return sum(x.numel() * x.element_size() for x in bundle.values())


class FIFORGBTiers:
    def __init__(self, root, gpu_capacity=512, ram_capacity=1024, device='cuda'):
        if gpu_capacity < 0 or ram_capacity < 0:
            raise ValueError('Nonnegative capacities required')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.gpu_capacity, self.ram_capacity = gpu_capacity, ram_capacity
        self.device = torch.device(device)
        self.gpu, self.ram = OrderedDict(), OrderedDict()
        self.disk = set()
        self.cpu_scratch = self.gpu_scratch = None
        self.stats = Counter()

    def _move(self, bundle, device, direction):
        start = time.perf_counter()
        result = {k: v.to(device, copy=True) for k, v in bundle.items()}
        self.stats[direction + '_host_seconds'] += time.perf_counter() - start
        self.stats[direction + '_bytes'] += nbytes(bundle)
        return result

    def add(self, uid, raw):
        if uid in self.gpu or uid in self.ram or uid in self.disk:
            raise ValueError('Repeated image admission')
        raw = raw.detach().squeeze(0) if raw.ndim == 4 else raw.detach()
        if raw.dtype != torch.uint8 or raw.device.type != 'cpu' or raw.ndim != 3:
            raise ValueError('CPU uint8 CHW RGB required')
        start = time.perf_counter()
        bundle = {'raw': raw.clone(), 'float': raw / 255.0}
        self.stats['normalization_host_seconds'] += time.perf_counter() - start
        # Make room before uploading, so persistent entries never exceed limits.
        if self.gpu_capacity:
            if len(self.gpu) == self.gpu_capacity:
                old, value = self.gpu.popitem(last=False)
                self._ram_add(old, self._move(value, 'cpu', 'd2h'))
            self.gpu[uid] = self._move(bundle, self.device, 'h2d')
        else:
            self._ram_add(uid, bundle)
        for tier in ('gpu', 'ram'):
            values = getattr(self, tier)
            self.stats['peak_' + tier + '_entries'] = max(self.stats['peak_' + tier + '_entries'], len(values))
            self.stats['peak_' + tier + '_bytes'] = max(self.stats['peak_' + tier + '_bytes'], sum(map(nbytes, values.values())))
        self.stats['arrivals'] += 1

    def _ram_add(self, uid, bundle):
        if self.ram_capacity:
            if len(self.ram) == self.ram_capacity:
                old, value = self.ram.popitem(last=False)
                self._write(old, value)
            self.ram[uid] = bundle
        else:
            self._write(uid, bundle)

    def _write(self, uid, bundle):
        start = time.perf_counter()
        dest = self.root / f'{uid}.pt'
        tmp = dest.with_suffix('.tmp')
        torch.save(bundle, tmp)
        os.replace(tmp, dest)
        self.disk.add(uid)
        self.stats['ssd_write_host_seconds'] += time.perf_counter() - start
        self.stats['ssd_write_bytes'] += dest.stat().st_size
        self.stats['ssd_writes'] += 1

    def cpu(self, uid):
        if uid in self.ram:
            self.stats['ram_hits'] += 1
            return self.ram[uid]
        if self.cpu_scratch is not None and self.cpu_scratch[0] == uid:
            return self.cpu_scratch[1]
        if uid in self.gpu:
            result = self._move(self.gpu[uid], 'cpu', 'd2h')
        elif uid in self.disk:
            start = time.perf_counter()
            path = self.root / f'{uid}.pt'
            result = torch.load(path, map_location='cpu', weights_only=True)
            self.stats['ssd_read_host_seconds'] += time.perf_counter() - start
            self.stats['ssd_read_bytes'] += path.stat().st_size
            self.stats['ssd_reads'] += 1
        else:
            raise KeyError(uid)
        self.cpu_scratch = (uid, result)
        self.stats['peak_cpu_scratch_bytes'] = max(self.stats['peak_cpu_scratch_bytes'], nbytes(result))
        return result

    def image(self, uid):
        if uid in self.gpu:
            self.stats['gpu_hits'] += 1
            return self.gpu[uid]['float']
        if self.gpu_scratch is not None and self.gpu_scratch[0] == uid:
            return self.gpu_scratch[1]
        result = self._move({'float': self.cpu(uid)['float']}, self.device, 'h2d')['float']
        self.gpu_scratch = (uid, result)
        self.stats['peak_gpu_scratch_bytes'] = max(self.stats['peak_gpu_scratch_bytes'], result.numel()*result.element_size())
        return result

    def clear_scratch(self):
        self.cpu_scratch = self.gpu_scratch = None

    def report(self):
        return dict(policy='arrival_FIFO_no_read_promotion', gpu_capacity=self.gpu_capacity,
                    ram_capacity=self.ram_capacity, gpu_entries=len(self.gpu), ram_entries=len(self.ram),
                    ssd_entries=len(self.disk), logical_entries=len(self.gpu)+len(self.ram)+len(self.disk),
                    ssd_directory=str(self.root), disk_format='lossless_torch_uint8_and_float32',
                    timings='host wall time, includes blocking copies; not CUDA kernel-only DMA time',
                    ssd_io='buffered filesystem IO; OS page cache enabled', scratch_limit='one CPU bundle plus one GPU image',
                    **dict(self.stats))
