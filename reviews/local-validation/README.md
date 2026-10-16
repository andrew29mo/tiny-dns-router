# Current local validation after MIT adoption

This run validates the current MIT metadata and unchanged production/test/tool
implementation, using one frozen source snapshot on native macOS ARM64 and
Linux aarch64 inside Colima. Each platform passed **40 identical formal test IDs**,
five actual production-network mutation checks, and **36 trials / 4,320 correct
responses**. All 72 trials / 8,640 replies are retained.

```sh
./tools/validate-local
.venv/bin/python -m tools.check_validation reviews/local-validation
```

- Native macOS: [JSON](native/benchmark/report.json), [HTML](native/benchmark/report.html),
  [formal outcomes](native/tests.json), [test log](native/tests.txt).
- Linux in Colima: [JSON](linux/benchmark/report.json), [HTML](linux/benchmark/report.html),
  [formal outcomes](linux/tests.json), [test log](linux/tests.txt).

`combined.json` binds the full snapshot, command results and cleanup; platform
receipts bind the same source manifest, exact test IDs and own measured report.
Raw Docker inspect/image/VM records agree with the summaries. The owned container
was removed and dedicated VM stopped. Text logs and command paths are normalized;
original local hashes are retained in `original-digests.json`. Source/report bytes
are unchanged. The project is now licensed under [MIT](../../LICENSE); third-party
components retain their [own terms](../../THIRD_PARTY_NOTICES.md).

Python 3.12.14 and pinned dependencies are identical across the platforms. The
native run precedes VM startup. The Linux VM has 4 vCPUs/6 GiB RAM; its non-root,
network-isolated container has 4 CPUs/4 GiB RAM, no live source mounts and no
architecture emulation. Native/VM performance and RSS remain separate. Proxy
process RSS excludes whole VM/kernel/client/peer memory and can miss brief peaks.
Fixed-load completion QPS is not saturated capacity. Invocation and scheduled
latency, issue lag and sample gaps are all retained. No cross-platform speedup,
native Linux hardware, WAN, independent DNS-codec validation, production security
or hosted-CI success is inferred.

Pre-MIT source/measurement records remain in
`reviews/historical-validation-pre-mit-e0c3a1f/`; historical receipts retain their
then-unselected license state. See [MIT adoption](../mit-adoption/README.md) and
[workflow details](../../docs/LOCAL_VALIDATION.md). GitHub remains Private.
