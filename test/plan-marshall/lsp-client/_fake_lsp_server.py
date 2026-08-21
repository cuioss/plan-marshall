#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""A configurable fake language server, and the helper that spawns one.

Not a test module — a fixture factory. The shipped diagnostics contract can only
be exercised against a server whose *publish timing* is under the test's control:
one that answers ``initialize`` and never publishes, one whose post-``didChange``
publish arrives after the settle window, one that publishes ``[A]`` before an
edit and ``[B]`` after. A real language server does none of those on demand, and
an in-process fake transport bypasses the very framing and threading the wait
depends on. So the fake is a **subprocess driven over the real**
:class:`StdioTransport`, which keeps the whole read loop under test while making
the server's behaviour a fixture.

The server is driven by a JSON config keyed by file **basename**, so a test
writes ``{'a.py': {'open': [...], 'change': [...]}}`` without having to reproduce
URI encoding. ``rename_edit`` and ``workspace_symbols`` supply the canned results
for the two request kinds that carry one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SERVER_SOURCE = r'''
import json, sys, time

CONFIG = json.loads(open(sys.argv[1]).read())
FILES = CONFIG.get("files", {})
DELAY = CONFIG.get("publish_delay", {})
# Models a CROSS-FILE rename: until every participating file has been changed,
# the workspace is genuinely inconsistent and the server reports it. Once the
# quorum is met each file re-publishes clean. A client that waits for one file's
# verdict before notifying the next can never reach the quorum.
CHANGE_QUORUM = CONFIG.get("change_quorum")
CHANGED = set()


def read_message():
    header = b""
    while b"\r\n\r\n" not in header:
        c = sys.stdin.buffer.read(1)
        if not c:
            return None
        header += c
    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    if length <= 0:
        return {}
    return json.loads(sys.stdin.buffer.read(length))


def write_frame(obj):
    body = json.dumps(obj).encode()
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()


def publish(uri, diagnostics):
    write_frame({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                 "params": {"uri": uri, "diagnostics": diagnostics}})


while True:
    message = read_message()
    if message is None:
        break
    method = message.get("method")
    if method == "initialize":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": {"capabilities": {}}})
    elif method == "shutdown":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": None})
    elif method == "exit":
        break
    elif method == "textDocument/rename":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": CONFIG.get("rename_edit")})
    elif method == "workspace/symbol":
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": CONFIG.get("workspace_symbols")})
    elif method in ("textDocument/didOpen", "textDocument/didChange"):
        uri = message["params"]["textDocument"]["uri"]
        phase = "open" if method.endswith("didOpen") else "change"
        if CHANGE_QUORUM is not None and phase == "change":
            CHANGED.add(uri)
            if len(CHANGED) < CHANGE_QUORUM:
                publish(uri, [{
                    "severity": 1, "code": "E-XFILE",
                    "message": "unresolved reference; the rename is only half applied",
                    "range": {"start": {"line": 0, "character": 0},
                              "end": {"line": 0, "character": 3}},
                }])
            else:
                for known in sorted(CHANGED):
                    publish(known, [])
            continue
        entry = FILES.get(uri.rsplit("/", 1)[-1], {})
        if phase in entry:
            delay = DELAY.get(phase, 0.0)
            if delay:
                time.sleep(delay)
            publish(uri, entry[phase])
    elif "id" in message:
        write_frame({"jsonrpc": "2.0", "id": message["id"], "result": None})
'''


def write_fake_server(directory: Path, config: dict[str, Any]) -> list[str]:
    """Write the fake server and its config; return the command that runs it."""
    server = directory / 'fake_lsp_server.py'
    server.write_text(_SERVER_SOURCE, encoding='utf-8')
    config_file = directory / 'fake_lsp_config.json'
    config_file.write_text(json.dumps(config), encoding='utf-8')
    return [sys.executable, str(server), str(config_file)]
