# Tiny DNS Router

An experimental local DNS forwarding service with label-aware suffix routing,
bounded TTL-aware caching, UDP/TCP forwarding and sequential upstream failover.
Use it for a trusted developer workstation or lab with different DNS upstreams
for different domain suffixes. The service uses real sockets and dnspython for
wire parsing; the routing, cache policy, limits and lifecycle are implemented here.

## Run

Python 3.12+ on macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m dnsrouter --config examples/local.json --state results/local/service
```

In another terminal:

```sh
.venv/bin/python -m tools.query www.example.com
.venv/bin/python -m tools.query www.example.com --type AAAA --tcp
```

The example routes `lab.test.` to your own DNS server on `127.0.0.1:15353`,
and all other names to the two explicitly configured public upstreams. Replace
these with upstreams permitted in your environment. The listener is restricted
to `127.0.0.1`; it never edits OS DNS settings or listens on public interfaces.
SIGTERM/SIGINT stops accepts, drains admitted queries up to the configured
limit, cancels remaining work and removes readiness. SIGKILL cannot drain work;
a stale ready file alone is not proof the service is alive.

## Implemented scope

- Longest DNS-label suffix wins: `x.lab.test` matches `lab.test`, `badlab.test` does not.
- Numeric IPv4 upstream addresses; UDP and TCP share one loopback port.
- TCP clients use TCP upstreams. UDP replies with TC trigger upstream TCP fallback.
- Sequential failover on transport errors, timeout or invalid response; valid DNS
  error responses retain their meaning. Truncated TCP replies are incomplete and trigger failover; A valid NXDOMAIN does not trigger failover.
- A/AAAA response cache, including CNAME chains. NXDOMAIN/NODATA caching requires
  an ancestor SOA and uses its TTL/MINIMUM conservatively. SERVFAIL, zero-TTL,
  truncated and unsupported cache shapes are not stored. Cache hits age every RRset.
- LRU limits both entry count and serialized response bytes. These are not hard
  limits on Python/process/kernel memory. Active requests and TCP connections
  are separately bounded; overload produces SERVFAIL or closes excess TCP connections.
- `metrics.json` includes upstream attempts/timeouts, cache hits/misses/evictions,
  active/rejected/cancelled requests and current cache wire bytes. Attempts count
  upstream destinations; a UDP-to-TCP fallback is counted separately. Completed
  requests count processing, while the benchmark independently checks receipt.

Configuration loads at startup; restart to change routes (the cache starts empty).
No recursive resolution, DNSSEC validation, TSIG, zone transfers, DoH/DoT,
query coalescing, stale serving, prefetch or live configuration reload is claimed.
Upstream AD/CD/EDNS semantics are forwarded; this service does not independently
establish DNS authenticity. See [architecture](docs/ARCHITECTURE.md) and
[security scope](SECURITY.md).

## Validate and measure

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.mutation_check
.venv/bin/python -m tools.benchmark --output results/local/benchmark --blocks 3 --label native-macOS
.venv/bin/python -m tools.check_report results/local/benchmark
```

Network tests invoke the same production `Server` path over real UDP/TCP sockets;
a separate subprocess test checks the actual module entry point, source identity,
exit status, readiness cleanup and request ledger. Monotonic-clock unit tests
also verify exact expiration and TTL aging boundaries. Additional network regressions cover negative expiration, byte-budget eviction,
CNAME lifetime, query-flag partitioning, shared UDP/TCP fallback deadlines and
forced TCP shutdown. Report tampering tests
reject missing trials, forged answers/resources, changed config and stale sources.
Mutation tests deliberately break production behavior and require actual network
assertions to fail. Expected mutation failures are not release-test failures.

## Measured results

<!-- measured:start -->
Native macOS loopback; three randomized paired blocks, 36 trials, 120 queries per trial.
Each mode starts cold and receives the same planned 3 ms arrival spacing.
Controlled upstreams add 6 ms async delay; failover adds a silent first peer and a 30 ms deadline.
Values below are medians across all three blocks, not confidence intervals.

| Transport | Workload | Cache | p50 ms | p95 ms | Completed QPS | Upstream queries | Peak RSS MiB |
|---|---|---|---:|---:|---:|---:|---:|
| udp | repeat | off | 7.457 | 9.145 | 327.6 | 120 | 29.94 |
| udp | repeat | on | 0.749 | 1.926 | 334.4 | 4 | 29.89 |
| udp | unique | off | 7.579 | 8.912 | 327.8 | 120 | 29.98 |
| udp | unique | on | 7.556 | 8.650 | 327.3 | 120 | 29.97 |
| udp | failover | off | 37.779 | 39.621 | 302.2 | 240 | 30.19 |
| udp | failover | on | 0.675 | 38.641 | 334.9 | 32 | 30.06 |
| tcp | repeat | off | 7.621 | 9.003 | 327.4 | 120 | 29.94 |
| tcp | repeat | on | 0.883 | 1.982 | 334.6 | 4 | 29.95 |
| tcp | unique | off | 7.676 | 8.909 | 327.7 | 120 | 29.83 |
| tcp | unique | on | 7.669 | 9.117 | 327.6 | 120 | 29.94 |
| tcp | failover | off | 37.804 | 39.409 | 302.6 | 240 | 30.09 |
| tcp | failover | on | 0.862 | 39.043 | 335.0 | 32 | 30.12 |

Correct responses: 4320/4320. Maximum client issue lag: 2.48 ms; maximum RSS sample gap: 12.31 ms.

Completed QPS reflects this fixed offered load, not maximum service capacity.
RSS covers only the sampled proxy process. These data do not establish Internet latency,
native Linux performance, universal cache benefit or superiority over CoreDNS/Unbound.
[JSON](results/native-macos/report.json) · [HTML](results/native-macos/report.html)
<!-- measured:end -->

See [measurement protocol](docs/MEASUREMENT.md) and [current review evidence](reviews/dns-review/README.md).
This grid compares this implementation with caching disabled/enabled. It is not
an independent resolver comparison or a benchmark against CoreDNS/Unbound.

The [first hosted CI run](https://github.com/andrew29mo/tiny-dns-router/actions/runs/38863471472)
was blocked by GitHub account billing/spending restrictions before any steps ran
on Linux or macOS. Native macOS validation is retained; hosted success and local
Linux validation are not claimed.

## Status and license

Private MVP. No project open-source license selected. Dependencies retain their
own terms; see [third-party notices](THIRD_PARTY_NOTICES.md). No private network
captures or external datasets are used in the retained synthetic DNS experiments.
