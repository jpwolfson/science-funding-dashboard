import json
import unittest
from pathlib import Path

from adapters.obligation_common import cents
from adapters.usaspending_obligations import alias_map, _pa
from scripts.plan_obligation_refresh import plan


REPO = Path(__file__).resolve().parent.parent

# The full Phase 3.2e scope (docs/phase-3.2e-handoff.md): federal account ->
# expected registry path. Discovery lands in three chunks
# (reference/sizing/nih_registry_discovery_{1,2,3}.json) landing over time;
# reference/sizing/build_nih_registry.py turns whatever chunks are present
# into registry entries. This module deliberately asserts only against
# whichever subset of FULL_SCOPE is currently registered, so it passes
# unchanged at 9/27 accounts today and again once the remaining 18 land --
# it is the exact-scope assertion in test_registered_accounts_are_within_the_scope
# that tightens automatically once every account is present.
FULL_SCOPE = {
    "075-0807": "hhs/nih-nlm",
    "075-0819": "hhs/nih-fic",
    "075-0837": "hhs/arpa-h",
    "075-0838": "hhs/nih-bf",
    "075-0843": "hhs/nih-nia",
    "075-0844": "hhs/nih-nichd",
    "075-0846": "hhs/nih-od",
    "075-0849": "hhs/nih-nci",
    "075-0851": "hhs/nih-nigms",
    "075-0862": "hhs/nih-niehs",
    "075-0872": "hhs/nih-nhlbi",
    "075-0873": "hhs/nih-nidcr",
    "075-0875": "hhs/nih-ncats",
    "075-0884": "hhs/nih-niddk",
    "075-0885": "hhs/nih-niaid",
    "075-0886": "hhs/nih-ninds",
    "075-0887": "hhs/nih-nei",
    "075-0888": "hhs/nih-niams",
    "075-0889": "hhs/nih-ninr",
    "075-0890": "hhs/nih-nidcd",
    "075-0891": "hhs/nih-nhgri",
    "075-0892": "hhs/nih-nimh",
    "075-0893": "hhs/nih-nida",
    "075-0894": "hhs/nih-niaaa",
    "075-0896": "hhs/nih-nccih",
    "075-0897": "hhs/nih-nimhd",
    "075-0898": "hhs/nih-nibib",
}

# Exact Program Activity code sets confirmed from discovery chunk 1
# (reference/sizing/nih_registry_discovery_1.json, 9 accounts). Accounts not
# yet discovered are exercised only by the generic checks below.
EXPECTED_CODES = {
    "hhs/nih-nlm": {"0000", "0024", "0801"},
    "hhs/nih-bf": {"0000", "0026", "0801"},
    "hhs/nih-od": {"0000", "0025", "0801"},
    "hhs/nih-niehs": {"0000", "0010", "0801"},
    "hhs/nih-ncats": {"0000", "0028", "0801"},
    "hhs/nih-ninds": {"0000", "0005", "0801"},
    "hhs/nih-ninr": {"0000", "0017", "0801"},
    "hhs/nih-nimh": {"0000", "0014", "0801"},
    "hhs/nih-nccih": {"0000", "0021", "0801"},
}


def _load_discovery():
    """Merge every reference/sizing/nih_registry_discovery_*.json chunk
    currently on disk. Returns {} if none are present."""
    merged = {}
    discovery_dir = REPO / "reference" / "sizing"
    for chunk_path in sorted(discovery_dir.glob("nih_registry_discovery_*.json")):
        chunk = json.loads(chunk_path.read_text())
        merged.update(chunk.get("accounts", {}))
    return merged


class NIHObligationOnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = json.loads(
            (REPO / "config" / "obligation_accounts.json").read_text()
        )
        cls.accounts = {
            row["path"]: row for row in registry["accounts"]
            if row["federalAccount"] in FULL_SCOPE
        }
        cls.crosswalk = json.loads(
            (REPO / "reference" / "aaas_federal_account_crosswalk.json").read_text()
        )["rows"]
        cls.discovery = _load_discovery()

    def test_registered_accounts_are_within_the_scope(self):
        self.assertTrue(self.accounts, "no NIH obligation accounts registered yet")
        self.assertLessEqual(len(self.accounts), len(FULL_SCOPE))
        for path, account in self.accounts.items():
            self.assertEqual(
                FULL_SCOPE[account["federalAccount"]], path,
                f"{account['federalAccount']} registered at unexpected path {path!r}",
            )
        # Once every discovery chunk has landed and been onboarded, the
        # registry must carry the exact 27-account scope -- no more, no
        # fewer -- rather than silently accepting a partial or padded set.
        if len(self.accounts) == len(FULL_SCOPE):
            self.assertEqual(
                set(FULL_SCOPE),
                {account["federalAccount"] for account in self.accounts.values()},
            )

    def test_accounts_resolve_to_a_resolved_crosswalk_row(self):
        for path, account in self.accounts.items():
            symbol = account["federalAccount"]
            matches = [
                row for row in self.crosswalk
                if any(item.get("code") == symbol
                       for item in row.get("federal_accounts", []))
            ]
            self.assertTrue(matches, f"{path}: no crosswalk row references {symbol}")
            self.assertTrue(
                all(row["status"] == "resolved" for row in matches),
                f"{path}: not every crosswalk row referencing {symbol} is resolved",
            )

    def test_baselines_carry_reviewed_file_a_pins_before_backfill(self):
        """Coordinator decision 2026-09-24 (superseding the earlier NSF
        pinless-scaffold approach, obsolete since
        adapters.obligation_common.baseline_pin_problems started requiring
        an integer ``obligationsCents`` on every non-``unavailable`` row):
        NIH scaffolds follow the current hhs/ahrq and dod/* precedent and
        carry REVIEWED File A/GTAS pins from the official federal-account
        endpoint (docs/phase-3.2d-other-civilian-handoff.md "AHRQ release"),
        not empty placeholders -- scripts/pull_obligation_account.py's
        ``pull()`` runs the identical pin-shape check on every existing pin
        before downloading, so a pinless scaffold would fail every backfill
        job outright.
        """
        for path, account in self.accounts.items():
            baseline = json.loads((REPO / account["baseline"]).read_text())
            self.assertEqual(2, baseline["schemaVersion"])
            self.assertEqual(account["federalAccount"], baseline["federalAccount"])
            self.assertTrue(baseline.get("source"))
            years = baseline["fiscalYears"]
            first_fy = account["availability"]["firstFiscalYear"]
            first_period = account["availability"]["firstFiscalYearPeriod"]
            self.assertEqual(set(map(str, range(2015, 2027))), set(years))
            for fy in range(2015, first_fy):
                self.assertEqual("unavailable", years[str(fy)]["status"])
                self.assertTrue(years[str(fy)].get("reason"))

            first_row = years[str(first_fy)]
            self.assertEqual("partial", first_row["status"])
            self.assertEqual(12, first_row["asOfPeriod"])
            self.assertEqual(first_period, first_row["firstPeriod"])
            self.assertIsInstance(first_row["obligationsCents"], int)

            for fy in range(first_fy + 1, 2026):
                row = years[str(fy)]
                self.assertEqual({"status", "obligationsCents"}, set(row),
                                  f"{path} FY{fy}")
                self.assertEqual("complete", row["status"])
                self.assertIsInstance(row["obligationsCents"], int)

            row_2026 = years["2026"]
            self.assertEqual("partial", row_2026["status"])
            self.assertIsInstance(row_2026["asOfPeriod"], int)
            self.assertIsInstance(row_2026["obligationsCents"], int)

            store = REPO / "data" / "obligations" / path / "events"
            if store.exists():
                # A real CI backfill may have advanced/replaced these pins
                # (e.g. FY2026's asOfPeriod moving forward); only the shape
                # asserted above still applies, not an exact discovery match.
                continue
            discovery_account = self.discovery.get(account["federalAccount"])
            if not discovery_account:
                continue
            for fy in range(first_fy, 2027):
                fy_row = discovery_account["fiscalYears"][str(fy)]
                file_a_cents = cents(fy_row["accountRecord"]["total_obligated_amount"])
                self.assertEqual(
                    fy_row["fileB"]["totalCents"], file_a_cents,
                    f"{path} FY{fy}: discovery File A/File B mismatch",
                )
                self.assertEqual(
                    file_a_cents, years[str(fy)]["obligationsCents"],
                    f"{path} FY{fy}: baseline pin does not match discovery File A",
                )

    def test_full_backfill_plan_selects_every_scaffold_year(self):
        jobs = plan(repo=REPO, mode="full", selectors=",".join(self.accounts))["include"]
        by_account = {}
        for job in jobs:
            by_account.setdefault(job["account"], []).append((job["fiscalYear"], job["period"]))
        self.assertEqual(set(self.accounts), set(by_account))
        for path, rows in by_account.items():
            first_fy = self.accounts[path]["availability"]["firstFiscalYear"]
            expected = [(fy, 12) for fy in range(first_fy, 2026)] + [(2026, 10)]
            self.assertEqual(expected, rows)

    def test_program_activity_identities_are_unique_and_alias_map_resolves(self):
        for path, account in self.accounts.items():
            activities = account["programActivities"]
            codes = [row["code"] for row in activities]
            slugs = [row["slug"] for row in activities]
            parks = [row["park"] for row in activities if row.get("park")]
            self.assertEqual(len(codes), len(set(codes)), f"{path}: duplicate PA code")
            self.assertEqual(len(slugs), len(set(slugs)), f"{path}: duplicate PA slug")
            self.assertEqual(len(parks), len(set(parks)), f"{path}: duplicate PA PARK")
            if path in EXPECTED_CODES:
                self.assertEqual(EXPECTED_CODES[path], set(codes))

            aliases = alias_map(account)
            for activity in activities:
                code4 = str(activity["code"]).zfill(4)
                pair = ("code-name", code4, activity["name"].strip().lower())
                self.assertEqual(activity["slug"], aliases[pair]["slug"])
                self.assertEqual(activity["slug"], aliases[("code", code4)]["slug"])
                if activity.get("park"):
                    self.assertEqual(
                        activity["slug"], aliases[("park", activity["park"])]["slug"],
                    )

    def test_every_observed_discovery_identity_resolves_through_pa(self):
        """Fail-closed alias-drift gate (docs/phase-3.2e-handoff.md): every
        (code, name, PARK) identity actually observed in discovery data --
        official per-account Program Activity lists and every fiscal year's
        File B rows -- must resolve through the exact adapter logic
        (alias_map + _pa) used at pull time, the same self-check
        reference/sizing/build_nih_registry.py runs at generation time.
        """
        for path, account in self.accounts.items():
            symbol = account["federalAccount"]
            discovery_account = self.discovery.get(symbol)
            if not discovery_account:
                continue
            aliases = alias_map(account)
            observed = set()
            for item in discovery_account.get("officialProgramActivities") or []:
                if item.get("type") == "PARK":
                    observed.add((None, item.get("name") or "", item["code"]))
                else:
                    observed.add((item["code"], item.get("name") or "", None))
            for fy_row in (discovery_account.get("fiscalYears") or {}).values():
                file_b = fy_row.get("fileB")
                if not file_b:
                    continue
                for pa in file_b.get("programActivities", []):
                    observed.add((pa.get("code") or "", pa.get("name") or "",
                                  pa.get("park") or ""))
            for code, name, park in observed:
                row = {
                    "program_activity_reporting_key": park or "",
                    "program_activity_code": code or "",
                    "program_activity_name": name or "",
                }
                try:
                    _pa(row, aliases)
                except Exception as error:  # noqa: BLE001
                    self.fail(
                        f"{path}: identity code={code!r} name={name!r} "
                        f"park={park!r} did not resolve via alias_map()/_pa(): {error}"
                    )


if __name__ == "__main__":
    unittest.main()
