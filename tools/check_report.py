"""Explicit validation, including complete planned trials and resource accounting."""
import argparse
import json
import math
from pathlib import Path
import dns.message
from tools.benchmark import COUNT,INTERVAL,SEED,expected,manifest,percentile,plan,question,render,summary


def need(ok,message):
    if not ok:raise ValueError(message)


def close(a,b):need(isinstance(a,(int,float)) and math.isfinite(a) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9),'numeric mismatch')


def verify(r,current=True):
    need(r['schema_version']==1 and r['status']=='passed','report not passed')
    need(type(r['plan']['blocks']) is int and r['plan']['blocks']>=1 and r['plan']['seed']==SEED,'plan')
    specs=plan(r['plan']['blocks']);need(len(r['trials'])==len(specs),'missing trials')
    runtime={n:h for n,h in r['source_files'].items() if n.startswith('dnsrouter/') or n in ['requirements.txt','requirements-dev.txt','pyproject.toml']}
    for spec,t in zip(specs,r['trials']):
        need(all(t[k]==v for k,v in spec.items()),'trial order or identity')
        need(t['runtime_identity']==runtime,'runtime source differs')
        cfg=t['actual_config'];need(cfg['cache_entries']==(64 if spec['cache']=='on' else 0) and cfg['cache_bytes']==(32768 if spec['cache']=='on' else 0),'cache config')
        need({k:v for k,v in cfg.items() if k not in ['routes','cache_entries','cache_bytes']}==dict(host='127.0.0.1',port=0,ttl_cap=3600,max_inflight=64,max_tcp_connections=32,max_query_bytes=4096,upstream_timeout=.03,tcp_idle_timeout=1.,drain_timeout=1.),'runtime settings')
        routes=cfg['routes'];need([x['suffix'] for x in routes]==['lab.test.','.'],'routing config')
        for route in routes:need(len(route['upstreams'])==(2 if spec['scenario']=='failover' else 1) and all(u['host']=='127.0.0.1' and 0<u['port']<65536 for u in route['upstreams']),'upstreams')
        need(t['offered_queries']==COUNT and t['arrival_interval_s']==INTERVAL and t['upstream_delay_s']==.006,'workload')
        fs=t['flows'];need(len(fs)==COUNT and [f['index'] for f in fs]==list(range(COUNT)),'flow coverage')
        for i,f in enumerate(fs):
            need((f['name'],f['type'])==question(i,spec['scenario']) and f['request_id']==1000+i,'query differs')
            close(f['planned_s'],i*INTERVAL)
            need(f['issued_s']>=f['planned_s']-.001 and f['finished_s']>=f['issued_s'],'timestamps')
            need(f['status']=='correct' and f['actual']==expected(i,spec['scenario']),'wrong answer')
            response=dns.message.from_wire(bytes.fromhex(f['wire_hex']))
            need(response.id==1000+i and summary(response)==f['actual'],'wire receipt')
            q=dns.message.make_query(f['name'],f['type']);q.id=1000+i
            need(q.is_response(response),'question mismatch')
            need(all(0<=rr.ttl<=(3 if i%4 in [2,3] else 120) for sec in [response.answer,response.authority] for rr in sec),'TTL bounds')
        close(t['elapsed_s'],max(f['finished_s'] for f in fs));close(t['completed_qps'],COUNT/t['elapsed_s'])
        latency=[f['finished_s']-f['issued_s'] for f in fs]
        close(t['latency_p50_s'],percentile(latency,.5));close(t['latency_p95_s'],percentile(latency,.95));close(t['max_issue_lag_s'],max(f['issued_s']-f['planned_s'] for f in fs))
        need(t['correct']==COUNT,'correct count')
        ss=t['samples'];need(len(ss)>2 and ss[0]['t']<=0 and ss[-1]['t']>=t['elapsed_s'],'sample coverage')
        need(all(s['rss']>0 and s['cpu']>=0 and math.isfinite(s['t']) for s in ss),'invalid samples')
        need(all(a['t']<=b['t'] and a['cpu']<=b['cpu'] for a,b in zip(ss,ss[1:])),'sample order')
        need(t['peak_rss']==max(s['rss'] for s in ss) and t['baseline_rss']==ss[0]['rss'] and t['rss_growth']==t['peak_rss']-t['baseline_rss'],'RSS')
        close(t['cpu_seconds'],ss[-1]['cpu']-ss[0]['cpu']);close(t['max_sample_gap_s'],max(b['t']-a['t'] for a,b in zip(ss,ss[1:])))
        m=t['proxy_metrics'];need(m['requests']==COUNT and m['completed']==COUNT and all(m[k]==0 for k in ['cancelled','rejected','active','internal_errors','malformed','tcp_connections']),'request accounting')
        need(m['cache_hits']+m['cache_misses']==COUNT and m['cache_misses']==m['routes']['.']+m['routes']['lab.test.'],'cache ledger')
        need(m['cache_entries']<=cfg['cache_entries'] and m['cache_wire_bytes']<=cfg['cache_bytes'] and m['peak_cache_wire_bytes']<=cfg['cache_bytes'] and m['peak_active']<=cfg['max_inflight'],'resource bounds')
        counts=t['upstream_counts'];need(len(counts)==(3 if spec['scenario']=='failover' else 2),'peer counts')
        need(all(type(v) is int and v>=0 for c in counts for v in c.values()),'peer counters')
        other='tcp' if spec['protocol']=='udp' else 'udp'
        need(all(c[other]==0 for c in counts),'wrong upstream transport')
        need(sum(counts[0].values())==m['routes']['.'] and sum(counts[1].values())==m['routes']['lab.test.'],'upstream route accounting')
        active=sum(sum(c.values()) for c in counts[:2]);need(active==m['cache_misses'],'real upstream requests')
        need(m['upstream_attempts']==active*(2 if spec['scenario']=='failover' else 1),'attempt ledger')
        if spec['scenario']=='failover':need(sum(counts[2].values())==active and m['upstream_timeouts']==active,'failover count')
        else:need(m['upstream_timeouts']==0,'unexpected timeout')
        if spec['cache']=='off' or spec['scenario']=='unique':need(m['cache_hits']==0,'unintended reuse')
    if current:need(r['source_files']==manifest(),'source differs; regenerate measurements')
    return len(specs)


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=json.loads((a.directory/'report.json').read_text())
    n=verify(r);need((a.directory/'report.html').read_text()==render(r),'HTML differs')
    print(f'Checked {n} planned trials: exact wire answers, arrivals, TTLs, cache/upstream ledgers, RSS and canonical HTML.')
if __name__=='__main__':main()
