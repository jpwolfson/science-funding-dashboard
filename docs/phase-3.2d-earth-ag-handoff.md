# Phase 3.2d earth, environment, and agriculture handoff

Status: Stage A run \`31787669479\` is terminal with 20 success (plan plus 19
pulls), one failure (EPA FY2022), and reconcile/deploy skipped. Only USGS
Surveys, Investigations and Research (\`014-0804\`) and EPA Science and
Technology (\`068-0107\`) are registered in this stage. The owner approved the
exact dual File A/File B pin representation for EPA FY2022 on 2026-08-14;
repair, bounded rerun, and atomic reconciliation remain pending.

## Serialized payload contract

The reviewed ten-account scaffold is split into four reconciliation-safe
payloads. Later accounts remain unregistered until their stage commit:

1. Stage A: \`doi/usgs-sir,epa/science-technology\` — 20 jobs.
2. Stage B: \`usda/ars-salaries-expenses,usda/ars-buildings-facilities,usda/forest-rangeland-research\` — 30 jobs.
3. Stage C: \`usda/nifa-extension,usda/nifa-research-education,usda/nifa-integrated-activities\` — 30 jobs.
4. Stage D: \`usda/ers,usda/nass\` — 20 jobs.

Each selector covers FY2017–FY2026: FY2017 uses the declared P6 source
boundary and plans P12, FY2018–FY2025 plan P12, and FY2026 is pinned to P9.
The coordinator owns triggers and all remote execution.

## Stage A evidence and semantic boundary

The official accounts are \`014-0804\`, titled \`Surveys, Investigations and
Research, Geological Survey\`, and \`068-0107\`, titled \`Science and
Technology, Environmental Protection Agency\`. Exact source endpoints and
FY2017–FY2026 GTAS/File A cents are pinned in their baseline files; FY2015 and
FY2016 are explicitly unavailable because Files A/B/C begin in FY2017 P6.

USGS-wide AAAS mission labels remain alternate context rather than synthetic
accounts or Program Activities. Reused USGS PAC \`0002\` names remain distinct
canonical identities. EPA's eight FY2026 mission PARK tokens remain distinct
from its legacy PAC/PAN identities; no legacy activity is silently mapped to a
current mission.

File B signed obligations remain canonical. File C and its signed residual are
separate award-financial detail; a low or negative signed File C ratio is not a
completeness percentage or evidence that File B is incomplete.

EPA FY2022 is the one owner-approved source-warning exception. Retained P12
File B and the independent official Program Activity endpoint both total
\`78,077,137,843\` cents; the official GTAS/File A pin is
\`78,078,798,237\` cents, an exact \`1,660,394\`-cent variance. The baseline
preserves all three values and a Data Broker A19 reason. No tolerance or
synthetic ledger event is permitted; accepted provenance must reproduce the
exact File B ledger total while retaining the File A account pin.

## Deferred release work

This local scaffold is not release-ready. Each authorized stage still requires
its serialized File B/File C backfill, exact baseline reconciliation, accepted
provenance, zero warnings, rendered review, and coordinator integration.
