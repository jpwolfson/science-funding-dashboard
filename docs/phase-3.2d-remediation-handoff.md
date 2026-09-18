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
- **Rule refinements from data (2026-09-17, after W3's first offline
  rebuild tripped its own validator on five account-years):**
  (1) a sub-half period is `notReported` only when a later period in the
  FY recovers to ≥ 0.5 × the last reported count, or when no later period
  exists yet (provisional); a sustained drop is a restructuring and becomes
  the new baseline — `commerce/census-current-surveys` FY2020 rows
  101 → 44 at P07 and stays, FY total reconciles. (2) Backward rule: rows
  below 0.25 × the FY's final accepted period's rows are `notReported`
  (final period exempt) — `commerce/noaa-orf` FY2024 has 5–10 rows for
  P04–P08 against 551 at P12. (3) The >50 % cumulative-drop check applies
  only above 100,000,000 cents previous cumulative and its curated
  explanation lives in the baseline file (`fiscalYears.<FY>.periodNotes`),
  not in generated provenance — `usda/nifa-integrated-activities` FY2022
  fired on a $24k base. `commerce/nist-its` FY2025 P11 and `dhs/cisa-rd`
  FY2023 P04 have full row counts with collapsed dollars: no row rule can
  classify them; they carry provisional notes until the CI re-pull.
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
| 2026-09-17 ~16:10 UTC | PR #66 merged to `main` (`6f4677f`) | W4 DoD interpretationNote, award-root coverage line, obligation subtitle, sentinel card language, sentinel height fix (65,219 → 12,488 px, clipped-tail defect reproduced in before-screenshot); registry 380/380, fast 7/7, rendered 4/4 | merged |
| 2026-09-17 15:36–15:51 UTC | run 35240994598 `pull-nih` jobs | First units: csr, cit OK; **fic FAILED** (40 moves vs threshold 20.0 on 4,552) and **nhgri FAILED** (57 vs 20.0 on 6,969) — the drift accumulated under the old non-overwriting adapter, measured by the steady-state churn rule on the ledger-initializing pull. Decision: the first source-current pull per unit initializes the ledger and is exempt (self-limiting: the committed ledger file is the marker); per-field diagnostics added. Worker W7, then re-dispatch of the failed units. | in progress |
| 2026-09-17 16:30 UTC | PR #67 merged (`8b27095`); second `Update data` dispatch on `main` (units=nih, full_refresh=true), pending behind run 35240994598 | W7 first-pull exemption + per-field move diagnostics; the second run re-pulls all 28 ICs under the exemption and rebuilds rollups with `validate_nih.py --live` | pending |
| 2026-09-17 15:33–16:50 UTC | run 35240994598 completed (failure) | 17 of 28 ICs failed on the churn threshold (moves ≈ 0.9–1.2 % of store: NCI 1,143/95,928, NHLBI 659/70,461, NEI 202/19,656 …); the 11 from NIEHS onward ran after W7 merged (jobs sync to branch tip) and committed under the exemption. Rollup: live decomposition OK for all 28 ICs (gaps 0–3 within tolerance) but `nih/ninds/ninds totalAwards=53141 vs aggregated 53140`: a returned id was counted by the leaf but its ledger flip was never committed (job staged only `data/<unit>`). Deploy skipped. | failure, diagnosed |
| 2026-09-17 17:05 UTC | run 35246439818 cancelled; PR #70 merged | W8: `pull-nih` commit step stages `reference/nih_reporter_exclusions.json`; the in-flight run used the old workflow definition and would have failed the same way | merged |
| 2026-09-17 17:08 UTC | third `Update data` dispatch on `main` (units=nih, full_refresh=true) | Full NIH pull under W7 exemption + W8 ledger commit; expected: all 28 ICs green, ledgers initialized, rollup `--live` green, deploy | running |
| 2026-09-17 15:33 UTC | `Update data` dispatched (run 35240994598) on `main` (units=nih, full_refresh=true) | First full NIH pull under the new contract: source-current fields, changes ledgers, exclusions ledger returns, `validate_nih.py --live` bounded gap | running |
| 2026-09-17 17:14 UTC | PR #68 merged to `main` (`167841c`) | W3 File B acceptance (165 account-years classified; 24 material), span reconciliation, pin-advancement guard, periodNotes; fast 6/7 on the merge commit (the one red check is main's own transient NIH state being fixed by the running pull), rendered 4/4, 343 unit tests | merged |
| 2026-09-17 17:16 UTC | `Update obligation ledger` dispatched on `main` (mode=weekly, all 53 accounts, ~28 h) | Sequencing decision: the reconcile freshness gate checks every account's current FY (last accepted snapshot 2026-08-24, 24 days > 10-day SLA), so a historical-only custom re-pull cannot commit until the weekly run restores freshness. This run also lands FY2026 P10 for all accounts (retires the P10 hatches) under the W3 rule and guards. Custom FY2025/2024/2023/2022 re-pulls are chained after it. | running |
| 2026-09-17 17:20 UTC | `Update funding-action sentinel` dispatched on `main` | First sentinel run under the decoupled gate (W2); sources were 23 days stale against the 10-day SLA | running |
| 2026-09-17 17:16 UTC | sentinel run 35251254148 | Built, validated, rendered green under the decoupled gate; failed only at `git push` (non-fast-forward: NIH leaf commits landed on main meanwhile). Single-push commit steps in the sentinel and obligation reconcile had no rebase retry. | failure, diagnosed |
| 2026-09-17 17:32 UTC | weekly run 35251206571 cancelled; PR #71 merged (`f5a9106`); weekly obligation run and sentinel run re-dispatched on `main` | W9: both commit steps replay on the branch tip up to five times (`pull --rebase -X theirs`), as the award workflow already did | running |
| 2026-09-17 17:32–17:37 UTC | sentinel run 35253304028 | **SUCCESS** — first accepted sentinel snapshot since 2026-08-25, under the decoupled gate (W2) and the retry push (W9); committed to `main` | green |
| 2026-09-17 17:05–18:30 UTC | run 35250546983 (third NIH full pull) | **SUCCESS**: 28/28 ICs pulled under the ledger-initializing exemption, 28 `changes.csv.gz` ledgers created, 4 exclusions flipped to `returned` and committed (W8), rollup rebuilt, `validate_nih.py --live` green, Pages deployed. Root `totalAwards` 860,636 = `storeIdCount`; NIH 721,062 = leaf union; zero NIH warnings, empty `dataQualityNotes`. | green |
| 2026-09-17 17:37 and 18:30 UTC | `Verify main` runs 35253809178 and 35259203139 (workflow_run after the sentinel and NIH refreshes) | `verify.py --tier fast` **PASS on `main`** twice, on the committed data tree — the HIGH-1 condition (fast tier red on main) is closed in CI, not only locally. Root warnings are the four pre-existing NSF cross-division dedup notes; the stale NSF "not returned by this full re-pull" warnings are gone. | green |
| 2026-09-17 22:25 UTC | run 35253300879 progress | 18/106 account-year pulls complete, 0 failed, ~14 min/job ⇒ reconcile expected ~19:00 UTC 2026-09-18. Closeout branch `claude/rem-closeout` pushed (manifest deleted, ci.yml lint line dropped, manifest test → absence test); PR opens only after the weekly run commits. | running |
| 2026-09-17 22:40 UTC | local `validate_obligations.py` on current `main` with the manifest deleted | HIGH-3 measured: **1 error** remains (`dhs/cwmd-rd FY2026: latest P09 has no same-period GTAS pin` — pin at P10, store at P09); the six `source-label-unavailable-*` identities no longer error (W3 rebuild gave them store data). The running weekly refresh pulls CWMD through P10 and closes it. | measured |
| 2026-09-18 02:35 UTC | run 35253300879 progress | 35/106 pulls complete, 0 failed; reconcile expected ~20:00 UTC 2026-09-18 | running |
| 2026-09-18 09:55 UTC | run 35253300879 progress | 64/106 pulls complete, 0 failed; reconcile expected ~20:30 UTC | running |
| 2026-09-18 21:02 UTC | run 35253300879 reconcile | 106/106 pulls green (27.3 h), reconcile merged 53 accounts, then `validate_obligations.py` **failed with 9 errors on 2 accounts** (`doe/sc`, `doe/fossil-energy` FY2026 P10): "has 0 File B residual rows" for 7 (P10, PA) buckets and "latest P10 has no same-period GTAS pin". Diagnosis: P10 classified `notReported` (provisional) — W3's state has File C events, no residual, pin held at P09 — and two validator checks were never aligned with that state (pin check uses latest stored, not latest reported, period; residual check does not skip notReported buckets). Worker W10; then a full weekly re-dispatch (the atomic reconcile committed nothing, so the freshness gate still spans all 53 accounts). | failure, diagnosed |

## Finding closure evidence (filled at closeout)

| Finding | Closed by | Evidence |
|---|---|---|
| HIGH-1 | W1, W5 | |
| HIGH-2 | W2, W5 | |
| HIGH-3 | W3 | |
| HIGH-4 | W4 | |
| HIGH-5 | W3 | |
