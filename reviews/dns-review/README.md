# Historical DNS correctness and measurement review

This receipt covers `2b88616`. Its unchanged reports are preserved in
`results/historical-dns-review-2b88616/`; current cross-platform evidence is in
`reviews/local-validation/`.

This review checks the production UDP/TCP forwarding path, bounded cache,
shutdown behavior, workload provenance and complete report accounting.
GitHub remains Private. No project open-source license has been selected.

## Findings and fixes

1. **Incomplete TCP upstream replies were returned to clients.** A real-socket
   regression first failed on the original implementation: TC remained set
   after TCP forwarding. The service now rejects a still-truncated TCP response
   and tries the next upstream, including after UDP-to-TCP fallback. Valid
   NXDOMAIN/SERVFAIL responses keep their previous meaning.
2. **Report checking had acceptance gaps.** Reproductions showed the original
   checker accepted negative cache bytes and 999 unaccounted upstream errors or
   unsupported queries. It now rejects invalid counters, unexpected errors,
   nonfinite time/CPU, truncated replies and changed peer settings. Peer
   readiness retains actual bound ports and delay/drop settings; routes must
   bind to those peers. The benchmark itself invokes the checker before
   publishing passed JSON/HTML. A regression verifies invalid ledgers leave
   failed JSON without successful HTML.
3. **Latency needed an additional view.** Invocation latency remains explicitly
   defined from actual client call through validation. Scheduled latency is now
   retained/recomputed from planned arrival through completion, including
   generator delay; HTML shows scheduled p95. Makespan/QPS already includes tails.

The old observation set is preserved byte-for-byte in
`results/historical-mvp-e04ef6a/`, with its original source/report hashes in
`reviews/mvp/receipt.json`. It does not validate the revised source.

## Coverage and evidence

Tests exercise the imported production Server with real UDP/TCP sockets, and
separately launch the actual production CLI. Added network regressions cover
NXDOMAIN/NODATA expiry, byte-budget-driven eviction independently of entry count,
CNAME lifetime, CD flag partitioning, one combined UDP/fallback upstream deadline,
still-truncated TCP replies and forced TCP shutdown disposition. Cache unit
checks add LRU promotion, expired-byte reclamation and CNAME-negative terminal
SOA/zero-MINIMUM cases. Negative lifetime uses the lower SOA TTL/MINIMUM, with
additional conservative lifetime limits; see
[RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html).

Adjacent mutation logs are expected failures of separate deliberately broken
copies, not release failures. Five faults must trigger actual network assertion
failures: label-unsafe suffix matching, expired-entry reuse, ignoring SOA.MINIMUM,
accepting truncated TCP and ignoring the wire-byte budget.

The receipt records final source hashes, actual test counts, report/log hashes
and command results. Logs replace local path prefixes. Original logs stay local.

## Interpretation limits

All 36 planned trials are retained, with the same 120 questions/order/IDs and
3 ms planned spacing per mode. Cache modes start cold in fresh processes.
Reference peers are actual separate processes with controlled 6 ms async delay;
failover adds a silent peer and a 30 ms deadline. The source manifest covers
production, fixtures, tests and tools. Every query's wire reply and complete
request/upstream/resource ledgers are checked; JSON/HTML/README agree.

This compares cache off/on in the same service at a fixed offered load. QPS is
finite-workload completion rate, not saturated capacity. Three blocks do not
establish confidence intervals. Scheduled arrivals are identical; actual wire
arrivals can differ. There is no miss coalescing. TCP opens a new connection
per query. RSS samples cover only the proxy process, may miss short peaks and
exclude clients, peers, kernel buffers and VM overhead. Wire-byte capacity is
not a process-memory cap. Tests and peers share dnspython's codec, so no
independent DNS-codec/security validation is claimed. No WAN or CoreDNS/Unbound
comparison, production readiness, Linux validation or cache memory saving is
inferred. Hosted CI availability is checked separately from native evidence.
