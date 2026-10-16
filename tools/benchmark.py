"""Paired actual DNS processes, identical planned arrivals, complete outcomes."""
import argparse
import asyncio
import hashlib
import html
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import dns
import dns.asyncquery
import dns.message
import dns.rcode
import psutil
from dnsrouter.service import identity

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from support import proxy_process,upstream_process,config

SEED=20261016
COUNT=120
INTERVAL=.003


def manifest():
    names=['requirements.txt','requirements-dev.txt','pyproject.toml']+[str(p.relative_to(ROOT)) for group in ['dnsrouter','tools','tests'] for p in (ROOT/group).glob('*.py')]
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(names)}


def plan(blocks):
    rng=random.Random(SEED);rows=[]
    for block in range(blocks):
        for protocol in ['udp','tcp']:
            for scenario in ['repeat','unique','failover']:
                modes=['off','on'];rng.shuffle(modes)
                rows.extend(dict(block=block,protocol=protocol,scenario=scenario,cache=mode) for mode in modes)
    return rows


def question(i,scenario):
    group=i%4
    prefix=['www','www','nx','nodata'][group]
    suffix='lab.test.' if group in [0,2] else 'test.'
    middle=f'u{i}.' if scenario=='unique' else ''
    return prefix+'.'+middle+suffix, 'AAAA' if group in [1,3] else 'A'


def summary(r):
    return dict(rcode=r.rcode(),answer=sorted([rr.name.to_text().lower(),rr.rdtype,x.to_text()] for rr in r.answer for x in rr),authority=sorted([rr.name.to_text().lower(),rr.rdtype,x.to_text()] for rr in r.authority for x in rr))


def expected(i,scenario):
    name,typ=question(i,scenario);group=i%4
    soa=[['test.',6,'ns.test. hostmaster.test. 1 60 60 60 3']]
    return dict(rcode=3 if group==2 else 0,answer=[] if group in [2,3] else [[name,28 if typ=='AAAA' else 1,'2001:db8::10' if typ=='AAAA' else '192.0.2.20']],authority=soa if group in [2,3] else [])


def percentile(values,p):
    return sorted(values)[max(0,math.ceil(len(values)*p)-1)]


async def trial(spec):
    peers=[];worker=None;flows=[];samples=[];sample_errors=[]
    try:
        for marker in [10,20]:peers.append(upstream_process(marker=marker,delay=.006))
        if spec['scenario']=='failover':peers.append(upstream_process(drop=True))
        routes=[]
        for suffix,peer in [('.',peers[0]),('lab.test.',peers[1])]:
            upstreams=[dict(host='127.0.0.1',port=peer.port)]
            if spec['scenario']=='failover':upstreams.insert(0,dict(host='127.0.0.1',port=peers[2].port))
            routes.append(dict(suffix=suffix,upstreams=upstreams))
        cfg=config(peers[0].port,routes=routes,upstream_timeout=.03,cache_entries=64 if spec['cache']=='on' else 0,cache_bytes=32768 if spec['cache']=='on' else 0,tcp_idle_timeout=1.,drain_timeout=1.)
        worker=proxy_process(cfg)
        if worker.ready['source_files']!=identity():raise RuntimeError('runtime source identity differs')
        proc=psutil.Process(worker.process.pid);stop=asyncio.Event()
        queries=[dns.message.make_query(*question(i,spec['scenario'])) for i in range(COUNT)]
        for i,q in enumerate(queries):q.id=1000+i
        origin=time.monotonic()+.1
        def sample():
            cpu=proc.cpu_times();samples.append(dict(t=time.monotonic()-origin,rss=proc.memory_info().rss,cpu=cpu.user+cpu.system))
        async def sampler():
            while not stop.is_set():
                try:sample()
                except Exception as e:sample_errors.append(type(e).__name__);return
                try:await asyncio.wait_for(stop.wait(),.01)
                except TimeoutError:pass
        async def client(i):
            q=queries[i];planned=i*INTERVAL;await asyncio.sleep(max(0,origin+planned-time.monotonic()))
            result=dict(index=i,planned_s=planned,issued_s=time.monotonic()-origin,name=question(i,spec['scenario'])[0],type=question(i,spec['scenario'])[1],request_id=q.id)
            try:
                fn=dns.asyncquery.tcp if spec['protocol']=='tcp' else dns.asyncquery.udp
                r=await fn(q,'127.0.0.1',port=worker.port,timeout=3)
                actual=summary(r);valid=actual==expected(i,spec['scenario']) and q.is_response(r)
                result.update(status='correct' if valid else 'mismatch',wire_hex=r.to_wire().hex(),actual=actual)
            except Exception as error:result.update(status='error',error_type=type(error).__name__)
            result['finished_s']=time.monotonic()-origin;flows.append(result)
        sample();sampling=asyncio.create_task(sampler())
        try:await asyncio.wait_for(asyncio.gather(*(client(i) for i in range(COUNT))),8)
        finally:stop.set();await sampling
        if sample_errors:raise RuntimeError('sampling failed: '+str(sample_errors))
        sample();ready=worker.ready;peer_readiness=[p.ready for p in peers]
        worker.close();metrics=worker.metrics;worker=None
        for p in peers:p.close()
        counts=[p.metrics for p in peers];peers=[]
        flows.sort(key=lambda f:f['index'])
        duration=max(f['finished_s'] for f in flows)
        latencies=[f['finished_s']-f['issued_s'] for f in flows]
        return spec | dict(runtime_identity=ready['source_files'],actual_config=ready['config'],flows=flows,samples=samples,proxy_metrics=metrics,upstream_counts=counts,upstream_readiness=peer_readiness,upstream_delay_s=.006,offered_queries=COUNT,arrival_interval_s=INTERVAL,elapsed_s=duration,correct=sum(f['status']=='correct' for f in flows),completed_qps=COUNT/duration,latency_p50_s=percentile(latencies,.5),latency_p95_s=percentile(latencies,.95),scheduled_p50_s=percentile([f['finished_s']-f['planned_s'] for f in flows],.5),scheduled_p95_s=percentile([f['finished_s']-f['planned_s'] for f in flows],.95),max_issue_lag_s=max(f['issued_s']-f['planned_s'] for f in flows),baseline_rss=samples[0]['rss'],peak_rss=max(s['rss'] for s in samples),rss_growth=max(s['rss'] for s in samples)-samples[0]['rss'],cpu_seconds=samples[-1]['cpu']-samples[0]['cpu'],max_sample_gap_s=max(b['t']-a['t'] for a,b in zip(samples,samples[1:])))
    finally:
        try:
            if worker is not None:worker.close()
        finally:
            errors=[]
            for p in peers:
                try:p.close()
                except Exception as e:errors.append(repr(e))
            if errors:raise RuntimeError('peer cleanup failed: '+str(errors))


def render(r):
    cells=[]
    for t in r['trials']:
        values=[t['block'],t['protocol'],t['scenario'],t['cache'],str(t['correct'])+'/'+str(COUNT),f"{t['latency_p50_s']*1000:.3f}",f"{t['latency_p95_s']*1000:.3f}",f"{t['scheduled_p95_s']*1000:.3f}",f"{t['completed_qps']:.1f}",sum(sum(p.values()) for p in t['upstream_counts']),f"{t['peak_rss']/1048576:.2f}",f"{t['rss_growth']/1048576:.2f}",f"{t['max_issue_lag_s']*1000:.2f}",f"{t['max_sample_gap_s']*1000:.2f}"]
        cells.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in values)+'</tr>')
    headings=['Block','Transport','Workload','Cache','Correct','p50 ms','p95 ms','Scheduled p95 ms','Completed QPS','Upstream requests','Peak RSS MiB','RSS growth MiB','Max issue lag ms','Sample gap ms']
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Tiny DNS Router results</title><style>body{font:16px system-ui;margin:2rem;color:#172b4d}table{border-collapse:collapse;font-size:13px}td,th{padding:.5rem;border-bottom:1px solid #ccc;text-align:left}</style><h1>Tiny DNS Router — measured cache trade-offs</h1><p>'+html.escape(r['environment']['label'])+'</p><p>Same 120 logical queries and planned 3 ms arrival spacing in both cache modes. Fresh proxy/peers each trial; cache starts cold. Upstreams are real local UDP/TCP peers with a configured 6 ms async delay. Failover adds a silent first peer and 30 ms per-upstream deadline. Every result, including failures and generator lag, is retained. QPS is completed work over makespan at this fixed offered load, not maximum server capacity. TCP uses a fresh connection per query. RSS is sampled proxy-process RSS; clients, upstreams, kernel buffers and VM overhead excluded. Invocation latency excludes generator lag; scheduled p95 includes it. </p><p>Paired blocks: '+str(r['plan']['blocks'])+'. No confidence interval or Internet/production claim.</p><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in headings)+'</tr></thead><tbody>'+''.join(cells)+'</tbody></table></html>\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--blocks',type=int,default=3);p.add_argument('--label',required=True);a=p.parse_args()
    if a.blocks<1:raise ValueError('blocks must be positive')
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.html').unlink(missing_ok=True)
    r=dict(schema_version=1,status='running',trials=[])
    def write():(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    write()
    try:
        r.update(plan=dict(blocks=a.blocks,seed=SEED),source_files=manifest(),environment=dict(label=a.label,os=platform.system(),release=platform.release(),machine=platform.machine(),python=platform.python_version(),dnspython=dns.__version__,psutil=psutil.__version__))
        write()
        for spec in plan(a.blocks):
            t=asyncio.run(trial(spec));r['trials'].append(t);write()
            print(json.dumps({k:t[k] for k in ['block','protocol','scenario','cache','correct','latency_p50_s','peak_rss']}),flush=True)
        if r['source_files']!=manifest():raise RuntimeError('source changed during measurements')
        if any(t['correct']!=COUNT for t in r['trials']):raise RuntimeError('incorrect or incomplete trial')
        r['status']='passed'
        from tools.check_report import verify
        verify(r)
        write();(a.output/'report.html').write_text(render(r))
    except BaseException as error:
        r.update(status='failed',error_type=type(error).__name__);write();(a.output/'report.html').unlink(missing_ok=True);raise

if __name__=='__main__':main()
