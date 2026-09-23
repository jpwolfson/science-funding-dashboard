"""Shared helpers for the award-pipeline refresh-status contract.

Phase 3.2d remediation W17 -- the award-ledger analogue of W12's
``data/obligations/refresh_status.json`` (see
``scripts/reconcile_obligation_artifacts.py``): one refused leaf's pull job
no longer vetoes the weekly rollup for all 87 award units. The refused
leaf keeps its last committed store, is recorded ``stale`` in a committed
``data/refresh_status.json``, and its page (and any rollup that aggregates
it) carries a disclosed "Not refreshed since <date>" note instead of
silently shipping a rollup built from a stale leaf under no notice.

See ``docs/nih-data-validation.md``, "Award refresh, freshness, and
publication (W17)", for the full contract. Consumers:

- ``scripts/award_refresh_status.py`` builds the file from this run's
  ``_pull_ok/*.json`` markers (``build_refresh_status`` / ``check_all_missing``).
- ``scripts/rollup.py`` (and ``scripts/reaggregate.py``, via its call into
  ``rollup.main()``) stamps each leaf dashboard and computes each rollup
  node's aggregate disclosure (``stamp_leaf_refresh_status`` /
  ``aggregate_refresh_status``).
- ``scripts/validate_nih.py`` downgrades a stale unit's live-gap check from
  an error to a warning (``default_entry`` / ``is_marked_stale``).
- ``scripts/validate_award_invariants.py`` fails closed on a malformed or
  inconsistent published file (``node_leaf_map``).
"""

import json
from pathlib import Path

REFRESH_STATUS_PATH = Path("data") / "refresh_status.json"

# Owner-approved verbatim text (Phase 3.2d remediation brief; the W12
# sentence with "account" -> "unit", nothing else changed). This is both
# the header note rendered on a stale unit's own page (site/index.html,
# renderUnitStaleNote) and the published `reason` for a stale unit's own
# refresh_status.json entry, so the two are always byte-identical -- only
# the date varies. Aggregate (multi-leaf) reasons are a different,
# W12-agency-aggregate-pattern sentence; see aggregate_refresh_status.
UNIT_STALE_REASON = (
    "Not refreshed since {stale_since}: the most recent scheduled pull for "
    "this unit did not complete; figures are the last accepted snapshot."
)


def unit_stale_reason(stale_since):
    return UNIT_STALE_REASON.format(stale_since=stale_since)


def load_refresh_status(repo):
    """The published per-unit staleness map, or {} if none/invalid exists.

    A missing data/refresh_status.json means every unit is fresh (W17
    contract): callers default an absent entry to ``{"status": "fresh"}``
    via ``default_entry``.
    """
    path = Path(repo) / REFRESH_STATUS_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    units = data.get("units") if isinstance(data, dict) else None
    return units if isinstance(units, dict) else {}


def write_refresh_status(repo, entries, generated_at):
    path = Path(repo) / REFRESH_STATUS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "units": entries,
    }, indent=1, sort_keys=True) + "\n")


def default_entry(unit_refresh):
    """The unit's refresh_status.json entry, defaulted when absent.

    Mirrors scripts/reconcile_obligation_artifacts.py's own default (W12):
    a unit with no recorded entry (including a repo with no
    data/refresh_status.json at all) is "fresh".
    """
    return unit_refresh if unit_refresh else {"status": "fresh"}


def is_marked_stale(unit_refresh):
    """True only for a *properly disclosed* stale unit.

    A bare ``status: "stale"`` with no ``staleSince``/``reason`` does not
    count -- nothing may go stale silently (Phase 3.2d remediation W12,
    generalized to the award ledger as W17).
    """
    return (
        unit_refresh.get("status") == "stale"
        and bool(unit_refresh.get("staleSince"))
        and bool(unit_refresh.get("reason"))
    )


def _leaf_paths(orgs_cfg):
    return [
        f"{ag['slug']}/{dr['slug']}/{dv['slug']}"
        for ag in orgs_cfg["agencies"]
        for dr in ag["directorates"]
        for dv in dr["divisions"]
    ]


def node_leaf_map(orgs_cfg):
    """{node path: [leaf paths aggregated under it]} for the root (``""``),
    every agency, every directorate, and every leaf (mapped to itself) in
    the configured org registry. Used both by scripts/rollup.py (via each
    level's already-computed leaf list; this function is the same
    computation, kept independently reusable) and by
    scripts/validate_award_invariants.py to check a rollup node's
    published refreshStatus against exactly the leaves it aggregates.
    """
    mapping = {}
    all_leaves = []
    for ag in orgs_cfg["agencies"]:
        ag_leaves = []
        for dr in ag["directorates"]:
            dr_path = f"{ag['slug']}/{dr['slug']}"
            dr_leaves = [f"{dr_path}/{dv['slug']}" for dv in dr["divisions"]]
            mapping[dr_path] = dr_leaves
            for leaf in dr_leaves:
                mapping[leaf] = [leaf]
            ag_leaves.extend(dr_leaves)
        mapping[ag["slug"]] = ag_leaves
        all_leaves.extend(ag_leaves)
    mapping[""] = all_leaves
    return mapping


def _leaf_dashboard_generated_date(repo, path):
    dash = Path(repo) / "data" / path / "dashboard.json"
    if not dash.exists():
        return None
    try:
        data = json.loads(dash.read_text())
    except json.JSONDecodeError:
        return None
    generated = data.get("generated")
    return generated if isinstance(generated, str) else None


def build_refresh_status(repo, orgs_cfg, planned_units, markers, generated_at):
    """Per-unit freshness state for every configured leaf.

    Mirrors scripts/reconcile_obligation_artifacts.py's
    ``_build_refresh_status`` (W12), generalized from "account" to "unit".

    ``planned_units``: the unit paths this run's pull matrix planned
    (nsf_matrix + nih_matrix). A unit not in this set keeps its prior
    published entry unchanged (a scoped custom run may not touch every
    unit); a brand-new unit with no prior record defaults to fresh.

    ``markers``: {unit path: marker dict} for every `_pull_ok/<slug>.json`
    marker downloaded this run -- written only by a pull job that reached
    its commit/push step successfully (see .github/workflows/
    update-data.yml). A planned unit with no marker is stale.

    Raises ValueError if a planned unit is not a configured leaf.
    """
    leaves = set(_leaf_paths(orgs_cfg))
    planned_units = list(planned_units)
    unknown = sorted(set(planned_units) - leaves)
    if unknown:
        raise ValueError(
            f"planned unit(s) not in config/orgs.json: {unknown}"
        )
    planned_set = set(planned_units)
    previous = load_refresh_status(repo)
    result = {}
    for path in leaves:
        prior = previous.get(path) or {}
        if path not in planned_set:
            result[path] = prior if prior else {"status": "fresh"}
            continue
        if path in markers:
            marker = markers[path] or {}
            result[path] = {
                "status": "fresh",
                "lastRefreshAttemptAt": generated_at,
                "lastAcceptedAt": marker.get("completedAt") or generated_at,
            }
            continue
        if prior.get("status") == "stale" and prior.get("staleSince"):
            stale_since = prior["staleSince"]
        elif prior.get("lastAcceptedAt"):
            stale_since = prior["lastAcceptedAt"][:10]
        else:
            stale_since = (
                _leaf_dashboard_generated_date(repo, path) or generated_at[:10]
            )
        result[path] = {
            "status": "stale",
            "lastRefreshAttemptAt": generated_at,
            "lastAcceptedAt": prior.get("lastAcceptedAt"),
            "staleSince": stale_since,
            "reason": unit_stale_reason(stale_since),
        }
    return result


def check_all_missing(planned_units, markers):
    """Refuse to publish when every planned unit is missing its marker.

    The only hard failure in the W17 contract (mirrors
    scripts/reconcile_obligation_artifacts.py's
    ``_apply_missing_partition_tolerance``): a run that produced NO marker
    for ANY planned unit must not publish a snapshot where every unit is
    silently marked stale.
    """
    planned_units = list(planned_units)
    if planned_units and not any(unit in markers for unit in planned_units):
        raise ValueError(
            f"no pull-ok marker was found for any of the {len(planned_units)} "
            "planned unit(s) in this run; refusing to publish an "
            "all-units-stale snapshot (docs/nih-data-validation.md, "
            "\"Award refresh, freshness, and publication (W17)\")"
        )


def aggregate_refresh_status(leaf_paths, refresh_status, level):
    """A rollup node's own ``refreshStatus``, or None if nothing is stale.

    ``leaf_paths``: exactly the leaves this node aggregates (a directorate's
    divisions, an agency's leaves across all its directorates, or the
    root's full leaf set).
    ``level``: "directorate", "agency", or "root" -- selects only the
    reason wording (see docs/nih-data-validation.md); no agency or unit
    name is ever consulted.

    A node that aggregates exactly one leaf (an NIH passthrough
    directorate, e.g. nih/fic over nih/fic/fic) republishes that leaf's own
    entry, `unit` included, so its own page carries the single-unit header
    note. A node aggregating several leaves gets a non-uniform aggregate
    reason naming how many are stale, with no `unit` key (mirrors
    scripts/rollup_obligations.py's ``_agency_refresh_status``, W12).
    """
    entries = [
        (path, refresh_status.get(path) or {"status": "fresh"})
        for path in leaf_paths
    ]
    stale = [(path, entry) for path, entry in entries if entry.get("status") == "stale"]
    if not stale:
        return None
    if len(leaf_paths) == 1:
        path, entry = stale[0]
        return {**entry, "unit": path}
    n = len(leaf_paths)
    k = len(stale)
    stale_sinces = sorted(
        entry.get("staleSince") for _, entry in stale if entry.get("staleSince")
    )
    if level == "root":
        reason = (
            f"{k} of {n} unit(s) were not refreshed in the most recent "
            "scheduled pull; see the agency page for which unit."
        )
    else:
        reason = (
            f"{k} of {n} unit(s) in this {level} were not refreshed in the "
            f"most recent scheduled pull; see the {level} page for which unit."
        )
    return {
        "status": "stale",
        "staleSince": stale_sinces[0] if stale_sinces else None,
        "staleUnits": [path for path, _ in stale],
        "reason": reason,
    }


def stamp_leaf_refresh_status(leaf_dir, entry, unit_path):
    """Add or remove the top-level ``refreshStatus`` disclosure on one
    already-written leaf dashboard.json, touching nothing else in it.

    A leaf with no dashboard.json yet (no pull has ever landed for it) has
    nothing to stamp. Idempotent: a leaf whose dashboard already carries
    the correct value (or correctly carries none) is left byte-identical.
    """
    dash_path = Path(leaf_dir) / "dashboard.json"
    if not dash_path.exists():
        return
    data = json.loads(dash_path.read_text())
    is_stale = bool(entry) and entry.get("status") == "stale"
    if is_stale:
        new_value = {**entry, "unit": unit_path}
        if data.get("refreshStatus") == new_value:
            return
        data["refreshStatus"] = new_value
    else:
        if "refreshStatus" not in data:
            return
        del data["refreshStatus"]
    dash_path.write_text(json.dumps(data, indent=1))
