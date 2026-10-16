# Dependencies and license status

Original project code and documentation are licensed under MIT; see
[LICENSE](LICENSE). The project MIT grant does not replace third-party terms.
Dependencies and optional validation tooling retain their own notices and
licenses. The current source-plus-requirements workflow introduces no vendored
third-party code or combined binary redistribution.

- dnspython 2.9.0: ISC (installed distribution License-Expression), runtime DNS
  parsing/query support. [Versioned license](https://github.com/rthalley/dnspython/blob/v2.9.0/LICENSE).
- psutil 7.0.0: BSD-3-Clause, development-only process measurement.
  [Versioned license](https://github.com/giampaolo/psutil/blob/release-7.0.0/LICENSE).
- Python runtime: PSF and bundled component notices.

No third-party source, binary or dataset is vendored. Synthetic names use `.test`,
answers use documentation address ranges, and reference peers bind loopback.
No user traffic captures or private DNS datasets are uploaded. A future bundled
runtime or binary/container distribution must retain its applicable notices.

Optional local validation tooling downloads official
[Colima 0.10.3 (MIT)](https://github.com/abiosoft/colima/blob/v0.10.3/LICENSE) and
[Lima 2.2.1 (Apache-2.0)](https://github.com/lima-vm/lima/blob/v2.2.1/LICENSE) releases, with version/digest pins in `tools/colima-lock.json`.
Binaries remain ignored locally and are not vendored or published. The Docker
recipe uses the official Python Debian image; its Python/OS component notices
remain applicable. No container image is published by this workflow.

ISC and BSD-3-Clause dependency terms permit use in this MIT-licensed source
project while their own attribution, notice and disclaimer conditions remain
applicable. If distributing dependency copies, retain their complete notices;
BSD-3-Clause also restricts use of contributor names for endorsement. For future
bundled binaries or container images, retain each runtime/OS/tool component’s
applicable notices and terms, including Apache-2.0 where applicable. No such
distribution is introduced by adding this project license.
