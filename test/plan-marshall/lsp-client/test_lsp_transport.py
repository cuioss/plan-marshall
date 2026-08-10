#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Transport robustness tests — no language server required.

Covers the reader-thread resilience raised in review: a malformed / length-0
frame (a stray non-JSON-RPC stdout line) must be skipped, not allowed to kill
the reader thread — otherwise every subsequent request hangs until it times out.
Drives a tiny fake server subprocess, so it runs in CI without pyright.
"""

from __future__ import annotations

import sys

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _lsp_jsonrpc import StdioTransport  # noqa: E402

# A minimal fake LSP server: read one framed request, echo its id in a reply —
# but first emit a length-0 junk frame, the exact case that used to make
# json.loads('') kill the reader thread.
_FAKE_SERVER = r'''
import json, sys

def read_message():
    header = b''
    while b'\r\n\r\n' not in header:
        c = sys.stdin.buffer.read(1)
        if not c:
            return None
        header += c
    length = 0
    for line in header.split(b'\r\n'):
        if line.lower().startswith(b'content-length:'):
            length = int(line.split(b':', 1)[1].strip())
    return json.loads(sys.stdin.buffer.read(length))

def write_frame(obj):
    body = json.dumps(obj).encode()
    sys.stdout.buffer.write(b'Content-Length: %d\r\n\r\n' % len(body) + body)
    sys.stdout.buffer.flush()

req = read_message()
# Junk frame BEFORE the real response — the reader must skip it and survive.
sys.stdout.buffer.write(b'Content-Length: 0\r\n\r\n')
sys.stdout.buffer.flush()
write_frame({'jsonrpc': '2.0', 'id': req['id'], 'result': {'capabilities': {}}})
# Stay alive so the client reads the response before EOF.
import time
time.sleep(1.0)
'''


def test_reader_survives_length_zero_junk_frame(tmp_path):
    server = tmp_path / 'fake_server.py'
    server.write_text(_FAKE_SERVER)
    transport = StdioTransport([sys.executable, str(server)], cwd=str(tmp_path))
    try:
        # If the length-0 junk frame killed the reader, this would hang to the
        # timeout and raise LspError; instead it returns the real response fast.
        response = transport.request('initialize', {}, timeout=5.0)
        assert response.get('result') == {'capabilities': {}}
    finally:
        transport.close()
