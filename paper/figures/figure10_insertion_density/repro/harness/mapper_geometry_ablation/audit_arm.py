"""Fail closed on budget, declared ablation settings, data leakage and evaluation."""
import argparse
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'mapper_baselines/v2'))
from custom_common import sha,write


def audit(run,contract):
    r=json.loads((run/'runtime.json').read_text());c=json.loads(contract.read_text());arm=r['ablation_arm']
    checks={}
    def check(name,value):
        checks[name]=bool(value)
        if not value:raise ValueError('Ablation audit failed: '+name)
    check('6N',r['completed_training_renders']==r['completed_adam_steps']==r['training_renders_attempted']==c['renders_per_training_input']*len(c['training_uids'])==c['render_budget'])  # LOCAL: budget from the contract
    check('full_inputs',r['input_drop_count']==0 and r['training_input_count']==len(c['training_uids']) and r['render_and_input_contract_verified'])
    check('heldout_disjoint',not r['heldout_overlap'] and not set(r['mapping_camera_uids']+r['loss_camera_uids'])&set(c['heldout_uids']))
    check('no_GT_depth',r['GT_depth_used'] is False and r['GT_pose_provided_to_frontend'] is False)
    check('no_optimizer_tail',r['post_refinement_optimizer_updates']==0 and r['geometry_c_export']['optimizer_updates']==0)
    check('causal_packets',all(all(u<=p['available_through_uid'] for u in p['uids']) for p in r['native_packet_events']))
    check('source_locks',all(sha(p)==h for p,h in {**r['source_locks'],**r['recipe']['sources']}.items()))
    tape=r['frontend_tape'];check('complete_tape',tape['all_events_consumed'] and sha(Path(tape['path'])/'manifest.json')==tape['manifest_sha256'])
    policies=[g['policy'] for g in r['training']['generations']]
    check('no_kappa_throttle',all(p['membership']=='immediate' for p in policies))
    check('quotas',all(p['batch_quotas']==arm['batch_quotas'] and p['auxiliary_mode']==arm['auxiliary_mode'] for p in policies))
    check('capacity',r['bounded_rgb']['dense_cameras']<=1024 and r['bounded_rgb']['float_rgb_cache']['capacity']==64)
    if not arm['dense_supervision']:
        check('no_dense',r['bounded_rgb']['peak_dense_cameras']==0)
    geo=r['geometry_c_training']
    check('normal_loss',geo['keyframe_loss']['mode']==('d3_normal' if arm['normal_loss'] else 'd3'))
    check('dense_depth',geo['dense_depth']['mode']==('geo' if arm['dense_depth_loss'] else 'off'))
    check('carve',geo['carve_stats'].get('self_grad_views',0)==(r['completed_training_renders'] if arm['carving'] else 0))
    stages=r['geometry_c_export']['stages'];check('map_stages',len(stages)==(3 if arm['carving'] else 1) and all(sha(run/s['ply'])==s['sha256'] for s in stages))
    work=json.loads((run/'render_work.json').read_text());check('physical_steps',len(work)==c['render_budget'] and all(v['completed'] and v['backward'] for v in work))
    metrics=json.loads((run/'stage_metrics.json').read_text());check('evaluations',metrics['passed'] and len(metrics['stages'])==len(stages))
    write(run/'audit.json',dict(passed=True,arm=arm['arm'],checks=checks,frontend_tape_sha256=tape['manifest_sha256']))
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--scene-contract',type=Path,required=True);a=p.parse_args();audit(a.run,a.scene_contract)
