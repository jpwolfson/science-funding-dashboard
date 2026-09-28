# Phase 3.2e — NIH obligation accounts: running record

Status: in progress. Owner approval 2026-09-23 (option A of the scope memo):
onboard the 27 NIH federal accounts that Phase 3.2d deliberately left out
(`docs/phase-history.md`, Phase 3.2d entry) into the appropriations
obligation ledger. This supersedes the NIH descoping notes in
`docs/phase-3.2d-agency-roadmap.md` and `docs/phase-3.2d-execution-protocol.md`.

Cold-start rule: read `CLAUDE.md`, then this file top to bottom. The
"Next action" line is always current.

## Scope

27 resolved AAAS crosswalk accounts (all `resolved`; titles from
`reference/aaas_federal_account_crosswalk.json`):

| Account | Unit |
|---|---|
| `075-0807` | National Library of Medicine |
| `075-0819` | Fogarty International Center |
| `075-0837` | Advanced Research Projects Agency for Health (ARPA-H) |
| `075-0838` | NIH Buildings and Facilities |
| `075-0843` | National Institute on Aging |
| `075-0844` | NICHD |
| `075-0846` | NIH Office of the Director |
| `075-0849` | National Cancer Institute |
| `075-0851` | NIGMS |
| `075-0862` | NIEHS |
| `075-0872` | NHLBI |
| `075-0873` | NIDCR |
| `075-0875` | NCATS |
| `075-0884` | NIDDK |
| `075-0885` | NIAID |
| `075-0886` | NINDS |
| `075-0887` | National Eye Institute |
| `075-0888` | NIAMS |
| `075-0889` | NINR |
| `075-0890` | NIDCD |
| `075-0891` | NHGRI |
| `075-0892` | NIMH |
| `075-0893` | NIDA |
| `075-0894` | NIAAA |
| `075-0896` | NCCIH |
| `075-0897` | NIMHD |
| `075-0898` | NIBIB |

Measure semantics (decision layer a): NIH obligations are an account-level
measure, separate from and not additive to the NIH award ledger. No public
text reconciles the two; an internal cross-check is permitted.

## Step 1 — CI sizing (NCI `075-0849`)

Probe: `scripts/size_obligation_account.py` via
`.github/workflows/size-obligations.yml`, triggered by
`.github/triggers/size-obligations.json` on `claude/phase-3.2e-nih-sizing`.
It issues the production File B and File C requests (same columns as
`scripts/pull_obligation_account.py`) for FY2025 P12 and FY2026 P10, with a
5.5 h status cap instead of the adapter's 2 h, and commits
`reference/sizing/075-0849-FY*.json`.

Comparison point: the largest File C downloads already handled are USDA ARS
FY2024 (537,177 rows) and NSF R&RA FY2023 (520,830 rows).

Capacity baseline (scheduled weekly run 35626367929, 53 accounts): 106
serialized pull jobs, all green; median 16.7 min, p90 18.3, max 26.8 (DoD
Air Force FY2020); pulls sum 29.2 h; reconcile 23.5 min; wall clock 29.7 h
(Mon 16:33 → Tue 22:17 UTC). Job time is nearly flat across accounts of very
different size, so it is dominated by the fixed per-request cost (up to 11
File B period requests + 1 File C, each with a 20 s cooldown and a
generator queue wait), not by File C volume. Naive extrapolation: 27 NIH
accounts × 2 jobs × ~17 min ≈ +15 h/week, so ~45 h wall clock — past the
Tue ~23:00 UTC merge-quiet window. That holds only if NCI sizing confirms
NIH File C generation stays inside the flat regime.

Result: run
[`35925926839`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/35925926839),
both jobs green (reports: `reference/sizing/075-0849-FY2025P12.json`,
`reference/sizing/075-0849-FY2026P10.json`):

| NCI `075-0849` | FY2025 P12 | FY2026 P10 |
|---|---:|---:|
| File C generate + retrieve | 328 s | 279 s |
| File C ZIP | 72.2 MB | 57.4 MB |
| File C rows (assistance / contracts / unlinked) | 130,115 (112,280 / 17,294 / 541) | 90,479 (80,848 / 9,039 / 592) |
| Nonzero File C rows | 12,981 | 7,898 |
| Distinct awards / normalized events (est.) | 10,189 / 12,904 | 6,667 / 7,840 |
| Peak RSS (parse + shape) | 554 MB | 437 MB |
| File B P-final rows / generate | 58 / 21 s | 48 / 16 s |
| File B total (net obligations) | $7,423,092,042.18 | $4,644,703,508.38 |
| File C total | $5,593,663,121.91 (75.4% of B) | $3,060,834,916.60 (65.9% of B) |

Program Activities: FY2025 PAC/PAN `0001` "NATIONAL CANCER INSTITUTE
(0849)", `0801` "NIH REIMBURSABLE - OTHER", `0000` UNKNOWN/OTHER (zero
cents); FY2026 PARK-only, `5ZC7KSR3EPF` plus the `0000` zero row.

**Decision (engineering, recorded):** NIH's largest account is ~¼ of the
File C rows already handled routinely (NSF R&RA FY2023 520,830; USDA ARS
FY2024 537,177) and generates in ~5 min, far inside the adapter's 2 h cap.
The earlier cap hits (NIFA FY2019, IES FY2018) were source-queue stalls on
small accounts, not volume; W11/W13 already cover them. Therefore:
no File C partitioning, no special rotation, and the standard weekly plan
(current FY + one rotating historical FY per account). Cost: +54 serialized
jobs × ~16 min ≈ +14–15 h, taking the weekly run from ~30 h to ~44–45 h
(Mon 10:37 → ~Wed 07:00 UTC). Actions minutes on this public repo are not
billed, so this is not recurring spend. The operational effect is a longer
merge-quiet window; that is recorded in `CLAUDE.md` at closeout. Reconcile
(23.5 min today, 60 min timeout) grows with account count; its timeout is
raised in the registration PR.

## Step 2 — registry discovery (27 accounts)

`scripts/discover_obligation_program_activities.py` (same workflow, three
serial chunks) records per account × FY2017–FY2026: File B PA identities at
the final period, the federal-account record (incl.
`total_obligated_amount`, the pull's File A check), the first non-empty
period of the first active FY, and the official per-account PARK list.
Output: `reference/sizing/nih_registry_discovery_{1,2,3}.json`. These feed
registry entries and baseline scaffolds (NSF precedent: replaceable
`partial` rows without `obligationsCents`; the backfill pins them). The
backfill remains the fail-closed alias-drift gate.

### Discovery results

Chunk 1 (run 35929645412, ~2 h 20 min for 9 accounts) and chunk 2: zero
errors; the account record's `total_obligated_amount` equals the File B
final-period total to the cent for every account-year (FY2017–FY2025 P12,
FY2026 P10). All accounts first active FY2017 P06. Uniform PA structure:
one institute PAC (`00xx`, PAN "<INSTITUTE> (08xx)"), `0801` NIH
REIMBURSABLE - OTHER, `0000` UNKNOWN/OTHER and/or ZERO OBLIGATION (zero
cents), and in FY2026 one institute PARK plus, for some accounts, PARK
`0000` (zero).

Exception: NIDDK `075-0884` also reports PAC `0031` TYPE 1 DIABETES (the
Special Diabetes Program, mandatory funding) every year FY2017–FY2025
($141.3M FY2017 … $1.7M FY2025). FY2026 has no separate PARK; it is inside
the NIDDK PARK `5ZC7KSR3EPY`. It is registered as its own historical PA.
**Reader-review watch item:** its PA series ends at FY2025 because FY2026
reporting folds it into the institute PARK. A reader could take that as the
program ending or being defunded. The account total is unaffected.

### Registry authoring

Sonnet worker, branch `claude/phase-3.2e-nih` (generator
`reference/sizing/build_nih_registry.py`, idempotent; re-run as chunks
land). Coordinator decision: baselines carry reviewed File A/GTAS pins from
the discovery account records (AHRQ/DoD precedent). The NSF pinless
scaffold predates `e4fac31b` (2026-08-14), which made
`baseline_pin_problems` require `obligationsCents`, and `pull()` checks every
pin before downloading, so pinless scaffolds would fail every job. With 9
accounts: registry 443/443; `validate_obligations --allow-empty` clean; fast
6/7, failing only the intentional `test_site_contract` 80-account pin until
all 27 are registered.

### Backfill plan

26 accounts × FY2017–FY2026 + ARPA-H FY2022–FY2026 = 265 account-year jobs,
above GitHub's 256-job matrix limit. Reconcile's `validate_obligations`
(require_data) rejects any registered account without events, so a partial
run cannot coexist with all 27 registered. Staged exactly as DoD was:

- **Stage 1 (group A, 13 accounts, 130 jobs):** a single commit removes the
  14 group-B registry entries (pure deletion, byte-preserving; baselines
  stay on disk), then a separate trigger commit starts `mode: full` for
  `hhs/nih-nlm, -bf, -od, -niehs, -ncats, -ninds, -ninr, -nimh, -nccih,
  -fic, -nia, -nci, -nhlbi`. Stage-1 state: registry 471/471; the reconcile
  unit set passes (69 tests; the exact-27 scope test skips).
  `test_site_contract` (expects 80) is red on the branch until stage 2. That
  is expected and branch-only.
- **Stage 2 (group B, 14 accounts incl. ARPA-H, 135 jobs):**
  `git checkout 0e355c25 -- config/obligation_accounts.json` restores group B
  byte-for-byte (the stage-1 commit `58945ab` also carries handoff edits, so
  do not `git revert` it; confirm the diff is pure additions); trigger
  `mode: full` for group B. Run 2's reconcile keeps group A's committed
  stores.
- **Ordering constraint:** `main` has since edited
  `config/obligation_accounts.json` (Stage 2b #95 added the temporary NIH
  `interpretationNote` to `hhs/aspr-rd-procurement` and `hhs/ahrq`). Do the
  stage-2 `git checkout 0e355c25 -- config/...` restore BEFORE merging `main`,
  or it would silently drop main's edits. After merging `main`, regenerate
  any conflicted generated files (obligation rollups/dashboards) with
  `scripts/rollup_obligations.py`, never by hand.
- Then restore the trigger to weekly/all, merge `main` (for Stage 2b's
  `site/index.html` changes), remove the temporary NIH disclosure, run
  release gates, and open the PR.

Registry generation completed at `0e355c2` (27/27: registry 569/569, fast
7/7, planner 265 jobs; ARPA-H PAC 0001 + PARK 61U701UBGJ3 folded into one
PA; NIDDK `0031` Type 1 Diabetes registered separately; ZERO OBLIGATION
aliases on NIA/NCI/NIDDK/NIAID).

## Release reader review (2026-09-27, fresh agent, screenshots only)

Pack: `scripts/verify.py --tier screens` (101 pages) on `d361a835`, plus
the HHS agency page, NCI institute PA and NIDDK Type 1 Diabetes PA. The
reviewer saw 13 pages and the rule-5 questions only.

| # | Sev | Introduced by 3.2e? | Finding | Disposition |
|---|---|---|---|---|
| F1 | High | **Yes** | NIDDK "Type 1 Diabetes" PA page shows $0 in every FY2026 tile beside $30–77M in prior years, with no explanation; reads as defunding. FY2026 File B has no separate PAC/PARK for it (it is inside the NIDDK PARK). | **Owner approved option A 2026-09-28**; the memo text is registered verbatim as the PA-level `interpretationNote` on NIDDK `type-1-diabetes`. Re-review below. |
| F1b | (Medium, found in follow-up scan) | **Yes** | Same shape on 21 "NIH reimbursable – other" (`0801`) PA pages: material FY2017–FY2020 (NIGMS $0.83–1.24B/yr), about $0 from FY2021. | Option A approved 2026-09-28, applied only where the claim is true by a stated test: max \|annual net\| FY2021–FY2026 ≤ 5% of the FY2017–20 mean, which must be positive. **20 accounts qualify**: NLM, OD, NCATS, NINDS, NINR, NIMH, NCCIH, FIC, NICHD, NIGMS, NHLBI, NIDCR, NIAID, NEI, NIAMS, NIDCD, NHGRI, NIAAA, NIMHD, NIBIB. **6 get no note**: NIA (FY2021 $8.7M vs a $9.1M mean, ratio 0.95), NIEHS (0.33), NCI (0.13), NIDA (0.09; $9.1M FY2024), NIDDK 0801 (0.08), B&F (no positive FY2017–20 history). On those six pages "near zero" would be false or unsupported, and the pattern that prompted F1b is absent or weaker. |
| R1 | High | **Yes** | Re-review 2026-09-28 (fresh Sonnet agent, 4 re-shot pages, no build context). The NIA reimbursable page has no note (excluded by the "near zero from FY2021" test: FY2021 $8.7M), yet it shows the same collapse one year later (FY2022 $2.1M, then ≤$0.2M). The sibling NIGMS page has a note, so the inconsistency reads as NIA-specific defunding. The same applies to NIEHS, NCI, NIDA and NIDDK 0801. | **Gates release.** Wording is owner-layer; memo 2026-09-28 proposes a second, data-true variant ("since FY2023 ... well below FY2017–2020 levels") for the 5 accounts (max \|FY2023+\| ≤ 20% of the FY2017–20 mean: NIA 0.02, NIEHS 0.20, NCI 0.13, NIDA 0.09, NIDDK 0.06). B&F still has no note (no pattern). |
| R2 | High | **Yes** | The T1D note explains FY2026 $0, but FY2025 shows $1.7M (vs $28.8–141M in FY2017–24), and the source reports that figure under PAC 0031 itself, so the reporting-structure explanation does not cover it. The reviewer also cites FY2024 $30.1M; that is inside the historical range (FY2018 $28.8M), so only FY2025 is a finding. | **Gates release.** Memo proposes appending a no-cause FY2025 sentence. |
| R3 | Medium | No | "No File C rows linked to public awards in FY2026" on zero-activity PA pages compounds the zero impression. | Existing site behavior on every zero-activity PA page; display ledger. |
| R4 | Low | No | The partial-FY asterisk key sits only at the page bottom. | Same as F4 (pre-existing); display ledger. |
| R5 | High (reviewer) → Medium (disposition) | Yes | Re-check 2026-09-28 of the approved R1/R2 text (fresh Sonnet agent, 3 pages). NIA: the note says "since FY2023 ... well below FY2017–2020 levels", but the chart shows the drop starting in FY2022 ($2.1M). The reviewer calls this a factual mismatch. | The claim is true: every FY2023+ value is ≤ 2% of the FY2017–20 mean. It states no onset year, and the exact values sit on the same page. The residual risk is a reader inferring FY2023 as the start of the decline, not a false defunding conclusion, so it does not gate. Offered to the owner as an optional wording refinement. |
| R6 | Medium-High (reviewer) | Yes | T1D and NIGMS: the notes state the FY2025 / FY2021+ drops but give no cause, and the magnitude (NIGMS ~$1B/yr) invites a cut reading. | Accepted residual. No cause is attributable from the source; the approved no-cause wording is the policy (owner layer b), and speculating (e.g. reclassification or statutory lapse) would be an unsupported public claim. |
| R7 | Low (reviewer) | Yes | NIA and NIGMS notes differ in wording and start year. | By design: each variant is the strongest claim true for its accounts (a single shared text would have to weaken the NIGMS claim). |
| F5 | Medium | Partly | No NIH-level obligations rollup; the award NIH total ($24.4B FY2026) and HHS obligations ($37.1B) are left unexplained side by side. | Brief forbids a public reconciliation; the existing separation disclosure stands. NIH rollup is a hierarchy/scope question (ARPA-H membership). Deferred; listed in the memo as a follow-up, not a release gate. |
| F7 | Low | Yes | Single-PA institutes: the PA drill-down duplicates the institute page. | Existing site behavior for every single-PA account (e.g. ARPA-H, ASPR); display ledger. |
| F9 | Low | Partly | Zero-value sibling PAs collapsed; a direct landing lacks sibling context. | Covered by the F1 note; display ledger. |
| F2 | High | No | Award deltas vs FY15-24 average shown without the amendment-bias caveat nearby. | Pre-existing (award ledger); display ledger for the owner. |
| F3 | High/Med | No | Sentinel unreviewed vs confirmed cards visually similar. | Pre-existing (sentinel language is owner-gated); display ledger. |
| F4 | Medium | No | Partial FY26 bar marked only by an asterisk. | Pre-existing; display ledger. |
| F6 | Medium | No | Commerce −7.1% File C/net and VA 0 linked awards unexplained on the landing. | Pre-existing; display ledger. |
| F8 | Low | No | Award root "Data quality notes" duplicates an NSF sentence. | Pre-existing bug in `site/index.html` (Stage 2b-owned); display ledger. |

## Log

| When (UTC) | Event | Result |
|---|---|---|
| 2026-09-23 22:01 | Sizing run 35925926839 | green; NCI small (above) |
| 2026-09-23 22:01 | Test run 35925926684 on probe commit | green (fast tier 9.5 min on CI) |
| 2026-09-23 22:40 | Discovery run 35929645412 triggered | chunks 1–2 clean; chunk 3 pending |
| 2026-09-24 01:15 | Registry worker: 9 accounts, File A pins | `claude/phase-3.2e-nih` @ 55b4630 |
| 2026-09-24 05:45 | Discovery chunk 3 | clean; ARPA-H first FY2022 P07 |
| 2026-09-24 06:40 | Registry 27/27 | `0e355c2`; registry 569/569, fast 7/7 |
| 2026-09-27 22:40 | **Group B committed** on `claude/phase-3.2e-nih-b`: run `36212428737` attempt 2 (fresh requests after the age bound) pulled NIAAA FY2019 (1,813 File C rows) and NIGMS FY2018 (9,104). Attempt 2's reconcile failed only on my own test (`test_baselines_carry_reviewed_file_a_pins_before_backfill`: ARPA-H FY2022 `firstPeriod` 7 ≠ 10). Post-backfill, `firstPeriod` is the first material event period (P10), so the test was wrong, not the data. Fixed in `15c22534`; attempt 3's reconcile committed `5aa0f6ad`. 14 stores (13×10 + ARPA-H 5). Only pin-row change: ARPA-H FY2022 `firstPeriod` 7→10, `obligationsCents` unchanged. | Integrated |
| 2026-09-28 18:15 | CI `Test` green on `4de08159`. Scheduled runs were delayed, not dropped: `Update data` 36459604422 started 17:38 (cron 09:13); `Update obligation ledger` 36463768489 started 18:14 (cron 10:37, 53 accounts, ~30 h → ~Wed 00:30 UTC). | Merge `main` after it commits |
| 2026-09-28 18:00 | Owner approved both R1/R2 texts; `4de08159` (5 variant notes + T1D FY2025 sentence; validate PASS, tests OK, registry 595/595). Re-check by a fresh agent: R5–R7, none gating (dispositions above). No scheduled workflow has fired today (obligation cron 10:37, data cron 09:13). | Waiting on the weekly `main` run |
| 2026-09-28 17:20 | Regenerated with notes (`2638a5d3`): diff = 21 notes + date stamps; `validate_obligations` PASS, 144 tests OK, registry 590/590. Re-shot 4 pages; fresh re-review: F1 note works for FY2026, NIGMS reimbursable note adequate, NIDDK institute page clean; new gating R1 (unnoted NIA-class reimbursable pages) and R2 (T1D FY2025 $1.7M). | Owner memo sent in chat |
| 2026-09-28 17:00 | Owner approved option A. Notes registered (1 T1D + 20 reimbursable, criterion above); regenerated. The weekly `main` obligation run had not started at 16:29 UTC, so the merge waits for it to commit. | Next: re-shoot and re-review F1, docs, merge `main` after the weekly run |
| 2026-09-27 23:30 | CI `Test` green (registry/fast/rendered tiers) on every head: `d361a835` (run 36355981394), `a347794d` (36356560879 push, 36356596690 PR), PR #97 head `deb66a26` (36356612959). | Waiting on the owner's F1 wording |
| 2026-09-27 23:55 | Push of `dc8fd1a7` (trigger restored to weekly/all without `[skip ci]`) started run `36354679967` on the branch; cancelled within ~2 min (plan + at most one pull; no reconcile, nothing committed). Merged `main` (`c68f1773`: Stage 2b #95/#96). Only 3 generated dashboards conflicted; regenerated. **Temporary NIH disclosure removed** from the obligations landing subtitle (`site/index.html`), the `interpretationNote` on `hhs/aspr-rd-procurement` and `hhs/ahrq`, and its two `tests/test_site_contract.py` pins. The test now asserts the sentence is absent; nothing else in the Stage 2b wording changed. `validate_obligations` PASS; site contract + NIH tests 67/67. | Next: release gates (registry/fast/rendered/screens), reader review, PR |
| 2026-09-27 23:10 | **Integration** on `claude/phase-3.2e-nih`: merged `claude/phase-3.2e-nih-b`. The NIH subtrees are disjoint. 770 generated files conflicted on regeneration stamps and were rebuilt with reconcile's own `build_obligations` + `build_sentinel` (13 min). `refresh_status.json` is the lossless union (53 shared entries byte-identical; +13 group A, +14 group B). Registry restored from `0e355c25` (80 accounts; the auto-merge had kept only 53 + group B). Trigger restored to main's weekly/all. `validate_obligations` (require data) PASS, 0 warnings. Root: 80 accounts, FY2026 P10. HHS: 29 children. | Next: merge `main`, remove the temporary NIH disclosure, release gates |
| 2026-09-27 19:31 | Group B run `36212428737` attempt 1 complete: 133/135 pulls green. Failures: `hhs/nih-niaaa` FY2019 (File C source stall) and `hhs/nih-nigms` FY2018 (job 108321691033; File B P08 request exhausted transport retries, `http.client.RemoteDisconnected`, a USAspending connection storm rather than a generation stall). Reconcile job 108671092956 reconciled 133 partitions / 14 accounts and failed closed at validation (both shards missing); nothing committed. | `rerun_failed_jobs` issued (attempt 2: both pulls + reconcile) |
| 2026-09-26 17:05 | **Group A committed.** Run `35963288599` attempt 4: the fresh NINDS FY2019 File C request finished (third request overall; the first two, 17 h apart, stalled at the source). Reconcile validated and committed atomic snapshot `c9dc3c58` (1,108 files). All 13 group-A accounts have 10/10 partitions through FY2026 P10. Every reviewed File A pin is unchanged: the reconcile diff to the 13 baselines is key order only, so File B = pin exactly for all 130 account-years. | Group A done; wait for group B |
| 2026-09-26 14:35 | NINDS FY2019 attempt 4 (`rerun_failed_jobs` 14:31, fresh request). Group B check: 36 pulls green (median 17.3 min), 1 failed: `hhs/nih-niaaa` FY2019 (job 108321685827), File C request stalled 10:11→12:11, same `TimeoutError`. **Pattern:** every stall so far is an older-year File C export (NIFA FY2019, IES FY2018, NINDS FY2019, NIAAA FY2019), while most same-year pulls succeed. So it is intermittent at the source, not deterministic per account. | Group B continues; after it completes, one `rerun_failed_jobs` (the age bound forces fresh requests). |
| 2026-09-26 03:45 | Group B run [`36212428737`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/36212428737) (136 jobs) running on `claude/phase-3.2e-nih-b`; first pulls green: ARPA-H FY2022 (first partial year, P07 start) and FY2024. Run 1 attempt 3 ended `failure` (fail-closed; nothing committed). | NINDS FY2019 attempt 4 scheduled ~14:30 UTC |
| 2026-09-26 02:45 | Run 1 attempt 3: the resume-age bound worked (`abandoning automatic resume ... request accepted 2026-09-25T07:33:02+00:00 is older than 4 h; requesting a fresh download`), but the FRESH NINDS FY2019 File C request also stalled past 2 h (job 108297583034, 00:28→02:28). Two independent requests 17 h apart: persistent source-side stall for this one export. Reconcile attempt 3 (job 108319802106) will fail closed; nothing committed. | Decision (engineering): no immediate retry; retry NINDS FY2019 after ~12 h (attempt 4). Group B backfill started in parallel on `claude/phase-3.2e-nih-b` (registry = 53 + group B, `a3bc081`; trigger `c9fba04`, 135 jobs). Owner memo only if the stall persists for days (IES FY2018 quarantine precedent). Group-A partition artifacts (7-day retention) expire ~2026-10-01/02. |
| 2026-09-25 23:50 | Run 1 attempt 2: NINDS FY2019 pull job 108256105370 **failed again**. W13 resumed the same File C request accepted 07:32 UTC (`resuming accepted ... (automatic, previous attempt)`); it was still unfinished at 23:32, so this is a stuck source export (IES FY2018 pattern), not transient. A third plain rerun would re-poll the same dead request. Fix: an automatic resume now abandons accepted requests older than 4 h (acceptance time parsed from the source file name) and requests fresh; tests + `docs/obligation-ledger.md`. Pull jobs check out the branch tip, so attempt 3 picks up the fix. | fix pushed; attempt 3 after attempt 2's reconcile finishes |
| 2026-09-25 21:25 | Run 1 attempt 1 complete: 129/130 pulls green; reconcile job 108220937537 reconciled 129 partitions, then `validate_obligations` failed closed (`hhs/nih-ninds FY2019: required shard file is missing`; `FY2019: required complete snapshot is missing`); nothing committed | `rerun_failed_jobs` issued (attempt 2: NINDS FY2019 W13 resume + reconcile) |
| 2026-09-25 10:20 | Run 1 check | 95/130 pulls green; **1 failed**: `hhs/nih-ninds` FY2019 (job 107516375728). File B P02–P12 accepted (through a USAspending disconnect burst 07:25–07:31); File C request accepted at 07:32 and never finished within the adapter's 2 h cap (`TimeoutError`). Same source-stall class as W11/W13, not volume. Remedy: after the run completes, re-run failed jobs once; W13 resumes the accepted request from raw artifact `obligation-raw-hhs--nih-ninds-FY2019-attempt1` (id 10855739411), and reconcile re-runs with the full partition set. |
| 2026-09-24 11:05 | Run 1 check | 0 failed jobs; `main` at `8b8a13b` (Stage 2b #95 merged; disclosure present in site/index.html:2431, registry interpretationNote ×2, test_site_contract.py:219,1036) |
| 2026-09-24 06:11 | Stage 1 `58945ab` + trigger `5869069`: backfill run 1 [`35963288599`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/35963288599) | running; first pull (B&F FY2018) green in 16 min; reconcile expected ~2026-09-25 17:00 |

## Next action

Draft PR #97. Blocked on the owner's answer to the R1/R2 wording memo
(2026-09-28). Then: register the approved text, regenerate, validate,
re-shoot, and a one-page re-check. Wait for the weekly `main` obligation
run to commit, merge `main`, regenerate, validate, add the
phase-history entry, mark #97 ready and merge when green (no weekly run in
flight). The CLAUDE.md bullet is already in place.
