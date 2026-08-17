# Phase 3.2d Commerce release handoff

Prepared from current live main `fc74455d275083feaa2c3e1e4d2511870e4d5295`.

## Current batch: NIST pair

This scaffold appends only:

- `commerce/nist-strs` — federal account `013-0500`, **Scientific and
  Technical Research and Services**.
- `commerce/nist-its` — federal account `013-0525`, **Industrial Technology
  Services**.

BEA is absent under the parked-account rule. No download, trigger, workflow,
remote branch, CI run, or pull request is created by the scaffold commit.

## NOAA release evidence

The pair retains all 99 reviewed official Program Activity identities (72
PAC/PAN and 27 PARK) as 28 stable dashboard paths. Exact code/name matching
keeps the collision-sensitive `0004`, `0006`, `0007`, `0010`, `0015`, and
`0066` identities distinct through the File B and event pipelines. Program
Support and Mission Support intentionally coalesce only where the official
source evidence establishes one reviewed identity.

FY2015–16 are unavailable. FY2017 begins at P06 and is partial through P12;
FY2018–25 are complete; FY2026 is partial through P09. Every source-available
year has an exact obligation-cent pin.

The accepted ORF FY2024 P12 File B archive from run `31910397962`, job
`95074505208`, totals `725047451996` cents. The live official FY2024 account
record independently reports the same `7250474519.96` dollars, so this exact
pin supersedes the earlier 2026-08-12 snapshot value. Raw artifact
`9255002876` is retained for 14 days with outer SHA-256
`6b8e9632a220bf8ef234a033c04931023cd4a63bc84b599465d6b1b2b80b5885`.

ORF FY2025 P02 also exposes 34 transient exact code/name pairs that do not
appear in the final all-history Program Activity inventory. They comprise
842 File B rows; the 34 newly reviewed pairs total `26829765627` cents and
map by exact name-qualified alias to the existing NOS, NMFS, OAR, NWS,
NESDIS, Program Support, OMAO, and NOAA Wide Support Services identities.
No bare-code or new dashboard identity was introduced. Raw artifact
`9255011172` is retained for 14 days with outer SHA-256
`c3a7710bdf9546e5b7e6c4ef060b3d9feddc7ffe19a81b51e25fd70061541b6b`.

The accepted PAC FY2024 P12 File B archive from job `95074505756` totals
`240475202079` cents, exactly matching the official account and date-filtered
Program Activity totals. FY2025 is an exact-source variance: the accepted
File B and date-filtered Program Activity total is `261595507473` cents while
the official GTAS/File A account total is `263240345521` cents, a difference
of `1644838048` cents. The owner-approved dual-pin row preserves both exact official
totals under the source-warning contract; File B remains canonical, and no
synthetic residual or tolerance is introduced. Raw artifacts `9256753415`,
`9256977273`, and the full attempt-2 archive `9257775657` are retained for 14
days with outer SHA-256 values
`4dcc46b56ec42b955f8c597c2dc4f193be3f4f74082479b1b9b0e20d71509f86`
`e2045264e322b42fb7de47fb9c175712d56905eaebfbb860515b7e5ee33f5126`,
and `c72bf72b4e57d0a86c982154fbbf33cb414f0a2e4ba8fc45806afc6a025a16be`.

The ORF FY2025 attempt-2 P06 archive adds three later transient exact pairs:
`0420 / NATIONAL WEATHER SERVICE`, `0520 / NESDIS`, and
`0620 / MISSION SUPPORT`. Their three rows total `275040646` cents and map
by exact name-qualified alias to the existing NWS, NESDIS, and Program
Support identities. Raw artifact `9257423821` is retained for 14 days with
outer SHA-256
`f78191873d5cb26cf164bd3b2642b4fecbd51a35c6aa4d2f90f6c9d030c53ce0`.

The ORF FY2025 P07 archive adds two later transient exact pairs. Attempt 3
first exposed `0240 / NATIONAL MARINE FISHERIES SERVICE`; after that mapping,
attempt 4 reached `0320 / OCEANIC AND ATMOPHERIC RESEARCH`. Their two rows
total `347700000` cents and map by exact name-qualified aliases to existing
NMFS `0002` and OAR `0003` identities. Raw attempt-3 artifact `9268213389`
and attempt-4 artifact `9268505081` are retained for 14 days with outer
SHA-256 values
`ee755e71ce210dce70f58409c6c7a054e2e5d9e5a780507202bc69eaf511753a`
and `0284c1aa82eed03321ba0b793e24eb324a49039ce83e89eae6cad6047a832811`.

Attempt 5 completed every ORF FY2025 File B period plus File C and exposed an
exact official source variance at final validation. The retained P12 File B
CSV has 731 rows totaling `749893110879` cents, and the official
date-filtered Program Activity endpoint independently totals the same exact
amount. The live GTAS/File A federal-account record remains `590995523920`
cents, so File A minus File B is `-158897586959` cents
(-$1,588,975,869.59). The owner-approved dual-pin row preserves both exact official
totals under the existing source-warning contract; File B remains canonical,
and no synthetic residual or tolerance is introduced. Attempt-specific raw
artifact `9268819942` is retained for 14 days with outer SHA-256
`3b6838b3ad267f24376f44c66de76556b39e690910c2465d4dc227de05861a85`;
its nested official P12 File B ZIP has SHA-256
`62e8dec24840a47441b146c14aa27bcbb5a3f5690d640b7429162084255d5b2a`.

After owner approval, attempt 6 reproduced both exact approved source totals
but exposed a validator endpoint-classification bug. The live GTAS fiscal-year
snapshot remains `590995523920` cents, while both P12 File B and the separate
federal-account detail endpoint return exactly `749893110879` cents. The
validator had assumed the detail endpoint always represented File A. The
repair remains fail-closed: for a declared dual pin only, the detail endpoint
must equal either the exact File A pin or the exact File B pin; any third value
still fails. Single-pin accounts retain the original exact File A check.
Attempt-specific raw artifact `9269112197` is retained for 14 days with outer
SHA-256 `6b6e57c4a5b65c9ac0eef48ad56e17563f27c6221b0d1025d5f9f5023f170c6b`.

Attempt 7 completed ORF FY2025 and unblocked reconcile. Candidate data
validation passed, then the fast tier correctly caught two scaffold-to-release
test assumptions: NOAA stores were still required to be absent, and FY2026
was still pinned to the pre-pull snapshot. The transition gate now permits
only two exact atomic states: both NOAA stores absent with the scaffold pins,
or both stores present with all ten FY2017--26 partitions and reconciled P09
pins (`303354666643` ORF cents and `105930342662` PAC cents). A one-store or
partial-partition state still fails closed. After the atomic commit, the
temporary scaffold alternatives must be removed before merge.

Attempt 8 reran only the failed reconcile job after that transition repair.
The complete terminal `filter=all` inventory is 184 raw executions across
pages of 100 and 84 jobs, followed by an explicitly empty page 3. Its latest
logical topology is exactly 22 successes (plan, all 20 pulls, and reconcile),
zero failures, and the branch deploy skipped. Atomic commit
`2ec3219fdb3895fed2e79c1c7ac651c13ba23309` materializes both ten-partition
NOAA stores, exact approved FY2025 dual pins, reconciled FY2026 P09 pins,
rebuilt rollups, and the 26-account combined sentinel. The temporary scaffold
alternatives are removed at the trigger-restored release head.

Post-reconcile release gates pass: Commerce `17/17`; both focused registries
`10/10`; whole registry `185/185` with 26 unique paths and federal-account
codes; fast `7/7`; rendered account, all-account, and sentinel matrices
`5/5`, `104/104`, and `2/2`; and the second screenshot pack `36/36` with no
capture errors. The footprint is `409029302` tracked bytes, `407462087` data
bytes, and `238061118` gzipped-store bytes. Its conservative, historical-
backfill-dominated 52-week projection remains flagged and is not treated as a
steady-state forecast.

The full batch payload is:

```json
{
  "mode": "full",
  "accounts": "commerce/noaa-orf,commerce/noaa-pac",
  "from_fy": null,
  "to_fy": null,
  "current_period": null
}
```

The selector must plan exactly 20 jobs: FY2017–26 for each account. Reconcile
must atomically materialize both ten-partition stores, replace the scaffold
pins with accepted source cents, rebuild obligation rollups, and rebuild the
combined sentinel before this batch can be called complete. Restore the
trigger to main's exact weekly/all content after reconcile, then require
fast/rendered/screens/footprint, PR merge, deploy, and live QA.

## NIST release contract

The NIST batch adds official accounts `013-0500` **Scientific and Technical
Research and Services** and `013-0525` **Industrial Technology Services**. It
retains the reviewed 24 official identities (12 PAC/PAN plus 12 PARK) as 15
stable account-scoped paths. The normal/special laboratory and MEP PARKs remain
distinct, as do the account-scoped uses of carryover PARK `EX202600313426`.

```json
{
  "mode": "full",
  "accounts": "commerce/nist-strs,commerce/nist-its",
  "from_fy": null,
  "to_fy": null,
  "current_period": null
}
```

The NIST selector must plan exactly 20 pinned jobs. Its accepted atomic data
commit must land and pass the full release path before Census Current starts.

Current-main preflight passes Commerce `17/17`, each focused registry `10/10`,
the 28-account registry `199/199`, exact 20-job selection, and fast `7/7`.
The pre-store all-account browser matrix passes every materialized account and
fails only the expected eight light/dark account/Program Activity requests for
the two NIST dashboard trees that reconcile has not created. Full rendered
verification is mandatory after the atomic commit.

## BEA quarantine

`commerce/bea` is deliberately absent from this release. Its FY2018 File C
request remains parked on the official USAspending status handle and must not
block ready Commerce accounts. Preserve the dedicated BEA branch, one-record
resume manifest, and reviewed raw ZIP evidence. Rejoin BEA only at a later
serial boundary after its own failed job and atomic reconcile succeed.

## Remaining Commerce order

After NOAA is fully live, release NIST STRS + NIST ITS, then Census Current,
then Census Periodic. Each batch follows register → full backfill → atomic
reconcile → trigger restoration → current-main integration → release QA.

## Official evidence

- Account records:
  `https://api.usaspending.gov/api/v2/federal_accounts/013-1450/` and
  `https://api.usaspending.gov/api/v2/federal_accounts/013-1460/`.
- Historical Program Activities: append `/program_activities/?limit=100` to
  either account endpoint.
- Commerce source boundary:
  `https://api.usaspending.gov/api/v2/reporting/agencies/013/overview/?limit=100`.
- Custom account Files A/B/C contract:
  `https://api.usaspending.gov/api/v2/download/accounts/`.
