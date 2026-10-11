"""Persistent TUM10 mapper/geometry ablation, gated by a full-scene pilot."""
import argparse
from collections import Counter, defaultdict
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
EQUAL=HERE.parent/'mapper_equal_render'
V2=HERE.parent/'mapper_baselines/v2'
SELECTED=Path('/home/intern/VIGS-SLAM-custom/scripts/selected_mapping')
sys.path[:0]=[str(EQUAL),str(V2),str(SELECTED)]
from run_c import c_environment
from custom_common import sha
from run_custom_c_large_pool_suite import wait_owned_child,write
from custom_c_gpu_exception import busy_lines
from corrected_memory_sampler import ProcessTreeSampler
from owned_process_group import terminate_remaining_run_workers


def read(p):return json.loads(Path(p).read_text())

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    lock=(out/'suite.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=read(out/'plan.json');selection=read(out/'scene_selection.json')['selection']
    order=['R4','R2@0.5','R2-I@0.5','R2@0.75','R2-I@0.75','R2@1','R2-I@1','R2@1.5','R2-I@1.5'];current=None
    state=read(out/'progress.json') if (out/'progress.json').exists() else dict(state='prepared',conditions=[],attempts=[],pilot_passed=False)
    if not state['conditions']:
        for i,s in enumerate(selection):
            for arm in (['R4','R4-replay-validation','R2@0.5','R2-I@0.5','R2@0.75','R2-I@0.75','R2@1','R2-I@1','R2@1.5','R2-I@1.5'] if i==0 else order):
                state['conditions'].append(dict(scene=s['scene'],arm=arm,scene_contract=s['scene_contract'],status='queued',
                    output=str(out/'trials'/s.get('dataset','tum_rgbd')/s['scene']/arm/'seed0'),cache=str(out/'frontend_cache'/s['scene']),
                    validation_only=arm=='R4-replay-validation'))
    source_paths=list(HERE.glob('*.py'))+[out/'plan.json',out/'scene_selection.json',EQUAL/'run_custom_c_large_pool_6n.py',EQUAL/'render_quota.py',V2/'evaluate_python.py']
    locks_path=out/'suite_source_locks.json'
    if not locks_path.exists():write(locks_path,{str(f):sha(f) for f in source_paths})
    locks=read(locks_path)
    py,cwd,env=c_environment()
    receipt=out/'gpu_exception.json';env['CUSTOM_C_GPU_EXCEPTION_FILE']=str(receipt)
    env['CUSTOM_C_BENCHMARK_BOOTSTRAP']='1'
    env['PYTHONPATH']=str(EQUAL/'queue_python_bootstrap')+':'+env['PYTHONPATH']
    # Parent recovery service orders UTMM first and holds snapshot-queue priority.
    wait_services=[]
    def save():
        state.update(updated_at=time.time(),pid=os.getpid(),status_counts=dict(Counter(r['status'] for r in state['conditions'])),
                     formal_status_counts=dict(Counter(r['status'] for r in state['conditions'] if not r['validation_only'])))
        write(out/'progress.json',state)
    def check():
        changed=[p for p,h in locks.items() if sha(p)!=h]
        if changed:raise RuntimeError('Ablation source changed after launch: '+str(changed))
        if (out/'stop_after_current_stage.json').exists():raise RuntimeError('Stop requested, artifacts preserved')
    def wait_gpu():
        while True:
            check()
            services=[s for s in wait_services if subprocess.run(['systemctl','--user','is-active','--quiet',s]).returncode==0]
            busy=busy_lines(receipt)
            if not services and not busy:return
            state.update(state='waiting_for_existing_GPU_jobs',waiting_services=services,waiting_gpu=busy);save();time.sleep(10)
    def command(row,stage,argv,gpu=True,training=False):
        nonlocal current
        while True:
            if gpu:wait_gpu()
            check();state.update(state=stage,current_condition={k:row[k] for k in ('scene','arm')});row['status']=stage
            log=out/'logs'/row['scene']/row['arm']/f'{len(state["attempts"]):04d}_{stage}.log';log.parent.mkdir(parents=True,exist_ok=True)
            attempt=dict(scene=row['scene'],arm=row['arm'],stage=stage,command=[py,*argv],log=str(log),started_at=time.time())
            state['attempts'].append(attempt)
            with log.open('w') as stream:
                current=subprocess.Popen([py,*argv],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                attempt['pid']=current.pid;save();sampler=ProcessTreeSampler(current.pid) if training else None
                code,guard=wait_owned_child(current,[out],out)
                attempt.update(returncode=code,finished_at=time.time(),guard=guard,cleanup=terminate_remaining_run_workers(current.pid))
                if sampler is not None and Path(row['output']).exists():write(Path(row['output'])/'gpu_memory.json',sampler.close())
                current=None;save()
            if code==75:time.sleep(10);continue
            if code:raise RuntimeError(f'{stage} failed, exit {code}: {log}')
            return
    def notify(title,message):
        subprocess.run(['notify-send','--app-name=TUM ablation',title,message],capture_output=True)
    def pilot_equivalence():
        rows=state['conditions'][:2];capture,replay=[read(Path(r['output'])/'runtime.json') for r in rows]
        ca,ra=[read(Path(r['output'])/'render_work.json') for r in rows]
        cq,rq=[read(Path(r['output'])/'stage_metrics.json')['stages'][0] for r in rows]
        checks=dict(same_tape=capture['frontend_tape']['manifest_sha256']==replay['frontend_tape']['manifest_sha256'],
                    identical_loss_view_sequence=[r['uid'] for r in ca]==[r['uid'] for r in ra],
                    same_render_budget=capture['completed_training_renders']==replay['completed_training_renders'],
                    same_mapping_uids=capture['mapping_camera_uids']==replay['mapping_camera_uids'],
                    gaussian_count_close=abs(cq['gaussian_count']-rq['gaussian_count'])<=max(2,.01*cq['gaussian_count']),
                    psnr_close=abs(cq['psnr']-rq['psnr'])<=.05,
                    depth_mae_close=(cq['depth_geometry']['mae_m'] is None and rq['depth_geometry']['mae_m'] is None) if cq['depth_geometry']['mae_m'] is None else abs(cq['depth_geometry']['mae_m']-rq['depth_geometry']['mae_m'])<=max(.001,.02*cq['depth_geometry']['mae_m']))  # LOCAL: no-depth scenes
        result=dict(passed=all(checks.values()),checks=checks,capture=cq,replay=rq)
        write(out/'pilot_frontend_equivalence.json',result)
        if not result['passed']:raise RuntimeError('Frontend capture/replay pilot mismatch; expansion stopped')
    def summary():
        rows=[]
        for r in state['conditions']:
            if r['status']!='completed' or r['validation_only']:continue
            runtime=read(Path(r['output'])/'runtime.json')
            for m in read(Path(r['output'])/'stage_metrics.json')['stages']:
                rows.append(dict(scene=r['scene'],**m,training_renders=runtime['completed_training_renders'],
                    cumulative_gaussian_births=runtime['cumulative_gaussian_births'],
                    dense_admissions=sum(len(g['admissions']) for g in runtime['training']['generations']),
                    dense_evictions=sum(len(g['policy']['dense_evictions']) for g in runtime['training']['generations'])))
        groups=defaultdict(list)
        for r in rows:groups[r['arm']].append(r)
        allarms=['R2@0.5','R2-I@0.5','R2@0.75','R2-I@0.75','R2@1','R2-I@1','R2@1.5','R2-I@1.5','R4','R4-O','R4-F']
        common=set.intersection(*(set(r['scene'] for r in groups[k]) for k in allarms))
        means=[]
        for arm in allarms:
            values=[r for r in groups[arm] if r['scene'] in common]
            means.append(dict(arm=arm,common_scenes=len(values),available_scenes=len(groups[arm]),
                **{k:sum(v[k] for v in values)/len(values) if values else None for k in ['psnr','ssim','lpips','gaussian_count']},
                **{'depth_'+k:sum(v['depth_geometry'][k] for v in values)/len(values) if values and all(v['depth_geometry'].get(k) is not None for v in values) else None for k in ['mae_m','rmse_m','absrel','delta1','coverage']}))
        write(out/'summary.json',dict(scope='prespecified stable TUM10 diagnostic subset, seed0',common_scenes=sorted(common),means=means,scenes=rows))
    def stop(*_):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    save()
    try:
        for index,row in enumerate(state['conditions']):
            if row['status'] in ('completed','failed','blocked_missing_frontend'):continue
            if index==6 and not state['pilot_passed']:
                if not all(r['status']=='completed' for r in state['conditions'][:6]):raise RuntimeError('Full pilot has not passed')
                pilot_equivalence();state['pilot_passed']=True;save()
            run=Path(row['output']);contract=Path(row['scene_contract']);arm='R4' if row['validation_only'] else row['arm']
            try:
                if not (run/'runtime.json').exists():
                    if run.exists():raise RuntimeError('Incomplete prior attempt preserved; use a fresh attempt directory')
                    if arm!='R4' and not (Path(row['cache'])/'manifest.json').exists():
                        row.update(status='blocked_missing_frontend');save();continue
                    run.parent.mkdir(parents=True,exist_ok=True)
                    argv=[str(HERE/'run_arm.py'),'--scene-contract',str(contract),'--output',str(run),'--arm',arm,'--frontend-cache',row['cache']]
                    if row['arm']=='R4':argv.append('--capture')
                    command(row,'training',argv,training=True)
                if not (run/'stage_metrics.json').exists():command(row,'evaluation',[str(HERE/'evaluate_stages.py'),'--scene-contract',str(contract),'--run',str(run)])
                if not (run/'audit.json').exists():command(row,'audit',[str(HERE/'audit_arm.py'),'--scene-contract',str(contract),'--run',str(run)],gpu=False)
                row.update(status='completed',finished_at=time.time());save();summary()
                if index==1:pilot_equivalence()
            except Exception as error:
                row.update(status='failed',exception=repr(error));save()
                if index<6:raise
        state.update(state='finished',finished_at=time.time());save();summary()
        write(out/'completion.json',dict(formal_status_counts=state['formal_status_counts'],pilot_passed=state['pilot_passed'],finished_at=time.time()))
        notify('TUM ablation queue finished',str(state['formal_status_counts'])+'\n'+str(out))
    except BaseException as error:
        state.update(state='stopped_with_error',exception=repr(error));save();notify('TUM ablation needs inspection',str(error));raise
    finally:
        if current is not None:
            if current.poll() is None:os.killpg(current.pid,signal.SIGTERM)
            try:current.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(current.pid,signal.SIGKILL);current.wait()
            terminate_remaining_run_workers(current.pid)
        lock.close()

if __name__=='__main__':main()
