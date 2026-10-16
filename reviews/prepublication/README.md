# Prepublication review

Reviewed base `ab8634a`. No new production, test, tool or dependency changes were
needed. Documentation now explicitly distinguishes invocation latency from
scheduled latency, clarifies that NXDOMAIN/NODATA are cached while SERVFAIL and
transport failures are not, and states the unselected project-license status.

## Verification

- Fresh native macOS run: **40 tests passed**, including actual production
  UDP/TCP/CLI behavior and validation failure/cleanup regressions.
- Retained native macOS and Linux/Colima evidence rechecked against the **current
  complete source manifest**: 40 identical formal test IDs per platform, five
  mutations each, all 72 planned trials and 8,640 correct replies. No performance
  rerun was needed for these documentation-only changes; this review does not
  claim another Linux test execution.
- Canonical native JSON/HTML exactly match the native platform evidence. The
  generated README table matches all retained blocks; no passing-pair selection
  or cross-platform speedup is claimed. The original MVP and DNS-review report
  hashes were also checked against their historical receipts.
- Proxy RSS, cache wire bytes and whole-VM memory remain distinct. Invocation
  latency excludes generator waiting; the linked reports also retain scheduled
  latency. Sample gaps and issue lag remain visible. Fixed-load QPS is not
  maximum capacity. Linux VM results are not native Linux hardware results.
- The current dedicated DNS VM was observed stopped. Stored container exit,
  removal, VM-stop, image/source and exact test-outcome evidence all passed the
  whole-run checker.

## License and repository state

No root LICENSE file, no project license in `pyproject.toml`, and no detected
GitHub license. README, security documentation and third-party notices agree.
Project licensing was not changed. Installed dependency metadata confirms
**dnspython 2.9.0: ISC** and **psutil 7.0.0: BSD-3-Clause**. No third-party model,
dataset, source tree, downloaded tool binary or container image is published.
Optional Colima/Lima/Python/OS tooling retains its own terms as documented.

GitHub remains **Private**, owned by `andrew29mo`, with no additional collaborators.
Actions retain read-only defaults, cannot approve PRs and require pinned action
SHAs. This review does not assert that hosted CI succeeded or remove the recorded
billing restriction. Visibility or license changes require a separate instruction.

## File and privacy checks

The heuristic scan covered 155 tracked baseline files and 154 unique reachable
Git blobs, including historical content. No private home/temp paths, recognized
GitHub/AWS credentials, private-key headers or credential-bearing URLs were
found. An additional baseline tracked-content scan found no email/JWT candidates. The
review scan record lists the existing public GitHub noreply author identity. Git
author identities use that noreply address. Personal instructions,
virtual environments, downloaded tools, raw local snapshots/state and caches
are ignored and absent from tracked files. No tracked symlinks, binaries or
files above the existing 10 MiB policy were found. Relative documentation links
were checked after adding this review.

See [receipt](receipt.json), [fresh test log](tests.txt), [scan scope](privacy-scan.json)
and [dual-platform evidence](../local-validation/README.md). Scan results reflect
patterns and inspected records; they are not a comprehensive secret/security
certification or hostile-producer attestation.
