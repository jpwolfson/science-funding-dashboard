import json
import tempfile
import unittest
from pathlib import Path

from adapters.funding_source_adapters import (
    parse_doe_portfolio_announcement,
    parse_nsf_terminated_awards,
)
from scripts.update_funding_sources import update_sources


NSF_SOURCE = {
    "id": "nsf-terminated-awards",
    "adapter": "nsf_terminated_awards_csv",
    "url": "https://nsf-gov-resources.nsf.gov/files/NSF-Terminated-Awards.csv",
    "freshnessMaxDays": 10,
}

DOE_SOURCE = {
    "id": "doe-october-2025-portfolio-action",
    "adapter": "doe_portfolio_announcement",
    "url": "https://www.energy.gov/articles/energy-department-announces-termination-223-projects-saving-over-75-billion",
    "freshnessMaxDays": 10,
    "sourceTitle": "Energy Department Announces Termination of 223 Projects, Saving Over $7.5 Billion",
    "expectedFacts": {
        "effectiveDate": "2025-10-01",
        "displayDate": "October 1, 2025",
        "awardCount": 321,
        "projectCount": 223,
        "amountCents": 756_000_000_000,
        "amountQualifier": "approximately",
    },
    "expectedOffices": [
        {"name": "Office of Clean Energy Demonstrations", "abbrev": "OCED"},
        {"name": "Energy Efficiency and Renewable Energy", "abbrev": "EERE"},
        {"name": "Grid Deployment", "abbrev": "GDO"},
        {"name": "Manufacturing and Energy Supply Chains", "abbrev": "MESC"},
        {"name": "Advanced Research Projects Agency-Energy", "abbrev": "ARPA-E"},
        {"name": "Fossil Energy", "abbrev": "FE"},
    ],
}

NSF_CSV = (
    "Award ID,Directorate,Recipient,Title,Obligated,,Date of export: 6/5/2025\r\n"
    '1231319,MPS ,Harvard University,Center for Integrated Quantum Materials,"$44,434,393 ",,\r\n'
    '2433239,TIP ,Technical College,"Collaborative Research, Pilot","$399,696 ",,\r\n'
).encode()

DOE_HTML = """<!doctype html><html><body>
<h1>Energy Department Announces Termination of 223 Projects, Saving Over $7.5 Billion</h1>
<span>October 1, 2025</span>
<p>DOE today announced the termination of 321 financial awards supporting 223 projects,
resulting in a savings of approximately $7.56 billion dollars for American taxpayers.</p>
<p>The awards were issued by the Offices of Clean Energy Demonstrations (OCED),
Energy Efficiency and Renewable Energy (EERE), Grid Deployment (GDO),
Manufacturing and Energy Supply Chains (MESC), Advanced Research Projects Agency-Energy
(ARPA-E) and Fossil Energy (FE).</p>
</body></html>""".encode()


class FundingSourceAdapterTests(unittest.TestCase):
    def test_nsf_csv_preserves_structured_award_facts(self):
        result = parse_nsf_terminated_awards(NSF_CSV, NSF_SOURCE)
        self.assertEqual("2025-06-05", result["metadata"]["sourceAsOf"])
        self.assertEqual(2, result["metadata"]["recordCount"])
        event = result["events"][0]
        self.assertEqual("termination", event["eventType"])
        self.assertEqual(["1231319"], event["awardIds"])
        self.assertEqual(4_443_439_300, event["priorObligationsCents"])
        self.assertNotIn("effectiveDate", event)

    def test_nsf_schema_drift_fails_closed(self):
        broken = NSF_CSV.replace(b"Award ID", b"Award Number")
        with self.assertRaisesRegex(ValueError, "schema changed"):
            parse_nsf_terminated_awards(broken, NSF_SOURCE)

    def test_nsf_windows_1252_text_is_preserved(self):
        payload = NSF_CSV.replace(b"Harvard University", b"Recipient\x92s University")
        result = parse_nsf_terminated_awards(payload, NSF_SOURCE)
        self.assertEqual("Recipient’s University", result["events"][0]["recipient"])
        self.assertEqual("cp1252", result["metadata"]["encoding"])

    def test_doe_announcement_preserves_exact_attributed_facts(self):
        event = parse_doe_portfolio_announcement(DOE_HTML, DOE_SOURCE)["events"][0]
        self.assertEqual(("announcement", "termination"),
                         (event["eventType"], event["announcedAction"]))
        self.assertEqual("approximately $7.56 billion",
                         event["announcedAffectedValueDisplay"])
        self.assertEqual((321, 223),
                         (event["announcedAwardCount"],
                          event["announcedProjectCount"]))
        self.assertEqual(6, len(event["namedOffices"]))
        self.assertEqual([], event["awardIds"])
        for field in ("observedDeobligationCents", "eliminatedFutureValueCents",
                      "restoredValueCents"):
            self.assertNotIn(field, event)

    def test_doe_fact_drift_fails_closed(self):
        broken = DOE_HTML.replace(b"321 financial", b"320 financial")
        with self.assertRaisesRegex(ValueError, "awardCount drifted"):
            parse_doe_portfolio_announcement(broken, DOE_SOURCE)

    def test_fetch_failure_retains_last_good_source_events(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "config").mkdir()
            (root / "config" / "funding_sentinel.json").write_text(json.dumps({
                "schemaVersion": 1,
                "sources": [NSF_SOURCE, DOE_SOURCE],
            }))
            payloads = {
                NSF_SOURCE["id"]: NSF_CSV,
                DOE_SOURCE["id"]: DOE_HTML,
            }
            first = update_sources(
                root, "2026-08-11T12:00:00+00:00",
                lambda source: payloads[source["id"]],
            )
            self.assertTrue(all(row["status"] == "current" for row in first))
            before = json.loads(
                (root / "data" / "sentinel" / "sourced-events.json").read_text()
            )["events"]

            def failing_fetcher(source):
                if source["id"] == DOE_SOURCE["id"]:
                    raise ValueError("schema changed")
                return payloads[source["id"]]

            second = update_sources(
                root, "2026-08-12T12:00:00+00:00", failing_fetcher
            )
            self.assertEqual("error", second[1]["status"])
            after = json.loads(
                (root / "data" / "sentinel" / "sourced-events.json").read_text()
            )["events"]
            self.assertEqual(before, after)
            statuses = json.loads(
                (root / "data" / "sentinel" / "source-status.json").read_text()
            )["sources"]
            doe_status = next(row for row in statuses if row["id"] == DOE_SOURCE["id"])
            self.assertEqual("error", doe_status["status"])
            self.assertTrue(doe_status["lastAcceptedSha256"])


if __name__ == "__main__":
    unittest.main()
