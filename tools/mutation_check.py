"""Require actual network tests to reject intentionally broken production paths."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
FAULTS=[('suffix_label_boundary','dnsrouter/config.py','name.is_subdomain(dns.name.from_text(r[\'suffix\']))','name.to_text().lower().endswith(r[\'suffix\'])','test_real_udp_tcp_a_aaaa_and_suffix'),('expired_cache_reused','dnsrouter/cache.py','if age>=ttl:','if False:','test_live_ttl_expiry_negative_and_uncacheable'),('ignore_negative_soa_minimum','dnsrouter/cache.py','rr.ttl=min(rr.ttl,min(x.minimum for x in rr))','rr.ttl=rr.ttl','test_live_negative_soa_minimum_is_enforced')]


def main():
    results=[];(ROOT/'results/local').mkdir(parents=True,exist_ok=True)
    for name,file,old,new,method in FAULTS:
        with tempfile.TemporaryDirectory(dir=ROOT/'results/local',prefix='fault-') as td:
            temp=Path(td)
            for group in ['dnsrouter','tools','tests']:
                (temp/group).mkdir()
                for f in (ROOT/group).glob('*.py'):shutil.copy2(f,temp/group/f.name)
            for n in ['requirements.txt','requirements-dev.txt','pyproject.toml']:shutil.copy2(ROOT/n,temp/n)
            p=temp/file;s=p.read_text()
            if s.count(old)!=1:raise RuntimeError('fault anchor changed: '+name)
            p.write_text(s.replace(old,new));env=os.environ.copy();env['PYTHONPATH']=str(temp/'tests')+os.pathsep+str(temp)
            r=subprocess.run([sys.executable,'-m','unittest','test_network.NetworkTests.'+method,'-v'],cwd=temp,env=env,capture_output=True,text=True,timeout=15)
            text=r.stdout+r.stderr;(ROOT/'results/local'/('mutation-'+name+'.txt')).write_text(text)
            if r.returncode==0 or 'AssertionError' not in text or 'FAILED (' not in text:raise RuntimeError('not behaviorally detected: '+name+'\n'+text)
            results.append(dict(fault=name,test=method,result='actual-network-assertion-failed-as-required'));print(name+': detected',flush=True)
    (ROOT/'results/local/mutations.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
