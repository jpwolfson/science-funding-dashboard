# Phase 3.2d earth, environment, and agriculture handoff

Status: Stage A run \`31787669479\` is terminal with 20 success (plan plus 19
pulls), one failure (EPA FY2022), and reconcile/deploy skipped. Only USGS
Surveys, Investigations and Research (\`014-0804\`) and EPA Science and
Technology (\`068-0107\`) are registered in this stage. The owner approved the
exact dual File A/File B pin representation for EPA FY2022 on 2026-08-14;
repair, bounded rerun, and atomic reconciliation remain pending.

## Serialized payload contract

The reviewed ten-account scaffold is split into four reconciliation-safe
payloads. Later accounts remain unregistered until their stage commit:

1. Stage A: \`doi/usgs-sir,epa/science-technology\` — 20 jobs.
2. Stage B: \`usda/ars-salaries-expenses,usda/ars-buildings-facilities,usda/forest-rangeland-research\` — 30 jobs.
3. Stage C: \`usda/nifa-extension,usda/nifa-research-education,usda/nifa-integrated-activities\` — 30 jobs.
4. Stage D: \`usda/ers,usda/nass\` — 20 jobs.

Each selector covers FY2017–FY2026: FY2017 uses the declared P6 source
boundary and plans P12, FY2018–FY2025 plan P12, and FY2026 is pinned to P9.
The coordinator owns triggers and all remote execution.

## Stage A evidence and semantic boundary

The official accounts are \`014-0804\`, titled \`Surveys, Investigations and
Research, Geological Survey\`, and \`068-0107\`, titled \`Science and
Technology, Environmental Protection Agency\`. Exact source endpoints and
FY2017–FY2026 GTAS/File A cents are pinned in their baseline files; FY2015 and
FY2016 are explicitly unavailable because Files A/B/C begin in FY2017 P6.

USGS-wide AAAS mission labels remain alternate context rather than synthetic
accounts or Program Activities. Reused USGS PAC \`0002\` names remain distinct
canonical identities. EPA's eight FY2026 mission PARK tokens remain distinct
from its legacy PAC/PAN identities; no legacy activity is silently mapped to a
current mission.

File B signed obligations remain canonical. File C and its signed residual are
separate award-financial detail; a low or negative signed File C ratio is not a
completeness percentage or evidence that File B is incomplete.

EPA FY2022 is the one owner-approved source-warning exception. Retained P12
File B and the independent official Program Activity endpoint both total
\`78,077,137,843\` cents; the official GTAS/File A pin is
\`78,078,798,237\` cents, an exact \`1,660,394\`-cent variance. The baseline
preserves all three values and a Data Broker A19 reason. No tolerance or
synthetic ledger event is permitted; accepted provenance must reproduce the
exact File B ledger total while retaining the File A account pin.

## Deferred release work

This local scaffold is not release-ready. Each authorized stage still requires
its serialized File B/File C backfill, exact baseline reconciliation, accepted
provenance, zero warnings, rendered review, and coordinator integration.

## Stage B release checkpoint (2026-08-18)

Stage A is merged, deployed, and live-QA green on the authoritative 30-account
`main` at `c654b32dc56d41bff10da3ebf199208472dc6cc5`. The approved EPA
FY2022 dual exact pins remain unchanged.

Stage B now registers only the three reviewed accounts
`usda/ars-salaries-expenses`, `usda/ars-buildings-facilities`, and
`usda/forest-rangeland-research`. Their exact FY2017--FY2026 GTAS/File A
pins and 27 canonical Program Activity identities come directly from the
reviewed ten-account scaffold. Stages C and D remain unregistered. The Stage B
full selector must plan exactly 30 jobs and fail closed on every new source
identity before an atomic reconcile is accepted.

The first Stage B source attempt retained exact raw evidence for one later
Salaries and Expenses identity: PAC `0014`, blank PARK,
`MISCELLANEOUS FEES/SUPPLEMENTALS`. It occurs once at zero cents in each of
FY2023 P04, FY2024 P05, and FY2025 P04. Those rows map to the existing
canonical `5ZBXSS9QSGU:miscellaneous-fees-supplementals` activity by exact
code-and-name alias; they do not create a new activity and do not alter any
File A or File B total.

The same attempt retained a single FY2020 P06 Forest and Rangeland Research
raw row (source submission label `FY2020Q2`) for PAC `0000`, blank PARK,
`UNKNOWN/OTHER`, at zero cents. It maps to that account's explicit
`0000:unknown-other` identity. This is ordinary missing attribution, not the
distinct nonblank-PARK identity contract used by the Census accounts, and it
does not alter either source total.

## Stage C release checkpoint (2026-08-19)

Stage B is merged, deployed, and live-QA green on authoritative 33-account
`main` at `0b1486664c47f76a44249b2d9e8487f1104ef924`. Its complete source graph,
atomic reconcile, weekly/all trigger restoration, current-main integration,
fast and rendered tests, screenshots, footprint, post-merge Test and Deploy,
byte-exact live JSON, and deployed light/dark rendering all passed.

Stage C registers only `usda/nifa-extension`,
`usda/nifa-research-education`, and `usda/nifa-integrated-activities`.

Stage C source run `32234385011` attempt 1 found one FY2026 P02 NIFA
Extension mapping gap: blank code/name with PARK `EX202500290511` and
`89,223,609` cents. That PARK is the already-established exact identity
`FINANCIAL ADJUSTMENT: PROGRAM NOT SPECIFIED`, so the repair registers the
same canonical identity for `usda/nifa-extension`; it does not alter any
source total or introduce a File A/File B variance. The retained raw artifact
is `9362983381` (14 days), 700 bytes, outer SHA256
`1c08f67e8dd815ca629dd28dda8d99c3f554dd81efbdfd08b16023e047fa93fa`.
Its sole inner archive is 522 bytes with SHA256
`46e853403d16b63dd1fc89e0d3fd72cf8c19402457c9eeb362b3b9a8209699bb`;
the exact 46-row snapshot totals `491,474,612` cents, including the reviewed
PARK row. The repair remains local-only until the source graph is terminal.

The same attempt later found one FY2019 P09 NIFA Integrated mapping gap:
code `FS09`, blank PARK, name `FSDW (FINANCIAL STATEMENT DATA WAREHOUSE)`,
and `404,906` cents. This is the established FSDW identity used by the other
NIFA accounts, so it is also an exact mapping repair rather than a source-total
variance. Retained raw artifact `9363925873` is 6,380 bytes with outer SHA256
`d201157626787df18d1cbb3b0dcc5bb68cd54741ed91e2bfa41e7a2dd9ce5aae`.
It preserves eight P02-P09 raw archives; the accepted 22-row P09 archive is
694 bytes, SHA256
`4e62fcb7dfd028748b66f537ef46d38858693e2e8d02fd353d60b5b73fe45d62`,
and totals `2,420,107,405` cents. This repair also remains local-only until
the source graph is terminal.

The same exact FS09 identity then recurred in four later Integrated Activities
partitions. The retained raw evidence is:

- FY2022 P02: artifact `9365104344`, 828 bytes, outer SHA256
  `5f49498b0cbe7a281b4cd22afb112ef7987f9899a888bae3c7003f61f0185cdf`;
  its 617-byte inner archive has SHA256
  `14d835d9d9680b20b1ece2cbf764c9046ab0ec07c42040bdae79245119596907`,
  13 rows totaling `2,425,851` cents, all from the one FS09 row.
- FY2023 P06: artifact `9365209011`, 4,362 bytes, outer SHA256
  `66468aa5fb5d583a45f0d9870e33130be9147b6201adcffb93813440e40e746a`;
  its 791-byte P06 archive has SHA256
  `64cd2d840073f1b7cc06860fdc75a8da94dba2b1b3d81d9e46ae1355cb34bd6c`,
  27 rows totaling `1,501,518,558` cents, including FS09 at `157,927` cents.
- FY2024 P05: artifact `9365292527`, 3,639 bytes, outer SHA256
  `1ae71739494a51196fa703e3c0e9c90efeb0bdc690739da22b21941944c9af8f`;
  its 766-byte P05 archive has SHA256
  `758b520ba220615cf235c4aead560635f60c5eaa76b4a66dc3d1a1a21b6a0ab4`,
  19 rows totaling `195,723,465` cents, including FS09 at `508,000` cents.
- FY2025 P02: artifact `9365314464`, 955 bytes, outer SHA256
  `a6f30483f6197d4247e30b0cb564ad71444bb3c977753c1768ac2793c5266b63`;
  its 739-byte inner archive has SHA256
  `2e675efae068bb8a386fa4d71734c0f5a2103a408f4b6e83df29cbfb3e8e0d8b`,
  17 rows totaling `31,492,400` cents, including FS09 at `187` cents.

All four are exact mapping repairs covered by the single canonical FS09 alias;
none changes a source total or adds a File A/File B variance.
Their exact FY2017--FY2026 GTAS/File A pins and reviewed Program Activity
identities come from the ten-account scaffold. Extension preserves both PAC
`0036` names as distinct identities. Research and Education keeps PARK
`Set Aside 1500` separate from generic historical set-aside rows; Integrated
Activities does the same for `Set Aside 1502`. The current `Homeland
Security` PARK is not silently merged with the longer legacy PAC label.

The Stage C full selector must plan exactly 30 FY2017--FY2026 jobs and fail
closed on every new source identity. Stage D remains unregistered until Stage
C has completed atomic reconcile, trigger restoration, current-main
integration, all local gates, merge/deploy, and live QA.

## Stage D release checkpoint (2026-08-20)

Stage C is merged, deployed, and live-QA green on authoritative 36-account
`main` at `d3aa7e3bc79052f97bb1d3d4c0872371c0609af3`. Its complete source graph,
atomic reconcile, weekly/all trigger restoration, current-main integration,
fast and rendered tests, screenshots, footprint, post-merge Test and Deploy,
byte-exact live JSON, and deployed light/dark rendering all passed. The live
FY2026 cumulative award and award-dollar lines retain the current-date cutoff.

Stage D registers only `usda/ers` (`012-1701`) and `usda/nass` (`012-1801`).
Their exact FY2017--FY2026 GTAS/File A pins and ten reviewed Program Activity
identities come from the serialized ten-account scaffold. ERS and NASS remain
separate statistical-capacity accounts rather than a synthetic USDA research
total. Reimbursable, FSDW, unknown/other, and financial-adjustment identities
remain exact and distinct. The Stage D full selector must plan exactly 20
FY2017--FY2026 jobs and fail closed on every new source identity. Any exact
File A/File B disagreement must be added to the source-variance ledger and
receive explicit owner approval before a dual exact pin is published.
