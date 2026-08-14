# Phase 3.2d other-civilian sequencing-safe handoff

Prepared 2026-08-12 on `agent/3-2d-other-civilian-v2`, based on
authoritative main `689aba6a27f7f7282c444eacd583c4e694789bd7`.

## Non-negotiable release order

The ASPR availability probe is a hard dependency, not one ordinary scaffold
among several. The only valid history is:

```text
base 689aba6
  -> P: ASPR FY2024 single-period probe registration
  -> R: accepted official probe result and exact snapshot pins
  -> D: one atomic reconciled ASPR FY2024-FY2026 data commit
  -> VA -> DHS -> DOT -> IES -> AHRQ -> BLS/OJP scaffold commits
```

Commit **P is the branch tip in this worktree**. R and D do not exist yet and
must not be fabricated locally. VA and later commits are a separate local patch
queue; the coordinator may cherry-pick them only onto D or a descendant of D.

This ordering is mechanically enforced in
`tests/test_obligations_other_civilian.py`. If any VA-or-later account is
registered, the suite requires all of the following before it can pass:

1. an evidence-backed R state with exact FY2024–FY2026 pins;
2. a three-partition ASPR manifest containing only FY2024, FY2025, and FY2026;
3. accepted event/provenance files for every partition with File B and File C
   scope for internal account ID 7008;
4. normalized/provenance cents equal to the baseline pins; and
5. a warning-free, complete ASPR dashboard through FY2026 P09.

The full offline validator then independently checks the atomic store and
exact File B/File C reconciliation. A premature later-account cherry-pick
therefore fails the dedicated suite before a trigger can be justified.

## P — probe registration only

P appends only `hhs/aspr-rd-procurement` (`075-1000`, internal account ID
7008). The five pre-existing DOE/NSF entries are preserved byte-for-byte.
P's baseline exposes only:

```json
"2024": {"status": "partial", "asOfPeriod": 2, "firstPeriod": 2}
```

There is deliberately no `obligationsCents`. FY2025 and FY2026 remain
`unavailable` behind the same gate. P therefore permits exactly this payload:

```json
{
  "mode": "custom",
  "accounts": "hhs/aspr-rd-procurement",
  "from_fy": 2024,
  "to_fy": 2024,
  "current_period": 2
}
```

It plans one FY2024 P02 job. Full mode also plans only that probe job; a custom
FY2024–FY2026 request fails closed at FY2025. P contains no probe result,
download, data store, or claimed pin.

ASPR is the whole Research, Development, and Procurement account. It is not
BARDA-only coverage and does not resolve the provisional Project BioShield
crosswalk row.

## R — official result commit, created only after the probe

The coordinator creates R after running the P payload. Acceptance requires:

- account resolution exactly `075-1000` / ID `7008`;
- both `object_class_program_activity` and `award_financial` downloads finish;
- echoed account/FY/period scope exactly matches the request;
- ZIP, row-count, and archive-hash checks pass;
- normalization and probe-period reconciliation are exact; and
- no nonblank Program Activity identity is unmapped.

If P02 is unavailable, do not widen the request. Probe P03, then P04 and later
periods one at a time until the first accepted period is found. Record that
period in both registry `firstFiscalYearPeriod` and FY2024 `firstPeriod`; never
synthesize earlier activity.

R must add
`reference/hhs_aspr_rd_procurement_probe_evidence.json` with this tested shape:

```json
{
  "schemaVersion": 1,
  "federalAccount": "075-1000",
  "accountId": "7008",
  "fiscalYear": 2024,
  "firstAcceptedPeriod": 2,
  "acceptedAt": "<UTC timestamp>",
  "downloads": [
    {
      "submissionType": "object_class_program_activity",
      "status": "finished",
      "archiveSha256": "<64 lowercase hex>",
      "statusRowCount": 0,
      "acceptedRequestScope": {
        "filters": {"federal_account": "7008", "fy": 2024, "period": 2}
      }
    },
    {
      "submissionType": "award_financial",
      "status": "finished",
      "archiveSha256": "<64 lowercase hex>",
      "statusRowCount": 0,
      "acceptedRequestScope": {
        "filters": {"federal_account": "7008", "fy": 2024, "period": 2}
      }
    }
  ],
  "accountSnapshots": [
    {
      "fiscalYear": 2024,
      "retrievedAt": "<UTC timestamp>",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2024",
      "obligationsCents": 0
    },
    {
      "fiscalYear": 2025,
      "retrievedAt": "<UTC timestamp>",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2025",
      "obligationsCents": 0
    },
    {
      "fiscalYear": 2026,
      "retrievedAt": "<UTC timestamp>",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2026",
      "obligationsCents": 0
    }
  ]
}
```

Every placeholder and zero above must be replaced with observed official
evidence. The tests compare all three snapshot cents to the baseline, validate
the accepted period/scopes, and reject a `pending` source citation. The
research brief's earlier values are candidates only; they are not authorization
to invent R.

If the first accepted period is P02, FY2024 may be `complete`; if it is later,
FY2024 remains `partial`. FY2025 must be complete and FY2026 partial through
P09. R must make the ASPR custom FY2024–FY2026 planner emit exactly three jobs:
FY2024 P12, FY2025 P12, and FY2026 P09. R does not add the full data store.

## D — atomic three-year ASPR reconciliation

Only after R is green may the coordinator run the exact ASPR selector:

```json
{
  "mode": "custom",
  "accounts": "hhs/aspr-rd-procurement",
  "from_fy": 2024,
  "to_fy": 2026,
  "current_period": 9
}
```

All three years must land in one reviewed data commit D. D contains the ASPR
event partitions, accepted provenance, manifest, dashboards, and any
registry-derived aggregate dashboard updates produced by the established
pipeline. It is accepted only when exact cents reconcile, warnings are zero,
the ASPR dedicated guard passes, and the full fast tier is green.

Do not cherry-pick VA or any later scaffold between R and D. Do not split D so
that a later account can observe a one- or two-year ASPR store.

## Post-D patch queue and exact selectors

After D is committed, apply these reviewed append-only batches in order. Each
selector remains independent; do not combine ASPR with AHRQ.

| Batch | Exact selector | Range | Mechanical jobs |
|---|---|---|---:|
| VA | `va/medical-prosthetic-research` | FY2017–FY2026 P09 | 10 |
| DHS | `dhs/science-technology-rd,dhs/cisa-rd,dhs/cwmd-rd` | FY2017–FY2026 P09 | 30 |
| DOT | `dot/ost-research-technology,dot/faa-research-engineering-development,dot/fra-rd` | FY2017–FY2026 P09 | 30 |
| Education | `ed/ies` | FY2017–FY2026 P09 | 10 |
| AHRQ | `hhs/ahrq` | FY2017–FY2026 P09 | 10 |
| Statistics | `dol/bls,doj/ojp-research-evaluation-statistics` | FY2017–FY2026 P09 | 20 |

The reviewed account objects, exact pins, collision-safe aliases, and
presentation constraints in the prepared queue are unchanged from the source
brief. In particular:

- VA legacy Clinical Science identities remain separate from current CSP.
- CISA/CWMD historical organizations and CAS/non-CAS labels remain visible.
- OST-R is the parent; BTS/ARPA-I are subsets. Reused PACs stay distinct.
- FAA PAC 0012 variants and FRA rolling-stock variants remain distinct.
- IES is the parent and NCES a subset; IES Program Admin stays separate.
- AHRQ legacy reimbursable identities remain visible.
- BLS remains a statistical-capacity account.
- OJP is the parent; BJS and NIJ are Program Activities.

## Evidence sources

- Account snapshots:
  `https://api.usaspending.gov/api/v2/federal_accounts/{CODE}/?fiscal_year={FY}`
- PA/PARK inventory:
  `https://api.usaspending.gov/api/v2/federal_accounts/{CODE}/program_activities/?limit=100&page=1&order=asc&sort=code`
- Program Activity contract:
  <https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/federal_accounts/federal_account_totals/program_activities.md>
- Custom account contract:
  <https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/accounts.md>
- Crosswalk: `reference/aaas_federal_account_crosswalk.json`

## P verification

Before publishing or running the probe, P must have:

- ASPR registry: 10/10;
- whole registry: 45/45;
- dedicated tests: green with the exact one-job and multi-year-block assertions;
- full planner: 51 registry jobs, only one attributable to ASPR;
- fast tier: 7/7;
- clean diff and ownership limited to the registry append, ASPR staging
  baseline, this handoff, and the dedicated test module.

No remote operation, trigger, download, CI run, result evidence, pin, or data
store is claimed by P.
