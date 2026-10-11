"""Paired quality, time and unchanged sample-stream checks for storage experiments."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean

def read(p):return json.loads(Path(p).read_text())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row_metrics(row):
    root=Path(row['output']);r=read(root/'runtime.json');q=read(root/'evaluation/quality.json')
    return dict(psnr=q['mean_psnr'],ssim=q['mean_ssim'],lpips=q['mean_lpips'],
                mapper_seconds=r['mapper_seconds'],whole_seconds=r['whole_seconds'],
                mapper_with_admission_seconds=r.get('mapper_with_admission_seconds'),
                input_mapping_stream_seconds=r.get('input_mapping_stream_seconds'),
                gaussians=r['gaussian_count'],renders=r['completed_training_renders'],
                peak_vram_gib=read(root/'gpu_memory.json')['peak_process_tree_vram_bytes_sampled']/1024**3,
                storage=r['bounded_rgb']['rgb_store'])
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args()
    state=read(a.root/'progress.json');rows=state['runs'];pairs=[]
    for dataset,repeat in sorted({(r['dataset'],r['repeat']) for r in rows}):
        arms={r['mode']:r for r in rows if r['dataset']==dataset and r['repeat']==repeat and r['status']=='completed'}
        if not {'full_ram','tiered_fifo'}<=arms.keys():continue
        left,right=(Path(arms[k]['output']) for k in ('full_ram','tiered_fifo'))
        rl,rr=(read(x/'runtime.json') for x in (left,right))
        ml,mr=(row_metrics(arms[k]) for k in ('full_ram','tiered_fifo'))
        sample=lambda path:[w['uid'] for w in read(path/'render_work.json')]
        checks=dict(sample_sequence_identical=sample(left)==sample(right),
                    memberships_counts_admissions_identical=rl['training']['generations']==rr['training']['generations'],
                    poses_identical=read(left/'causal_native_keyframe_poses.json')==read(right/'causal_native_keyframe_poses.json'),
                    map_file_identical=digest(left/'online_map.ply')==digest(right/'online_map.ply'),
                    equal_steps=ml['renders']==mr['renders'],audits_passed=read(left/'audit.json')['passed'] and read(right/'audit.json')['passed'])
        assert checks['equal_steps'] and checks['audits_passed']
        if not state['native']:
            assert checks['sample_sequence_identical'] and checks['memberships_counts_admissions_identical'] and checks['poses_identical']
        pairs.append(dict(dataset=dataset,repeat=repeat,baseline=ml,tiered=mr,checks=checks,
                          psnr_delta=mr['psnr']-ml['psnr'],mapper_time_change_percent=100*(mr['mapper_seconds']/ml['mapper_seconds']-1),
                          whole_time_change_percent=100*(mr['whole_seconds']/ml['whole_seconds']-1)))
    summary=[]
    for dataset in sorted({p['dataset'] for p in pairs}):
        values=[p for p in pairs if p['dataset']==dataset]
        record=dict(dataset=dataset,repeats=len(values),baseline_psnr=mean(p['baseline']['psnr'] for p in values),tiered_psnr=mean(p['tiered']['psnr'] for p in values),
                    baseline_mapper_seconds=mean(p['baseline']['mapper_seconds'] for p in values),tiered_mapper_seconds=mean(p['tiered']['mapper_seconds'] for p in values),
                    baseline_whole_seconds=mean(p['baseline']['whole_seconds'] for p in values),tiered_whole_seconds=mean(p['tiered']['whole_seconds'] for p in values))
        record['mapper_time_change_percent']=100*(record['tiered_mapper_seconds']/record['baseline_mapper_seconds']-1)
        record['whole_time_change_percent']=100*(record['tiered_whole_seconds']/record['baseline_whole_seconds']-1)
        record['psnr_delta']=record['tiered_psnr']-record['baseline_psnr']
        summary.append(record)
    result=dict(native=state['native'],pairs=pairs,summary=summary,complete=all(r['status']=='completed' for r in rows),
        scope='Storage comparison, full logical replay in both arms; same-seed repetitions measure runtime variability, not independent algorithm seeds')
    (a.root/'comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
