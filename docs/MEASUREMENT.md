# Measurement protocol

Each trial launches the production CLI and independent UDP/TCP reference peers
as separate processes. The peers answer from simple fixed synthetic records,
not from the production routing/cache implementation. All ends use dnspython
wire encoding, so this is not an independent DNS-codec validation. Reference
addresses, RCODE, SOA and record data are explicitly checked per query. Reports
retain response wire bytes, actual invocation/finish times and all outcomes.

Three randomized paired blocks each cover UDP/TCP × repeat/unique/failover ×
cache off/on (36 trials). Each fresh worker starts cold and receives 120 queries
at planned 3 ms intervals. Four query shapes exercise positive A, positive AAAA,
NXDOMAIN and NODATA, across a default and more-specific suffix route. Unique
queries never repeat; repeat/failover reuse four keys. Identical question/order,
IDs, route policy, limits, peer delay and planned schedule apply to both modes;
only cache count/byte limits differ. Actual wire arrival times can differ, so
client invocation lag is retained rather than claiming identical wire traffic.

The live reference peers apply a configured 6 ms asyncio delay. The failover
scenario puts a silent peer first, with a 30 ms per-upstream deadline. This
controlled local delay is not Internet RTT or a measurement of a real ISP outage.
There is no coalescing: overlapping cold misses may each reach the upstream.
TCP uses a new connection per query; persistent-connection performance is separate.

Completed QPS is all completed work divided by last completion from the common
planned origin, including tails. At this fixed offered load it does not establish
maximum QPS. For a finite batch, 120 queries have only 119 spacing intervals, so this QPS may
slightly exceed the reciprocal of the arrival interval without implying higher
steady-state capacity. Latency is from actual client invocation through response
validation, including connection setup for TCP. All 120 outcomes remain in every trial. A
bad/incomplete trial prevents a passed report; pairs are never selected by result.
Source manifests cover production/tests/tools and pinned dependency metadata.
The CLI's runtime identity must agree. Source changes require regeneration.

Psutil samples only the separate proxy process's RSS/CPU every approximately
10 ms. Baseline precedes the workload and a final sample follows completion.
JSON retains all samples, baseline, peak, growth, CPU seconds and maximum gap.
Errors in sampling fail the run. Short-lived RSS peaks can be missed. Peer/client,
kernel socket and VM memory are excluded; cache wire-byte limits are a distinct
quantity. No cache-induced memory saving or speedup is assumed.

Artifact state is invalidated before provenance setup. An execution error leaves
failed JSON without old successful HTML. The checker recomputes complete planned
order, query data, wire replies, TTL bounds, latency/QPS, samples and proxy/peer
ledgers and exact HTML. This provides consistency checks, not hostile-producer
attestation. Normal Python assertions are required for the test/fixture harness;
optimized validation is refused.

Run timing alone, without concurrent tests or VM build activity. Retained results
are labelled native macOS; do not infer native Linux, WAN, NIC, energy, hard RSS
bounds or production DNS-security behavior from this workload.
