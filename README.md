# Tiny DNS Router

An experimental local DNS forwarding service with label-aware suffix routing,
bounded TTL-aware caching, UDP/TCP forwarding and sequential upstream failover.
Use it for a trusted developer workstation or lab with different DNS upstreams
for different domain suffixes. The service uses real sockets and dnspython for
wire parsing; the routing, cache policy, limits and lifecycle are implemented here.

## Run

Python 3.12+ on macOS or Linux (retained validation uses Python 3.12.14):

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
  error responses retain their meaning. Truncated TCP replies trigger failover;
  a valid NXDOMAIN does not.
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

## Local cross-platform validation

On macOS with the project Python 3.12 environment and Docker CLI:

```sh
./tools/validate-local
```

This runs the same frozen implementation on native macOS and in Colima Linux,
retaining formal tests, separate complete measurements and cleanup evidence.
Colima/Lima install automatically from checksum-pinned official releases.
[Workflow and limits](docs/LOCAL_VALIDATION.md) ·
[Retained platform evidence](reviews/local-validation/README.md).
Linux VM performance/RSS is reported separately from native macOS.

## Measured results

Latency columns start at the actual client invocation and exclude generator
waiting. The linked HTML also reports scheduled p95, which includes that waiting.

<!-- measured:start -->
Native macOS loopback; three randomized paired blocks, 36 trials, 120 queries per trial.
Each mode starts cold and receives the same planned 3 ms arrival spacing.
Controlled upstreams add 6 ms async delay; failover adds a silent first peer and a 30 ms deadline.
Values below are medians across all three blocks, not confidence intervals.

| Transport | Workload | Cache | p50 ms | p95 ms | Completed QPS | Upstream queries | Peak RSS MiB |
|---|---|---|---:|---:|---:|---:|---:|
| udp | repeat | off | 7.331 | 8.626 | 328.8 | 120 | 30.05 |
| udp | repeat | on | 0.688 | 1.648 | 335.0 | 4 | 29.97 |
| udp | unique | off | 7.465 | 8.490 | 328.5 | 120 | 29.98 |
| udp | unique | on | 7.270 | 8.538 | 328.6 | 120 | 30.00 |
| udp | failover | off | 37.541 | 38.592 | 303.3 | 240 | 30.06 |
| udp | failover | on | 0.664 | 38.145 | 335.4 | 32 | 29.98 |
| tcp | repeat | off | 7.480 | 8.708 | 328.1 | 120 | 29.98 |
| tcp | repeat | on | 0.713 | 1.340 | 335.4 | 4 | 30.00 |
| tcp | unique | off | 7.414 | 8.348 | 328.4 | 120 | 29.91 |
| tcp | unique | on | 7.408 | 8.507 | 328.5 | 120 | 29.98 |
| tcp | failover | off | 37.688 | 38.986 | 303.3 | 240 | 30.16 |
| tcp | failover | on | 0.715 | 38.170 | 335.2 | 32 | 30.14 |

Correct responses: 4320/4320. Maximum client issue lag: 4.42 ms; maximum RSS sample gap: 15.72 ms.

Completed QPS reflects this fixed offered load, not maximum service capacity.
RSS covers only the sampled proxy process. These data do not establish Internet latency,
native Linux performance, universal cache benefit or superiority over CoreDNS/Unbound.
[JSON](results/native-macos/report.json) · [HTML](results/native-macos/report.html)
<!-- measured:end -->

See [measurement protocol](docs/MEASUREMENT.md) and [current platform evidence](reviews/local-validation/README.md).
The [earlier correctness review](reviews/dns-review/README.md) is retained with its historical results.
This grid compares this implementation with caching disabled/enabled. It is not
an independent resolver comparison or a benchmark against CoreDNS/Unbound.

The [first hosted CI run](https://github.com/andrew29mo/tiny-dns-router/actions/runs/38863471472)
was blocked by GitHub account billing/spending restrictions before any steps ran
on Linux or macOS. Native macOS validation is retained; hosted success is not claimed. Separate local Linux-container validation
is recorded above; it is not a substitute claim of hosted CI or native Linux hardware.

## Status and license

Private MVP. Original project code and documentation are licensed under the
[MIT License](LICENSE), copyright (c) 2026 Andrew Yuan. `pyproject.toml` declares
MIT and lists the license and third-party notice files. Dependencies and
validation tooling retain their own licenses; see
[third-party notices](THIRD_PARTY_NOTICES.md). No private network captures or
external datasets are used in the retained synthetic DNS experiments.
Historical review receipts preserve their license state at the time of review.
See [MIT adoption verification](reviews/mit-adoption/README.md).

[Pre-MIT prepublication review](reviews/prepublication/README.md).
