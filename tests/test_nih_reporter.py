import json
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.nih_reporter import NihReporterPull, _award_kind


def row(appl_id, agency="NIGMS"):
    return {
        "appl_id": appl_id,
        "fiscal_year": 2025,
        "project_num": f"5R01GM{appl_id:06d}-01",
        "award_notice_date": "2025-01-15T00:00:00",
        "budget_start": "2025-02-01T00:00:00",
        "project_start_date": "2025-02-01T00:00:00",
        "award_amount": 123456,
        "award_type": "5",
        "activity_code": "R01",
        "project_title": "Example project",
        "organization": {"org_name": "Example University"},
        "agency_ic_admin": {"abbreviation": agency},
        "funding_mechanism": "Non-SBIR/STTR",
    }


class NihReporterTests(unittest.TestCase):
    def test_application_and_activity_codes_map_to_dashboard_bins(self):
        self.assertEqual(_award_kind("F32", "5"), "Fellowship")
        self.assertEqual(_award_kind("R01", "5"), "Continuing award")
        self.assertEqual(_award_kind("R01", "1"), "Standard/new award")
        self.assertEqual(_award_kind("ZIA", ""), "Other award")

    def test_two_ordered_pagination_passes_must_match(self):
        rows = [row(i) for i in range(1, 502)]

        def fake_post(payload, retries=5):
            del retries
            ordered = rows if payload["sort_order"] == "asc" else list(reversed(rows))
            offset = payload["offset"]
            limit = payload["limit"]
            return {"meta": {"total": len(rows)},
                    "results": ordered[offset:offset + limit]}

        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1000, "max_monthly": 1000},
            Path("unused"),
        )
        with patch("adapters.nih_reporter.api_post", side_effect=fake_post):
            fetched = puller.fetch_year(2025)
        self.assertEqual(set(fetched), set(range(1, 502)))

    def test_normalize_namespaces_ids_and_uses_award_notice_date(self):
        puller = NihReporterPull(
            "NIGMS", {"min_total": 0, "max_total": 1, "max_monthly": 1},
            Path("unused"),
        )
        normalized, fallback = puller.normalize(row(123))
        self.assertFalse(fallback)
        self.assertEqual(normalized["id"], "nih:123")
        self.assertEqual(normalized["date"], "2025-01-15")
        self.assertEqual(normalized["amount"], 123456)
        self.assertEqual(normalized["type"], "cont")

    def test_config_has_all_current_reporter_nih_admin_components(self):
        cfg = json.loads((Path(__file__).parents[1] / "config" / "orgs.json").read_text())
        nih = next(agency for agency in cfg["agencies"] if agency["slug"] == "nih")
        values = {division["params"]["reporter_agency"]
                  for directorate in nih["directorates"]
                  for division in directorate["divisions"]}
        self.assertEqual(values, {
            "CLC", "CSR", "CIT", "FIC", "NCATS", "NCCIH", "NCI", "NEI",
            "NHGRI", "NHLBI", "NIA", "NIAAA", "NIAID", "NIAMS", "NIBIB",
            "NICHD", "NIDA", "NIDCD", "NIDCR", "NIDDK", "NIEHS", "NIGMS",
            "NIMH", "NIMHD", "NINDS", "NINR", "NLM", "OD",
        })


if __name__ == "__main__":
    unittest.main()
