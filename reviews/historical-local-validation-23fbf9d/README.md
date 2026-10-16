# Historical local validation at 23fbf9d

These are unchanged pre-audit measurements and receipts. Check with the validator
from `23fbf9d`; current code requires stronger test/exit evidence. Current results
are in `reviews/local-validation/`. The original README follows.

# Local macOS / Colima Linux validation

Both environments passed the same frozen formal implementation: **35 tests each**,
five production mutations detected in each, **36 complete measured trials and
4,320/4,320 correct replies per environment** (72 trials / 8,640 replies total).
The owned container was removed and dedicated VM stopped.

Run with `./tools/validate-local`. Recheck this retained record with:

```sh
.venv/bin/python -m tools.check_validation reviews/local-validation
```

The base checkout was `2b88616`; the exact staged implementation and setup are
identified by the source/snapshot hashes in `combined.json` and platform receipts.
Both platforms use Python 3.12.14 and the same pinned requirements. Native macOS
is ARM64; Linux is aarch64 inside Colima, without architecture emulation. The
VM has 4 vCPUs / 6 GiB RAM; the isolated non-root container has 4 CPUs / 4 GiB RAM,
no source mount, no external network, all capabilities dropped and no new privileges.

## Evidence and failure handling

Each environment runs the production socket/CLI tests, its own newly generated
benchmark/report checks and the same five network mutation checks. The report
fixture environment variable selects each platform’s own data and preserves full
source validation. Added runner regressions prove nonzero exits and timeouts do
not pass, descendants in new sessions are reclaimed, and changed snapshot inputs
are rejected. Process/readiness shutdown regressions remain in the formal suite.

The final checker requires successful command exits, non-OOM container state,
matching native/Linux source manifests, snapshot binding, canonical JSON/HTML,
log hashes and verified cleanup. A `docker start --attach` outcome alone is not
accepted as a container test outcome; the actual container exit is inspected.

Text logs replace local paths and OS username; source and report bytes are
unchanged. `original-digests.json` retains original local digests. Full snapshots,
venvs, downloaded tools, VM disk and raw logs stay ignored locally. The fixed
source snapshot is copied into the image, not mounted from a changing checkout.

Additional checker probes rejected seven inconsistent records: command timeout,
nonzero container exit, unfinished cleanup, changed source binding, missing Linux
evidence, altered test log and missing benchmark trial. See
[probe outcomes](negative-checks.json). These supplement the 35-test formal suite.

## Separate observations

Medians over three randomized paired blocks per row. Same 120-query planned
3 ms schedule in each cache mode; cold starts, real controlled peers with 6 ms
async delay. Failover adds a silent first peer / 30 ms deadline. All rows remain.
Invocation p50/p95 exclude generator lag; scheduled p95 includes it. QPS is
finite-workload completed queries / makespan, not saturated service capacity.

### Native macOS ARM64

[JSON](native/benchmark/report.json) · [HTML](native/benchmark/report.html) · [Test log](native/tests.txt)

| Transport | Workload | Cache | p50 ms | p95 ms | Scheduled p95 ms | QPS | Peak process RSS MiB |
|---|---|---|---:|---:|---:|---:|---:|
| udp | repeat | off | 7.371 | 8.191 | 8.413 | 328.8 | 29.94 |
| udp | repeat | on | 0.645 | 1.195 | 1.406 | 335.1 | 29.88 |
| udp | unique | off | 7.404 | 8.494 | 8.711 | 328.1 | 29.91 |
| udp | unique | on | 7.319 | 8.236 | 8.409 | 328.1 | 29.94 |
| udp | failover | off | 37.536 | 38.653 | 38.851 | 303.3 | 29.98 |
| udp | failover | on | 0.706 | 38.162 | 38.289 | 335.3 | 30.02 |
| tcp | repeat | off | 7.462 | 8.721 | 8.899 | 328.6 | 29.92 |
| tcp | repeat | on | 0.738 | 1.629 | 1.911 | 335.2 | 29.98 |
| tcp | unique | off | 7.408 | 8.068 | 8.286 | 328.5 | 29.91 |
| tcp | unique | on | 7.456 | 8.296 | 8.520 | 328.2 | 29.95 |
| tcp | failover | off | 37.706 | 38.716 | 38.986 | 303.5 | 30.14 |
| tcp | failover | on | 0.739 | 37.899 | 38.186 | 335.2 | 30.11 |

Maximum issue lag: 2.36 ms; maximum RSS sample gap: 12.55 ms.

### Linux aarch64 inside Colima VM

[JSON](linux/benchmark/report.json) · [HTML](linux/benchmark/report.html) · [Test log](linux/tests.txt)

| Transport | Workload | Cache | p50 ms | p95 ms | Scheduled p95 ms | QPS | Peak process RSS MiB |
|---|---|---|---:|---:|---:|---:|---:|
| udp | repeat | off | 7.761 | 8.798 | 9.737 | 328.6 | 26.71 |
| udp | repeat | on | 0.525 | 1.431 | 2.069 | 334.7 | 26.68 |
| udp | unique | off | 7.652 | 8.778 | 9.633 | 328.2 | 26.71 |
| udp | unique | on | 7.700 | 8.450 | 9.495 | 328.5 | 26.74 |
| udp | failover | off | 38.113 | 39.198 | 40.038 | 302.8 | 26.82 |
| udp | failover | on | 0.441 | 38.372 | 39.203 | 334.9 | 26.77 |
| tcp | repeat | off | 7.934 | 8.672 | 9.486 | 328.1 | 26.73 |
| tcp | repeat | on | 0.546 | 0.990 | 1.975 | 334.3 | 26.70 |
| tcp | unique | off | 8.034 | 9.170 | 9.998 | 327.8 | 26.74 |
| tcp | unique | on | 8.028 | 8.717 | 9.634 | 327.9 | 26.76 |
| tcp | failover | off | 38.657 | 39.772 | 40.646 | 302.1 | 26.88 |
| tcp | failover | on | 0.556 | 38.579 | 39.352 | 335.0 | 26.85 |

Maximum issue lag: 8.74 ms; maximum RSS sample gap: 13.96 ms.

## Limits

These are separate OS/runtime observations. No cross-platform speedup or memory
saving is inferred. Guest proxy RSS excludes whole-VM/Colima/kernel/client/peer
memory and may miss short peaks. This does not establish native Linux hardware
performance, WAN behavior, maximum throughput, independent DNS-codec validation,
production security or hosted CI success. GitHub remains Private; project license
is still unselected. See [workflow details](../../docs/LOCAL_VALIDATION.md).
