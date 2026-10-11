"""CPU checks for immediate bounded admission and causal full-packet replay."""
import ast
import inspect
import json
from pathlib import Path
import tempfile
import textwrap
import random
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=['/home/intern/VIGS-SLAM-custom/vigs','/home/intern/VIGS-SLAM-custom/scripts/selected_mapping',str(HERE)]
import ablation_support as support
from frontend_tape import FrontendTape


def main():
    import numpy as np
    import torch
    import bounded_rgb_pool as bounded
    from online_view_training import DenseObservation
    support.install_membership()
    def policy(kappa):
        return bounded.BoundedUnifiedTrainingSet(membership='immediate',selector='ervs',kappa=kappa,
            tau=4.,selection_count_scope='all_rgb',growth_budget_scope='dense_only',dense_capacity=2,
            batch_quotas=(3,3,6),auxiliary_mode='dense_rgb',seed=0,heldout=(99,))
    for kappa in [1,16,1000000]:
        p=policy(kappa);p.register_keyframes([0,10]);p.offer_many([DenseObservation(u,0,10,10) for u in [1,2,3]])
        assert p.admitted=={2,3} and p.rgb_steps_completed==0 and p.evictions[0]['uid']==1
        selection=p.reserve(window=[0,10]);p.offer(4,0,10,available_through=10)
        assert p.admitted=={2,3}
        p.commit_prefix(selection,len(selection.uids));assert p.admitted=={3,4}
        try:p.offer(5,0,10,available_through=9)
        except ValueError:pass
        else:raise AssertionError('Future anchor accepted')
    # Verify the exact narrow initialization edit against pinned source without loading CUDA.
    source=Path('/home/intern/VIGS-SLAM-custom/vigs/gaussian/scene/gaussian_model.py').read_text()
    tree=ast.parse(source);node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='create_pcd_from_image_and_depth')
    method=textwrap.dedent('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))
    old='w = sob[rows, cols].astype(np.float64)\n            w = w + w.mean() * 0.1 + 1e-6\n            w /= w.sum()'
    assert method.count(old)==1
    compile(method.replace(old,'w = np.full(len(rows), 1.0 / len(rows), dtype=np.float64)'),'<uniform>','exec')
    # CPU-only tape test; CUDA RNG is an empty list for this adapter-level test.
    torch.cuda.get_rng_state_all=lambda:[]
    torch.cuda.set_rng_state_all=lambda states:None
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);contract=root/'contract.json';contract.write_text('{}')
        writer=FrontendTape(root/'cache',capture=True,contract=contract)
        packet=dict(images=torch.arange(12,dtype=torch.uint8).reshape(1,3,2,2),depths=torch.ones(1,2,2),normals=torch.zeros(1,3,2,2),final=False)
        with torch.no_grad():writer.record(4,'track','packet',packet)
        expected=(random.random(),np.random.random(),torch.rand(1))
        packet['depths'].zero_()
        writer.record(4,'service','service_rng',None);writer.record(7,'track','reset',None);written=writer.finish()
        reader=FrontendTape(root/'cache',capture=False,contract=contract)
        assert list(reader.events(3,'track'))==[]
        kind,payload,grad=next(reader.events(4,'track'));assert kind=='packet' and payload['depths'].sum()==4 and not grad
        assert random.random()==expected[0] and np.random.random()==expected[1] and torch.equal(torch.rand(1),expected[2])
        assert list(reader.events(4,'service'))[0][0]=='service_rng'
        assert list(reader.events(7,'track'))[0][0]=='reset'
        assert reader.finish()['manifest_sha256']==written['manifest_sha256']
        bad=FrontendTape(root/'cache',capture=False,contract=contract)
        try:list(bad.events(6,'track'))
        except RuntimeError:pass
        else:raise AssertionError('Missed event not detected')
    print(json.dumps(dict(passed=True,checks=['immediate_before_any_training','kappa_independent','bounded_oldest_eviction','reserved_batch_retained','future_anchor_rejected','uniform_edit_matches','packet_tensor_clone','causal_event_order','RNG_restore','tape_digest_identity'])))

if __name__=='__main__':main()
