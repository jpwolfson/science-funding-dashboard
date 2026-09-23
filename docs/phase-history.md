# Phase history — completed-phase detail and evidence

Moved verbatim from CLAUDE.md's roadmap on 2026-08-12 to keep the roadmap
lean (per the working regime's token-economy rules). This file is the
durable record; the roadmap carries only terse summaries and pointers.

- [x] Kickoff: repo created, regime + API lessons documented, DMS pipeline
      and verified baseline seeded under `reference/` (2026-08-07)
- [x] Phase 1 — NSF-wide (completed 2026-08-10):
      - Done: `adapters/common.py` (aggregation regression-verified EXACT
        against fed-funding-dashboard's committed dashboard.json),
        `adapters/nsf.py` (all API-defect workarounds + org-filter probe +
        per-unit plausibility caps from `config/orgs.json` `checks`),
        `scripts/pull_unit.py`, `scripts/rollup.py` (id-deduped rollups,
        child summaries, `data/index.json`), `scripts/verify_dms_baseline.py`
        (exact-parity gate), `scripts/discover_orgs.py`, both workflows,
        `site/index.html` (multi-node port of the old page).
      - **RELEASE BAR MET 2026-08-08 00:02 UTC**: run 31224153926 pull +
        rollup + verify-dms ALL GREEN — fresh full pull = 11,508 awards,
        0 warnings, exact parity with the hand-verified baseline. Owner
        has enabled Pages (Settings done); deploy fires on merge to main.
      - Discovery: run 1 (showAward HTML parser) failed → run 2 (bulk XML,
        commit 93779a9) failed because NSF redesigned Award Search: the
        legacy download endpoint serves a 128-byte meta-refresh stub to
        non-browser clients, and bulk files converted XML→JSON 2025-01.
        v3 proved the ENTIRE legacy /awardsearch/ path — download.jsp
        included, browser UA or not — serves only a 128-byte redirect
        stub; bulk zips remain unreachable. v4 SUCCEEDED via detail-API
        fallback (44 divisions) but review found 3 defects: 16 unresolved
        codes incl. all of TIP (value-pattern extraction missed names
        without a "Division of" prefix), ENG grouped under CSE / AST
        under OD (tie-break bug in name matcher), active=False everywhere
        (recent-window probes inexplicably empty). KEY FACT from v4's
        committed dump: api.nsf.gov/services/v1/awards/{id}.json returns
        EXPLICIT fields divAbbr, dirAbbr, orgCodeDiv, orgCodeDir,
        orgLongName (directorate), orgLongName2 (division). v5 (commit
        fc41f7c, fired 2026-08-09 ~22:10 UTC) extracts by key, checks
        param semantics via orgCodeDiv == swept code, ships all entries
        active:true (derive real flags from pulled data post-backfill).
        Sweep facts established: 59 live org codes, 461 empty, unknown
        codes return EMPTY.
      - REGISTRY DONE (v5, run committed ccb592a, reviewed 2026-08-09):
        59/59 codes verified, 0 unresolved, param semantics exact via
        orgCodeDiv, TIP + ENG + MPS grouping correct, DMS entry intact.
        14 directorate-tier groups = 8 science + OD + 5 admin (BFA, IRM,
        NCO, NNCO, OCIO — kept for completeness). All entries active:true;
        real flags to be derived from pulled data post-backfill.
      - BACKFILL COMPLETE 2026-08-10 01:35 UTC (run 31340113408): all 59
        pulls green, 0 warnings in every unit, rollup green, verify-dms
        exact-parity green post-re-pull. NSF-wide totals: 138,162 unique
        awards since FY2015 (0 cross-division id dups); FY2024 = 11,687
        awards / $8.0B intended (matches NSF's published annual volume);
        FY2026 to date = 5,308 / $4.0B.
      - Active flags derived from pulled data (scripts/derive_active_flags.py,
        24-month window): 40 active, 19 dormant admin/legacy units with
        last-award notes. Re-run after future backfills.
      - Site verified against real data in-browser (9 pages, 0 console
        errors, children tables exactly match rollup JSON). 3 sparse-unit
        display bugs found and fixed (missing tile row on no-current-FY
        units, mechanism-chart label/axis collision, "1 awards" plural);
        fixes re-verified in-browser.
      - Phase 1 exit: PR to main opened + merged by Claude (owner
        pre-approved); Pages deploy fires from update-data runs on main
        (weekly Mondays 09:13 UTC; dispatchable on demand).
      - Known open items: if bulk-XML discovery also fails, diagnose from
        reference/discover_debug/ dumps (now committed even on failure)
        and re-fire via `.github/triggers/discover.json`. Watch the
        report's "not queryable via the API" section — any bulk code the
        API refuses means awards invisible to our pulls. Site review of a
        node with many children (root/agency) once real multi-division
        data exists. Weekly schedule only activates once merged to main.
- [x] Cumulative FY-to-date overlay charts on every node (completed
      2026-08-10 per `docs/handoff-cumulative-fy-charts.md`): `fyCumulative`
      in `aggregate()`, `cumulativeChart` ×2 leading every node page,
      `scripts/reaggregate.py` (offline re-aggregation path — reusable
      whenever `aggregate()` gains keys). All acceptance checks green via
      independent verification sweep: endpoint invariant exact on 256
      year-series across 62 dashboards, DMS byte-parity with
      fed-funding-dashboard@2c211a0 incl. mid-year points, light+dark
      browser pass, awards.csv untouched. Known inherited behavior: FYs
      with zero awards in the 5-year window are absent from fyCumulative
      (fewer lines), not all-zero series.
- [x] Phase 2 — NIH via RePORTER API (completed 2026-08-11, reviewed by
      Fable + independent Sonnet verification sweep):
      - Implementation: 28 current RePORTER administrative components in the
        registry; `adapters/nih_reporter.py` with per-IC/per-FY pagination,
        opposite-order exact ID-set checks, non-destructive merge,
        source-aware award links/labels, and deterministic fiscal-year gzip
        shards. NIH CI runs serially and the adapter throttles to the
        official one-request-per-second guidance. Intramural (`IM`) records
        and subprojects are excluded to avoid zero-dollar records and
        parent/subproject double counting. Layered fail-closed validation
        (`scripts/validate_nih.py`, `docs/nih-data-validation.md`): offline
        shard/manifest/dedup/range/warning gates in the Test workflow, NIH
        like-for-like Data Book benchmarks (counts and dollars ±2%), and `--live`
        same-source reconciliation gating every NIH data refresh.
      - RELEASE BAR MET: backfill run 31426718058 (28/28 ICs green, merged
        via PR #4); Test green on main incl. offline validation; production
        chain exercised end-to-end on main by run 31448155904 (2026-08-11
        01:23 UTC): incremental pull ×28 → rollup → validate --live (28/28
        exact live reconciliations in 29 s) → data commits → Pages deploy,
        ALL GREEN. 694,443 NIH awards FY2015–present, zero warnings in all
        28 stores; Data Book agreement FY2022 +0.12% / FY2025 −0.16%; root
        = 832,616 awards = NSF 138,173 + NIH 694,443 exactly. Sweep: 15
        tests + 33 subtests green, 58/58 dashboards invariant-exact
        (monthly ≡ FY ≡ total; fyCumulative endpoints exact), browser pass
        7 pages × light+dark with 0 console errors, NIH links →
        reporter.nih.gov. Oct–Nov 2025 award collapse (7 / 154 vs ~800 /
        ~2,000 historically) verified as the real shutdown signal, not a
        pull artifact (Oct-1 date-fallback rows are only 0.9% and October
        is NIH's quietest month).
      - Review hardening follow-ups are complete: live NIH validation checks
        the mechanism partition, and NIH-scale dollar tiles use the site's
        billions formatter rather than rendering values such as "$23314M".
      - Phase 3.1b follow-up (2026-08-11): a corrected mechanism whitelist
        recovered 13,790 intentionally in-scope contract/IAA records. The
        former Data Book comparison accidentally measured that complete
        product against a grants-only benchmark. NIH rows now persist funding
        mechanism and activity code; the validator derives the Data Book's
        non-zero grant/OT subset while retaining the complete 708,233-record
        product universe. A fresh 28-IC full pull and rollup are the release
        gate; legacy shards without structured mechanism detail fail closed.
- [x] Phase 3.1 — USAspending award-search adapter + calibration gate
      (completed at its designed STOP 2026-08-11 via PR #5; reviewed by
      Fable, verdict: correct execution, real blocker, sound diagnosis).
      The calibration-before-onboarding ordering worked exactly as
      intended — DOE was NOT onboarded, and the findings drove the Phase
      3.1b redesign below.
      - **CALIBRATION STOP GATE TRIGGERED 2026-08-10 — DOE NOT ONBOARDED.**
        Core award-search adapter and fail-closed pagination checks are built;
        the Phase 2 NIH mechanism tripwire is also built (and exposed missing
        `RDC` / uppercase `OTHER`, now fixed). DMS FY2024 count coverage is
        99.80%, but NIGMS demonstrates that RePORTER application-year records
        cannot be reconciled to USAspending base awards. More decisively, DOE
        089-0222 FY2024 is $9.282B in authoritative account obligations versus
        $3.397B for new awards/current whole-award totals and $37.342B for an
        account-filtered transaction series. Program Activity award filters
        overlap (660 memberships / 575 distinct awards across eight science
        programs), so program-office rollups double-count. Per the ordered risk
        control below, no DOE registry/data/workflow was added. Evidence and
        owner choices: `docs/usaspending-calibration.md` and
        `reference/usaspending_calibration.json`; CI prevents USAspending
        registry onboarding while status is blocked. Recommended next phase:
        redesign around File C account/PARK allocation events.
- [x] Phase 3.1b — obligation ledger + DOE Office of Science pilot
      (completed 2026-08-11 via PRs #6–#9; post-deploy QA, landing-page
      obligation summaries, and deployed Pages smoke checks passed).
      - Two ledgers remain physically separate and clearly labeled. The award
        ledger answers how many source-native awards/applications were made and
        their reported totals. The obligation ledger answers how signed dollars
        moved through an appropriations account by agency submission period.
      - Canonical dollars are File B Program Activity CPE deltas. File C is the
        award-financial subset used for recipient/flow detail; an explicit
        signed File B-minus-File C residual makes every PA-period and account
        total exact. File C is not substituted for GTAS/File B.
      - FY2015–16 are unavailable, FY2017 begins at P06 and is partial-source
        history, FY2018–25 reconcile to GTAS/File A at exact cents, and FY2026 is
        pinned through P09. Correctable fiscal-year partitions are replaceable;
        negative activity remains negative.
      - DOE `089-0222` is live at the account and Program Activity tiers.
        Calibration is `ready`; the NSF DMS count diagnostic and like-for-like
        NIH Data Book gate remain separate award-ledger checks.
      - Post-deploy QA hardening: baselines now drive partial-year rendering;
        zero-activity PA periods are materialized instead of compressing time;
        unmapped nonblank Program Activities fail closed; manifest, required-
        year, residual-bucket, dashboard-freshness, and child-timeline checks
        are enforced. UI copy distinguishes File C/net from a bounded coverage
        score, scopes every current-FY tile, exposes freshness, names charts for
        assistive technology, improves light-theme contrast, and collapses the
        180-row recipient/flow tail behind current-year summaries. The landing
        page now gives DOE obligations the same summary-tile prominence as
        award activity while stating that the measures are separate and that
        negative sign alone does not establish cancellation.
      - Detailed contract and release evidence:
        `docs/obligation-ledger.md`, `docs/phase-3.1b-handoff.md`.
- [x] Phase 3.2a — platformize before account fan-out (completed 2026-08-11).
      - Registry-driven account × FY planning now supports weekly current-FY
        refreshes for every account, one rotating historical reconciliation per
        account, and full/custom dispatches. Baseline paths, availability, and
        the ten-day freshness SLA are account-owned contracts.
      - Per-FY schema-v2 provenance persists accepted request scopes, status and
        parsed row counts, raw ZIP hashes, normalized content fingerprints,
        compact diffs, and replacement lineage across one-day reconcile
        artifacts. Raw ZIPs retain for 14 days; normalized stores and audit
        records remain in Git. Pre-v2 shards are honestly marked
        `legacy-migrated` until rotation replaces them.
      - Reconciliation validates every registered account and renders one
        candidate snapshot before the same tree is committed and uploaded to
        Pages. Obligation-only commits no longer rely on the generic deploy.
      - The hard dashboard migration removed `fileCCoverage` in favor of only
        `fileCToNetRatio`. All obligation JSON was regenerated at schema v2.
      - Fail-closed checks cover required shards, manifests, provenance,
        freshness, dashboard staleness, PA drift, public links, and a five-case
        Chrome matrix across themes, widths, empty/negative/out-of-range ratio
        states, keyboard focus, and console/network failures.
      - Local release evidence: 64 tests plus all offline validators and the
        rendered matrix pass. Detailed contract: `docs/phase-3.2a-handoff.md`.
- [x] Phase 3.2b — build and review the AAAS-to-federal-account crosswalk
      (completed 2026-08-11 as reference-only research).
      Treat the AAAS R&D Appropriations Dashboard as the scope/framing source,
      not as an unattended production registry. Commit a dated source snapshot
      and a reviewed, possibly many-to-many mapping to federal accounts; CI may
      detect AAAS drift but must not auto-onboard or silently remap an account.
      Preserve AAAS-facing labels while making the federal-account identity and
      any aggregation explicit. Each row must be `resolved`, `provisional`, or
      `unresolved`, with evidence. Resolved rows may proceed without waiting for
      optional review of the others. Federal-account hierarchy is canonical;
      AAAS is an alternate grouping/framing view. Source discovery and mapping
      were completed in a separate worktree without changing the registry,
      production workflows, schemas, or generated dashboard data.
      - The dated snapshot preserves 45 AAAS grouping fields and 237 exact
        labels from the public FY 2026 Power BI model; the reviewed crosswalk
        classifies 185 rows as resolved, 10 as provisional, and 42 as
        unresolved, with row-level evidence and explicit account arrays.
      - Artifacts: `reference/aaas_rd_appropriations_2026-08-11.json`,
        `reference/aaas_federal_account_crosswalk.{json,csv}`, and
        `docs/aaas-federal-account-crosswalk.md`.
      - Phase 3.2a satisfies the technical prerequisite, but the crosswalk
        remains reference-only pending reviewed account onboarding. It does not
        authorize automatic registry onboarding, production remapping, workflow
        changes, or automated drift enforcement.

## Phase 3.2d — resolved-account obligation fan-out (completed 2026-09-14)

Phase 3.2d completed the site-building and release work for 53 federal
obligation accounts across 13 agencies. The registry, accepted account stores,
baselines, rollups, site pages, fail-closed checks, rendered review, Pages
footprint, deployment, and live QA are complete. File B remains canonical;
File C supplies award-linked detail; the signed residual remains explicit; and
File C plus residual equals File B exactly at every accepted grain.

The exact resolved scope is 83 unique federal accounts from 185 resolved AAAS
crosswalk rows. Its partition is complete and disjoint:

- **53 registered Phase 3.2d accounts:** DOE 11 (`089-0222`, `089-0337`,
  `089-0321`, `089-2297`, `089-0213`, `089-0318`, `089-2250`, `089-0319`,
  `089-0240`, `089-0309`, `089-0216`); NSF 4 (`049-0100`, `049-0106`,
  `049-0180`, `049-0551`); HHS 2 (`075-1000`, `075-1700`); NASA 6
  (`080-0120`, `080-0126`, `080-0131`, `080-0128`, `080-0124`, `080-0115`);
  DOI 1 (`014-0804`); EPA 1 (`068-0107`); Commerce 6 (`013-1450`,
  `013-1460`, `013-0500`, `013-0525`, `013-0401`, `013-0450`); USDA 8
  (`012-1400`, `012-1401`, `012-1104`, `012-0502`, `012-1500`, `012-1502`,
  `012-1701`, `012-1801`); VA 1 (`036-0161`); DHS 3 (`070-0803`, `070-0805`,
  `070-0860`); DOT 3 (`069-1730`, `069-8108`, `069-0745`); Education 1
  (`091-1100`); and DoD 6 (`021-2040`, `017-1319`, `057-3600`, `057-3620`,
  `097-0400`, `097-0130`).
- **27 NIH obligation accounts intentionally out of Phase 3.2d:**
  `075-0807`, `075-0819`, `075-0837`, `075-0838`, `075-0843`, `075-0844`,
  `075-0846`, `075-0849`, `075-0851`, `075-0862`, `075-0872`, `075-0873`,
  `075-0875`, `075-0884`, `075-0885`, `075-0886`, `075-0887`, `075-0888`,
  `075-0889`, `075-0890`, `075-0891`, `075-0892`, `075-0893`, `075-0894`,
  `075-0896`, `075-0897`, and `075-0898`.
- **Three owner-approved quarantines:** BEA `013-1500`, BLS `016-0200`, and
  OJP `015-0401`. BLS and OJP remain the quarantined Stats/OJP pair; their
  graph is absent. These quarantines are unchanged.

There are no registered codes outside the resolved set and no silent resolved
omissions. The source crosswalk also retains its 10 provisional and 42
unresolved rows. DARPA is included within Defense-Wide `097-0400`; it is not a
standalone account or total.

The accepted Phase 3.2d atomic snapshot is
`640af0afd0ebb53508c2b34bf7769cf471c58c28`; the weekly/all trigger restore is
`c33c1de0697fb6619acc866048d40e5d491a02d5`. At that accepted snapshot, all 53
accounts report FY2026 through P09. Exact source-derived per-agency current-FY
net obligations are:

| Agency | Accounts | FY2026 through P09 |
| --- | ---: | ---: |
| Commerce | 6 | $6,785,783,895.39 |
| DHS | 3 | $139,758,037.28 |
| DoD | 6 | $184,724,968,208.97 |
| DOE | 11 | $39,682,374,520.41 |
| DOI | 1 | $1,352,224,602.47 |
| DOT | 3 | $183,378,560.80 |
| Education | 1 | $323,537,255.49 |
| EPA | 1 | $456,962,937.04 |
| HHS | 2 | $2,078,379,885.08 |
| NASA | 6 | $13,874,791,867.29 |
| NSF | 4 | $2,732,173,457.24 |
| USDA | 8 | $2,591,207,599.40 |
| VA | 1 | $621,486,212.92 |
| **Total** | **53** | **$255,547,027,039.78** |

Exact dual-source contracts are preserved without tolerance or synthetic
residual: Navy FY2025 File A `2788535575911` / canonical File B
`2788488646275` / variance `46929636` cents; DHP FY2025 File A
`4692069313553` / canonical File B `4676524125773` / variance `15545187780`
cents; Defense-Wide FY2025 File A `3813645882772` / canonical File B
`3812362307540` / variance `1283575232` cents; and DHS FY2026 P10 File A
`1990656262` / canonical File B `2660942811` / variance `-670286549` cents.
Completed-year pins remain immutable; the current FY remains partial and
source-refreshable.

The DoD source graph closed with Stage 3 run `33472362131` attempt 18 and
reconcile job `100038084744` green through all 16 steps. Final integration
commit `74b667a56456a767e6ee34693f7eb2df520a2a22` has exact tree
`ba3318f728b12b1f5b650b2f753ad4c2c53efa1b`. Main Test run `33573026004`
and job `100070867854` passed; Main Deploy Pages run `33573025999` and job
`100070868257` passed with deploy not skipped. Live QA passed at
<https://jpwolfson.github.io/science-funding-dashboard/>, including the DoD
parent and both Defense-Wide and DHP account pages. Full provenance and
failure-recovery detail is retained in `docs/phase-3.2d-dod-handoff.md`.

The exact ED/IES FY2018 export
`FY2018Q1-Q4_All_FA_AccountBreakdownByAward_2026-09-08_H07M33S17838315.zip`
is an owner-approved upstream-source quarantine after remaining `ready` with
all completion fields null for more than six days. It does not remove ED/IES
`091-1100`, change its accepted FY2018 pin/data, authorize another quarantine,
or permit a replacement request. Failed wait job `102982598555` is retired;
raw artifact `10170260290` is preserved with digest
`sha256:517b46d4d7cf1d181c393380a791c5018e8e8be5d1529a9009fee50cb7f88c19`.

The weekly obligation refresh remains automatic and independent of Phase 3.2d
closeout. It may advance FY2026 when the source accepts a newer period and may
rotate historical checks, but it neither redefines the completed build nor
keeps an agent goal open. Scheduled run `34868893350` was left to continue
normally; it was not cancelled, rerun, resubmitted, or used as release
evidence.

## Post-completion notes (2026-08-12)

- Phase 3.1b's named release gate — the fresh 28-IC NIH full pull with the
  corrected mechanism whitelist plus rollup — WAS met before the phase was
  checked off: committed state is 708,233 NIH awards, zero warnings, and
  `validate_nih.py` green, which is exactly the post-gate state. The
  original entry never recorded a "RELEASE BAR MET" line; this note is
  that record. The "13,790 recovered records" figure is historical (a
  diff against a pre-fix state not retained in the repo) and is not
  reproducible from committed data alone.
- The cumulative-chart endpoint invariant was violated by one award in
  `nih/od/od` FY2026 (found by the 2026-08-12 independent review sweep):
  NIH award-notice dates can post-date the pull, and the partial-FY
  series ended at `today`, excluding one future-dated award counted in
  the FY row. Fixed in `adapters/common.py` by ending the partial year at
  the latest data date; all 511 endpoint series verified exact after
  reaggregation.

## Post-completion review and remediation (2026-09-17 → 2026-09-23)

Independent review `docs/reviews/2026-09-15-phase-3.2d-independent-review.md`
found five severity-high defects in the Phase 3.2d operating state (fast
tier red on `main`, no scheduled refresh green since the DoD merge, retry
hatches load-bearing rather than temporary, DoD disclosure unpublished,
fabricated multi-billion-dollar File B period swings) and held Stage 2
(`docs/display-improvements-ledger.md`) per the regime's sequencing rule.
Owner decision A (2026-09-17): repair the operating state first, re-review,
then release Stage 2. Six verbatim owner decisions covering sequencing, the
not-yet-reported File B period display, the DoD disclosure text, award-root
and obligation-landing framing text, sentinel-facing language, and NIH
award-ledger semantics are recorded in
`docs/phase-3.2d-remediation-brief.md`. Later owner decisions: run
resilience W12/W13 (2026-09-20); render curated `periodNotes` as
source-figure statements without cause attribution (2026-09-21), with the
two `publicNote` texts approved verbatim (2026-09-23); award-pipeline
atomicity W17 (2026-09-23). A coordinator session ran the repair
2026-09-17 → 2026-09-20; post-soak sessions closed it on 2026-09-23. The
running record, wave plan, CI-run log, and per-finding evidence are in
`docs/phase-3.2d-remediation-handoff.md`.

**Finding closure:**
- HIGH-1 (fast tier red on `main`): closed by W1 (#65)/W7 (#67)/W8 (#70).
  `verify.py --tier fast` PASS on `main` in `Verify main` run 35259203139
  (2026-09-17, after the full NIH pull; the earlier run 35253809178 did not
  pass) and on every PR since. Full source-current NIH pull (run
  35250546983): root `totalAwards` 860,636 = `storeIdCount`, NIH 721,062 =
  leaf union, zero warnings; month-shrink rule replaced by id-level
  invariants (`docs/verification-regime.md`). The tier went red again on
  2026-09-21 (refreshed NIH leaves committed under a stale rollup when the
  NCI leaf was refused) and was restored by W15 (#83); W18 (#82) made the
  `Verify main` run conclusion reflect the tier, which had read `success`
  through `continue-on-error`.
- HIGH-2 (soak gate not met): closed 2026-09-23. Scheduled `Update
  obligation ledger` run 35626367929 green end-to-end (106/106 pulls,
  atomic commit `8b317e82`, deploy; 53/53 accounts `fresh`). Scheduled
  `Update funding-action sentinel` run 35757359002 green. Scheduled
  `Update data` run 35621987484 failed in code merged during this
  remediation (W1's churn gate refused 148 NIH `amount` revisions at NCI;
  revision, not displacement); per the soak rule the re-dispatched run
  35802597549 after W15 (#83) is the award-ledger soak: 28/28 ICs,
  `validate_nih.py --live` green at 723,486 awards, deploy green. `Verify
  main` run 35804388539 green on the resulting tree. The award-ledger
  evidence is a dispatched run, not a cron-fired one.
- HIGH-3 (retry hatches permanent): closed by W3 (#68), closeout (#76).
  Weekly-mode P10 pull (run 35481780814) gave every account a P10 partition;
  `reference/obligation_retry_recovery.json` deleted in #76;
  `validate_obligations.py` zero errors, no hatch
  (`tests/test_obligation_retry_recovery.py` asserts absence).
- HIGH-4 (DoD disclosure unpublished): closed by W4 (#66). Owner-approved
  text lives as registry field `interpretationNote` on the six DoD
  accounts, rendered on every DoD account/PA page and the landing-table DoD
  row, pinned verbatim by `tests/test_site_contract.py`; deployed 2026-09-17
  18:30 UTC (run 35250546983). Screenshots:
  `docs/reviews/evidence-2026-09-17-w4/`.
- HIGH-5 (fabricated period swings): closed by W3 (#68), W10 (#72), W14
  (#80), and CI re-pulls. Universal `classify_file_b_periods` acceptance
  rule plus reporting-span reconciliation and a pin-advancement guard; 165
  account-years classified, 24 material. W14 added the dollar-transient
  rule (full row counts, >50 % cumulative deviation that reverts at the
  next period) and hid not-reported points with no prior reported value,
  after the 2026-09-20 reader review found Navy FY2024 P11 and NOAA ORF
  FY2024. Screenshots: `docs/reviews/evidence-2026-09-17-w3/`,
  `docs/reviews/evidence-2026-09-20/w14/`.

**Engineering changes landed** (one line each; detail in the handoff):
- NIH ledger (W1 #65, W7 #67, W8 #70): source-current field overwrite,
  soft-delete exclusions ledger, append-only move ledger, id-count invariant.
- Publication gates (W2 #63, W6 #64, W9 #71): sentinel/obligation workflows
  no longer run the NIH suite; structural (not literal) current-FY pin
  tests; commit-step rebase retry on branch tip.
- File B acceptance (W3 #68, W10 #72, W14 #80, W19 #84): `notReported`
  classification + span reconciliation + pin-advancement guard; validator
  checks aligned to the `notReported` state; dollar-transient rule.
- Framing/DoD/sentinel (W4 #66): `interpretationNote`; award-root/obligation
  coverage text; sentinel gross/net language; clipped sentinel-card layout
  fixed.
- Run resilience (W11 #73, W12 #75, W13 #74, W17 #85 (acceptance run 35824669422)): reconcile
  tolerates a failed rotating-historical job; per-account (W12) and
  per-award-unit (W17) `stale` marking with the owner-approved "Not
  refreshed since" note, so one failed leaf no longer blocks the rollup,
  the live reconciliation, or the deploy; resumable (not resubmitted)
  timed-out downloads.
- NIH churn gate split (W15 #83): displacement guard (`date` moves +
  returns, `max(20, 0.1 %)`) separate from a value-churn guard
  (`amount`/`title`/`type`, `max(100, 1 %)`); methodology line "counts as
  of the pull date; NIH revises award notice dates and amounts."
- Source-figure notes (W16 #81): curated `periodNotes` render as "Notes on
  source figures" on the two affected account pages.
- `Verify main` conclusion (W18 #82): a red fast tier is a red run.
- Closeout (#76): retry-recovery manifest deleted; absence test added.
- Confirmed notes: NIST ITS FY2025 P11 real deobligation (#77) and DHS
  CISA FY2023 P03 over-report corrected at P04 (#78), each confirmed by a
  CI re-pull.

**Measured outcomes:**
- NIH: 721,056 after PR #65's offline reaggregation (4 ledgered ids then
  `excluded`) → 721,062 after the first full source-current pull (run
  35250546983: those 4 flipped to `returned`, net new records added); both
  correct for their trees. 723,486 after the W15 re-dispatch (run
  35802597549), per-IC live gaps 0–2 within tolerance.
- The 12 distinct account-years the review flagged (its "13" tallied 8
  exact-zero points + 5 >50 % drops, with overlap) were re-pulled on CI
  (runs 35520419335, 35528556931, 35535164305, 35538536444); none changed
  at the source. Six DoD FY2025 accounts still return a 1-row P11 File B
  snapshot; NOAA ORF/PAC FY2024 and Air Force RDT&E FY2024 still return
  near-empty mid-year snapshots — `notReported` with a held cumulative and
  hollow marker is the permanent public state. `commerce/nist-its` FY2025
  P11 returns full rows and is a real $5.03B net deobligation; DHS CISA
  FY2023 P03 is a source over-report corrected at P04; USDA NIFA
  Integrated Activities FY2022 P03 is a genuine small net deobligation
  below the $1M drop-check floor.
- CI: first accepted 53-account obligation snapshot is run 35481780814
  (2026-09-20, commit `ea328c4a`). Two weekly passes were lost to
  single-job failures before resilience landed: 2026-09-18 (reconcile
  failed on `doe/sc`/`doe/fossil-energy` FY2026 P10 validator
  misalignment, fixed by W10 #72) and 2026-09-19
  (`usda/nifa-research-education` FY2019 rotating-historical download hit
  the adapter's 2 h cap twice, tolerated going forward by W11 #73).
- Mechanical tiers re-run on the final tree 2026-09-20
  (`docs/reviews/evidence-2026-09-20/verify-*.json`); fresh-agent reader
  review `docs/reviews/evidence-2026-09-20/reader-review.md`, gating
  findings closed by W14, the rest dispositioned to the Stage 2 ledger.

**Explicitly out of scope (operational follow-ups):**
- Rotating-historical account-years hitting the 2 h download cap (`ed/ies`
  FY2018, `usda/nifa-research-education` FY2019) are not remediation items:
  W11 (#73) tolerates their failure, W13 (#74) makes the retry resume
  rather than resubmit. Landing them is ordinary rotation.
- Stage 2 (`docs/display-improvements-ledger.md`) released from hold on
  2026-09-23. W17's fresh-agent reader review gated one fix before merge
  (a stale unit's "last updated" stamp now names its snapshot date) and
  appended ledger items 9–10 (staleness marker on figures; plain-language
  warnings banner).

## Display-improvements batch: Stage 2 (2026-09-23)

`docs/display-improvements-ledger.md` items 1–11 shipped as one
reader-review-gated release. Scope was display only: no data, store, or
measure-semantics change. The one exception is item 8's curated note,
carried by the existing `periodNotes` mechanism. Work went through the
integration branch `claude/stage2-display` (cut from `main` `c356a78`), with
item PRs #89 (items 11, 1, 5, 2, 4, 7, 9), #90 (the owner-approved items),
and #92 (reader-review fixes and closeout docs), then one PR to `main`. The
running record is `docs/stage-2-display-handoff.md`; evidence is in
`docs/reviews/evidence-2026-09-23/stage2/`.

**Agent-owned items:**
- 11: the in-progress month in the monthly award chart draws as a dashed
  segment to an open marker, labelled "… to date". This was the W17 High.
- 1: obligation period charts draw explicit steps and carry the owner's
  cadence caption verbatim.
- 5: curated source-figure notes get "see note" guides on the period chart.
- 2: metric-identity audit (three label fixes, plus provider-aware
  count-chart titles).
- 4: inline "No File C rows linked to public awards in FY…" placeholders.
- 7: "…, FY2017–FY2026 combined" on the all-years total.
- 9: stale markers on figures and tiles.

**Owner-decided items (2026-09-23):**
- 3: the award tab carries no obligation figures; a link card replaces
  them, and the note moved onto the obligations landing.
- 6: the sentinel drops its age counter; financial-episode headings add
  the account and FY.
- 8: the DHS CISA R&D decline caption, carried as a baseline `publicNote`.
- 10: de-duplication notices go to the neutral notes block; real warnings
  get plain-language glosses with the raw text behind "Technical detail".
- Stamp qualifier: "· includes N unit(s)/account(s) last refreshed <date> †".

Afterwards the owner authorized the coordinator to merge fully green PRs
without further sign-off.

**Data defect #88** (found while checking item 5, fixed out of scope in
its own session, PR #91): 88 covering `reportingPeriods` rows omitted their
absorbed periods' activity. The worst was Navy RDT&E FY2024 P12, published
as −$25.05B where the true value is +$4.15B. The "correction pairs" the
2026-09-20 review saw on Navy and the Commerce accounts were this defect.
`aggregate()` now folds the span, and `validate_obligations.py` checks
covering rows and the FY sums cents-exact. 123 rows in 102 dashboards were
corrected, and only `reportingPeriods` changed.

**Release reader review** (fresh agent, screens pack only, 74 pages on the
integration head `a826fc3`): 7 High, 11 Med, and 10 Low findings. None of
the Highs was introduced by Stage 2; each is live on `main` `c356a78`. The
agent-owned parts were fixed before release: covering-step span labels,
$0 program activities folded into a group, and three nits. The
owner-layer findings (obligation scope, NIH absence, sentinel figure
wording, source award descriptions, the Army RDT&E FY2022 path, the
Oct–Nov 2025 lapse, the root title, and sentinel source status) are the
Stage 2b queue, ledger items 12–22. Tiers: registry 380/380, fast 7/7,
rendered 4/4, screens 74/74 on `a826fc3`, re-run on the final head before
the PR to `main`.

**Tooling added:** `scripts/capture_cards.py` (per-card before/after
captures, `--data` for staged scenarios). The screens tier now also
captures award sub-pages discovered from `data/index.json`.

