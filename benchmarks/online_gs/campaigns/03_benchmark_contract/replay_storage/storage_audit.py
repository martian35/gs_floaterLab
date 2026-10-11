"""Validate logical retention independently of the replay image storage tier."""
def audit_storage(r):
    b=r['bounded_rgb']; s=b['rgb_store']; c=r['replay_storage_config']
    assert not b['membership_changed'] and not b['keyframes_capped']
    assert not b['sampling_changed'] and not b['frontend_buffers_changed']
    assert b['replacement']=='none_full_admitted_pool'
    assert s['expired_rgb']==s['heldout_retained']==0
    for generation in r['training']['generations']:
        p=generation['policy']
        assert not p['retired_dense'] and not p['dense_evictions']
        assert p['dense_capacity'] is None
    if c['mode']=='tiered_fifo':
        t=s['tiers']
        assert t['logical_entries']==s['retained_rgb']
        assert t['logical_entries']==t['gpu_entries']+t['ram_entries']+t['ssd_entries']
        assert t.get('peak_gpu_entries',0)<=t['gpu_capacity']==c['gpu_capacity']
        assert t.get('peak_ram_entries',0)<=t['ram_capacity']==c['ram_capacity']
        assert t['policy']=='arrival_FIFO_no_read_promotion'
        assert t['cameras_exact_pixels_checked']>0
    else:
        assert c['mode']=='full_ram'
        assert b['float_rgb_cache']['peak_entries']<=64
    return dict(policy='full_logical_replay',storage=c['mode'],passed=True)
