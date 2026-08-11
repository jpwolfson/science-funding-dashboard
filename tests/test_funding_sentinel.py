import unittest

from adapters.funding_sentinel import (
    accept_source_snapshot,
    apply_source_freshness,
    build_coverage,
    build_episodes,
    detect_financial_observations,
    episode_id,
    record_source_failure,
)
from adapters.obligation_common import normalize_event


def ledger_event(event_id, amount, period="FY2025P02", award_id="A1",
                 gross_positive=None, gross_negative=None,
                 source="file_c", program="0001"):
    row = normalize_event({
        "id": event_id,
        "source": source,
        "submissionPeriod": period,
        "federalAccount": "089-0222",
        "programActivityCode": program,
        "programActivityName": "Basic Energy Sciences",
        "amountCents": amount,
        "awardId": award_id if source == "file_c" else "",
        "linked": source == "file_c",
        "recipient": f"Recipient {award_id}",
        "grossPositiveCents": (max(amount, 0) if gross_positive is None
                               else gross_positive),
        "grossNegativeCents": (min(amount, 0) if gross_negative is None
                               else gross_negative),
    })
    row["accountPath"] = "doe/sc"
    return row


DETECTOR = {
    "materialGrossNegativeCents": 2_500,
    "clusterGrossNegativeCents": 2_500,
    "clusterMinimumDistinctAwards": 5,
}


class FundingSentinelTests(unittest.TestCase):
    def test_coverage_contract_comes_from_both_registries(self):
        accounts = {"089-0222": {
            "path": "doe/sc", "agency": "Department of Energy",
            "name": "Office of Science", "abbrev": "DOE SC",
            "federalAccount": "089-0222",
        }}
        coverage = build_coverage(accounts, [{
            "id": "doe-actions", "name": "DOE portfolio actions",
        }])
        self.assertEqual("089-0222", coverage["financialAccounts"][0]
                         ["federalAccount"])
        self.assertEqual("doe-actions", coverage["authoritativeSources"][0]["id"])
        self.assertIn("not evidence", coverage["disclaimer"])

    def test_gross_negative_triggers_when_net_is_positive_and_residual_never_does(self):
        mixed = ledger_event(
            "mixed", 7_500, gross_positive=10_000, gross_negative=-2_500
        )
        residual = ledger_event(
            "residual", -100_000, source="file_b_residual", award_id=""
        )
        observations = detect_financial_observations(
            [residual, mixed], DETECTOR, "2026-08-11"
        )
        self.assertEqual(1, len(observations))
        self.assertEqual(["mixed"], observations[0]["ledgerEventIds"])
        self.assertEqual(-2_500, observations[0]["grossNegativeCents"])
        self.assertEqual(7_500, observations[0]["netActivityCents"])

    def test_cluster_groups_awards_and_recurring_periods_share_one_episode(self):
        rows = []
        for period in ("FY2025P02", "FY2025P03"):
            for index in range(5):
                rows.append(ledger_event(
                    f"{period}-{index}", -600, period=period,
                    award_id=f"A{index}",
                ))
        observations = detect_financial_observations(
            rows, DETECTOR, "2026-08-11"
        )
        self.assertEqual(2, len(observations))
        self.assertTrue(all(row["ruleIds"] == ["portfolio-cluster"]
                            for row in observations))
        episodes = build_episodes(observations, [], [], "2026-08-11")
        self.assertEqual(1, len(episodes))
        self.assertEqual(5, len(episodes[0]["awardIds"]))
        self.assertEqual(-6_000, episodes[0]["grossNegativeCents"])

    def test_ids_are_stable_and_removed_observations_are_superseded(self):
        rows = [ledger_event("one", -3_000), ledger_event("two", -4_000,
                                                          award_id="A2")]
        first = detect_financial_observations(rows, DETECTOR, "2026-08-10")
        reordered = detect_financial_observations(
            list(reversed(rows)), DETECTOR, "2026-08-11", first
        )
        self.assertEqual([row["id"] for row in first],
                         [row["id"] for row in reordered])
        retained = detect_financial_observations(
            rows[:1], DETECTOR, "2026-08-12", reordered
        )
        self.assertEqual(2, len(retained))
        self.assertEqual(1, len([row for row in retained if not row["active"]]))

    def test_source_failure_preserves_last_good_snapshot(self):
        event = {
            "sourceRecordId": "official-1",
            "episodeKey": "portfolio|089-0222|0001|FY2025",
            "eventType": "termination",
            "effectiveDate": "2026-07-01",
            "sourceUrl": "https://example.gov/actions/1",
            "sourceSha256": "b" * 64,
            "announcedAffectedValueCents": 50_000,
        }
        accepted, statuses = accept_source_snapshot(
            [], [], "agency-list", [event], "a" * 64,
            "2026-08-10T12:00:00+00:00",
        )
        failed = record_source_failure(
            statuses, "agency-list", "2026-08-11T12:00:00+00:00",
            "schema changed",
        )
        self.assertEqual(1, len(accepted))
        self.assertEqual("error", failed[0]["status"])
        self.assertEqual(statuses[0]["lastAcceptedSha256"],
                         failed[0]["lastAcceptedSha256"])
        self.assertEqual(statuses[0]["acceptedEventIds"],
                         failed[0]["acceptedEventIds"])

    def test_source_becomes_stale_without_losing_last_good_snapshot(self):
        statuses = [{
            "id": "agency-list", "status": "current",
            "lastAcceptedAt": "2026-07-01T12:00:00+00:00",
            "lastAcceptedSha256": "a" * 64,
            "acceptedEventIds": ["source-event-1"],
        }]
        stale = apply_source_freshness(statuses, [{
            "id": "agency-list", "name": "Agency list",
            "freshnessMaxDays": 10,
        }], "2026-08-11")
        self.assertEqual("stale", stale[0]["status"])
        self.assertEqual(41, stale[0]["ageDays"])
        self.assertEqual(["source-event-1"], stale[0]["acceptedEventIds"])

    def test_episode_states_keep_source_review_and_restoration_distinct(self):
        observation = detect_financial_observations(
            [ledger_event("one", -3_000)], DETECTOR, "2026-08-11"
        )[0]
        key = observation["episodeKey"]
        termination = {
            "id": "event-1", "episodeKey": key, "eventType": "termination",
            "effectiveDate": "2026-07-01", "awardIds": ["A1"],
        }
        confirmed = build_episodes(
            [observation], [termination], [], "2026-08-11"
        )
        self.assertEqual("source-confirmed-event", confirmed[0]["state"])
        review = {
            "id": "review-1", "episodeId": episode_id(key),
            "finding": "confirmed-status-event", "reviewedAt": "2026-08-01",
        }
        reviewed = build_episodes(
            [observation], [termination], [review], "2026-08-11"
        )
        self.assertEqual("reviewed-finding", reviewed[0]["state"])
        restoration = {
            "id": "event-2", "episodeKey": key, "eventType": "restoration",
            "effectiveDate": "2026-08-05", "awardIds": ["A1"],
        }
        restored = build_episodes(
            [observation], [termination, restoration], [review], "2026-08-11"
        )
        self.assertEqual("restored", restored[0]["state"])


if __name__ == "__main__":
    unittest.main()
