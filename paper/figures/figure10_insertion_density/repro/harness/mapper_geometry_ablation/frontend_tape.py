"""Record every delivered reference-gauge frontend packet and control event.

Tensor device/dtype, dispatch grad mode, RNG, arrival UID and service phase are
preserved. No final geometry, future observations or GT depth enter training.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


class FrontendTape:
    def __init__(self, directory, *, capture, contract):
        self.root = Path(directory)
        self.capture = capture
        self.contract_sha = sha(contract)
        self.rows = []
        self.cursor = 0
        if capture:
            self.root.mkdir(parents=True, exist_ok=False)
        else:
            self.manifest = json.loads((self.root/'manifest.json').read_text())
            if not self.manifest['complete'] or self.manifest['contract_sha256'] != self.contract_sha:
                raise ValueError('Incomplete or mismatched frontend tape')
            self.rows = self.manifest['events']

    def record(self, uid, phase, kind, payload):
        import numpy as np
        import torch
        if not self.capture:
            raise RuntimeError('Cannot append replay tape')
        devices = {}
        if isinstance(payload, dict):
            value = {}
            for key, item in payload.items():
                if isinstance(item, torch.Tensor):
                    devices[key] = str(item.device)
                    value[key] = item.detach().cpu().clone()
                else:
                    value[key] = item
        else:
            value = payload
        path = self.root / f'{len(self.rows):07d}.pt'
        torch.save(dict(payload=value, devices=devices, grad_enabled=torch.is_grad_enabled(),
                        rng=dict(python=random.getstate(), numpy=np.random.get_state(),
                                 torch=torch.get_rng_state(), cuda=torch.cuda.get_rng_state_all())), path)
        self.rows.append(dict(uid=int(uid), phase=phase, kind=kind, file=path.name, sha256=sha(path), bytes=path.stat().st_size))

    def events(self, uid, phase):
        import numpy as np
        import torch
        while self.cursor < len(self.rows):
            row = self.rows[self.cursor]
            if row['uid'] < uid:
                raise RuntimeError('Replay skipped a causal event')
            if (row['uid'], row['phase']) != (uid, phase):
                return
            path = self.root / row['file']
            if sha(path) != row['sha256']:
                raise RuntimeError('Frontend packet changed')
            saved = torch.load(path, map_location='cpu', weights_only=False)
            value = saved['payload']
            for key, device in saved['devices'].items():
                value[key] = value[key].to(device)
            rng = saved['rng']
            random.setstate(rng['python'])
            np.random.set_state(rng['numpy'])
            torch.set_rng_state(rng['torch'])
            torch.cuda.set_rng_state_all(rng['cuda'])
            self.cursor += 1
            yield row['kind'], value, saved['grad_enabled']

    def finish(self):
        if self.capture:
            self.manifest = dict(schema='custom_full_frontend_tape_v1', complete=True,
                contract_sha256=self.contract_sha, events=self.rows,
                tensors='all delivered KF additions and updates, RGB, depth, normals, intrinsics, fixed poses',
                gauge='causal native-to-common-reference Sim3, applied before recording',
                total_bytes=sum(r['bytes'] for r in self.rows))
            (self.root/'manifest.json').write_text(json.dumps(self.manifest, indent=2)+'\n')
        elif self.cursor != len(self.rows):
            raise RuntimeError('Replay did not consume every frontend event')
        return dict(path=str(self.root), manifest_sha256=sha(self.root/'manifest.json'),
                    events=len(self.rows), total_bytes=self.manifest['total_bytes'],
                    mode='capture' if self.capture else 'replay', all_events_consumed=True)
