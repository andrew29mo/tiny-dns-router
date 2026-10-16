import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import dns.asyncquery
import dns.message

ROOT=Path(__file__).resolve().parents[1]
if not __debug__:raise RuntimeError('optimized Python is refused for validation')


def config(port,**kwargs):
    return dict(port=0,upstream_timeout=.08,tcp_idle_timeout=.3,drain_timeout=.2,
                routes=[dict(suffix='.',upstreams=[dict(host='127.0.0.1',port=port)])]) | kwargs


async def query(port,name='www.test.',typ='A',tcp=False,**kwargs):
    q=dns.message.make_query(name,typ,**kwargs)
    fn=dns.asyncquery.tcp if tcp else dns.asyncquery.udp
    return await fn(q,'127.0.0.1',port=port,timeout=2)


class Process:
    def __init__(self,args):
        self.closed=False;self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.log=(self.path/'stderr.txt').open('w+')
        self.process=subprocess.Popen([sys.executable,*args(self.path)],cwd=ROOT,stdout=self.log,stderr=self.log)
        end=time.monotonic()+5
        while time.monotonic()<end:
            if (self.path/'state/ready.json').exists():
                self.ready=json.loads((self.path/'state/ready.json').read_text());self.port=self.ready['port'];return
            if self.process.poll() is not None:break
            time.sleep(.01)
        self.close(force=True);raise AssertionError('process never became ready')
    def close(self,force=False):
        if self.closed:return
        try:
            if self.process.poll() is None:self.process.terminate()
            try:self.process.wait(5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(2);raise AssertionError('shutdown deadline exceeded')
            self.log.flush();self.log.seek(0);self.output=self.log.read()
            if not force and self.process.returncode!=0:raise AssertionError(self.output)
            if (self.path/'state/metrics.json').exists():self.metrics=json.loads((self.path/'state/metrics.json').read_text())
            if not force and (self.path/'state/ready.json').exists():raise AssertionError('stale readiness after normal exit')
        finally:self.closed=True;self.log.close();self.temp.cleanup()


def proxy_process(cfg):
    def args(path):
        (path/'config.json').write_text(json.dumps(cfg))
        return ['-m','dnsrouter','--config',str(path/'config.json'),'--state',str(path/'state')]
    return Process(args)


def upstream_process(**kwargs):
    def args(path):
        argv=['-m','tools.upstream','--state',str(path/'state')]
        for k,v in kwargs.items():
            if v is True:argv+=['--'+k]
            else:argv+=['--'+k,str(v)]
        return argv
    return Process(args)
