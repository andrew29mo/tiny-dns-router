# Architecture and contracts

One asyncio process owns the UDP listener, TCP listener, bounded request slots
and an in-memory LRU. Numeric IPv4 upstreams avoid bootstrap DNS dependencies.
Configuration is immutable for a process lifetime. Routes compare canonical DNS
labels and choose the longest suffix, with a mandatory default dot route.

## Cache

The cache admits only ordinary single-question IN A/AAAA queries without extra
answer/authority/additional content, TSIG, EDNS options or unsupported EDNS version.
Keys include canonical name, question type/class, all query header flags, EDNS
flags/version/payload. Query IDs are excluded; replies restore the current ID and
question casing. Negative entries are conservatively question-type specific.
Other ordinary record types are forwarded without caching.

Responses come from the selected upstream, checked by dnspython and explicit
query/response matching. UDP TC responses are retried using TCP before caching.
Every RRset TTL is clamped downward to the configured cap; negative SOA TTL is
also clamped to SOA.MINIMUM. Positive answers must resolve their CNAME chain;
negative answers need an SOA ancestor of the terminal canonical name. Lifetime
is the minimum retained RRset TTL, which can conservatively shorten caching.
Zero lifetime is not cached. SERVFAIL, transport failures and stale responses are not cached. NXDOMAIN and
NODATA are handled by the negative-cache policy above.

Cache expiration uses monotonic time. Hit TTLs subtract the ceiling of elapsed
seconds, so values are conservative and never reset to the original lifetime.
Entries are removed at the exact expiry boundary. Expired entries are also swept
on insertion; the bounded dictionary can retain expired bytes until lookup or a
later insertion. Wire-byte accounting is exact for stored response payloads,
excluding keys, Python metadata/allocator, socket buffers and overall RSS.

## Transport and resource ownership

UDP packets are admitted without an unbounded task queue. Oversized/malformed
requests are rejected by the production parser. Requests above `max_inflight`
produce SERVFAIL; kernel loss before receipt cannot appear in application counts.
TCP handlers are capped separately; excess connections close. TCP framing has
bounded request lengths, idle/read deadlines and write-drain deadlines. Multiple
requests on one TCP connection are processed in order. TCP responses may use up
to 65535 DNS bytes; UDP replies use 512 bytes without EDNS and at most the smaller
of the advertised size and 1232 bytes with EDNS, truncating with TC when needed.

Each cache miss tries its route's upstreams in configured order. One per-upstream
absolute deadline includes UDP plus any TCP fallback; total failure time is
bounded by the number of upstreams times that deadline, plus scheduling overhead.
Timeouts, transport errors and invalid replies advance to the next upstream.
Valid negative/SERVFAIL replies do not. No upstream health cache or retry backoff
is implemented; an unhealthy first upstream is attempted on every miss.

Shutdown first stops TCP accepts, then lets admitted work finish within the drain
limit, then cancels remaining tasks and closes listeners. It must not wait for
all TCP clients before enforcing the drain deadline. Normal exit removes readiness.
An OS state-directory lock prevents two processes from owning the same state;
it is not crash recovery for pending DNS requests. No in-flight query survives
process termination and no complete DNS delivery guarantee is made.

Final request ledger: requests = completed + cancelled + rejected + active.
Completed means handler completion/response production, not proof the client got
the response. Invalid TCP framing and pre-admission connection rejection have
separate counters. Route counters count forwarded misses, not cache hits.
