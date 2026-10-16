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
        need(v['status']=='passed' and v['exit_code']==0 and v.get('reclaimed_orphans')==0,'command failed: '+k)
        need(v['log']==k+'.txt' and sha(output/v['log'])==v['log_sha256'],'command log hash')
    need(sha(output/'linux-runtime.json')==r['linux_runtime_sha256'],'runtime hash')
    vm=json.loads((output/'linux-runtime.json').read_text());co=vm['container']
    need(co==dict(NetworkMode='none',Privileged=False,NanoCpus=4000000000,Memory=4294967296,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],user='validator',mounts=[]),'container isolation')
    need(vm['Architecture'] in ['aarch64','arm64','x86_64','amd64'] and vm['image']['Os']=='linux','VM architecture')
    raw_image=json.loads((output/'image-info.txt').read_text())[0]
    raw_container=json.loads((output/'container-info.txt').read_text())[0]
    raw_exit=json.loads((output/'container-exit.txt').read_text())[0]['State']
    need(all(raw_exit[k]==v for k,v in r['container_exit'].items()),'container exit contradicts inspect')
    need(all(raw_image[k]==v for k,v in vm['image'].items()) and raw_container['Image']==vm['image']['Id'],'image binding')
    need(all(raw_container['HostConfig'][k]==v for k,v in co.items() if k not in ['user','mounts']) and raw_container['Config']['User']==co['user'] and raw_container['Mounts']==co['mounts'],'runtime contradicts inspect')
    final_states=[json.loads(x) for x in (output/'final-vm-state.txt').read_text().splitlines() if x.strip()]
    need([x['status'] for x in final_states if x['name']=='dns']==['Stopped'],'VM stop contradicts list')
    need(not (output/'cleanup-remaining.txt').read_text().strip(),'container removal contradicts list')
    suites=[];reports=[];test_sets=[]
    for folder,environment,system in [('native','native-macos','Darwin'),('linux','colima-linux','Linux')]:
        directory=output/folder;s=json.loads((directory/'validation.json').read_text());suites.append(s)
        need(s['schema_version']==1 and s['status']=='passed' and s['environment']==environment and s['os']==system and s['children_remaining']==0,'suite outcome')
        need(set(s['operations'])=={'benchmark','report','tests','mutations'},'suite commands')
        for k,v in s['operations'].items():
            need(v['status']=='passed' and v['exit_code']==0 and v.get('reclaimed_orphans')==0,'suite command failed or orphaned children')
            need(v['log']==k+'.txt' and sha(directory/v['log'])==v['log_sha256'],'suite log hash')
            module={'benchmark':'tools.benchmark','report':'tools.check_report','tests':'tools.run_tests','mutations':'tools.mutation_check'}[k]
            need(v['command'][1:3]==['-m',module],'wrong formal command')
        need(sha(directory/'tests.json')==s['test_outcomes_sha256'],'test outcomes hash')
        outcomes=json.loads((directory/'tests.json').read_text());test_sets.append(outcomes['expected_ids'])
        need(outcomes['schema_version']==1 and outcomes['status']=='passed' and outcomes['expected_ids'] and outcomes['expected_ids']==sorted(set(outcomes['expected_ids'])) and outcomes['expected_ids']==outcomes['started_ids']==outcomes['success_ids'],'test inventory or outcomes')
        tests=(directory/'tests.txt').read_text();need(re.search(r'Ran [1-9][0-9]* tests',tests) is not None and tests.rstrip().endswith('OK'),'test completion')
        need(re.search(r'Ran ([0-9]+) tests',tests).group(1)==str(len(outcomes['expected_ids'])),'test count differs')
        need((directory/'mutations.txt').read_text().count(': detected')==5,'mutation completion')
        report=json.loads((directory/'benchmark/report.json').read_text());reports.append(report)
        need(verify(report,current=current)==36,'incomplete measurements')
        need(report['environment']['label']==environment and report['environment']['os']==system and report['environment']['machine']==s['machine'] and report['environment']['python']==s['python'] and report['source_files']==s['source_files'],'report environment/source')
        need(render(report)==(directory/'benchmark/report.html').read_text(),'HTML differs')
    need(test_sets[0]==test_sets[1],'different formal tests')
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
