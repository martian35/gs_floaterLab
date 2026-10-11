"""Existing heldout RGB/depth evaluator on the requested ablation export stages."""
import argparse
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
EQUAL = HERE.parent/'mapper_equal_render'
V2 = HERE.parent/'mapper_baselines/v2'
sys.path[:0] = [str(EQUAL),str(V2)]
from custom_common import sha, write
from geometry_reference_path import geometry_reference_path
from depth_metrics import aggregate_depth_metrics


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scene-contract',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    a=p.parse_args(); c=json.loads(a.scene_contract.read_text());r=json.loads((a.run/'runtime.json').read_text())
    assert r['recipe_variant']=='mapper_geometry_ablation' and r['render_and_input_contract_verified']
    assert r['completed_training_renders']==c['render_budget'] and sha(c['reference_pose_file'])==r['GT_pose_sha256']
    poses={v['uid']:v['c2w'] for v in json.loads(Path(c['reference_pose_file']).read_text())}
    expected=sorted(u for u in c['heldout_uids'] if poses.get(u) is not None)
    arm=r['ablation_arm']['arm']; stages=r['geometry_c_export']['stages'];rows=[]
    for i,stage in enumerate(stages):
        ply=a.run/stage['ply'];assert sha(ply)==stage['sha256']
        label=arm if len(stages)==1 or i==0 else ['R4','R4-O','R4-F'][i]
        out=a.run/('evaluation' if label==arm else 'evaluation_'+label)
        if not (out/'quality.json').exists():
            sys.argv=[str(V2/'evaluate_python.py'),'--system','custom','--archive',c['archive'],
                      '--run',str(a.run),'--config',str(a.run/'native_sensor_config.yaml'),
                      '--ply',str(ply),'--output',str(out)]
            depth=geometry_reference_path(a.scene_contract)
            if depth is not None:sys.argv+=['--depth-reference',str(depth)]
            runpy.run_path(str(V2/'evaluate_python.py'),run_name='__main__')
            q=json.loads((out/'quality.json').read_text())
            q.update(ablation_arm=label, map_stage=ply.stem,common_scene_contract_sha256=sha(a.scene_contract),
                     reference_kind=c['reference_kind'],evaluation_reference_is_gt=c['reference_kind']=='independent_camera_gt',
                     completed_renders=r['completed_training_renders'],frontend_tape_sha256=r['frontend_tape']['manifest_sha256'])
            write(out/'quality.json',q)
        q=json.loads((out/'quality.json').read_text())
        assert q['ply_sha256']==stage['sha256'] and q['gaussian_count']==stage['gaussians']
        assert [v['uid'] for v in q['per_view']]==expected
        assert q['depth_geometry']==aggregate_depth_metrics(q['per_view'])
        assert q['depth_geometry']['views_with_depth']>0 or __import__('os').environ.get('ABLATION_ALLOW_NO_DEPTH')=='1'  # LOCAL: RPNG/Aria/UTMM have no depth GT
        assert all(v.get('depth_geometry',{}).get('per_view_scale_fit',False) is False for v in q['per_view'])
        rows.append(dict(arm=label,quality=str(out/'quality.json'),quality_sha256=sha(out/'quality.json'),
                         psnr=q['mean_psnr'],ssim=q['mean_ssim'],lpips=q['mean_lpips'],
                         gaussian_count=q['gaussian_count'],heldout_views=q['view_count'],depth_geometry=q['depth_geometry']))
    write(a.run/'stage_metrics.json',dict(passed=True,scene=c['scene'],stages=rows))

if __name__=='__main__':main()
