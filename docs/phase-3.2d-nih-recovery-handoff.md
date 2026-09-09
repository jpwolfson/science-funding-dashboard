# Phase 3.2d NIH live-count recovery handoff

Prepared 2026-08-24 from git main
`5df93c2c6a791b4aa3d97ee0f43f30e35053f968` after scheduled Update data run
`32714795623` committed fresh leaf stores but its rollup failed before it could
publish consistent NIH and root totals.

## Exact recovery graph

Source commit `1d246b32e222da7df2290aee85b24036e9e9ecbc` changes only
`.github/triggers/update.json` to a six-unit full refresh for NHLBI, NIA,
NIAID, NICHD, NIEHS, and OD. Authoritative branch
`codex/3-2d-freshness-nih-20260824` was required by the workflow's
`codex/**` push filter.

Recovery run `32726575277` attempt 1 is terminal failure. Its complete
`filter=all`, `per_page=100` inventory is exactly 11 jobs on page 1 with page
2 empty: plan and all six full pulls succeeded, rollup failed, and three jobs
skipped. The artifact inventory is exactly zero on page 1 and page 2 empty
because NIH stores commit directly to the branch. The six successful pull
commits end at `7d8dd380a616fe4b300bf626e36f39aeb2c2f460`. That terminal failed
graph must not be rerun or used as a recovery artifact source.

## Reviewed RePORTER record disappearances

The failed rollup rebuilt NIH to 711,164 applications but live validation
found nine stored application records that the complete current RePORTER
source no longer returns. Each affected fiscal year was fetched in complete
ascending and descending application-ID order and reconciled independently
to `meta.total`. One exact `appl_ids` request then queried all nine IDs with
known-live control `11126249`: the control returned and none of the nine IDs
did. Exact evidence is preserved in
`reference/nih_reporter_retraction_evidence_20260824.json`.

The nine records total exactly $1,288,767: NHLBI FY2025 IDs `nih:11161340`
and `nih:11327923`; NIA FY2026 `nih:11462449`; NIAID FY2026
`nih:11380142` and `nih:11461896`; NICHD FY2026 `nih:11286738` and
`nih:11290350`; NIEHS FY2026 `nih:11555862`; and OD FY2026
`nih:11437634`.

An exact-title, award-number, recipient, and amount web review found no news
or official notice classifying any of these nine application rows as a grant
cancellation. Several underlying awards remain active in HHS TAGGS or NIH
award listings; one exact amount has an HHS debit/re-credit transaction
sequence. These entries are therefore classified only as reviewed RePORTER
**application-record retractions or supersessions**, not grant cancellations.
The owner approved this exact classification and nine-record set on
2026-08-24.

The adapter remains fail-closed: only exact ledger IDs may be removed during
a full pull, their original award months bound the permitted monthly count
shrink, any unreviewed disappearance remains retained and warned, and any
ledger ID that returns to RePORTER triggers renewed review. No live-source
validation threshold, tolerance, pin, or residual is weakened.

## Authorized continuation

The approved ledger/evidence/test/handoff commit must be a strict child of
`7d8dd380a616fe4b300bf626e36f39aeb2c2f460`. A failed-rollup-only rerun is
not sufficient: `scripts/rollup.py` reads leaf stores but does not remove
reviewed records, while removal is intentionally confined to a full pull in
`adapters/nih_reporter.py`. Safe-cycle `.github/triggers/update.json` through
the exact then-current-main form and back to the exact six-unit full trigger,
creating one fresh graph. Require a latest logical plan, all six fresh full
pulls, live validation and rollup success, a rollup commit, and branch deploy
skipped. Then restore `.github/triggers/update.json` to the exact
then-current-main form, run current-main integration and all NIH release gates
including before/after affected-chart screenshots and footprint checks,
merge, deploy, and perform byte-exact plus light/dark live QA before resuming
the parked AHRQ release.

## Completed fresh recovery graph

The approved ledger/evidence/test/handoff commit
`169be8dacd2a500eaf2cfc1228d80649dac26fd8` is the required strict child of
the six successful pull commits at `7d8dd380a616fe4b300bf626e36f39aeb2c2f460`.
The safe trigger cycle first restored the exact main trigger in
`36b0aa77713456e740123b6c616bfae9929ba4bf`, then created fresh six-unit
source commit `05f51d82c7f416b3ee333aa5339b4335ea21362d`.

Fresh recovery run `32758515872` attempt 1 is terminal success and must not be
rerun. Its complete `filter=all`, `per_page=100` inventory is exactly 11 jobs
on page 1 with page 2 empty: plan, all six full pulls, and rollup succeeded;
the NSF pull, DMS verification, and branch deploy were skipped. Its artifact
inventory is exactly zero on page 1 with page 2 empty because the NIH workflow
commits stores directly. Each pull reported zero warnings and exact reviewed
removals: two NHLBI, one NIA, two NIAID, two NICHD, one NIEHS, and one OD.

Rollup commit `0ed512cbd150d70e9eea50e0190cd953162cc5d8`
reconciled all 28 NIH units to the current complete RePORTER source, rebuilt
NIH to exactly 711,155 unique application records, and left every validation
warning empty. The root award dashboard contains exactly 850,494 records.
The obligation registry and sentinel remain exactly 46 accounts. Weekly
trigger restore `ba39caa6c992ce67d05f933101b470d7b8da529a` is a strict child of
the rollup and restores `.github/triggers/update.json` to the exact current-
main blob `d5e7d52a547dc6d08c09c48e902fbfbdf3d8c231`.

## Exact data and chart effect

A row-level comparison of the six fresh pre-removal stores at `7d8dd380` to
the completed recovery proves that exactly the nine owner-approved IDs were
removed: there are zero additions and zero changes to any surviving row. The
exact reviewed effect is nine application records and $1,288,767: NHLBI
FY2025 decreases by two records and $54,288; NIA FY2026 by one and $55,114;
NIAID FY2026 by two and $277,410; NICHD FY2026 by two and $331,228; NIEHS
FY2026 by one and $141,727; and OD FY2026 by one and $429,000.

This causal comparison is intentionally separate from the release comparison
to git main `5df93c2`: the six required full pulls also incorporated ordinary
live RePORTER additions and transaction corrections that arrived after the
scheduled main snapshot. The resulting aggregate NIH change from that main
snapshot is 709,868 to 711,155 records, while the reviewed removal itself
remains exactly the nine rows above. No sentinel event is inferred because
these are RePORTER application-record retractions or supersessions, not
verified grant cancellations.

## Release-gate evidence

Focused NIH tests pass 19/19. The registry tier passes 325/325 with 46 unique
obligation accounts. The fast tier passes 7/7, including 242 unit tests with
one expected skip, all 28 NIH units at 711,155 records, all 132 award-ledger
invariants, obligations, USAspending calibration, the funding-action
sentinel, and the DMS baseline. The full rendered tier passes 4/4: five core
cases, 184 all-account light/dark cases, 59 public-link cases, and two
sentinel cases. The reader-review screen tier captured all 61 pages
successfully.

The chart-geometry review captured 16 additional 1440-by-1000 full-page
screenshots: before and after versions of root, NIH, NHLBI, NIA, NIAID,
NICHD, NIEHS, and OD. All 16 passed the render-complete, link-integrity,
viewport, color-scheme, network, and browser-diagnostic contracts. Visual
review found every expected cumulative-count, cumulative-dollar, monthly,
mechanism, and fiscal-year series present, with the exact endpoint movements
described above and no unexplained disappearance or broken geometry.

The assembled Pages artifact is 268,508,680 bytes across 1,682 files, leaving
731,491,320 bytes of headroom. It retains all 59 NSF award CSVs and excludes
all 446 audit-only obligation event archives. The repository is 571,283,149
tracked bytes, including 336,591,221 bytes of compressed stores; the
historical-backfill trajectory remains flagged only as a conservative upper
bound.

Branch Test run `32764893219` is terminal success. Its complete head-SHA run
inventory is exactly one run on page 1 with page 2 empty, and its complete
`filter=all`, `per_page=100` job inventory is exactly one successful job
`97552034535` on page 1 with page 2 empty. Compile/registry, fast, rendered,
Pages assembly, and footprint steps all succeeded. Git main remains exactly
`5df93c2c6a791b4aa3d97ee0f43f30e35053f968` and is an ancestor of the
recovery head, so then-current-main integration is an exact no-op rather than
a synthetic merge.
