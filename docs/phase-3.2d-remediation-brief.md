# Phase 3.2d remediation brief (owner-approved 2026-09-17)

Origin: `docs/reviews/2026-09-15-phase-3.2d-independent-review.md` (Stage 1
of the independent review). The owner chose option A: repair the operating
state first, re-review, then run the display-improvements batch (Stage 2,
`docs/display-improvements-ledger.md`). Stage 2 stays held until every gate
below is green.

This brief is addressed to ONE coordinating agent in a fresh session. It
orchestrates Sonnet workers for mechanical breadth, owns every merge, and
runs long pulls on CI (never in-session). Standing git authority and the
decision layers in `CLAUDE.md` apply unchanged.

## Owner decisions (verbatim outcomes, 2026-09-17)

1. **Sequencing:** A — repairs first, then Stage 2.
2. **Not-yet-reported File B period display:** option (a) — omit the period
   from the activity chart, hold the last reported value in the cumulative
   step with a hollow marker, and show "not reported at pull" in the table
   row. Never publish the derived swing.
3. **DoD disclosure (approved text, render verbatim):**
   > Award-level detail is sparse for Department of Defense accounts.
   > Classified, intramural, interagency, and contract-heavy activity is not
   > reported with equivalent public award detail in File C. A low File C
   > share is an attribution limit, not evidence of missing or unobligated
   > dollars; the File B account total is complete.
   Rendered on every DoD account page, every DoD Program Activity page, and
   as a note on the DoD row of the obligations landing table.
4. **Award-root framing (approved text):**
   - Coverage line on the award root: "Award ledger: NIH and NSF, 87 units.
     Obligation ledger: 53 registered federal accounts across 13 agencies."
     (Derive the counts from `config/orgs.json` and
     `config/obligation_accounts.json`; the wording is fixed.)
   - Subtitle on the obligations landing and on the root obligation tile:
     "Obligations from 53 registered science-related federal accounts,
     including defense RDT&E." (count derived, wording fixed).
5. **Sentinel-facing language (approved):**
   - Keep the gross-negative detection rule. Card header shows gross
     negative and net side by side; add the state line "net activity in
     this period was positive" when net > 0.
   - Replace "affected award IDs" with "award IDs with negative entries".
   - Drop "(not overdue)"; show age only.
6. **NIH award-ledger semantics:** source-current dates (the latest RePORTER
   notice date wins), with a generated move ledger for auditability;
   id-level retention invariant with a churn threshold; soft-delete
   exclusions; live `meta.total` as a bounded, explained gap. Methodology
   line (approved): "counts as of the pull date; NIH revises award notice
   dates."

Nothing else in this brief needs the owner. Engineering choices are the
coordinator's; record them in the handoff, do not ask.

## Workstreams

### W1 — NIH award ledger: source-current semantics, id-level invariants

Files: `adapters/nih_reporter.py`, `adapters/common.py`
(`write_dashboard` shrink logic, `_allowedMonthlyShrink`),
`scripts/validate_nih.py`, `scripts/rollup.py`, `scripts/reaggregate.py`,
`reference/nih_reporter_retractions.json` and the two
`nih_reporter_*_evidence_*.json` files, `tests/test_nih_reporter.py`,
`tests/test_nih_validation.py`, `docs/nih-data-validation.md`, site notes.

Contract to implement:
- A stored award id never disappears from the store. Reviewed exclusions are
  a **soft delete**: a committed exclusions ledger (`id`, `unit`,
  `classification`, `reason`, `decidedOn`, `status` ∈ {excluded, returned})
  marks records that aggregation skips. The store retains them. If the live
  source re-emits an excluded id, the pull flips `status` to `returned`,
  re-includes it, logs a NOTICE, and does **not** fail. Migrate the existing
  retraction ledger and evidence pins into this form; retire the
  exact-field evidence tests (they pinned the source's mutable fields).
- **Source-current fields.** An incremental or full pull overwrites a stored
  record's date, amount, title, and type with the live values. Every field
  change is appended to a generated, committed move ledger per unit
  (`data/nih/<ic>/<ic>/changes.csv.gz` or equivalent: pullDate, id, field,
  old, new). Deterministic, append-only, small.
- **Invariants (replace the month-count shrink rule):**
  1. missing-uncovered ids (stored, not returned by a full pull, not in the
     exclusions ledger) are retained and reported; they never fail a pull
     but they do appear as a published data-quality note.
  2. moves + returns per unit per pull ≤ max(20, 0.1 % of the unit's store)
     — above that is the pagination-bug signature (regime rule 4) and the
     pull fails closed. Record the constant in `docs/verification-regime.md`.
  3. a re-dated record whose new date falls outside the record's own
     `fiscal_year` from the source is a source anomaly: retain, ledger it,
     count it under the source-current date, and report it.
  4. the existing totals invariants are unchanged (`totalAwards == Σ
     fiscalYears == Σ monthly`, cumulative endpoints exact, root == Σ
     children).
- **Live check** (`validate_nih.py --live`): `meta.total − (store − excluded
  − retained-missing)` must be within max(3, 0.01 %) per IC and the gap is
  printed with its decomposition; equality is not required.
- Month counts are derived and may move. The award root and NIH pages carry
  the approved methodology line.
- Regenerate all NIH leaves with a full pull on CI (day-of-month gate
  bypassed via dispatch/trigger file), then rollups. `validate_nih.py` must
  be green with zero errors on the result; warnings are gone by
  construction because the shrink rule no longer exists.

### W2 — Decouple publication gates

- `update-sentinel.yml`: run only `tests/test_funding_sentinel*.py`,
  `tests/test_funding_source_adapters.py`, `tests/test_site_contract.py`,
  and `validate_funding_sentinel.py` before rendering; never the NIH suite.
- `update-obligations.yml` reconcile job: run `validate_obligations.py`,
  the obligation unit tests, `validate_award_invariants.py`, and the
  rendered matrix; not `validate_nih.py` and not the NIH unit tests.
- `update-data.yml` rollup job keeps `validate_nih.py` (its own ledger).
- `ci.yml` `Test` still ignores `data/**`; add a scheduled or post-refresh
  `verify.py --tier fast` on `main` that files an issue on failure (the
  validation contract in `CLAUDE.md` already calls for auto-filed issues).
  Keep it non-blocking for deploys.

### W3 — File B snapshot acceptance and the not-reported state

Files: `adapters/usaspending_obligations.py`, `adapters/obligation_common.py`
(`aggregate`), `scripts/validate_obligations.py`, `site/index.html`
(`obligationCumulativeChart`, `obligationPeriodsChart`, tables),
`docs/obligation-ledger.md`, `docs/verification-regime.md`, tests.

- **Re-pull first.** On CI, re-request File B (and File C) for the 13
  affected account-years: all six DoD accounts FY2025 (P11), NIST ITS
  FY2025 (P11), NOAA ORF and NOAA PAC FY2024 (P02–P11), Air Force RDT&E
  FY2024 (P05, and P11's 5,460→2,956 spike), DHS CISA FY2023 (P04), USDA
  NIFA Integrated FY2022 (P03). If the source now returns full snapshots,
  accept the replacements through ordinary provenance lineage and the
  defect is closed for those periods.
- **Acceptance rule (universal, registry-free):** a File B period snapshot
  whose row count is zero, or below half the previous accepted period's row
  count in the same fiscal year, is accepted as `notReported` — its bytes
  and provenance are kept, but it contributes no cumulative value and no
  derived activity. The next reported period's activity is differenced
  against the last *reported* period. A `notReported` P12 is a hard error
  (the FY pin cannot reconcile). Add a `validate_obligations.py` check that
  flags any accepted period whose cumulative File B drops by more than 50 %
  from the previous reported period as a warning requiring a provenance
  note (real large deobligations exist; they must be explained, not
  hidden).
- **Display (owner decision 2):** period chart omits `notReported`
  periods; cumulative step holds the last reported value and draws a hollow
  marker at the not-reported period; the table row reads "not reported at
  pull". Chart geometry change ⇒ `rendered` plus before/after screenshots.
- Land or retire P10: either the pending nine-account P10 retry completes
  on CI and `reference/obligation_retry_recovery.json` is removed, or the
  six empty `source-label-unavailable-*` identities and the DHS P10 pin are
  reverted so `validate_obligations.py` is green with the hatches disabled.
  Either way the hatches must not be exercised on `main` at closeout.

### W4 — DoD disclosure and framing text (owner decisions 3–5)

- Add a registry-declared, agency-neutral field for an account-level
  interpretation note (`config/obligation_accounts.json` entry:
  `interpretationNote`), rendered by the site on account and PA pages and
  as a row note on the landing table. Populate it for the six DoD accounts
  with the approved text. No agency conditional in the site or verifiers:
  the field is the specialization surface. Add it to the specialization
  schema table in `docs/verification-regime.md`.
- Award-root coverage line and obligation subtitle per decision 4.
- Sentinel card changes per decision 5 (`site/index.html` sentinel
  functions; `tests/test_site_contract.py`); fix the truncated final card
  and the blank tail (reproduce with a full-page screenshot at 1100 px;
  the smoke matrix must gain a layout assertion that the last episode card
  is fully rendered and the notes section follows it); add an anchor or
  filter that surfaces the source-confirmed episodes.

### W5 — Rebuild, soak, close

- Rebuild NIH and root rollups after W1; `verify.py --tier fast` and
  `--tier rendered` green on `main` with the hatches disabled.
- Soak: one scheduled green run each of `Update data`, `Update obligation
  ledger` (53 accounts), and `Update funding-action sentinel`. Schedule
  check-ins with `send_later`; never poll.
- Phase history: add a "Post-completion review and remediation" entry
  citing the review file, the owner decisions above, and the measured
  outcomes. CLAUDE.md: replace the remediation status line once.
- Then a re-run of the review's mechanical tiers and a scoped reader
  review of touched pages; only then release Stage 2 from hold.

## Release bar

`registry`, `fast`, `rendered` green on `main` with
`reference/obligation_retry_recovery.json` absent; zero validator errors;
three green scheduled runs; every owner-approved string present verbatim in
the rendered pages (add contract tests for each); before/after screenshots
for every chart whose geometry changed; the review's HIGH-1..5 each closed
with evidence in the handoff.
