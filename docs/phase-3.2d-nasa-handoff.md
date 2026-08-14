# Phase 3.2d NASA handoff

Status: Stage A is complete and live through PR
[#34](https://github.com/jpwolfson/science-funding-dashboard/pull/34).
Science `080-0120` has ten accepted FY2017--FY2026 partitions, its exact-cent
baseline, the canonical `Science (Direct)` Program Activity, dashboards, and
combined sentinel coverage. Stages B and C remain deliberately deferred.

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
separate. The accepted backfill retains Assistance, Contracts, and Unlinked
files and does not call File C/net a bounded completeness percentage.

## Stage A accepted release evidence

Durable run
[`31776315157`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/31776315157)
completed with 13 logical jobs: plan, all ten account-year pulls, and reconcile
succeeded (12 successes); the branch-only deploy job was skipped. Reconcile
atomically committed `f6b918ac8b0efcee1907ce43ee8142e096b9bd86`, and PR
#34 merged it at `dba5ea7c5e6db7076ebfe9ea43a4b5a2ad544a08` after current-main
integration and exact trigger restoration.

Across all ten accepted years, File A and canonical File B each total
`6,836,252,778,705` cents. File C totals `5,836,343,689,260` cents and the
explicit residual totals `999,909,089,445` cents, so File C plus residual
equals File B exactly. File C/net is `85.37343305151431%`. The store contains
90,546 signed events normalized from 420,211 parsed rows in 113 accepted
download snapshots; no Program Activity remains unmapped and validation has
zero warnings.

The Science subtree is 30,508,064 bytes; compressed event partitions are
28,873,162 bytes and provenance records are 194,814 bytes. The serialized run
elapsed 2h47m59s and reconciliation ran 9m24s. NASA tests passed 5/5, registry
10/10, whole registry 122/122, fast 7/7, and rendered 3/3 including 68
all-account light/dark cases. The 22-page screenshot pack and live Science
account/activity pages passed reader review.

## Remaining rollout work

Stage B must materialize Aeronautics, Space Technology, and STEM Engagement
atomically before Stage C appends Exploration and Space Operations. Each stage
still requires its own source run, exact reconciliation, trigger restoration,
current-main integration, PR, deploy, and live reader review. The worker opens
but never merges those future NASA pull requests.
