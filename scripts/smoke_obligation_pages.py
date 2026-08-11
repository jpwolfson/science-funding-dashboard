#!/usr/bin/env python3
"""Render the phase-3.2a obligation page matrix in headless Chrome."""

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parent.parent


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])


class DevToolsSocket:
    """Small RFC 6455 client sufficient for Chrome DevTools JSON messages."""
    def __init__(self, url):
        parsed = urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        target = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.socket.sendall(request.encode())
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.socket.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"DevTools WebSocket upgrade failed: {response[:200]!r}")
        self.next_id = 1
        self.events = []

    def _read_exact(self, length):
        value = b""
        while len(value) < length:
            chunk = self.socket.recv(length - len(value))
            if not chunk:
                raise EOFError("DevTools WebSocket closed")
            value += chunk
        return value

    def _send_frame(self, payload, opcode=1):
        payload = payload if isinstance(payload, bytes) else payload.encode()
        mask = os.urandom(4)
        length = len(payload)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([0x80 | length])
        elif length < 65536:
            header += bytes([0x80 | 126]) + struct.pack("!H", length)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(header + mask + masked)

    def _receive(self):
        while True:
            first, second = self._read_exact(2)
            opcode, length = first & 0x0F, second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            masked = bool(second & 0x80)
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length)
            if mask:
                payload = bytes(value ^ mask[index % 4]
                                for index, value in enumerate(payload))
            if opcode == 9:
                self._send_frame(payload, opcode=10)
                continue
            if opcode == 8:
                raise EOFError("DevTools WebSocket closed")
            if opcode == 1:
                return json.loads(payload)

    def call(self, method, params=None):
        call_id = self.next_id
        self.next_id += 1
        self._send_frame(json.dumps({"id": call_id, "method": method,
                                     "params": params or {}}))
        while True:
            message = self._receive()
            if message.get("id") == call_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})
            self.events.append(message)

    def close(self):
        try:
            self._send_frame(b"", opcode=8)
        finally:
            self.socket.close()


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def render_page(executable, url, width, height, theme):
    port = _free_port()
    with tempfile.TemporaryDirectory() as profile:
        process = subprocess.Popen([
            executable, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
            "--remote-allow-origins=*", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        client = None
        try:
            endpoint = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 15
            while True:
                try:
                    request = Request(
                        endpoint + "/json/new?" + quote("about:blank", safe=""),
                        method="PUT",
                    )
                    page = json.load(urlopen(request, timeout=2))
                    break
                except Exception:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("Chrome DevTools endpoint did not start")
                    time.sleep(0.1)
            client = DevToolsSocket(page["webSocketDebuggerUrl"])
            client.call("Page.enable")
            client.call("Runtime.enable")
            client.call("Log.enable")
            client.call("Network.enable")
            client.call("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height, "deviceScaleFactor": 1,
                "mobile": width <= 500,
            })
            client.call("Emulation.setEmulatedMedia", {
                "features": [{"name": "prefers-color-scheme", "value": theme}]
            })
            client.call("Page.navigate", {"url": url})
            deadline = time.monotonic() + 20
            while True:
                state = client.call("Runtime.evaluate", {
                    "expression": "({complete:document.documentElement.dataset.renderComplete||null,error:document.documentElement.dataset.renderError||null})",
                    "returnByValue": True,
                })["result"].get("value", {})
                if state.get("complete") or state.get("error"):
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError("page render marker timed out")
                time.sleep(0.1)
            document = client.call("Runtime.evaluate", {
                "expression": "({html:document.documentElement.outerHTML,text:document.body.innerText,width:window.innerWidth,dark:window.matchMedia('(prefers-color-scheme: dark)').matches})",
                "returnByValue": True,
            })["result"]["value"]
            diagnostics = []
            for event in client.events:
                method, params = event.get("method"), event.get("params", {})
                if method == "Runtime.exceptionThrown":
                    diagnostics.append(str(params.get("exceptionDetails")))
                if method == "Log.entryAdded" and params.get("entry", {}).get("level") == "error":
                    diagnostics.append(str(params["entry"]))
                if method == "Network.loadingFailed" and not params.get("canceled"):
                    diagnostics.append(str(params))
            return document, "\n".join(diagnostics)
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def chrome_path(explicit=None):
    candidates = [
        explicit,
        os.environ.get("CHROME_BIN"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for value in candidates:
        if value and Path(value).exists():
            return value
    raise FileNotFoundError("headless Chrome executable was not found")


def _dashboards(repo):
    values = []
    for path in sorted((repo / "data" / "obligations").rglob("dashboard.json")):
        value = json.loads(path.read_text())
        if value.get("kind") == "obligations":
            values.append(value)
    return values


def page_matrix(repo):
    values = _dashboards(repo)
    if not values:
        raise ValueError("no obligation dashboards found")

    def select(label, predicate):
        value = next((row for row in values if predicate(row)), None)
        if not value:
            raise ValueError(f"render matrix has no {label} dashboard case")
        return value["node"]["path"]

    root = select("root", lambda row: row.get("node", {}).get("level") == "root")
    account = select("account", lambda row: row.get("node", {}).get("level") == "account")
    empty = select("empty current-year", lambda row: any(
        fy.get("fy") == row.get("currentFY") and fy.get("netObligationsCents") == 0
        for fy in row.get("fiscalYears", [])
    ))
    negative = select("negative activity", lambda row: any(
        period.get("deobligationsCents", 0) < 0
        for period in row.get("reportingPeriods", [])
    ))
    out_of_range = select("out-of-range File C/net", lambda row: any(
        metric.get("fileCToNetRatio") is not None
        and not 0 <= metric["fileCToNetRatio"] <= 1
        for metric in row.get("reportingPeriods", []) + row.get("fiscalYears", [])
    ))
    return [
        ("root-wide-light", root, 1440, 1000, "light"),
        ("account-narrow-dark", account, 390, 844, "dark"),
        ("empty-narrow-light", empty, 390, 844, "light"),
        ("negative-wide-dark", negative, 1440, 1000, "dark"),
        ("out-of-range-narrow-dark", out_of_range, 390, 844, "dark"),
    ]


def run(repo=REPO, chrome=None):
    repo = Path(repo)
    html_source = (repo / "site" / "index.html").read_text()
    if ":focus-visible" not in html_source:
        raise AssertionError("visible keyboard focus styling is missing")
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
    try:
        for label, org_path, width, height, theme in page_matrix(repo):
            url = (f"http://127.0.0.1:{server.server_port}/index.html"
                   f"?org={quote(org_path, safe='/')}")
            document, diagnostic = render_page(
                executable, url, width, height, theme
            )
            rendered, visible_text = document["html"], document["text"]
            case_errors = []
            if document.get("width") != width:
                case_errors.append(
                    f"viewport width {document.get('width')} != expected {width}"
                )
            if bool(document.get("dark")) != (theme == "dark"):
                case_errors.append(f"{theme} color-scheme emulation did not apply")
            if 'data-render-complete="true"' not in rendered:
                case_errors.append("render did not complete")
            if "data-render-error=" in rendered:
                case_errors.append("page recorded a JavaScript error")
            if "data-network-error=" in rendered:
                case_errors.append("page recorded a network failure")
            if "No data yet for this unit" in visible_text:
                case_errors.append("known dashboard rendered as missing data")
            for marker in ("Uncaught ", "net::ERR_", "exceptionDetails"):
                if marker in diagnostic:
                    case_errors.append(f"browser diagnostic contains {marker.strip()}")
            links = Links()
            links.feed(rendered)
            if not links.hrefs:
                case_errors.append("rendered page has no keyboard-native links")
            invalid_links = [href for href in links.hrefs
                             if "localhost" in href or href.startswith("file:")]
            if invalid_links:
                case_errors.append(f"non-public links remain: {invalid_links[:3]}")
            if 'tabindex="-1"' in rendered:
                case_errors.append("rendered controls remove keyboard focus")
            if case_errors:
                failures.append(f"{label}: " + "; ".join(case_errors))
            else:
                print(f"PASS {label}: {org_path} ({width}×{height}, {theme})")
    finally:
        server.shutdown()
        server.server_close()
        assembly.cleanup()
    if failures:
        raise AssertionError("\n".join(failures))
    return len(page_matrix(repo))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome")
    args = parser.parse_args()
    count = run(chrome=args.chrome)
    print(f"Rendered obligation page matrix passed ({count} cases)")


if __name__ == "__main__":
    main()
