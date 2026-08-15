#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""End-to-end tests for `serve` as an LSP CLIENT actually spawns it.

These drive the real script as a subprocess with **no `PYTHONPATH`**, which is
the environment any `lspServers` declaration produces — this bundle ships none,
so the declaration is operator-added, but either way the client spawns the
script directly and there is no executor to inject one.

⚠ The in-process protocol tests cannot catch what these catch. They drive
`LspServer.serve()` against `BytesIO`, so they never exercise the import
bootstrap, and the server's own lenient `read_message` round-trips its own
output — which would hide a corrupted `\\r\\n\\r\\n` header terminator from a
test that only replays it through the same reader.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import get_script_path

SCRIPT = get_script_path('pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py')

ENABLED = {'code_intelligence': {'corpus_language_server': {'enabled': True}}}


def _framed(payload: dict) -> bytes:
    body = json.dumps(payload).encode('utf-8')
    return b'Content-Length: %d\r\n\r\n' % len(body) + body


def _handshake(project_path: Path) -> subprocess.CompletedProcess[bytes]:
    """Spawn `serve` the way a client does — no PYTHONPATH — and initialize."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    stdin = _framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}}) + _framed(
        {'jsonrpc': '2.0', 'method': 'exit'}
    )
    return subprocess.run(
        [sys.executable, str(SCRIPT), 'serve', '--project-path', str(project_path)],
        input=stdin,
        capture_output=True,
        env=env,
        timeout=120,
    )


def _capabilities(stdout: bytes) -> dict:
    assert b'\r\n\r\n' in stdout, f'header terminator must be CRLFCRLF, got: {stdout[:60]!r}'
    message = json.loads(stdout.split(b'\r\n\r\n', 1)[1])
    capabilities: dict = message['result']['capabilities']
    return capabilities


def _project(root: Path, marshal: dict | None) -> Path:
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    if marshal is not None:
        (root / '.plan').mkdir(parents=True, exist_ok=True)
        (root / '.plan' / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
    return root


class TestServeWithoutPythonPath:
    """The import bootstrap must carry the script when no executor set PYTHONPATH."""

    def test_starts_and_answers_initialize(self, tmp_path: Path) -> None:
        result = _handshake(_project(tmp_path, ENABLED))
        assert result.returncode == 0, result.stderr.decode()
        assert result.stderr == b'', f'a clean start must emit nothing on stderr: {result.stderr!r}'

    def test_enabled_project_advertises_the_three_verbs(self, tmp_path: Path) -> None:
        capabilities = _capabilities(_handshake(_project(tmp_path, ENABLED)).stdout)
        assert capabilities['definitionProvider'] is True
        assert capabilities['referencesProvider'] is True
        assert capabilities['hoverProvider'] is True

    def test_unconfigured_project_advertises_nothing(self, tmp_path: Path) -> None:
        """The no-op path, driven through the real client-facing entry point."""
        assert _capabilities(_handshake(_project(tmp_path, None)).stdout) == {}


class TestFramingSurvivesTheRealPipe:
    """A real pipe is where newline translation would corrupt the LSP header."""

    def test_header_terminator_is_crlfcrlf(self, tmp_path: Path) -> None:
        stdout = _handshake(_project(tmp_path, ENABLED)).stdout
        assert b'\r\n\r\n' in stdout
        assert b'Content-Length:' in stdout

    def test_body_is_parseable_json_rpc(self, tmp_path: Path) -> None:
        stdout = _handshake(_project(tmp_path, ENABLED)).stdout
        message = json.loads(stdout.split(b'\r\n\r\n', 1)[1])
        assert message['jsonrpc'] == '2.0'
        assert message['id'] == 1
