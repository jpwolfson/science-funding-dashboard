#!/usr/bin/env python3
"""Build the non-blocking funding-action sentinel from committed stores."""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adapters.funding_sentinel import build


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--as-of", help="ISO date used for deterministic builds")
    args = parser.parse_args()
    dashboard = build(args.repo, args.as_of)
    summary = dashboard["summary"]
    print(
        f"Built {summary['episodeCount']} sentinel episodes from "
        f"{summary['financialObservationCount']} financial observations, "
        f"{summary['sourcedEventCount']} sourced events, and "
        f"{summary['reviewFindingCount']} optional findings."
    )


if __name__ == "__main__":
    main()
