# Dependencies and license status

No project open-source license is selected for this Private MVP. Dependencies
retain their own terms; this file does not relicense them or original project code.

- dnspython 2.9.0: ISC (installed distribution License-Expression), runtime DNS
  parsing/query support. [Upstream](https://github.com/rthalley/dnspython).
- psutil 7.0.0: BSD-3-Clause, development-only process measurement.
  [Versioned license](https://github.com/giampaolo/psutil/blob/release-7.0.0/LICENSE).
- Python runtime: PSF and bundled component notices.

No third-party source, binary or dataset is vendored. Synthetic names use `.test`,
answers use documentation address ranges, and reference peers bind loopback.
No user traffic captures or private DNS datasets are uploaded. A future bundled
runtime or binary/container distribution must retain its applicable notices.

Optional local validation tooling downloads official Colima (MIT) and Lima
(Apache-2.0) releases, with version/digest pins in `tools/colima-lock.json`.
Binaries remain ignored locally and are not vendored or published. The Docker
recipe uses the official Python Debian image; its Python/OS component notices
remain applicable. No container image is published by this workflow.
