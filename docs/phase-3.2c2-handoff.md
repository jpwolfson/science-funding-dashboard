# Phase 3.2c-2 handoff

Status: source pilots complete on 2026-08-11. Phase 3.2c is launch-green without
financial-account expansion or manual review.

## Delivered source adapters

- `adapters/funding_source_adapters.py` implements two bounded, fail-closed
  parsers. It hashes the exact raw bytes before normalization and rejects empty,
  oversized, malformed, duplicate, or schema-drifted responses.
- The NSF adapter ingests the official terminated-awards CSV. The first
  accepted export is dated June 5, 2025 and contains 1,667 unique award IDs.
  Each normalized record preserves directorate, recipient, title, source-listed
  prior obligations, and an identifier-backed NSF award link. The source does
  not supply an award-specific termination date or reason, so neither is
  inferred.
- The DOE adapter watches the official October 1, 2025 portfolio announcement.
  It preserves the attributed facts “approximately $7.56 billion,” 321 awards,
  223 projects, and the six named offices: Office of Clean Energy
  Demonstrations (OCED), Energy Efficiency and Renewable Energy (EERE), Grid
  Deployment (GDO), Manufacturing and Energy Supply Chains (MESC), Advanced
  Research Projects Agency-Energy (ARPA-E), and Fossil Energy (FE).
- The DOE page publishes no award identifiers. Its event is therefore an
  attributed announcement of termination with no inferred award match and no
  financial-account join.

## Evidence boundaries

Announcement, termination, suspension, appeal, closeout, litigation,
deobligation, supersession, and restoration are supported as distinct event
types. The DOE record uses `eventType: announcement` plus
`announcedAction: termination`; a later lifecycle step cannot silently rewrite
it. Tests specifically prove that announcement, appeal, closeout, litigation,
deobligation, and restoration retain separate stable IDs inside one episode.

Amounts also remain non-interchangeable. The schema keeps announced affected
value, source-listed prior obligations, observed deobligation, eliminated
future value, and restored value in separate exact-cent fields. The DOE event
populates only announced affected value and its “approximately” qualifier.
NSF's `Obligated` column populates only prior obligations.

## Failure and workflow behavior

`scripts/update_funding_sources.py` fetches every registered source before the
independent weekly sentinel build. Successful snapshots update the accepted
hash, source-as-of date, record count, and content-change history. A failed
fetch or parser records an error but retains the last good events and hash. The
script exits successfully because a stale/error source is a publishable state,
not a reason to block unrelated publication.

The source update remains confined to `data/sentinel`. Award pulls, obligation
pulls, rollups, validators, and deploys have no review or source-adapter
dependency. No GitHub Issue, agent finding, human approval, new obligation
account, or six-office financial backfill was required for this phase.

## First accepted output

- 1,667 NSF source-backed termination records, correlated into one portfolio
  episode to avoid treating the list as 1,667 independent alarms.
- One DOE termination-announcement event with the exact source facts above.
- Nine existing File C financial observations remain separate and correlate
  into eight unreviewed financial episodes.
- The generated dashboard contains 1,668 sourced events and 10 total episodes,
  with zero optional review findings.
- The public source-freshness table exposes source-as-of dates, record counts,
  last acceptance, and last attempt. The NSF portfolio is compactly summarized
  in the UI while all normalized award records remain in dashboard JSON.

## Release checks

- Source parser unit tests cover exact DOE facts, all six offices, schema/fact
  drift, Windows-1252 NSF text, exact obligated-dollar parsing, and last-good
  retention after failure.
- Sentinel unit tests cover separate lifecycle records and the existing
  financial-observation/episode contracts.
- The fail-closed validator checks registry uniqueness and HTTPS URLs, first
  source attempts, snapshot history, active-event/source-hash agreement,
  amount/count types, exact DOE facts, office attribution, and absence of
  financial-effect fields on the announcement.
- Rendered browser checks require the exact DOE qualifier, counts, and all six
  office names in wide/light and narrow/dark views.

The eight-week cost measurement remains a non-blocking operational follow-up.
It does not keep this phase open and does not delay Phase 3.2d+ account fan-out.
