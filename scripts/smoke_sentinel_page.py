#!/usr/bin/env python3
"""Render the funding-action sentinel in wide/light and narrow/dark modes."""

import argparse
import json
import os
import sys
import tempfile
import threading
from functools import partial
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import time

from scripts.smoke_obligation_pages import (
    DevToolsSocket,
    Links,
    QuietHandler,
    _start_chrome,
    _stop_chrome,
    chrome_path,
    render_page,
)
from scripts.assemble_pages_site import assemble_pages_site, rendered_link_problems

# The layout metrics expression below finds the last VISIBLE episode card
# (excluding cards collapsed inside a closed <details> overflow block, which
# a browser does not lay out or paint) and checks it against the document
# and the notes footer. Written as one expression so a single
# Runtime.evaluate call gets every measurement.
_LAYOUT_METRICS_EXPRESSION = """
(() => {
  // A card inside a closed <details> is not laid out for real (Chromium
  // gives it content-visibility: hidden, which can still report a nonzero,
  // stale getBoundingClientRect() for the element itself even though it
  // contributes nothing to its ancestors' layout) -- so visibility is
  // decided structurally: is any ancestor <details> present and closed.
  const isCollapsed = card => { const d = card.closest('details'); return Boolean(d) && !d.open; };
  const cards = Array.from(document.querySelectorAll('article.card'))
    .filter(card => !isCollapsed(card));
  const last = cards[cards.length - 1];
  const notes = document.getElementById('notes');
  const confirmed = document.getElementById('confirmed');
  const doc = document.documentElement;
  if (!last || !notes) {
    return { ok: false, reason: 'missing last visible card or #notes',
             visibleCardCount: cards.length, hasNotes: Boolean(notes) };
  }
  const cardRect = last.getBoundingClientRect();
  const notesRect = notes.getBoundingClientRect();
  const docHeight = doc.scrollHeight;
  const clippedInternally = last.scrollHeight > last.clientHeight + 1;
  const withinDocument = cardRect.bottom <= docHeight + 1 && cardRect.right <= doc.scrollWidth + 1;
  const notesAfterCard = notesRect.top >= cardRect.bottom - 1;
  const notesNonEmpty = notes.textContent.trim().length > 0;
  return {
    ok: withinDocument && !clippedInternally && notesAfterCard && notesNonEmpty,
    reason: !withinDocument ? 'last card extends beyond the document'
      : clippedInternally ? 'last card content is clipped (scrollHeight > clientHeight)'
      : !notesAfterCard ? 'notes section does not follow the last card'
      : !notesNonEmpty ? 'notes section is empty' : 'ok',
    visibleCardCount: cards.length, docHeight,
    cardBottom: cardRect.bottom, notesTop: notesRect.top,
    hasConfirmedAnchor: Boolean(confirmed),
  };
})()
"""


def _layout_metrics(executable, url, width=1100, height=900, timeout=20):
    """Render `url` and evaluate _LAYOUT_METRICS_EXPRESSION against the live
    DOM. A minimal, self-contained DevTools session (built from the same
    primitives render_page() uses) rather than a change to the shared
    render_page() helper, which returns only html/text/diagnostics."""
    with tempfile.TemporaryDirectory() as profile_root:
        process, page = _start_chrome(executable, profile_root)
        client = None
        try:
            client = DevToolsSocket(page["webSocketDebuggerUrl"])
            client.call("Page.enable")
            client.call("Runtime.enable")
            client.call("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height, "deviceScaleFactor": 1,
                "mobile": False,
            })
            client.call("Page.navigate", {"url": url})
            deadline = time.monotonic() + timeout
            while True:
                state = client.call("Runtime.evaluate", {
                    "expression": "({complete:document.documentElement.dataset.renderComplete||null,error:document.documentElement.dataset.renderError||null})",
                    "returnByValue": True,
                })["result"].get("value", {})
                if state.get("complete") or state.get("error"):
                    if state.get("error"):
                        raise AssertionError(f"page render error before layout check: {state['error']}")
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("page render marker timed out")
                time.sleep(0.1)
            result = client.call("Runtime.evaluate", {
                "expression": _LAYOUT_METRICS_EXPRESSION, "returnByValue": True,
            })["result"]["value"]
            return result
        finally:
            if client:
                try:
                    client.close()
                except OSError:
                    pass
            _stop_chrome(process)

# Owner-approved 2026-08-12 rule: agency headlines never occupy heading
# positions, even quoted. The page has no dedicated "card-heading" class —
# every card and episode heading is a bare h1-h4 element — so checking those
# tags covers all heading positions the page uses.
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
ATTRIBUTED_QUOTE_CLASS = "attributed-quote"

# Reproduced directly (Phase 3.2d remediation): the unmodified pre-fix
# sentinel page rendered a 65,219px-tall document whose full-page
# screenshot capture painted content only through ~y=39,370 and was blank
# for the remaining ~25,850px, clipping the final card mid-word -- an
# exact match to the independent review's report -- with no notes footer
# since it sat past the blank region. An earlier, less-loaded run of the
# identical unmodified page and capture code succeeded completely, so this
# looks like a system-load-dependent raster/tile limit for very tall
# composited screenshots, not a fixed byte-for-byte threshold; headless
# Chrome's full-page capture is documented to clip near 16,384px in a
# number of builds, which is a working hypothesis, not a proven single
# mechanism. Rather than depend on any exact limit, the sentinel page
# keeps its default height comfortably under this bound.
MAX_SAFE_DOC_HEIGHT_PX = 16000


class ProvenanceText(HTMLParser):
    """Collects the flattened text of every heading element and every
    attributed-quote span in a rendered page, tracking arbitrary nesting (a
    state badge or link inside an h2, a quote span inside a paragraph) with a
    stack so nested markup still attributes its text to the right ancestor."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.heading_texts = []
        self.quote_texts = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        self.stack.append({
            "is_heading": tag in HEADING_TAGS,
            "is_quote": ATTRIBUTED_QUOTE_CLASS in classes,
            "buf": [],
        })

    def handle_endtag(self, tag):
        if not self.stack:
            return
        frame = self.stack.pop()
        text = "".join(frame["buf"])
        if frame["is_heading"]:
            self.heading_texts.append(text)
        if frame["is_quote"]:
            self.quote_texts.append(text)

    def handle_data(self, data):
        for frame in self.stack:
            frame["buf"].append(data)


def run(repo=REPO, chrome=None):
    repo = Path(repo)
    dashboard = json.loads(
        (repo / "data" / "sentinel" / "dashboard.json").read_text()
    )
    if dashboard.get("kind") != "sentinel" or not dashboard.get("episodes"):
        raise AssertionError("sentinel smoke test requires a non-empty dashboard")
    doe_headline = next(
        (event["sourceTitle"]
         for episode in dashboard["episodes"]
         for event in episode.get("sourcedEvents", [])
         if event.get("sourceId") == "doe-october-2025-portfolio-action"
         and event.get("sourceTitle")),
        None,
    )
    if not doe_headline:
        raise AssertionError("sentinel smoke test requires the DOE announcement's sourceTitle")
    executable = chrome_path(chrome)
    assembly = tempfile.TemporaryDirectory()
    assembly_path = Path(assembly.name) / "_site"
    assemble_pages_site(repo, assembly_path)
    handler = partial(QuietHandler, directory=str(assembly_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    failures = []
    cases = [
        ("wide-light", 1440, 1000, "light"),
        ("narrow-dark", 390, 844, "dark"),
    ]
    try:
        for label, width, height, theme in cases:
            url = (f"http://127.0.0.1:{server.server_port}/index.html"
                   f"?org={quote('sentinel')}")
            document, diagnostic = render_page(
                executable, url, width, height, theme
            )
            rendered, visible = document["html"], document["text"]
            case_errors = []
            if document.get("width") != width:
                case_errors.append("viewport width did not apply")
            if bool(document.get("dark")) != (theme == "dark"):
                case_errors.append("color-scheme emulation did not apply")
            if 'data-render-complete="true"' not in rendered:
                case_errors.append("render did not complete")
            if "data-render-error=" in rendered or "data-network-error=" in rendered:
                case_errors.append("page recorded a render/network error")
            for marker in (
                "Funding-action sentinel", "A signal is not a cancellation",
                "Current automated financial coverage",
                "Current authoritative-source coverage",
                "Absence from this page is not evidence that no funding action occurred",
                "Unreviewed signal", "Coverage and interpretation limits",
                "Estimated pilot burden",
                # Phase 3.2d remediation decision 5 (sentinel-facing language,
                # owner-approved): "affected award IDs" is retired in favor
                # of "award IDs with negative entries", and an unreviewed
                # episode's age is shown without an "(not overdue)" claim.
                "award IDs with negative entries",
                "gross negative", "net activity",
                "net activity in this period was positive",
                "Source-confirmed episodes",
                "approximately $7.56 billion", "321 awards", "223 projects",
                "Office of Clean Energy Demonstrations (OCED)",
                "Energy Efficiency and Renewable Energy (EERE)",
                "Grid Deployment (GDO)",
                "Manufacturing and Energy Supply Chains (MESC)",
                "Advanced Research Projects Agency-Energy (ARPA-E)",
                "Fossil Energy (FE)",
            ):
                if marker not in visible:
                    case_errors.append(f"missing visible marker: {marker}")
            for retired in ("not overdue", "affected award IDs"):
                if retired in visible:
                    case_errors.append(f"retired sentinel-language marker still present: {retired}")
            # Phase 3.2d remediation: the source-confirmed episodes must be
            # reachable at a stable anchor, not merely present somewhere in
            # 170+ unreviewed episodes (independent review finding #16).
            if 'id="confirmed"' not in rendered:
                case_errors.append('missing #confirmed anchor for source-confirmed episodes')
            # Owner-approved 2026-08-12 rule: the DOE source headline must
            # render only quoted and cited, never as a heading — even
            # though a sourced episode's card heading is itself derived
            # from the same event's structured fields.
            provenance = ProvenanceText()
            provenance.feed(rendered)
            if any(doe_headline in text for text in provenance.heading_texts):
                case_errors.append(
                    "DOE source headline appears inside a heading element (h1-h4)"
                )
            if not any(doe_headline in text for text in provenance.quote_texts):
                case_errors.append(
                    "DOE source headline is missing from any quoted attribution span"
                )
            if f"“{doe_headline}”" not in visible:
                case_errors.append(
                    "DOE source headline does not render inside quotation marks"
                )
            links = Links()
            links.feed(rendered)
            if not links.hrefs:
                case_errors.append("rendered sentinel has no native links")
            link_errors = rendered_link_problems(links.hrefs, assembly_path)
            if link_errors:
                case_errors.append(
                    f"rendered sentinel public-link integrity: {link_errors[:3]}"
                )
            for marker in ("Uncaught ", "net::ERR_", "exceptionDetails"):
                if marker in diagnostic:
                    case_errors.append(f"browser diagnostic contains {marker.strip()}")
            if case_errors:
                failures.append(f"{label}: " + "; ".join(case_errors))
            else:
                print(f"PASS sentinel-{label} ({width}×{height}, {theme})")

        # Layout assertion (Phase 3.2d remediation, independent-review
        # finding, reproduced -- see MAX_SAFE_DOC_HEIGHT_PX's comment
        # above): at the same 1100px width the review's screenshot pack
        # used, the last VISIBLE episode card (excluding ones collapsed
        # behind the overflow <details>) must be fully inside the document
        # and unclipped, and #notes must follow it and be non-empty. The
        # document-height check keeps comfortably under the working
        # hypothesis's limit rather than depending on exactly reproducing a
        # system-load-dependent raster limit on every run.
        layout_url = (f"http://127.0.0.1:{server.server_port}/index.html"
                      f"?org={quote('sentinel')}")
        metrics = _layout_metrics(executable, layout_url, width=1100, height=900)
        if not metrics.get("ok"):
            failures.append(f"layout-1100px: {metrics.get('reason')} ({metrics})")
        elif not metrics.get("hasConfirmedAnchor"):
            failures.append("layout-1100px: #confirmed anchor not found in the rendered DOM")
        elif (metrics.get("docHeight") or 0) >= MAX_SAFE_DOC_HEIGHT_PX:
            failures.append(
                f"layout-1100px: default document height {metrics.get('docHeight')}px "
                f">= the {MAX_SAFE_DOC_HEIGHT_PX}px safe headroom bound"
            )
        else:
            print(f"PASS sentinel-layout-1100px (doc height {metrics.get('docHeight')}px, "
                  f"under the {MAX_SAFE_DOC_HEIGHT_PX}px bound; "
                  f"{metrics.get('visibleCardCount')} visible card(s))")
    finally:
        server.shutdown()
        server.server_close()
        assembly.cleanup()
    if failures:
        raise AssertionError("\n".join(failures))
    return len(cases)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome")
    args = parser.parse_args()
    count = run(chrome=args.chrome)
    print(f"Rendered funding-action sentinel passed ({count} cases)")


if __name__ == "__main__":
    main()
