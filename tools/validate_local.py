"""One owned immutable snapshot; sequential macOS and isolated Colima Linux."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
from tools.install_colima import install
from tools.validation_process import execute,cancellation_signals,cleanup_signals
from tools.validation_suite import save,sha

ROOT=Path(__file__).resolve().parents[1]


def inventory(root):
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root,timeout=30).decode().split('\0')
    result={}
    for name in filter(None,names):
        p=root/name
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root.resolve()):raise ValueError('Snapshot requires ordinary tracked files')
        result[name]=sha(p)
    return result


class Commands:
    def __init__(self,output,receipt):self.output=output;self.receipt=receipt;self.env=None
    def call(self,name,command,timeout=120,check=True,cwd=ROOT):
        result=execute(command,self.output/(name+'.txt'),timeout=timeout,cwd=cwd,env=self.env)
        self.receipt['operations'][name]=result;save(self.output/'combined.json',self.receipt)
        if check and (result['status']!='passed' or result['exit_code']!=0):raise RuntimeError('Command failed or timed out: '+name)
        return result
    def capture(self,name,command,**kwargs):
        self.call(name,command,**kwargs);return (self.output/(name+'.txt')).read_text().strip()


def profile_state(c,colima,label):
    items=[json.loads(line) for line in c.capture(label,[colima,'list','--json']).splitlines() if line.strip()]
    items=[p for p in items if p['name']=='dns']
    if len(items)>1:raise RuntimeError('Ambiguous VM profile')
    return items[0]['status'] if items else 'Absent'


def check_snapshot(workspace,files):
    if any(not (workspace/n).is_file() or sha(workspace/n)!=h for n,h in files.items()):raise RuntimeError('Snapshot input changed')


def run(output):
    if platform.system()!='Darwin' or sys.version_info[:2]!=(3,12):raise RuntimeError('Use project macOS Python 3.12 environment')
    output=Path(output).resolve()
    # Build contexts must never contain the live output recursively.
    if not output.is_relative_to(ROOT/'results/local'):raise ValueError('Output must be inside ignored results/local')
    output.mkdir(parents=True,exist_ok=False)
    r=dict(schema_version=1,status='running',generated_utc=datetime.now(timezone.utc).isoformat(),operations={},scope='Native macOS and Colima Linux VM measured separately; process RSS excludes VM/kernel/client/peer memory.')
    save(output/'combined.json',r);c=Commands(output,r)
    token=uuid.uuid4().hex;colima=docker=name=None;attempted=False
    lockpath=ROOT/'results/local/validation.lock'
    with lockpath.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            r['status']='failed';save(output/'combined.json',r);raise RuntimeError('Another validation owns this project VM') from None
        try:
            try:
                binaries,c.env=install();colima=str(binaries/'colima');docker=str(binaries/'docker')
                state=profile_state(c,colima,'initial-vm-state');r['initial_vm_state']=state
                if state not in ['Stopped','Absent']:raise RuntimeError('Dedicated DNS VM is already running; stop it before validation')
                files=inventory(ROOT);r['input_files']=files
                r['base_commit']=c.capture('base-commit',['git','rev-parse','HEAD'])
                workspace=output/'context/workspace';workspace.mkdir(parents=True)
                for n in files:
                    dest=workspace/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,dest)
                check_snapshot(workspace,files)
                native_env=output/'native-env'
                c.call('native-venv',[sys.executable,'-m','venv',str(native_env)])
                python=str(native_env/'bin/python')
                c.call('native-install',[python,'-m','pip','install','-r','requirements-dev.txt'],cwd=workspace,timeout=300)
                print('Running native macOS suite and complete measurements; DNS VM stopped.',flush=True)
                c.call('native-driver',[python,'-m','tools.validation_suite','--output',str(output/'native'),'--environment','native-macos'],cwd=workspace,timeout=1200)
                check_snapshot(workspace,files)
                attempted=True
                print('Starting dedicated Colima Linux VM.',flush=True)
                c.call('vm-start',[colima,'start','dns','--cpu','4','--memory','6','--disk','30','--vm-type','vz','--runtime','docker','--mount','none','--activate=false','--ssh-config=false','--ssh-agent=false','--vz-rosetta=false','--binfmt=false'],timeout=900)
                info=json.loads(c.capture('docker-info',[docker,'info','--format','{{json .}}']))
                runtime={k:info[k] for k in ['ServerVersion','KernelVersion','Architecture','OperatingSystem','NCPU','MemTotal']}
                expected=['aarch64','arm64'] if platform.machine()=='arm64' else ['x86_64','amd64']
                if runtime['Architecture'] not in expected:raise RuntimeError('Unexpected VM architecture')
                runtime['colima_version']=c.capture('colima-version',[colima,'version'])
                runtime['lima_version']=c.capture('lima-version',[str(binaries/'limactl'),'--version'])
                shutil.copy2(workspace/'containers/validation.Dockerfile',output/'context/Dockerfile')
                image='tiny-dns-validation:'+token
                c.call('image-build',[docker,'build','--load','-t',image,str(output/'context')],timeout=900)
                im=json.loads(c.capture('image-info',[docker,'image','inspect',image]))[0]
                runtime['image']={k:im[k] for k in ['Id','Architecture','Os']}
                name='tiny-dns-validation-'+token
                c.call('container-create',[docker,'create','--name',name,'--label','tiny-dns.validation.run='+token,'--network','none','--cap-drop','ALL','--security-opt','no-new-privileges','--cpus','4','--memory','4g',image,'--output','/evidence/run','--environment','colima-linux'])
                ci=json.loads(c.capture('container-info',[docker,'inspect',name]))[0]
                runtime['container']={k:ci['HostConfig'][k] for k in ['NetworkMode','Privileged','NanoCpus','Memory','CapDrop','SecurityOpt']}
                runtime['container'].update(user=ci['Config']['User'],mounts=ci['Mounts'])
                save(output/'linux-runtime.json',runtime);r['linux_runtime_sha256']=sha(output/'linux-runtime.json')
                print('Running Linux suite and separate VM measurements.',flush=True)
                attached=c.call('linux-driver',[docker,'start','--attach',name],timeout=1200,check=False)
                st=json.loads(c.capture('container-exit',[docker,'inspect',name]))[0]['State']
                r['container_exit']={k:st[k] for k in ['Running','ExitCode','OOMKilled','Error']}
                c.call('linux-export',[docker,'cp',name+':/evidence/run',str(output/'linux')])
                if attached['status']!='passed' or st['ExitCode']!=0 or st['Running'] or st['OOMKilled'] or st['Error']:raise RuntimeError('Linux attach or container failed')
                check_snapshot(workspace,files)
                if inventory(ROOT)!=files:raise RuntimeError('Working input changed during run')
            finally:
                with cleanup_signals():
                    cleanup=dict(container='not-created',vm='not-started',errors=[])
                    if docker and attempted:
                        try:
                            ids=c.capture('cleanup-owned',[docker,'ps','-aq','--filter','label=tiny-dns.validation.run='+token]).split()
                            for ident in ids:
                                st=json.loads(c.capture('cleanup-inspect',[docker,'inspect',ident]))[0]['State']
                                if st['Running']:c.call('cleanup-kill',[docker,'kill',ident])
                                if not (output/'linux').exists():c.call('cleanup-export',[docker,'cp',ident+':/evidence',str(output/'linux-failed')],check=False)
                                c.call('cleanup-remove',[docker,'rm',ident])
                            if c.capture('cleanup-remaining',[docker,'ps','-aq','--filter','label=tiny-dns.validation.run='+token]):raise RuntimeError('Owned container survived')
                            cleanup['container']='removed'
                        except BaseException as e:cleanup['errors'].append('container: '+type(e).__name__)
                    if colima and attempted:
                        try:
                            c.call('vm-stop',[colima,'stop','dns'],timeout=180)
                            if profile_state(c,colima,'final-vm-state')!='Stopped':raise RuntimeError('VM not stopped')
                            cleanup['vm']='stopped'
                        except BaseException as e:cleanup['errors'].append('vm: '+type(e).__name__)
                    r['cleanup']=cleanup;save(output/'combined.json',r)
            if r['cleanup']['errors']:raise RuntimeError('Cleanup failed')
            r['status']='checking';save(output/'combined.json',r)
            from tools.check_validation import check
            check(output,finalizing=True)
            r['status']='passed';save(output/'combined.json',r)
        except BaseException as e:
            r.update(status='failed',error_type=type(e).__name__);save(output/'combined.json',r);raise
    print('Both environments passed; evidence: '+str(output),flush=True)
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'results/local/validation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));a=p.parse_args()
    with cancellation_signals():run(a.output)
