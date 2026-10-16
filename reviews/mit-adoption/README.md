# MIT adoption verification

The owner explicitly selected MIT. Root `LICENSE` contains the standard MIT grant
with copyright (c) 2026 Andrew Yuan. README, SECURITY, third-party notices and
`pyproject.toml` now agree: original project code/documentation is MIT;
`license-files` lists LICENSE and THIRD_PARTY_NOTICES.md. GitHub stays Private.

## Third-party scope

Runtime dnspython 2.9.0 remains ISC; development psutil 7.0.0 remains BSD-3-Clause.
Installed metadata and their versioned upstream licenses were checked. Optional
Colima 0.10.3 remains MIT and Lima 2.2.1 remains Apache-2.0; Python and Debian
components retain their own terms. See the versioned primary-source links in
[third-party notices](../../THIRD_PARTY_NOTICES.md). The project MIT grant does
not relicense these components or remove their attribution/notice/disclaimer
conditions. No third-party model, dataset, source tree, binary or container image
is added to the repository by this change.

## Verification and provenance

The source manifest includes pyproject metadata, so prior reports were archived
without editing their original source hashes or historical license fields.
The full one-click workflow was rerun: **40 identical tests per platform**, five
mutations each, and **36 trials / 4,320 correct responses each**, with zero omitted
rows. Current native/VM JSON and HTML pass source, wire-answer, ledger, test-ID,
command-exit, container and cleanup checks. README is regenerated from the current
native report. Linux VM results remain separate; no new universal performance or
memory claim is introduced. The owned container was removed and VM stopped.

See [current dual-platform evidence](../local-validation/README.md), [receipt](receipt.json)
and [workflow](../../docs/LOCAL_VALIDATION.md). Historical reviews explicitly state
that their then-unselected license status predates this adoption. Original receipt
JSON is preserved. No runtime/test/tool code or dependency version was changed.
