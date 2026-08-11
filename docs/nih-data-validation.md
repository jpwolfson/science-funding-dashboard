# NIH data validation

The NIH pipeline uses layered, fail-closed checks. A green pull means the
committed data are internally complete relative to RePORTER's declared result
universe and remain within independently published NIH aggregate benchmarks.

## Extraction contract

Every administering institute/center and fiscal year is paged twice by
application ID, once ascending and once descending. Publication requires:

1. `meta.total` remains constant on every page;
2. each pass returns exactly `meta.total` unique application IDs;
3. the ascending and descending ID sets are identical;
4. every row matches the requested fiscal year and administering component;
5. every row is a parent record with a non-intramural funding mechanism; and
6. the fiscal-year result set remains below RePORTER's 15,000-row pagination
   ceiling.

The whole fiscal-year snapshot is retried after a transient inconsistency and
the unit is not written after a persistent failure. The unique-count check
specifically detects the cross-page duplicate displacement observed in the NSF
API: a repeated row can no longer silently replace a missing row.

## Store and aggregation contract

`scripts/validate_nih.py` checks all committed NIH stores without contacting an
API by default:

- gzip shards are readable, their rows belong to the named fiscal year, and
  the manifest record count and year list are exact;
- IDs are unique within and across institutes and use the `nih:` namespace;
- leaf dashboard totals equal raw store rows;
- the NIH agency rollup equals the union of all leaf IDs and is marked
  `dataComplete`;
- each institute remains within its configured FY2015-present volume range;
- monthly counts remain under the plausibility cap; and
- published dashboard warnings fail validation unless explicitly allowed.

Each normalized row also persists the RePORTER funding mechanism, activity
code, and award type in the existing `transType` detail. This makes external
benchmark scope reproducible from the committed store. Legacy rows without
that structured detail fail validation and require a full re-pull; the
validator never guesses a mechanism from the dashboard's broader award bin.

The pull itself is non-destructive. An ID omitted by a later full pull remains
in the store and produces a visible warning. Deterministic shard rewrites also
prevent a corrected date from leaving one ID in two fiscal-year files.

## Orthogonal and external reconciliation

With `--live`, the validator issues one multi-year `meta.total` query per
institute and requires exact equality with the committed store. This uses a
different query shape from the per-year pagination and detects partition,
registry, union, and store-loss errors. It is same-source reconciliation, not
an independent source.

Independent reasonableness gates use NIH Data Book reports 400 and 401. Those
reports are produced through NIH's monthly extramural-awards publication path,
while RePORTER refreshes weekly. FY2022-FY2025 award counts must remain within
2% and award dollars within 2% of the pinned values in
`reference/nih_databook_baseline.json`.

This comparison is deliberately like-for-like rather than a check of the
dashboard's complete product total. The benchmark subset contains parent
grants and Other Transactions with non-zero award dollars and excludes R&D
contracts, interagency agreements, intramural projects, and loan-repayment
activity codes. The dashboard and its RePORTER exact-count gate continue to
include contracts and interagency agreements. The machine-readable validation
report publishes both `fiscalYears` (complete product scope) and
`dataBookScopeFiscalYears` (benchmark scope), so the exclusion is auditable.

Sources:

- <https://report.nih.gov/nihdatabook/report/400>
- <https://report.nih.gov/nihdatabook/report/401>
- <https://report.nih.gov/faqs>
- <https://report.nih.gov/exporter-data-dictionary>
- <https://grants.nih.gov/funding/activity-codes>

## Commands

```bash
# No network: shard, manifest, dedup, dashboard, rollup, range, and Data Book checks
python scripts/validate_nih.py

# Release/refresh gate: adds exact multi-year RePORTER count reconciliation
python scripts/validate_nih.py --live
```

The live gate is run after rollup construction for any workflow that refreshes
NIH data. A validation failure makes the rollup job fail and prevents a Pages
deployment.
