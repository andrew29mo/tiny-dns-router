"""Verify portable dual-platform evidence; no performance/RSS ratios across OSes."""
import argparse
import json
from pathlib import Path
import re
from tools.benchmark import manifest,render
from tools.check_report import need,verify
from tools.validation_suite import sha


def check(output,finalizing=False,current=True):
    output=Path(output);r=json.loads((output/'combined.json').read_text())
    need(r['schema_version']==1 and r['status']==('checking' if finalizing else 'passed'),'combined status')
    need(r['initial_vm_state'] in ['Absent','Stopped'],'VM active during native run')
    need(r['cleanup']==dict(container='removed',vm='stopped',errors=[]),'cleanup')
    need(r['container_exit']==dict(Running=False,ExitCode=0,OOMKilled=False,Error=''),'container exit')
    required=['native-venv','native-install','native-driver','vm-start','image-build','container-create','linux-driver','linux-export','cleanup-owned','cleanup-remove','cleanup-remaining','vm-stop','final-vm-state']
    need(all(k in r['operations'] for k in required),'missing command')
    for k,v in r['operations'].items():
        need(v['status']=='passed' and v['exit_code']==0,'command failed: '+k)
        need(v['log']==k+'.txt' and sha(output/v['log'])==v['log_sha256'],'command log hash')
    need(sha(output/'linux-runtime.json')==r['linux_runtime_sha256'],'runtime hash')
    vm=json.loads((output/'linux-runtime.json').read_text());co=vm['container']
    need(co==dict(NetworkMode='none',Privileged=False,NanoCpus=4000000000,Memory=4294967296,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],user='validator',mounts=[]),'container isolation')
    need(vm['Architecture'] in ['aarch64','arm64','x86_64','amd64'] and vm['image']['Os']=='linux','VM architecture')
    suites=[];reports=[]
    for folder,environment,system in [('native','native-macos','Darwin'),('linux','colima-linux','Linux')]:
        directory=output/folder;s=json.loads((directory/'validation.json').read_text());suites.append(s)
        need(s['schema_version']==1 and s['status']=='passed' and s['environment']==environment and s['os']==system and s['children_remaining']==0,'suite outcome')
        need(set(s['operations'])=={'benchmark','report','tests','mutations'},'suite commands')
        for k,v in s['operations'].items():
            need(v['status']=='passed' and v['exit_code']==0,'suite command failed')
            need(v['log']==k+'.txt' and sha(directory/v['log'])==v['log_sha256'],'suite log hash')
        tests=(directory/'tests.txt').read_text();need(re.search(r'Ran [1-9][0-9]* tests',tests) is not None and tests.rstrip().endswith('OK'),'test completion')
        need((directory/'mutations.txt').read_text().count(': detected')==5,'mutation completion')
        report=json.loads((directory/'benchmark/report.json').read_text());reports.append(report)
        need(verify(report,current=current)==36,'incomplete measurements')
        need(report['environment']['label']==environment and report['environment']['os']==system and report['source_files']==s['source_files'],'report environment/source')
        need(render(report)==(directory/'benchmark/report.html').read_text(),'HTML differs')
    need(suites[0]['source_files']==suites[1]['source_files'],'different formal implementation')
    need(all(r['input_files'].get(n)==h for n,h in suites[0]['source_files'].items()),'snapshot/source binding')
    aliases={'arm64':'arm64','aarch64':'arm64','amd64':'x86_64','x86_64':'x86_64'}
    need(aliases[suites[0]['machine']]==aliases[suites[1]['machine']]==aliases[vm['Architecture']]==aliases[vm['image']['Architecture']],'emulated or different architecture')
    if current:
        root=Path(__file__).resolve().parents[1]
        for name in ['containers/validation.Dockerfile','tools/colima-lock.json','tools/validate-local']:
            need(r['input_files'][name]==sha(root/name),'validation setup differs')
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();check(a.directory)
    print('Both formal suites and 72 measured trials verified; cleanup passed; native and VM results remain separate.')
