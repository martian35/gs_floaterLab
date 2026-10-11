"""Shared causal frontend, unchanged D 6N sampling, storage-only comparison."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE), '/home/intern/VIGS-SLAM-custom/vigs',
             '/home/intern/VIGS-SLAM-custom/scripts/selected_mapping']
p=argparse.ArgumentParser(add_help=False)
p.add_argument('--replay-storage',choices=('legacy','full_ram','tiered_fifo'),required=True)
p.add_argument('--replay-gpu-capacity',type=int,default=512)
p.add_argument('--replay-ram-capacity',type=int,default=1024)
a, rest=p.parse_known_args()
sys.argv=[sys.argv[0],*rest]
out=Path(rest[rest.index('--output')+1])
config=dict(mode=a.replay_storage,gpu_capacity=a.replay_gpu_capacity,
            ram_capacity=a.replay_ram_capacity,directory=str(out/'replay_images'))
base=HERE.parent/'temporal_pool_equal_time/run_mapper.py'
spec=importlib.util.spec_from_file_location('shared_frontend_storage_runner',base)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
original=runner.install_variant

def install_variant(variant):
    assert variant=='legacy'
    original(variant)
    if a.replay_storage!='legacy':
        from fifo_runtime import install
        install(config)
runner.install_variant=install_variant
paths=[Path(__file__),HERE/'fifo_runtime.py',HERE/'tiered_rgb.py']
payloads={str(p):p.read_bytes() for p in paths}
locks={p:hashlib.sha256(b).hexdigest() for p,b in payloads.items()}
runner.main()
r=json.loads((out/'runtime.json').read_text())
r['replay_storage_config']=config
r['source_locks'].update(locks)
(out/'runtime.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
frozen=out/'replay_storage_source';frozen.mkdir()
for p,b in payloads.items():(frozen/Path(p).name).write_bytes(b)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in locks.items())
