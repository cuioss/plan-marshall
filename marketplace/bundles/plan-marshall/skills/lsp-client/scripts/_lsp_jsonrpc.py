#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Minimal stdlib LSP client — JSON-RPC over a language server's stdio.

The transport (:class:`StdioTransport`) spawns a language server (e.g.
``pyright-langserver --stdio``), frames JSON-RPC messages with ``Content-Length``
headers, and routes the three inbound message kinds a real server emits:

* **responses** (carry ``id``) — matched to the pending request;
* **server-to-client requests** (carry ``id`` and ``method``) — answered by a
  built-in handler (``workspace/configuration`` returns an analysis config that
  enables workspace indexing so ``workspace/symbol`` searches unopened files;
  progress / capability-registration requests are acked with ``null``);
* **notifications** (no ``id``) — buffered, with ``publishDiagnostics`` tracked
  per URI so a post-edit re-diagnose can wait for the *next* push.

:class:`LspSession` layers the LSP handshake and the read/write operations on
top of *any* transport implementing ``request`` / ``notify`` /
``wait_for_diagnostics`` — so tests inject a fake transport and exercise the
session logic with no server, while the shipped path drives a real one.

Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Protocol

from _lsp_workspace_edit import path_to_uri

_HEADER_SEPARATOR = b'\r\n\r\n'


class LspError(Exception):
    """A language server returned a JSON-RPC error, or the transport failed."""


class Transport(Protocol):
    """The surface :class:`LspSession` needs — real or fake."""

    def request(self, method: str, params: dict[str, Any], timeout: float = ...) -> dict[str, Any]: ...

    def notify(self, method: str, params: dict[str, Any]) -> None: ...

    def wait_for_diagnostics(self, uri: str, settle: float = ..., timeout: float = ...) -> list[dict[str, Any]]: ...

    def wait_until_idle(self, settle: float = ..., timeout: float = ...) -> None: ...

    def close(self) -> None: ...


def default_analysis_config() -> dict[str, Any]:
    """Analysis settings requested by ``workspace/configuration`` pulls.

    ``indexing`` on lets ``workspace/symbol`` search files the client never
    opened; ``openFilesOnly`` keeps diagnostics scoped to the files under edit.
    """
    return {
        'indexing': True,
        'diagnosticMode': 'openFilesOnly',
        'useLibraryCodeForTypes': True,
        'typeCheckingMode': 'basic',
    }


def _config_for_section(section: str) -> Any:
    """Return the config object a server expects for a requested section name."""
    analysis = default_analysis_config()
    if section.endswith('analysis'):
        return analysis
    if section in ('python', 'basedpyright', 'pyright', ''):
        return {'analysis': analysis}
    return {}


class StdioTransport:
    """Spawn a language server and speak JSON-RPC over its stdio pipes."""

    def __init__(self, command: list[str], cwd: str) -> None:
        self._proc = subprocess.Popen(  # noqa: S603 — command is operator-configured
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
        )
        self._next_id = 0
        self._lock = threading.Lock()
        self._cond = threading.Condition()
        self._responses: dict[int, dict[str, Any]] = {}
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._diag_seq = 0
        self._activity_seq = 0
        self._closed = False
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    # -- wire I/O -----------------------------------------------------------

    def _write_message(self, obj: dict[str, Any]) -> None:
        stdin = self._proc.stdin
        if stdin is None:
            raise LspError('language server stdin is closed')
        body = json.dumps(obj).encode('utf-8')
        header = f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii')
        with self._lock:
            stdin.write(header + body)
            stdin.flush()

    def _read_loop(self) -> None:
        stdout = self._proc.stdout
        if stdout is None:
            return
        try:
            while True:
                header = b''
                while _HEADER_SEPARATOR not in header:
                    chunk = stdout.read(1)
                    if not chunk:
                        return
                    header += chunk
                length = 0
                for line in header.split(b'\r\n'):
                    if line.lower().startswith(b'content-length:'):
                        length = int(line.split(b':', 1)[1].strip())
                body = b''
                while len(body) < length:
                    chunk = stdout.read(length - len(body))
                    if not chunk:
                        return
                    body += chunk
                self._dispatch(json.loads(body.decode('utf-8')))
        except (OSError, ValueError):
            return

    def _dispatch(self, message: dict[str, Any]) -> None:
        server_request: dict[str, Any] | None = None
        with self._cond:
            self._activity_seq += 1
            if 'id' in message and 'method' in message:
                server_request = message
            elif 'id' in message:
                self._responses[int(message['id'])] = message
            elif message.get('method') == 'textDocument/publishDiagnostics':
                params = message.get('params') or {}
                self._diagnostics[params.get('uri', '')] = params.get('diagnostics') or []
                self._diag_seq += 1
            self._cond.notify_all()
        # Answer a server-to-client request outside the state lock — the reply
        # writes to stdin under its own lock.
        if server_request is not None:
            self._answer_server_request(server_request)

    def _answer_server_request(self, message: dict[str, Any]) -> None:
        method = message.get('method')
        result: Any = None
        if method == 'workspace/configuration':
            items = (message.get('params') or {}).get('items') or []
            result = [_config_for_section((item or {}).get('section', '')) for item in items]
        self._write_message({'jsonrpc': '2.0', 'id': message['id'], 'result': result})

    # -- public API ---------------------------------------------------------

    def request(self, method: str, params: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
        with self._cond:
            self._next_id += 1
            request_id = self._next_id
        self._write_message({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        with self._cond:
            while request_id not in self._responses:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LspError(f'timed out waiting for response to {method}')
                self._cond.wait(remaining)
            message = self._responses.pop(request_id)
        if 'error' in message:
            raise LspError(f'{method} failed: {message["error"]}')
        response: dict[str, Any] = message
        return response

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write_message({'jsonrpc': '2.0', 'method': method, 'params': params})

    def wait_for_diagnostics(self, uri: str, settle: float = 2.0, timeout: float = 15.0) -> list[dict[str, Any]]:
        """Return the latest diagnostics for ``uri`` once the push stream settles.

        Blocks until ``settle`` seconds pass with no new ``publishDiagnostics``
        for any URI (or ``timeout`` elapses), then returns the last diagnostics
        seen for ``uri`` — an empty list when the server reported the file clean,
        which pyright does explicitly rather than by silence.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            last_seq = self._diag_seq
            quiet_until = time.monotonic() + settle
            while time.monotonic() < deadline:
                if self._diag_seq != last_seq:
                    last_seq = self._diag_seq
                    quiet_until = time.monotonic() + settle
                if time.monotonic() >= quiet_until and uri in self._diagnostics:
                    break
                self._cond.wait(min(settle, max(0.0, quiet_until - time.monotonic())) or 0.05)
            return list(self._diagnostics.get(uri, []))

    def wait_until_idle(self, settle: float = 1.5, timeout: float = 8.0) -> None:
        """Block until no inbound message arrives for ``settle`` seconds.

        Used before a ``workspace/symbol`` query: the server indexes the
        workspace in the background after ``initialized`` (pyright answers a
        workspace-symbol query with nothing until that finishes), so the client
        waits for the message stream to settle rather than racing the index.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            last_seq = self._activity_seq
            quiet_until = time.monotonic() + settle
            while time.monotonic() < deadline:
                if self._activity_seq != last_seq:
                    last_seq = self._activity_seq
                    quiet_until = time.monotonic() + settle
                if time.monotonic() >= quiet_until:
                    return
                self._cond.wait(max(0.0, quiet_until - time.monotonic()) or 0.05)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.request('shutdown', {}, timeout=5.0)
            self.notify('exit', {})
        except (LspError, OSError):
            pass
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5.0)
        except (OSError, subprocess.TimeoutExpired):
            try:
                self._proc.kill()
            except OSError:
                pass
        self._reader.join(timeout=2.0)
        # Close the pipes explicitly so a warnings-as-errors test run never trips
        # a ResourceWarning on a lingering stdio pipe.
        for stream in (self._proc.stdin, self._proc.stdout):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


class LspSession:
    """LSP handshake plus the read/write operations, over an injected transport."""

    def __init__(self, transport: Transport, root_path: str) -> None:
        self._t = transport
        self._root = str(Path(root_path).resolve())
        self._doc_versions: dict[str, int] = {}

    def initialize(self, timeout: float = 30.0) -> dict[str, Any]:
        root_uri = path_to_uri(self._root)
        params: dict[str, Any] = {
            'processId': None,
            'rootUri': root_uri,
            'workspaceFolders': [{'uri': root_uri, 'name': Path(self._root).name}],
            'initializationOptions': {'python': {'analysis': default_analysis_config()}},
            'capabilities': {
                'textDocument': {
                    'documentSymbol': {'hierarchicalDocumentSymbolSupport': True},
                    'definition': {'linkSupport': False},
                    'references': {},
                    'rename': {'prepareSupport': True},
                    'publishDiagnostics': {},
                },
                'workspace': {
                    'symbol': {},
                    'configuration': True,
                    'workspaceEdit': {'documentChanges': True},
                },
            },
        }
        response = self._t.request('initialize', params, timeout=timeout)
        self._t.notify('initialized', {})
        return response

    def open(self, path: str) -> None:
        abs_path = str(Path(path).resolve())
        text = Path(abs_path).read_text(encoding='utf-8')
        self._doc_versions[abs_path] = 1
        self._t.notify('textDocument/didOpen', {
            'textDocument': {'uri': path_to_uri(abs_path), 'languageId': 'python', 'version': 1, 'text': text},
        })

    def change_to_disk(self, path: str) -> None:
        """Notify the server that ``path`` changed to its current on-disk content."""
        abs_path = str(Path(path).resolve())
        text = Path(abs_path).read_text(encoding='utf-8')
        version = self._doc_versions.get(abs_path, 1) + 1
        self._doc_versions[abs_path] = version
        self._t.notify('textDocument/didChange', {
            'textDocument': {'uri': path_to_uri(abs_path), 'version': version},
            'contentChanges': [{'text': text}],
        })

    def document_symbols(self, path: str) -> list[dict[str, Any]]:
        response = self._t.request('textDocument/documentSymbol', {
            'textDocument': {'uri': path_to_uri(path)},
        })
        result = response.get('result') or []
        return list(result)

    def definition(self, path: str, line: int, character: int) -> list[dict[str, Any]]:
        response = self._t.request('textDocument/definition', {
            'textDocument': {'uri': path_to_uri(path)},
            'position': {'line': line, 'character': character},
        })
        return _as_location_list(response.get('result'))

    def references(self, path: str, line: int, character: int) -> list[dict[str, Any]]:
        response = self._t.request('textDocument/references', {
            'textDocument': {'uri': path_to_uri(path)},
            'position': {'line': line, 'character': character},
            'context': {'includeDeclaration': True},
        })
        return _as_location_list(response.get('result'))

    def workspace_symbol(self, query: str) -> list[dict[str, Any]]:
        self._t.wait_until_idle()
        response = self._t.request('workspace/symbol', {'query': query})
        result = response.get('result') or []
        return list(result)

    def rename(self, path: str, line: int, character: int, new_name: str) -> dict[str, Any]:
        response = self._t.request('textDocument/rename', {
            'textDocument': {'uri': path_to_uri(path)},
            'position': {'line': line, 'character': character},
            'newName': new_name,
        })
        result = response.get('result')
        return result if isinstance(result, dict) else {}

    def diagnostics(self, path: str, settle: float = 2.0, timeout: float = 15.0) -> list[dict[str, Any]]:
        return self._t.wait_for_diagnostics(path_to_uri(path), settle=settle, timeout=timeout)

    def close(self) -> None:
        self._t.close()


def _as_location_list(result: Any) -> list[dict[str, Any]]:
    """Normalise a definition/references result into a list of Location dicts."""
    if result is None:
        return []
    if isinstance(result, dict):
        return [result]
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []
