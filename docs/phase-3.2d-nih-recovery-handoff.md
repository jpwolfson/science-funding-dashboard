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
