"""Independent full-input/6N/reference/recipe audit for Custom C datasets."""
import argparse
import sys
sys.path[:0]=["/home/intern/VIGS-SLAM-custom/scripts/selected_mapping/geometry_c"]
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from plyfile import PlyData


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene-contract',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--evaluation',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    c=json.loads(a.scene_contract.read_text())
    manifest=json.loads((Path(c['archive'])/'archive_manifest.json').read_text())
    image_height,image_width=manifest['preprocessing']['output_image_size_hw']
    r=json.loads((a.run/'runtime.json').read_text())
    q=json.loads((a.evaluation/'quality.json').read_text())
    work=json.loads((a.run/'render_work.json').read_text())
    ledger=json.loads((a.run/'render_ledger.json').read_text())
    poses=json.loads((a.run/'causal_native_keyframe_poses.json').read_text())
    oracle={int(v['uid']):v['c2w'] for v in json.loads(Path(c['reference_pose_file']).read_text())}
    train=set(c['training_uids']);heldout=set(c['heldout_uids'])
    completions=[e for e in ledger['events'] if e['kind']=='optimizer_completion']
    assert len(work)==len(completions)==c['render_budget']==r['completed_training_renders']==r['completed_adam_steps']
    granted=completed=0
    grants=[]
    for e in ledger['events']:
        if e['kind']=='quota_grant':
            n=e['training_inputs_seen'];assert n%64==0 or n==len(train)
            assert c['training_uids'][n-1]==e['input_uid']
            granted=e['cumulative_quota'];assert granted==6*n
            grants.append(n)
        elif e['kind']=='optimizer_completion':
            completed+=len(e['view_uids']);assert completed==e['completed_renders']<=granted
            assert all(u in train and u<=e['available_through_uid'] for u in e['view_uids'])
    assert completed==granted==c['render_budget']
    assert grants==list(range(64,len(train),64))+[len(train)]
    for w,e in zip(work,completions):
        assert w['completed'] and w['backward'] and e['view_uids']==[w['uid']]
        assert w['pixels']==image_height*image_width
    assert r['input_drop_count']==0 and r['tracked_input_count']==c['input_frames']-len(heldout)
    assert not r['heldout_overlap'] and not r['pending_packets']
    assert set(r['mapping_camera_uids'])<=train and set(r['loss_camera_uids'])<=train
    assert all(u in train and u<=e['available_through_uid'] for e in r['native_packet_events'] for u in e['uids'])
    assert all(u in train and u<=e['available_through_uid'] for e in r['geometry_alignment_records'] for u in e['uids'])
    errors=[float(np.max(np.abs(np.asarray(v['c2w'])-np.asarray(oracle[v['uid']])))) for v in poses]
    assert max(errors)<1e-4
    expected=sorted(u for u in heldout if oracle.get(u) is not None)
    assert [v['uid'] for v in q['per_view']]==expected
    assert q['view_count']==len(expected)>0
    assert q['reference_kind']==c['reference_kind']
    assert q['evaluation_reference_is_gt']==(c['reference_kind']=='independent_camera_gt')
    assert q['common_scene_contract_sha256']==sha(a.scene_contract)
    assert q['ply_sha256']==sha(a.run/'online_map.ply')
    for name in ('psnr','ssim','lpips'):
        values=[v[name] for v in q['per_view']]
        assert np.isfinite(values).all()
        assert abs(np.mean(values)-q['mean_'+name])<1e-10
    locks={**r['source_locks'],**r['recipe']['sources']}
    assert all(sha(path)==digest for path,digest in locks.items())
    assert [s['completed_renders'] for s in r['snapshots']]==c['snapshot_renders']
    for s in r['snapshots']:
        assert sha(a.run/s['ply'])==s['ply_sha256']
    vertex=PlyData.read(a.run/'online_map.ply')['vertex'].data
    assert len(vertex)==q['gaussian_count']==r['gaussian_count']
    assert all(np.isfinite(vertex[name]).all() for name in vertex.dtype.names)
    assert r['topology']['pass'] and r['terminal_prune']['optimizer_updates']==0
    assert r['recipe_variant']=='D' and r['terminal_prune']['enabled'] is True
    d=json.loads((a.run/'recipe_d.json').read_text())
    assert float(d['B_SCALE_CAP'])==.5 and float(d['B_COVERED_OPACITY'])==.02
    assert d.get('projection_calls',0)>0 and d.get('selop',{}).get('births',0)>0
    assert d['selop'].get('error',0)==d['selop'].get('small_error',0)==0
    assert r['unified_scale_projection']['max_scale']==.5
    assert r['recipe_d']['optional_birth_probe_enabled'] is False
    assert r['recipe_d']['birth_count_and_positions_changed'] is False
    b = r['bounded_rgb']; store = b['rgb_store']
    pool_policy = r.get('training_pool_policy', 'legacy')
    storage_mode=r.get('replay_storage_config',{}).get('mode','legacy')
    if storage_mode!='legacy':
        sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'replay_storage'))
        from storage_audit import audit_storage
        pool_checks=audit_storage(r)
    elif pool_policy == 'temporal':
        from temporal_audit import audit_temporal
        pool_checks = audit_temporal(r)
        assert b['membership_changed'] and b['keyframes_capped']
        assert r['recipe_configuration'] == 'D_temporal_pool'
        assert store['peak_retained_rgb'] <= store['dense_capacity'] + store['recent_capacity']
    else:
        assert pool_policy == 'legacy'
        pool_checks = {'policy': 'legacy'}
        assert b['float_rgb_cache']['peak_entries'] <= b['float_rgb_cache']['capacity'] == 64
        assert b['membership_changed'] and not b['keyframes_capped']
        assert b['replacement']=='oldest_frame_uid'
        assert b['peak_dense_cameras'] <= b['dense_capacity']
        assert store['peak_retained_rgb'] <= b['dense_capacity'] + b['recent_capacity']
    if storage_mode=='legacy':
        assert store['image_spill_reads']==store['image_spill_writes']==0
    assert store['heldout_retained']==0
    from audit_c_export import check_export
    c_checks=check_export(a.run, c, r)

    assert not r['fake_IMU_provided']
    assert r['optional_imu_adapter']['thresholds_changed'] is False
    assert r['optional_imu_adapter']['fake_IMU_provided'] is False
    assert not r['final_ba'] and not r['final_refinement'] and not r['GT_depth_used'] and not r['GT_pose_provided_to_frontend']
    assert all(r['TensorRT_engines_loaded'].values())
    roles=dict(Counter(row['role'] for row in r['training']['loss_routes']))
    result={'recipe_variant':'D','D_projection_calls':d['projection_calls'],'D_selective_births':d['selop'],'passed':True,'custom_c':c_checks,'training_renders':completed,'adam_steps':len(completions),
        'training_pool_policy':pool_policy,'pool_checks':pool_checks,
        'tracked_inputs':r['tracked_input_count'],'valid_training_inputs':len(train),
        'heldout_views':len(expected),'mapping_cameras':len(poses),'loss_cameras':len(r['loss_camera_uids']),
        'heldout_overlap':0,'max_camera_c2w_absolute_error':max(errors),
        'source_hashes_checked':len(locks),'snapshot_hashes_checked':len(r['snapshots']),
        'gaussian_count':len(vertex),'loss_role_counts':roles,
        'mean_psnr':q['mean_psnr'],'mean_ssim':q['mean_ssim'],'mean_lpips':q['mean_lpips'],
        'reference_kind':c['reference_kind'],'independent_GT':c['reference_kind']=='independent_camera_gt',
        'scope':'one scene, recipe D on selected C backbone; 6N training plus separately counted FM export; no real-time or geometry quality claim'}
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
