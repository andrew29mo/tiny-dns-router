# Historical MVP validation evidence

This receipt describes source at `e04ef6a` (implementation `0a6fc55`). Its
unchanged JSON/HTML are now in `results/historical-mvp-e04ef6a/`. For current
source and results, see `reviews/dns-review/README.md`.

Native macOS ARM64: 24 Python test methods passed, including actual UDP/TCP
production-service tests, production CLI subprocess/readiness/shutdown checks,
monotonic-clock cache boundary checks, failure-artifact handling and report
forgery/selective-removal tests. No live OS DNS configuration is changed.

Three deliberately broken production variants were rejected by network tests:
label-unsafe suffix routing, reuse of expired cache entries, and omission of
SOA.MINIMUM for negative caching. Adjacent mutation logs contain **expected
failures**, not failures of the release implementation. They are separate
copies of the actual source, not replacement scheduler/cache models.

An early smoke run exposed unbounded shutdown waiting caused by awaiting the
TCP listener before closing existing clients. Production and reference-peer
teardown order was corrected; a real idle-TCP deadline regression now passes.
The full final grid runs after the correction and without concurrent tests.
Exploratory/failed smoke logs remain ignored locally and are not pooled with
formal observations or used for improvement claims.

The 36 planned paired trials retained all 4,320 correct query responses, raw
response wire bytes, invocation/completion timestamps, process samples and
proxy/upstream counters. Every process closes successfully; abnormal exits or
cleanup deadlines fail execution. JSON/HTML/README are recomputed against the
full source manifest and workload plan. Exact source/report/log SHA-256 hashes
are in `receipt.json`. These are consistency checks, not hostile-producer
attestation. Personal path prefixes in the published logs are replaced;
original log digests are retained separately.

Comparison is cache off/on in the same implementation, starting cold, at a
fixed offered schedule. Live reference peers use a configured async delay;
this is not a real ISP latency/outage measurement or a maximum-QPS result.
RSS is sampled proxy-process RSS, excluding peers/kernel/VM. Upstream counts
include both attempts in failover. No query coalescing is implemented, so cold
overlapping requests can independently reach the upstream.

Hosted Linux/macOS CI is configured separately; no success is inferred from
this native macOS evidence. No native Linux or container test run is claimed
by this receipt. Project licensing is not selected; GitHub remains Private.

Observed hosted run for initial commit `0a6fc55`:
[38863471472](https://github.com/andrew29mo/tiny-dns-router/actions/runs/38863471472).
Both jobs were blocked by account billing/spending restrictions and executed
zero steps. Detailed account annotations remain local; this is not a test failure
of an executed Linux/macOS job, nor evidence that those jobs passed.
