# Phase 3.2d Commerce release handoff

Prepared from current live main `97fde03c4318957130bbcfd08474ddfe6b7cd2fc`.

## Current batch: NOAA

This scaffold appends only:

- `commerce/noaa-orf` — federal account `013-1450`, **Operations, Research
  and Facilities**.
- `commerce/noaa-pac` — federal account `013-1460`, **Procurement,
  Acquisition and Construction**.

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
