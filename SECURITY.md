# Security scope

Experimental DNS forwarding for trusted local users and explicitly configured
upstreams. The listener is restricted to 127.0.0.1. It is not a hardened public
resolver, DNS firewall or independent DNSSEC validator. No TSIG/DoH/DoT, traffic
confidentiality, source authentication or DNS poisoning resistance certification
is claimed. Upstream data remains a trust dependency.

Query slots, TCP connections and cache wire bytes/entries are bounded. Python
metadata, kernel buffers, packet allocation before validation and entire process
RSS/CPU are not hard-capped. Do not expose this through public port forwarding.
No query/client names are logged in routine metrics. Example public upstreams
are explicit configuration, not an automatic change to your system resolver.

Keep local state, credentials, environments, raw test failures and personal paths
out of Git. Publication checking is heuristic. CI uses hosted runners, SHA-pinned
actions, read-only permissions and no checkout credential persistence. No project
open-source license is selected yet; third-party terms remain separate.
