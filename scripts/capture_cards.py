#!/usr/bin/env python3
"""scripts/capture_cards.py -- per-card before/after evidence captures.

Renders one or more dashboard pages at a fixed width and saves a PNG of
each requested card (the `.card` or `.summary-group` whose heading text
starts with the given title), plus the card's rendered text. Used for the
display batch's per-chart before/after evidence; it never gates anything.

    python scripts/capture_cards.py --out DIR [--site site/index.html]
        [--data data] [--width 1100] [--theme light]
        LABEL=ORG=TITLE [LABEL=ORG=TITLE ...]

ORG is the `?org=` path ("" for the award root); TITLE is a heading prefix
("*" captures the page header block and the whole page instead).
`--data` may point at a scratch copy of data/ (e.g. a staged stale-unit
scenario) so the committed tree is never modified.
"""

import argparse
import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.smoke_obligation_pages import (  # noqa: E402
    DevToolsSocket, QuietHandler, _start_chrome, _stop_chrome, chrome_path,
)

FIND_CARD = """
(title => {
  const heads = [...document.querySelectorAll('.card h2, .summary-group h2, .card h3')];
  const h = heads.find(n => n.textContent.trim().startsWith(title));
  if (!h) return null;
  const box = h.closest('.card, .summary-group') || h.parentElement;
  box.scrollIntoView();
  const r = box.getBoundingClientRect();
  return {x: r.left + window.scrollX, y: r.top + window.scrollY,
          width: r.width, height: r.height, text: box.innerText};
})
"""


def capture(executable, base_url, targets, out_dir, width, theme):
    results = []
    for label, org, title in targets:
        query = f"?org={quote(org, safe='/')}" if org else ""
        url = f"{base_url}/index.html{query}"
        with tempfile.TemporaryDirectory() as profile_root:
            process, page = _start_chrome(executable, profile_root)
            client = None
            try:
                client = DevToolsSocket(page["webSocketDebuggerUrl"])
                client.call("Page.enable")
                client.call("Runtime.enable")
                client.call("Emulation.setDeviceMetricsOverride", {
                    "width": width, "height": 900, "deviceScaleFactor": 1,
                    "mobile": width <= 500})
                client.call("Emulation.setEmulatedMedia", {
                    "features": [{"name": "prefers-color-scheme", "value": theme}]})
                client.call("Page.navigate", {"url": url})
                deadline = time.monotonic() + 20
                while True:
                    state = client.call("Runtime.evaluate", {
                        "expression": "({c:document.documentElement.dataset.renderComplete||null,"
                                      "e:document.documentElement.dataset.renderError||null})",
                        "returnByValue": True})["result"].get("value", {})
                    if state.get("c") or state.get("e"):
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"{url}: render marker timed out")
                    time.sleep(0.1)
                if state.get("e"):
                    results.append({"label": label, "org": org, "title": title,
                                    "error": state["e"]})
                    continue
                metrics = client.call("Page.getLayoutMetrics")
                content = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
                full_height = max(int(content.get("height") or 900), 900)
                client.call("Emulation.setDeviceMetricsOverride", {
                    "width": width, "height": full_height, "deviceScaleFactor": 1,
                    "mobile": width <= 500})
                if title == "*":
                    box = {"x": 0, "y": 0, "width": width, "height": full_height,
                           "text": client.call("Runtime.evaluate", {
                               "expression": "document.body.innerText",
                               "returnByValue": True})["result"]["value"]}
                else:
                    box = client.call("Runtime.evaluate", {
                        "expression": f"{FIND_CARD}({json.dumps(title)})",
                        "returnByValue": True})["result"].get("value")
                if not box:
                    results.append({"label": label, "org": org, "title": title,
                                    "error": "card not found"})
                    continue
                pad = 8
                clip = {"x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
                        "width": min(width, box["width"] + 2 * pad),
                        "height": box["height"] + 2 * pad, "scale": 1}
                shot = client.call("Page.captureScreenshot", {
                    "format": "png", "captureBeyondViewport": True, "clip": clip})
                png = out_dir / f"{label}.png"
                png.write_bytes(base64.b64decode(shot["data"]))
                (out_dir / f"{label}.txt").write_text(box["text"])
                results.append({"label": label, "org": org, "title": title,
                                "file": str(png)})
            finally:
                if client:
                    try:
                        client.close()
                    except OSError:
                        pass
                _stop_chrome(process)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--site", default=str(REPO / "site" / "index.html"))
    parser.add_argument("--data", default=str(REPO / "data"))
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--theme", default="light", choices=["light", "dark"])
    parser.add_argument("--chrome")
    parser.add_argument("targets", nargs="+", help="LABEL=ORG=TITLE")
    args = parser.parse_args()
    targets = []
    for spec in args.targets:
        parts = spec.split("=", 2)
        if len(parts) != 3:
            parser.error(f"bad target {spec!r}; expected LABEL=ORG=TITLE")
        targets.append(tuple(parts))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    executable = chrome_path(args.chrome)
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        shutil.copy2(args.site, root / "index.html")
        os.symlink(Path(args.data).resolve(), root / "data", target_is_directory=True)
        server = ThreadingHTTPServer(("127.0.0.1", 0),
                                     partial(QuietHandler, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            results = capture(executable, f"http://127.0.0.1:{server.server_port}",
                              targets, out_dir, args.width, args.theme)
        finally:
            server.shutdown()
            server.server_close()
    (out_dir / "manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    failed = [r for r in results if r.get("error")]
    for r in results:
        print(r["label"], r.get("error") or r["file"])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
