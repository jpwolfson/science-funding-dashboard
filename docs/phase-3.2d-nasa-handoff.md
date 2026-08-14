# Phase 3.2d NASA handoff

Status: Stage A registry scaffold is complete on the NASA worker branch.
Science `080-0120` is registered with its official-source exact-cent baseline
and one canonical `Science (Direct)` Program Activity. No custom-account
download, trigger, generated obligation store, rendered review, push, or pull
request has occurred.

## Staged rollout contract

NASA must be registered and backfilled in three bounded stages because the
production reconcile validates every registered store:

1. Stage A: Science (`nasa/science`), 10 FY2017–26 jobs.
2. Stage B: Aeronautics, Space Technology, and STEM Engagement, 30 jobs.
3. Stage C: Exploration and Space Operations, 20 jobs.

The coordinator owns trigger changes. The worker appends only the accounts for
the stage about to run; later empty accounts must not be pre-registered.

## Stage A evidence boundary

The official federal account is `080-0120`, titled `Science, National
Aeronautics and Space Administration`. USAspending Files A/B/C begin at FY2017
P06, so FY2015–16 are unavailable, FY2017 is partial P06–P12, FY2018–25 are
complete, and FY2026 is pinned through certified P09 as retrieved 2026-08-12.
The exact source endpoint is recorded in the baseline file.

Official PA evidence contains historical `0001 SCIENCE (DIRECT)` and current
PARK `5ZD5GGPDU49 SCIENCE (DIRECT)`. Both normalize to the single
`science-direct` identity. AAAS mission labels such as Astrophysics, Earth
Science, Heliophysics, and Planetary Science remain crosswalk context and do
not become File B Program Activity pages.

File B signed obligations remain canonical; File C and its signed residual are
separate. Science is contract-heavy, so the later backfill must retain
Assistance, Contracts, and Unlinked files and must not call File C/net a bounded
completeness percentage.

## Deferred release work

After coordinator authorization, Stage A still requires its full live
backfill, exact File B-to-baseline and File C-plus-residual reconciliation,
accepted provenance, zero warnings, fast/rendered JSON evidence, light/dark
reader review, and runtime/artifact-growth reporting. Stages B and C follow
only after the preceding stage's validated data commit is present. The worker
opens but never merges the final NASA pull request.
