"""Contract test for the uniform verification regime (docs/verification-regime.md).

GOVERNING PRINCIPLE: the verification regime is uniform across agencies. The
verifier contains universal invariants only; every agency-specific fact is a
declared parameter in that account's registry entry
(config/obligation_accounts.json) or baseline file
(reference/*_obligation_baseline.json). No agency-conditional code paths in
any verifier.

This test enforces that mechanically: no registry agency/account slug may
appear as a string literal in the shared verifier modules. The slug list is
derived from the registry itself at test time, so a newly onboarded agency
is covered automatically without ever touching this file.

scripts/validate_funding_sentinel.py is intentionally excluded. Its DOE
October 2025 announcement pins ("doe-october-2025-portfolio-action" etc.)
are per-SOURCE content pins that hold one sourced event's structured fields
constant (see Phase 3.2c-2) -- sentinel scope, not obligation-account
verification -- so they are not a violation of this contract and are not
flagged here.
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECKED_FILES = (
    "scripts/verify.py",
    "scripts/validate_obligations.py",
    "scripts/validate_award_invariants.py",
    "scripts/smoke_obligation_pages.py",
)


def registry_slugs():
    config = json.loads(
        (REPO / "config" / "obligation_accounts.json").read_text()
    )
    slugs = set()
    for account in config.get("accounts", []):
        path = account.get("path", "")
        segments = [segment for segment in path.split("/") if segment]
        slugs.update(segments)
        if path:
            slugs.add(path)
    # Slugs shorter than 3 characters are too collision-prone against
    # ordinary English words/identifiers to check as a whole-word literal
    # (there are none in the registry today; this guards future entries).
    return {slug for slug in slugs if len(slug) >= 3}


class UniformityContractTests(unittest.TestCase):
    def test_no_registry_slug_is_a_string_literal_in_shared_verifiers(self):
        slugs = registry_slugs()
        self.assertTrue(slugs, "expected at least one registry slug to check")
        violations = []
        for rel_path in CHECKED_FILES:
            text = (REPO / rel_path).read_text()
            for slug in sorted(slugs):
                pattern = re.compile(r"(?<![\w/-])" + re.escape(slug) + r"(?![\w/-])")
                if pattern.search(text):
                    violations.append(f"{rel_path}: contains registry slug {slug!r}")
        self.assertEqual(
            [], violations,
            "shared verifiers must read agency-specific facts from the "
            "registry/baseline, never hardcode them:\n" + "\n".join(violations),
        )

    def test_funding_sentinel_validator_is_deliberately_excluded(self):
        self.assertNotIn(
            "scripts/validate_funding_sentinel.py", CHECKED_FILES,
            "the sentinel validator's DOE-announcement pins are per-source "
            "content pins, not account verification -- see module docstring",
        )


if __name__ == "__main__":
    unittest.main()
