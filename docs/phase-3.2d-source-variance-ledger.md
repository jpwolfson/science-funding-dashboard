# Phase 3.2d File A / File B source-variance ledger

This is the running spot-QA list for every approved obligation baseline where
the official GTAS/File A total differs from the accepted File B Program
Activity total. The machine-readable source is
[reference/obligation_source_variance_ledger.json](../reference/obligation_source_variance_ledger.json).
A unit test requires that it cover every dual exact pin in every registered
account baseline, so a future disagreement cannot be added silently.

File B remains the canonical dashboard ledger. These rows preserve both exact
official totals, emit the existing source warning, and never add a tolerance or
synthetic balancing event. Variance is always **File A minus File B**; a
negative value means File B is higher.

## Current inventory

| Spot-QA priority | Account / FY | File A | File B | A − B | Absolute variance / File A | Status |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | NOAA ORF `013-1450` / FY2025 | $5,909,955,239.20 | $7,498,931,108.79 | −$1,588,975,869.59 | **26.8864%** | Live |
| 2 | DHP `097-0130` / FY2025 | $46,920,693,135.53 | $46,765,241,257.73 | $155,451,877.80 | **0.3313%** | Pending |
| 3 | NOAA PAC `013-1460` / FY2025 | $2,632,403,455.21 | $2,615,955,074.73 | $16,448,380.48 | **0.6248%** | Live |
| 4 | Defense-Wide RDT&E `097-0400` / FY2025 | $38,136,458,827.72 | $38,123,623,075.40 | $12,835,752.32 | **0.0337%** | Pending |
| 5 | Census Current `013-0401` / FY2025 | $343,719,439.23 | $345,384,177.96 | −$1,664,738.73 | **0.4843%** | Live |
| 6 | DHS CWMD `070-0860` / FY2026 | $23,808,508.44 | $25,027,373.29 | −$1,218,864.85 | **5.1195%** | Live |
| 7 | Navy RDT&E `017-1319` / FY2025 | $27,885,355,759.11 | $27,884,886,462.75 | $469,296.36 | **0.0017%** | Pending |
| 8 | EPA S&T `068-0107` / FY2022 | $780,787,982.37 | $780,771,378.43 | $16,603.94 | **0.0021%** | Live |
| 9 | Defense-Wide RDT&E `097-0400` / FY2023 | $35,077,389,781.09 | $35,077,388,772.51 | $1,008.58 | **0.0000%** | Pending |

NOAA ORF is the clear magnitude outlier: its File B total exceeds File A by
about $1.589 billion, or 26.9% of File A. It should receive the first post-
project spot check. DHP is the second-largest disagreement in absolute dollars;
Defense-Wide FY2023 is the smallest.

## Evidence index

- **NOAA ORF FY2025:** workflow run `31910397962`, discovery job
  `95212047055`, raw artifact `9268819942`, and the nested P12 File B
  digest recorded in the JSON ledger. The accepted File B total independently
  matched the date-filtered Program Activity endpoint.
- **NOAA PAC FY2025:** workflow run `31910397962`, discovery job
  `95107812703`, raw artifact `9257775657`. The accepted File B total
  independently matched the date-filtered Program Activity endpoint.
- **Census Current FY2025:** workflow run `32013883488`, job `95339201920`,
  raw artifact `9287062264`. Its 43-row P12 File B archive totals
  `34538417796` cents; the entire `-166473873`-cent variance is the exact
  `0000 / UNKNOWN/OTHER` File B bucket. PR `#43` merged at
  `4b99fe8b81653d1ca79095631c12af344a8f5e81`; post-merge Test run
  `32097824562` and Deploy Pages run `32097824547` succeeded, and the live
  account JSON matched the merged file byte-for-byte.
- **DHS CWMD FY2026:** workflow run `32449818249`, source job `96781297151`,
  raw artifact `9442894725`, and nested P09 File B digest recorded in the JSON
  ledger. The official File A endpoint returned `2380850844` cents; the
  accepted 36-row P09 File B archive returned `2502737329` cents. The owner
  approved publishing File B as canonical on 2026-08-21 while preserving the
  exact File A total. PR `#53` merged at
  `37bca577ed75d1f9107853179667e21bd7b0114b`; post-merge Test run
  `32516046467` and Deploy Pages run `32516046481` succeeded, and the live
  account/manifest/root/sentinel JSON matched the merged files byte-for-byte.
- **Navy RDT&E FY2025:** workflow run `33145859877`, source job
  `98766675969`, and raw artifact `9682337050`. The retained P12 File B
  archive totals `2788488646275` cents, exactly matching the separate
  date-filtered 15-row Program Activity response with no next page. The
  official File A endpoint remains `2788535575911` cents. The owner approved
  the exact `46929636`-cent dual pin on 2026-08-28; raw, nested File B, File A,
  and Program Activity digests are recorded in the JSON ledger.
- **DHP FY2025:** workflow run `33472362131`, source job `99744617337`, and
  raw artifact `9788896971`. The retained P12 File B archive totals
  `4676524125773` cents, exactly matching the separate date-filtered 22-row
  Program Activity response with an explicitly empty page 2. The official
  File A endpoint remains `4692069313553` cents. The owner approved the exact
  `15545187780`-cent dual pin on 2026-09-01; raw and Program Activity response
  digests are recorded in the JSON ledger.
- **Defense-Wide RDT&E FY2023:** workflow run `33472362131`, source job
  `99744618294`, and raw artifact `9790896334`. The retained P12 File B archive
  totals `3507738877251` cents, exactly matching the separate date-filtered
  28-row Program Activity response with an explicitly empty page 2. The
  official File A endpoint remains `3507738978109` cents. The owner approved
  the exact `100858`-cent dual pin on 2026-09-01; raw and Program Activity
  response digests are recorded in the JSON ledger. DARPA is included within
  this Defense-Wide federal account; the full account is not labeled DARPA.
- **Defense-Wide RDT&E FY2025:** workflow run `33472362131`, attempt-16
  source job `99974200547`, and raw artifact `9814928296`. The retained P12
  File B archive totals `3812362307540` cents, exactly matching the separate
  date-filtered 26-row Program Activity response with an explicitly empty
  page 2. The official File A endpoint remains `3813645882772` cents. The
  owner approved the exact `1283575232`-cent dual pin on 2026-09-01; raw,
  nested File B, File A, and Program Activity response digests are recorded
  in the JSON ledger. DARPA is included within this Defense-Wide federal
  account; the full account is not labeled DARPA.
- **EPA S&T FY2022:** workflow run `31787669479`, accepted retry job
  `94810063304`, raw artifact `9224418566`, and owner-approval commit
  `8c850bb5136d43092235eaddc1007f765ba70f37`. File B independently matched
  the official Program Activity total; the source reason records Data Broker
  rule A19.

Artifact IDs and digests are retained as chain-of-custody evidence even after
GitHub's downloadable artifact expires. Baseline rows, accepted provenance,
commit history, and this ledger remain durable.

## Post-project spot-QA procedure

1. Work in the priority order above, then process any new ledger entries by
   descending `absoluteVarianceCents`.
2. Re-fetch the official fiscal-year snapshot named by the account baseline and
   verify it equals `fileAObligationsCents`.
3. Re-run or independently query the exact P12 File B Program Activity scope
   and verify it equals `fileBObligationsCents`. Use the account, fiscal year,
   period, submission type, and columns recorded by accepted provenance.
4. Verify the signed arithmetic exactly:
   `File A - File B = fileAFileBVarianceCents`. Do not use a tolerance.
5. Compare the Program Activity breakdown to the recorded explanation. For
   Census, confirm the full difference is still the `UNKNOWN/OTHER` bucket.
6. Verify the live dashboard still exposes the source warning and that no
   synthetic residual event was introduced to force agreement.
7. Record the QA date and result in this document or a follow-up issue; if an
   official source changes, require a new exact pin, raw evidence, tests, owner
   approval, reconcile, deploy, and live QA.

## Maintenance contract

Whenever a new baseline gains `fileBObligationsCents`,
`fileAFileBVarianceCents`, and `fileAFileBVarianceReason`:

- add the exact row and chain-of-custody evidence to the JSON ledger;
- add or update its human-readable table row here;
- rank it by absolute variance for later spot QA;
- preserve owner approval and release status; and
- run the obligation validation tests and the fast verification tier.
