# Obligation ledger contract

Phase 3.1b adds a second ledger without changing the NSF or NIH award ledger.

| Ledger | Atom | Answers |
|---|---|---|
| Award | one source-native award/application record | How many new awards were made, and how much was committed? |
| Obligation | one File B Program Activity flow, enriched with File C award allocations | How much was obligated from an appropriations account, and when was it reported? |

The ledgers deliberately do not reconcile. Award totals and obligation flows
measure different things.

## Source and completeness contract

Ingestion uses USAspending's official asynchronous custom-account download:

`POST https://api.usaspending.gov/api/v2/download/accounts/`

The obligation ledger has two source layers:

- File B (`object_class_program_activity`) is the canonical account and
  Program Activity dollar series.
- File C (`award_financial`) supplies award, recipient, and transaction detail
  for the award-linked subset of File B.

The adapter resolves the API's internal federal-account ID from the requested
account symbol. Each download selects one account, fiscal year, reporting
period, and submission type. A pull is accepted only when the status reaches
`finished`, the echoed scope matches, ZIP integrity passes, all expected CSVs
and columns exist, the status row count matches parsed CSV records, and every
row belongs to the requested account and year. File C requires Assistance,
Contracts, and Unlinked files.

File B `obligations_incurred` is cumulative through the selected period. The
adapter downloads each available snapshot and derives reporting-period activity
by subtracting the previous snapshot at the account and Program Activity
grain. USAspending performs the object-class and funding-dimension sum in the
download query; subtracting those PA totals is algebraically identical to an
outer-joined full-grain delta. File C
`transaction_obligated_amount` is already reporting-period activity and is
never differenced. Blank File C obligation values are excluded. Signed zero-net
groups with real positive and negative rows remain auditable.

Files A/B/C begin in FY2017 Q2. FY2015 and FY2016 are recorded as unavailable,
FY2017 as partial, and FY2018 as the first full fiscal year. Award-search amounts
must never be used to fill the unavailable years.

## Normalized events and stable identity

Multiple File C rows can share the approved atom because the source also groups
by object class and DEFC. Those rows are deliberately summed in exact cents at:

`(award identity, federal account, Program Activity identity, submission period)`

Program Activity identity prefers PARK. Legacy rows use the committed
code-and-name alias table so the FY2026 PARK transition does not split pages.
Award identity prefers USAspending's generated award key, then PIID/parent,
FAIN, URI, and finally a deterministic unlinked token.

For each account, Program Activity, and submission-period bucket, the adapter
adds a residual event equal to:

`File B activity - File C activity`

The residual is first-class and may be positive or negative. It represents
payroll, intramural, and other account activity without a File C allocation.
Therefore `File C + residual = File B` exactly.

Persisted events include a stable ID, source (`file_c` or
`file_b_residual`), submission period, derived fiscal year/period/end date,
account, Program Activity code/name/PARK, signed integer cents, award/recipient
metadata where present, source-row count, and gross positive/negative cents.
Unlinked File C rows retain dollars but never inflate `distinctLinkedAwards`.
Missing Program Activities go to visible code `0000` instead of being dropped.
When File C reports non-zero `0000` activity for a period in which File B has
no unknown-PA bucket, the ledger retains that award-linked overlay and creates
an equal opposite `file_b_residual` event in `0000`. The canonical File B net
for that bucket is therefore exactly zero. A File C bucket for any known PA
that is absent from File B remains a fatal scope/alias error.

Period 2 is the first supported monthly window and can include October and
November. Historical quarterly submissions remain quarterly. The dashboard
uses “reported in submission period” and never invents action-month precision.

## Persistence and corrections

Stores are deterministic `FY####.csv.gz` shards plus a manifest. A materialized
partition is replaceable because agency submissions can be corrected; raw
archive hashes, row counts, normalized fingerprints, and prior manifests make
the replacement auditable. No row is silently omitted from a completed
download.

## Dashboard contract

Every obligation dashboard has `kind: "obligations"`; missing `kind` continues
to mean `awards`. Obligation dashboards publish:

- signed File B totals by reporting period and fiscal year;
- cumulative FYTD totals at submission-period endpoints;
- File C award-linked dollars, residual dollars, and File C coverage;
- distinct linked awards with activity, using set unions at parents;
- top recipients and positive/negative flows from File C only;
- child Program Activities whose canonical dollars add exactly to the parent.

Distinct linked-award counts are not additive. Dollar rollups are additive.
Negative events and residuals remain visible throughout the UI.

## Reconciliation gate

For every covered account-year:

`sum(File B activity cents) = pinned GTAS/File A obligated cents`

and, for every account/Program Activity/reporting-period bucket:

`sum(File C cents) + residual cents = File B activity cents`

The machine-readable baseline is under `reference/`. Missing sources,
unavailable-year misrepresentation, incomplete account/Program Activity
partitions, warnings, or a difference outside an explicitly documented
provisional-period tolerance fail CI. Completed snapshots reconcile to exact
cents. USAspending calibration cannot become `ready` until the full DOE run,
offline invariants, site smoke test, and browser release bar are green.

Official references:

- [Custom Account Data](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/accounts.md)
- [Download Status](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/status.md)
- [USAspending sign transformation notes](https://github.com/fedspendingtransparency/usaspending-api/blob/master/data_reformatting.md)
- [USAspending About the Data](https://www.usaspending.gov/data/about-the-data-download.pdf)
