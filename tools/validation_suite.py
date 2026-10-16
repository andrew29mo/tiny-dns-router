"""Identical formal suite and measurement driver in both environments."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import psutil
from tools.benchmark import manifest
from tools.validation_process import execute,cancellation_signals

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path,value):
    path=Path(path);temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)

def run(output,environment):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    receipt=dict(schema_version=1,status='running',environment=environment,os=platform.system(),machine=platform.machine(),python=platform.python_version(),source_files={},operations={})
    def write():save(output/'validation.json',receipt)
    write()
    try:
        receipt['source_files']=manifest();write()
        if (environment=='native-macos' and platform.system()!='Darwin') or (environment=='colima-linux' and platform.system()!='Linux'):raise RuntimeError('Wrong platform')
        commands=[('benchmark',[sys.executable,'-m','tools.benchmark','--output',str(output/'benchmark'),'--blocks','3','--label',environment]),('report',[sys.executable,'-m','tools.check_report',str(output/'benchmark')]),('tests',[sys.executable,'-m','tools.run_tests','--output',str(output/'tests.json')]),('mutations',[sys.executable,'-m','tools.mutation_check'])]
        env=dict(os.environ,DNSROUTER_TEST_REPORT=str(output/'benchmark'))
        for name,command in commands:
            result=execute(command,output/(name+'.txt'),timeout=300,cwd=ROOT,env=env)
            receipt['operations'][name]=result;write()
            if result['status']!='passed' or result['exit_code']!=0:raise RuntimeError('Failed or timed out: '+name)
        receipt['test_outcomes_sha256']=sha(output/'tests.json')
        if receipt['source_files']!=manifest():raise RuntimeError('Source changed during validation')
        live=[p for p in psutil.Process().children(recursive=True) if p.is_running() and p.status()!=psutil.STATUS_ZOMBIE]
        if live:raise RuntimeError('Owned children survived suite')
        receipt['children_remaining']=0;receipt['status']='passed';write()
    except BaseException as e:
        receipt.update(status='failed',error_type=type(e).__name__);write();raise
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',choices=['native-macos','colima-linux'],required=True);a=p.parse_args()
    with cancellation_signals():run(a.output,a.environment)
