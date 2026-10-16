import argparse
import json
from pathlib import Path
import statistics
from tools.check_report import verify


def section(r):
    lines=['<!-- measured:start -->','Native macOS loopback; three randomized paired blocks, 36 trials, 120 queries per trial.','Each mode starts cold and receives the same planned 3 ms arrival spacing.','Controlled upstreams add 6 ms async delay; failover adds a silent first peer and a 30 ms deadline.','Values below are medians across all three blocks, not confidence intervals.','', '| Transport | Workload | Cache | p50 ms | p95 ms | Completed QPS | Upstream queries | Peak RSS MiB |','|---|---|---|---:|---:|---:|---:|---:|']
    for protocol in ['udp','tcp']:
        for scenario in ['repeat','unique','failover']:
            for mode in ['off','on']:
                ts=[t for t in r['trials'] if t['protocol']==protocol and t['scenario']==scenario and t['cache']==mode]
                med=lambda k:statistics.median(t[k] for t in ts)
                upstream=statistics.median(sum(sum(x.values()) for x in t['upstream_counts']) for t in ts)
                lines.append(f'| {protocol} | {scenario} | {mode} | {med("latency_p50_s")*1000:.3f} | {med("latency_p95_s")*1000:.3f} | {med("completed_qps"):.1f} | {upstream:.0f} | {med("peak_rss")/1048576:.2f} |')
    lines+=['',f'Correct responses: {sum(t["correct"] for t in r["trials"])}/{len(r["trials"])*120}. Maximum client issue lag: {max(t["max_issue_lag_s"] for t in r["trials"])*1000:.2f} ms; maximum RSS sample gap: {max(t["max_sample_gap_s"] for t in r["trials"])*1000:.2f} ms.','', 'Completed QPS reflects this fixed offered load, not maximum service capacity.','RSS covers only the sampled proxy process. These data do not establish Internet latency,','native Linux performance, universal cache benefit or superiority over CoreDNS/Unbound.','[JSON](results/native-macos/report.json) · [HTML](results/native-macos/report.html)','<!-- measured:end -->']
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();r=json.loads(Path('results/native-macos/report.json').read_text());verify(r)
    if len(r['trials'])!=36:raise ValueError('README requires full 36-trial plan')
    readme=Path('README.md');text=readme.read_text();start=text.index('<!-- measured:start -->');end=text.index('<!-- measured:end -->')+len('<!-- measured:end -->');generated=section(r)
    if a.check:
        if text[start:end]!=generated:raise ValueError('README differs')
    else:readme.write_text(text[:start]+generated+text[end:])
    print('README matches every retained trial')
if __name__=='__main__':main()
