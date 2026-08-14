# Phase 3.2d earth, environment, and agriculture handoff

Status: Stage A registry scaffold is complete on the staged worker branch.
Only USGS Surveys, Investigations and Research (\`014-0804\`) and EPA Science
and Technology (\`068-0107\`) are registered in this stage. No custom-account
download, trigger, generated obligation store, push, pull request, CI run, or
remote action has occurred.

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

## Deferred release work

This local scaffold is not release-ready. Each authorized stage still requires
its serialized File B/File C backfill, exact baseline reconciliation, accepted
provenance, zero warnings, rendered review, and coordinator integration.
