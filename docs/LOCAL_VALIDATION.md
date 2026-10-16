# Local macOS and Colima Linux validation

After creating the project Python 3.12 virtual environment and installing
`requirements-dev.txt` as in the README, run on macOS:

```sh
./tools/validate-local
# Optional: choose a NEW output directory inside results/local
./tools/validate-local --output results/local/my-validation
.venv/bin/python -m tools.check_validation results/local/my-validation
```

An existing Docker CLI is required (Docker Desktop does not need to run).
The runner installs checksum-pinned official Colima 0.10.3 and Lima 2.2.1
binaries under ignored `results/local/toolchain/`, verifies their versions,
and uses a dedicated DNS profile in a project-specific Colima home. It does not
change the active Docker context, OS DNS or unrelated VM profiles. A profile
already running causes refusal. The project lock prevents concurrent runs.
New source files must be staged first: snapshots include tracked files only.

The runner copies one fixed snapshot, runs native macOS first while the dedicated
VM is stopped, then starts a native-architecture Linux VM (4 vCPU, 6 GiB RAM).
The checksum-pinned Python 3.12.14 Debian image installs the same dependencies
and copies the snapshot without a live source mount. The test container is a
non-root user, has no external network, drops capabilities and limits itself to
4 CPUs/4 GiB RAM. DNS tests use only loopback, available inside this network mode.
There is no architecture emulation. Builds/installations require network access;
the test/measurement container does not.

Each environment generates the complete 36-trial benchmark, verifies wire
answers and ledgers, runs the full formal unittest suite, and rejects five
mutated production variants. Report tests use that environment's freshly
measured report through `DNSROUTER_TEST_REPORT`; this selects the data artifact,
not another implementation or relaxed source checks. The source manifest and
snapshot bindings must agree in both environments. Changed source, failed
commands, timeouts, abnormal/OOM container exits or failed cleanup prevent an
overall passed record. Commands have deadlines; cancellation reclaims descendants,
including subprocesses which open new sessions. Supervised formal commands inherit
unique ownership tags; leftover tagged processes are reclaimed even after a parent
exits normally, and that command fails. This protects against accidental leaks,
not hostile processes that remove tags or evade process inspection. VM lifecycle
commands are separately managed, so their intentional daemons are not reclaimed.
Exact discovered/started/successful unittest IDs are retained in `tests.json`
and must match between platforms. Manifest setup failures and interrupted commands
also leave failed receipts. The container is identified by a
unique per-run label, removed only after successful export (failed export retains the stopped
container), and the owned VM is stopped.
Interrupted runs retain failed/incomplete evidence and cannot be mistaken for
successful validation. Cached images and the stopped VM disk remain for reuse.

`combined.json` records command statuses/log hashes, snapshot identities,
container exit and cleanup. Each platform has its own `validation.json`, test and
mutation logs, and `benchmark/report.json` plus HTML. `linux-runtime.json` records
VM/container limits and image identity. Raw working directories and logs remain
ignored locally; selected normalized evidence is retained in
`reviews/local-validation/`. Checks provide consistency, not hostile-producer
attestation or comprehensive secret scanning.

Native and Linux-VM latency/QPS/CPU/RSS are separate observations; do not compute
a cross-platform speedup from them. Linux RSS covers the proxy process inside
the guest, not Colima, the entire VM, kernel socket buffers, clients or peers.
Both platforms' sampled RSS can miss brief peaks. These fixed offered schedules
are not saturated capacity measurements, native Linux hardware tests, WAN tests
or hosted GitHub CI. Existing billing-blocked CI remains a separate limitation.
