# Public repository verification

Repository: [andrew29mo/tiny-dns-router](https://github.com/andrew29mo/tiny-dns-router).
The owner authorized Public visibility. GitHub reports `public`, `private=false`
and MIT. Root LICENSE, project metadata, README and third-party notices agree.
Historical receipts preserve their Private/pre-MIT states; they are dated evidence.

## Correctness and evidence

The publication changes only documentation and repository settings. A fresh
native macOS run passed **40 tests**. The retained macOS and Colima Linux records
were rechecked against current production/test/tool/metadata hashes: **40 identical
test IDs per environment**, five mutations each, **72 full trials / 8,640 correct
replies**, canonical JSON/HTML, correct container exit and successful cleanup.
No new Linux timing run is claimed for publication. No cross-platform speedup,
whole-VM RSS or saturated-capacity claim is introduced. The root native table
matches the retained report, and Linux guest performance/RSS stays separate.

See [current dual-platform evidence](../local-validation/README.md),
[fresh test log](tests.txt) and [receipt](receipt.json). The earlier private hosted
run was billing-blocked; hosted CI for the publication commit is checked separately
at the [workflow](https://github.com/andrew29mo/tiny-dns-router/actions/workflows/ci.yml).
Passing local evidence is not treated as proof a hosted job executed.

## Security settings

[Observed configuration](security-settings.json):

- Secret scanning and push protection enabled; zero open secret alerts observed.
- Dependabot alerts and security updates enabled and unpaused; weekly pip and
  GitHub Actions updates configured. Zero open Dependabot alerts observed.
- Active main-history rules prevent deletion and force-push, with no bypass.
- Separate main-CI rules require Linux/macOS checks, with admin bypass for the
  solo maintainer. No mandatory second reviewer blocks single-person maintenance.
- Every external PR contributor requires approval before Actions execution.
- Workflow tokens default to read-only and cannot approve PRs. Actions are limited
  to checkout/setup-python, with SHA pinning enforced; checkout credentials are
  not persisted. No `pull_request_target` workflow exists.
- Only the owner is a write collaborator; no deploy keys or Actions secrets exist.
  Public readers may read/fork/propose changes and receive no direct write grant.

Alert counts are point-in-time observations; no background scanning completion or
absence of all vulnerabilities is inferred. Repository safeguards do not turn the
experimental loopback DNS service into a hardened public resolver. Heuristic file
checks and preserved source/record checks are not comprehensive security attestation.
