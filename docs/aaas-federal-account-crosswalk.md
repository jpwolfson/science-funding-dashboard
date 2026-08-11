# AAAS-to-federal-account crosswalk review

Status: Phase 3.2b research complete on 2026-08-11. The schema-v2/workflow prerequisite is complete; the crosswalk remains reference-only pending reviewed account onboarding.

## Outcome

The dated snapshot preserves **45 AAAS grouping fields and 237 distinct displayed labels** from the public FY 2026 Power BI model. The reviewed crosswalk classifies **185 resolved**, **10 provisional**, and **42 unresolved** labels. Resolved rows are independently usable for reviewed account onboarding; provisional and unresolved rows do not block them.

The federal-account hierarchy is canonical. AAAS labels are preserved verbatim as an alternate framing layer, including source spelling (`Integrated Activites`) and leading spaces on totals. No account registry, ingestion workflow, dashboard schema, or generated dashboard data changed in this phase.

## Source discovery and snapshot

The former AAAS page now returns HTTP 404. Its latest distinct archived HTML capture (2026-05-17) identifies the still-public Power BI report. The public model reports a May 6, 2026 refresh and exposes eight pages, one hidden. A read-only semantic-model query selected the distinct values of every account/grouping column; this avoids relying on screenshots, chart truncation, or manual transcription.

Artifacts:

- `reference/aaas_rd_appropriations_2026-08-11.json` — source URLs, archive identity, Power BI identifiers/timestamps, page metadata, and exact labels.
- `reference/aaas_federal_account_crosswalk.json` — canonical review artifact, evidence catalog, status definitions, account arrays, and rationale per AAAS row.
- `reference/aaas_federal_account_crosswalk.csv` — flattened human-review view; pipe-delimited account/evidence arrays retain many-to-many rows.

The snapshot is intentionally static. It is not a production scraper or an unattended source of registry changes.

## Review rules

`resolved` means that an official USAspending federal-account code/title directly matches the AAAS label, or that AAAS unambiguously nests program lines under a single account field. An explicit AAAS total may resolve to multiple accounts when the displayed scope is exhaustive.

`provisional` records defensible candidates but not enough label-level information for automatic integration. These are Defense program labels that omit service/program-element identity (8 rows), National Center for Health Statistics within CDC scientific services (1), and Project BioShield across changing HHS structures (1).

`unresolved` means either that the source cannot establish an account or that the source row is not an account at all:

- 33 AAAS R&D-character, department, and budget-function aggregates;
- 8 proposed consolidated NIH organizations with no current account;
- the CDC-wide AAAS aggregate, which spans current CDC accounts without an exposed allocation (1).

## Important many-to-many results

- DOD S&T/R&D character totals span Army `021-2040`, Navy `017-1319`, Air Force `057-3600`, Space Force `057-3620`, and Defense-Wide `097-0400`.
- NNSA RDT&E Total spans Weapons Activities `089-0240` and Defense Nuclear Nonproliferation `089-0309`.
- Total NIH spans the 27 current institute/center, ARPA-H, buildings, and Office of the Director accounts displayed by AAAS.
- NSF Total spans R&RA, STEM Education, Agency Operations, and MREFC; NASA Total spans the six displayed mission accounts.
- ARS, NIFA, NIST, NOAA, and Census totals each require explicit multi-account aggregation.
- BEA resolves to `013-1500`; DOT's own organization and budget materials resolve both BTS and ARPA-I to the canonical Research and Technology account `069-1730`.

These arrays are deliberate. Collapsing them to one synthetic account would invert the roadmap rule that federal accounts are canonical.

## Evidence model

Every crosswalk row references the AAAS snapshot evidence plus either the exact federal-account evidence or an official account-definition/tree source explaining why the row remains unresolved. USAspending defines a federal account as the unique combination of Treasury Account Symbol agency identifier and main account code. VA `036-0161` uses the FY 2026 OMB Appendix on GovInfo because it was absent from the current USAspending reference-tree response.

The mapping of an AAAS program line to its parent account is an explicit inference from two observations: the line appears under an account-specific AAAS field, and the official directory confirms that field's federal-account title. The rationale on each row makes this inference inspectable.

## Account onboarding and drift contract

The schema-v2 and registry-driven workflow contract is implemented. Any future account onboarding should:

1. translate, not copy, these reference rows into the schema-v2 account model;
2. retain `aaas_label` and grouping metadata while joining through canonical federal-account codes;
3. keep explicit account arrays for AAAS totals and never synthesize a replacement federal account;
4. accept resolved rows independently of provisional/unresolved review;
5. require review for any changed source row before onboarding or remapping.

Schema v2 does not define a crosswalk integration-state vocabulary, so every row uses `reference_only_pending_account_onboarding`. This state describes the production boundary, not mapping quality; `resolved`, `provisional`, and `unresolved` remain the independent evidence classifications.

The completed technical prerequisite does not authorize automatic registry onboarding, production remapping, workflow changes, or drift enforcement. A future drift check should compare the source page/report identity, model refresh time, 45-field inventory, and exact `aaas_row_key` set against this snapshot. Drift may fail or open a review issue, but it must never auto-onboard a new label, delete a missing row, or silently change a mapping.

## Acceptance review

- Dated AAAS source snapshot: complete.
- Exact AAAS-facing labels preserved: complete.
- Federal-account codes/titles and many-to-many arrays: complete.
- `resolved` / `provisional` / `unresolved` on every row: complete.
- Evidence IDs and rationale on every row: complete.
- Account registry, ingestion, schema, and generated data untouched: verified by repository diff.
- Account onboarding and drift automation: not implemented; each remains a separate reviewed change.
