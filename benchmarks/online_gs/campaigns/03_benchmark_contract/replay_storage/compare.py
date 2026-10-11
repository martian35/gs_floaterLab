"""Serial 6N quality/time regression of logical-full replay storage."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
EQUAL=HERE.parent/'mapper_equal_render'
SHARED=HERE.parent/'temporal_pool_equal_time'
sys.path[:0]=[str(EQUAL),str(HERE.parent/'mapper_baselines/v2'),'/home/intern/VIGS-SLAM-custom/scripts/selected_mapping']
from run_c import c_environment
from custom_c_gpu_exception import busy_lines
from corrected_memory_sampler import ProcessTreeSampler
from run_custom_c_large_pool_suite import wait_owned_child
from owned_process_group import terminate_remaining_run_workers
BASE=Path('/ssd/intern/paperExperiments/runs/campaigns/03_benchmark_contract/temporal_pool_equal_time/20261010_v1')

def read(p):return json.loads(Path(p).read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
 p.add_argument('--smoke',action='store_true');p.add_argument('--repeats',type=int,default=2)
 p.add_argument('--native',action='store_true')
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
 receipt=out/'gpu_exception.json'
 if not receipt.exists():
  r=read(BASE/'gpu_exception.json');r['scope']='User-authorized D storage-only quality and timing comparison; same Jupyter process coexistence';write(receipt,r)
 captures={r['dataset']:r for r in read(BASE/'progress.json')['runs'] if r['variant']=='capture' and r['status']=='completed'}
 if (out/'progress.json').exists(): state=read(out/'progress.json')
 else:
  rows=[]
  for repeat in range(a.repeats):
   for dataset in (['rpng'] if a.smoke else ['aria','rpng','tum_rgbd']):
    modes=['stress'] if a.smoke else (['full_ram','tiered_fifo'] if repeat%2==0 else ['tiered_fifo','full_ram'])
    for mode in modes:
     c=captures[dataset]
     rows.append(dict(dataset=dataset,scene=c['scene'],mode=mode,repeat=repeat,
       output=str(out/f'{dataset}_{mode}_r{repeat}'),contract=c['scene_contract'],tape=c['tape'],status='pending'))
  state=dict(runs=rows,attempts=[],native=a.native,scope='6N, seed0, D 3:3:6 without replacement, image-wise Adam')
  write(out/'progress.json',state)
 python,cwd,env=c_environment()
 env.update(CUSTOM_C_BENCHMARK_BOOTSTRAP='1',CUSTOM_C_GPU_EXCEPTION_FILE=str(receipt))
 env['PYTHONPATH']=str(EQUAL/'queue_python_bootstrap')+':'+env['PYTHONPATH']
 def command(row,stage,argv,training=False):
  while busy_lines(receipt):
   state['state']='waiting_GPU';write(out/'progress.json',state);time.sleep(10)
  state['state']=stage;row['status']=stage;log=out/(Path(row['output']).name+'_'+stage+'.log')
  record=dict(command=[python,*argv],stage=stage,log=str(log),started=time.time())
  state['attempts'].append(record)
  with log.open('w') as f:
   child=subprocess.Popen([python,*argv],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   record['pid']=child.pid;write(out/'progress.json',state)
   sampler=ProcessTreeSampler(child.pid) if training else None
   code,guard=wait_owned_child(child,[out],out)
   record.update(returncode=code,finished=time.time(),guard=guard,cleanup=terminate_remaining_run_workers(child.pid))
   if sampler is not None and Path(row['output']).exists():write(Path(row['output'])/'gpu_memory.json',sampler.close())
  write(out/'progress.json',state)
  if code:raise RuntimeError(f'{stage} failed: {log}')
 for row in state['runs']:
  if row['status']=='completed':continue
  run=Path(row['output']);mode='tiered_fifo' if row['mode']=='stress' else row['mode']
  try:
   if not (run/'runtime.json').exists():
    runner=HERE.parent/'mapper_recipe_d/run_d.py' if a.native else HERE/'run_mapper.py'
    argv=[str(runner),'--scene-contract',row['contract'],'--output',str(run),'--seed','0','--replay-storage',mode]
    if not a.native:argv+=['--frontend-cache',row['tape'],'--variant','legacy']
    if row['mode']=='stress':argv+=['--replay-gpu-capacity','16','--replay-ram-capacity','32']
    command(row,'training',argv,True)
   if not (run/'evaluation/quality.json').exists():
    evaluator=EQUAL/'evaluate_run.py' if a.native else SHARED/'evaluate.py'
    command(row,'evaluation',[str(evaluator),'--scene-contract',row['contract'],'--run',str(run),'--config',str(run/'native_sensor_config.yaml'),'--output',str(run/'evaluation')])
   audit=HERE.parent/'mapper_recipe_d/audit_d.py' if a.native else SHARED/'audit.py'
   command(row,'audit',[str(audit),'--scene-contract',row['contract'],'--run',str(run),'--evaluation',str(run/'evaluation'),'--output',str(run/'audit.json')])
   r=read(run/'runtime.json');q=read(run/'evaluation/quality.json')
   row.update(status='completed',psnr=q['mean_psnr'],ssim=q['mean_ssim'],lpips=q['mean_lpips'],mapper_seconds=r['mapper_seconds'],whole_seconds=r['whole_seconds'],renders=r['completed_training_renders'],gaussians=r['gaussian_count'])
   write(out/'progress.json',state)
  except BaseException as exc:
   row.update(status='failed',error=repr(exc));write(out/'progress.json',state);raise
 state['state']='completed';write(out/'progress.json',state)

if __name__=='__main__':main()
