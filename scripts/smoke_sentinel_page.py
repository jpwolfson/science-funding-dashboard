#!/usr/bin/env python3
"""Render the funding-action sentinel in wide/light and narrow/dark modes."""

import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.smoke_obligation_pages import (
    Links,
    QuietHandler,
    chrome_path,
    render_page,
)


def run(repo=REPO, chrome=None):
    repo = Path(repo)
    dashboard = json.loads(
        (repo / "data" / "sentinel" / "dashboard.json").read_text()
    )
    if dashboard.get("kind") != "sentinel" or not dashboard.get("episodes"):
        raise AssertionError("sentinel smoke test requires a non-empty dashboard")
    executable = chrome_path(chrome)
    assembly = tempfile.TemporaryDirectory()
    assembly_path = Path(assembly.name)
    shutil.copy2(repo / "site" / "index.html", assembly_path / "index.html")
    os.symlink(repo / "data", assembly_path / "data", target_is_directory=True)
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
                "Estimated pilot burden", "not overdue",
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
            links = Links()
            links.feed(rendered)
            if not links.hrefs:
                case_errors.append("rendered sentinel has no native links")
            if any("localhost" in href or href.startswith("file:")
                   for href in links.hrefs):
                case_errors.append("rendered sentinel has a non-public link")
            for marker in ("Uncaught ", "net::ERR_", "exceptionDetails"):
                if marker in diagnostic:
                    case_errors.append(f"browser diagnostic contains {marker.strip()}")
            if case_errors:
                failures.append(f"{label}: " + "; ".join(case_errors))
            else:
                print(f"PASS sentinel-{label} ({width}×{height}, {theme})")
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
