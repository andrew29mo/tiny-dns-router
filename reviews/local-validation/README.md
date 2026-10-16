# Local validation audit

Both platforms passed the revised workflow using the same frozen production,
fixture and tool sources: **40 identical formal unittest IDs each**, five actual
network mutation checks each, and **36 full trials / 4,320 correct replies each**.
All 72 trials / 8,640 replies are retained. This validates native macOS ARM64 and
Linux aarch64 inside Colima, not native Linux hardware or hosted GitHub CI.
GitHub remains Private; project license is unselected.

## Findings fixed

- The original executor could mark a normally exited parent **passed** while a
  new-session child remained alive. Supervised formal commands now propagate
  unique ownership tags through descendants, reclaim tagged leftovers after
  normal/nonzero/timeout exits, and fail if a normal exit left children behind.
  Regressions cover both exit 0 and exit 7, plus a timeout whose SIGTERM handler
  exits 0. Ownership tags address accidental leaks in inspectable cooperating
  processes; they are not a hostile-process containment guarantee.
- The old checker accepted a Linux log claiming only one test alongside 35 native
  tests after the log hash was updated. The new standard unittest driver records
  discovered, started and successful test IDs in `tests.json`. Both platforms must
  match exactly, with no missing, repeated, failed or skipped tests. Command module,
  outcome hashes and summary counts are checked. See the preserved
  [old checker counterexample](original-count-counterexample.json).
- A failed recovery export previously still allowed container removal. Removal
  now requires successful export. An **actual exit-7 container** with a deliberately
  invalid export destination was retained as expected, then manually removed after
  the probe; its VM was stopped. See [probe](export-failure-probe.json). The formal
  suite also exercises this branch with a controlled failing command result.
- Manifest initialization failure now leaves failed suite JSON; interrupted
  outer commands retain their interrupted disposition. Raw Docker inspect/image
  data, final VM list and remaining-container list must agree with summary fields.

## Evidence

```sh
./tools/validate-local
.venv/bin/python -m tools.check_validation reviews/local-validation
```

The source/snapshot hashes, real command arguments and operation outcomes are in
`combined.json` and each platform's `validation.json`. Runtime/image/container
limits are in `linux-runtime.json`. Each platform retains its own `tests.json`,
test/mutation logs and complete benchmark JSON/HTML. Reports test the production
socket/CLI implementation; the environment variable selects freshly measured
report data, with full source checks preserved. No alternative router is tested.

[Thirteen negative record probes](negative-checks.json) reject timeout, reclaimed
orphans, container error, inspect/summary contradiction, unfinished cleanup,
wrong source binding, absent Linux evidence, altered logs, missing trials,
incomplete outcomes, a wrong test command, a misleading VM label, and a
self-consistent but different platform test inventory. The last probe changes
Linux to 39 completed tests while native has 40, and is specifically rejected
for differing formal tests.

The final whole-run checker passed after the owned container was removed and
VM stopped. The separate export-failure probe runs **after** both formal timing
runs, so it does not contaminate the performance observations. Logs and command
arguments replace local home/repository paths and OS username; source/report
bytes are unchanged. Original local digests are in `original-digests.json`.
These checks establish consistency, not hostile-producer attestation. Raw local
snapshots, environments, tools and logs remain ignored.

Pre-audit records are preserved in `reviews/historical-local-validation-23fbf9d/`.
They describe the old source and weaker checks, not current-source validation.

## Separate performance and RSS

Each linked report retains all workloads and blocks, invocation and scheduled
latency, completed QPS, issue lag, RSS baseline/peak/growth and sampling gaps.

- **Native macOS ARM64**: [JSON](native/benchmark/report.json),
  [HTML](native/benchmark/report.html), [40-test outcomes](native/tests.json).
- **Linux aarch64 / Colima VM**: [JSON](linux/benchmark/report.json),
  [HTML](linux/benchmark/report.html), [40-test outcomes](linux/tests.json).

Both use Python 3.12.14, identical pinned requirements and planned query schedules.
The dedicated VM is stopped during native measurement. Linux uses a 4-vCPU/6-GiB
VM, with a non-root, network-isolated, capability-dropped 4-CPU/4-GiB container,
without a live source mount or architecture emulation.

No cross-platform speedup or memory saving is inferred. RSS covers only the proxy
process; guest RSS excludes whole-VM/Colima/kernel/client/peer memory. Sampling can
miss short peaks. These fixed offered loads and controlled delayed peers do not
establish saturated capacity, WAN performance, independent DNS-codec validation,
production security or hosted CI success. See [workflow](../../docs/LOCAL_VALIDATION.md).
