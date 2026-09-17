# Phase 3.2d remediation — coordinator handoff

Coordinator session started 2026-09-17 against `main` at `b06773a`.
Instruction: `docs/phase-3.2d-remediation-brief.md` (owner decisions 1–6 are
settled there). Findings being closed: HIGH-1..5 in
`docs/reviews/2026-09-15-phase-3.2d-independent-review.md`. This file is the
running record: wave plan, engineering decisions, CI runs, and per-finding
evidence. It is updated as waves complete.

## Wave plan

Wall-clock target: every code PR merged to `main` before the next scheduled
runs (`Update data` Mon 2026-09-21 09:13 UTC, `Update obligation ledger`
Mon 10:37 UTC, `Update funding-action sentinel` Tue 2026-09-22 12:17 UTC),
which are the W5 soak. Missing that window slips the soak one week.

| Wave | What | Runs where | Parallel with |
|---|---|---|---|
| 0 | This plan; CI-log triage of the four failed scheduled runs (34141166514, 34865108437, 34868893350, 34998223996) to size soak risk | Sonnet agent, read-only | wave 1 |
| 1 | W1, W2, W3, W4 implemented by four Sonnet workers in separate worktrees on `claude/rem-w1-nih`, `claude/rem-w2-gates`, `claude/rem-w3-fileb`, `claude/rem-w4-framing`; each ends in an open PR carrying `verify.py --tier fast` and `--tier rendered` JSON (W3/W4: before/after screenshots too) | branches | all four |
| 2a | Merge W2 first (small; it unblocks obligation reconcile on branches from the NIH gate) | `main` | — |
| 2b | W1 branch: full NIH re-pull via `.github/triggers/update.json` (`units: nih`, `full_refresh: true`) so the PR carries code + regenerated leaves + rollups + green `validate_nih.py --live` | CI on `claude/rem-w1-nih` | 2c |
| 2c | W3 branch (rebased on post-W2 main): re-pull of the affected account-years in `custom` mode via `.github/triggers/update-obligations.json`, one trigger commit per FY (2025: six DoD + NIST ITS; 2024: NOAA ORF, NOAA PAC, Air Force RDT&E; 2023: DHS CISA; 2022: USDA NIFA Integrated), plus any account-year the retroactive acceptance rule flags | CI on `claude/rem-w3-fileb` | 2b |
| 3 | Serial merges with revalidation between each: W1 → W3 → W4. Then dispatch `Update obligation ledger` (weekly mode) on `main` to land P10/P11 for all 53 accounts; then a closeout PR removing `reference/obligation_retry_recovery.json`; then dispatch `Update funding-action sentinel` on `main` | `main` + CI | — |
| 4 | Soak: the three scheduled runs above, green, checked via `send_later`. Phase history + CLAUDE.md entry. Re-run `registry`/`fast`/`rendered`/`screens`; scoped reader review of touched pages by a fresh agent. Release Stage 2 hold | `main` | — |

Concurrency: `update-obligations.yml` serializes per ref (one running, one
pending), so obligation runs on a branch are chained by check-in, not queued.
`update-data.yml` and `update-obligations.yml` on different branches run in
parallel.

## Engineering decisions (coordinator's; recorded, not escalated)

### W1 — NIH source-current ledger

- **Exclusions ledger** `reference/nih_reporter_exclusions.json` (schema 1):
  records `{id, unit, classification, reason, decidedOn, status}` with
  `status ∈ {excluded, returned}`. Migrated from
  `reference/nih_reporter_retractions.json` (every active record →
  `excluded`, `decidedOn` = that ledger's `observedAt`). The two evidence
  files stay as dated evidence; the tests pinning their mutable source
  fields are retired. Records already removed from the store before this
  contract are ledgered but not re-synthesized; from this contract on, no
  stored id is ever dropped.
- **Soft delete**: shards keep excluded rows; aggregation (adapter,
  `rollup.py`, `reaggregate.py`) skips ids whose ledger status is
  `excluded`. A live re-emit flips the status to `returned`, re-includes the
  record, logs `NOTICE`, never fails.
- **Move ledger** `data/nih/<ic>/<ic>/changes.csv.gz`, columns
  `pullDate,id,field,old,new`, append-only, sorted `(pullDate,id,field)`.
  Fields tracked: `date`, `amount`, `title`, `type`.
- **Shrink rule replaced.** `_allowedMonthlyShrink` and the month-shrink
  warning leave `adapters/common.py`. The universal replacement in
  `write_dashboard` is an id-count rule: the stored id total may never
  decrease (a warning, as before, since NSF shares this path). Month counts
  are derived and may move.
- **Invariants** (constants in `docs/verification-regime.md`):
  retained-missing ids are a published `dataQualityNotes` entry, never a
  failure; `moves + returns ≤ max(20, 0.1 % of the unit store)` per pull
  else fail closed; a source-current date outside the record's own
  `fiscal_year` is retained, ledgered, counted under the new date, and
  noted; totals invariants unchanged.
- **Live check** tolerance `max(3, 0.01 %)` per IC with the gap decomposed
  (`store − excluded − retainedMissing` vs `meta.total`).
- **Dashboard fields** (award-ledger `dashboard.json`): `dataQualityNotes:
  [string]` (rendered as notes, not warnings) and `methodologyNote` with the
  approved text, emitted on every NIH node and the award root. W4 renders
  them; W1 emits them.

### W3 — File B snapshot acceptance

- Per-period File B row counts already live in each
  `events/FY####.provenance.json` (`downloads[].statusRowCount`), so the
  rule is applied at **rebuild** time from provenance as well as at pull
  time; existing stores are classified without a re-pull, and the CI
  re-pull is a chance to replace the empty snapshots, not a prerequisite.
- Rule: rows == 0, or rows < 0.5 × the previous *reported* period's rows in
  the same FY ⇒ `notReported`. P12 `notReported` ⇒ error.
- File C is downloaded once per FY with its own `submission_period`, so a
  not-reported File B period still has File C events. Reconciliation is
  therefore over **reporting spans**: File B activity for a reported period
  = its snapshot minus the last reported snapshot; the residual booked in
  that period = that delta − Σ File C over the span (the not-reported
  periods it absorbs plus itself). `File C + residual = File B` holds per
  span; the not-reported period has File C events, no File B activity, no
  residual. The next reported row is labeled as covering the span.
- Dashboard shape: each period row carries `status` (`reported` /
  `notReported`); cumulative points at a not-reported period carry the held
  value plus `held: true`; period activity is `null` there. Site: omitted
  from the period chart, hollow marker on the cumulative step, table row
  "not reported at pull".
- Validator additions: the >50 % drop-between-reported-periods warning
  requiring a `largeChangeNote` in that FY's provenance; the P12 rule.
- **P10 hatches: retire by landing.** The six `source-label-unavailable-*`
  identities are needed for any pull that reaches P10 to succeed (attempt 1
  of run 34141166514 failed on exactly those PARKs), so they stay; a fresh
  weekly-mode run on `main` after W3 merges lands P10/P11 for all 53
  accounts and gives them store data. `reference/obligation_retry_recovery.json`
  is then deleted in the closeout PR and `validate_obligations.py` must be
  green with no hatch. The failed-job retry of run 34141166514 is not used.

### W4 — framing and DoD note

- `interpretationNote` is an optional string on a registry entry; the
  registry tier validates its type; `rollup_obligations.py` copies it into
  the account and PA `dashboard.json`; the site renders it wherever present
  and on the landing table row. No agency conditional anywhere.
- The award-root coverage line and the obligation subtitle derive their
  counts in the browser from `index.json` and the obligations root
  `dashboard.json`; contract tests compute the same counts from
  `config/orgs.json` and `config/obligation_accounts.json` and assert the
  verbatim strings.

### Wave 0 triage outcomes (2026-09-17) and resulting additions

- The 2026-09-14 scheduled obligation run was not stuck: all 106
  account-year pulls succeeded serially in 28.4 h (median job 16 min), and
  the reconcile failed only at the fast tier — the NIH defect (HIGH-1) plus
  53 failures in `test_obligations_other_civilian` because every agency
  test file pins the current FY's partial `asOfPeriod`/cents literally.
  Any weekly advance therefore fails the gate. **Added W6** (branch
  `claude/rem-w6-moving-pins`): current-FY partial rows are asserted
  structurally; historical complete pins stay literal.
- The same reconcile advanced `ed/ies` FY2026 to `asOfPeriod 10,
  obligationsCents 0`: the empty-snapshot defect (HIGH-5) reaches the
  partial-pin update path too. **W3 addition:** a pin may only advance to
  a period whose File B snapshot is `reported`; a zero File A total after a
  positive one is not pinned.
- Run 34141166514 (09-07) failed on `ed/ies` FY2018 P12 `award_financial`
  in all 7 attempts with the adapter's own 2 h download cap. The weekly
  rotation (`isocalendar week % len(historical)`) selects FY2018 for
  `ed/ies` in ISO weeks 37 and 46 (next: 2026-11-09), not in the soak
  window (09-21 → FY2020). Recorded as an operational follow-up, not a
  remediation item.
- Sizing: a 12-account-year custom re-pull ≈ 3.2 h; a weekly run ≈ 28 h.
  A full NIH re-pull has no measured precedent; the 10-unit targeted
  repair took 43 min.
- Test on PR #62 (run 35234915388) fails the fast tier with the HIGH-1
  signature, so every PR's CI is red on `validate-nih`/`unit-tests` until
  W1 merges. Merge order becomes W2 → W6 → W1 → W3 → W4, with W1's PR
  carrying the offline reaggregation so the fast tier is green on `main`
  before the CI full re-pull is dispatched there.

## CI runs (filled as they happen)

| When | Workflow / ref | Purpose | Result |
|---|---|---|---|
| 2026-09-17 15:05 UTC | PR #63 merged to `main` (`98f9990`) | W2 gate decoupling; fast 5/7 (HIGH-1 signature only), rendered 4/4 | merged |
| 2026-09-17 15:40 UTC | PR #64 merged to `main` (`f22750e`) | W6 moving-pin tests: 109 obligation tests green, scratch P09→P10 bump proof, registry 374/374 | merged |
| 2026-09-17 15:32 UTC | PR #65 merged to `main` (`0e00cb5`) | W1 NIH source-current ledger + offline reaggregation; fast 7/7, rendered 4/4; root == leaf union == 721,056 | merged |
| 2026-09-17 15:33 UTC | `Update data` dispatched (run 35240994598) on `main` (units=nih, full_refresh=true) | First full NIH pull under the new contract: source-current fields, changes ledgers, exclusions ledger returns, `validate_nih.py --live` bounded gap | running |

## Finding closure evidence (filled at closeout)

| Finding | Closed by | Evidence |
|---|---|---|
| HIGH-1 | W1, W5 | |
| HIGH-2 | W2, W5 | |
| HIGH-3 | W3 | |
| HIGH-4 | W4 | |
| HIGH-5 | W3 | |
