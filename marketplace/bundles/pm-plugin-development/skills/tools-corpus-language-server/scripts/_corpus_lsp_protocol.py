#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Server-side LSP framing and dispatch for the corpus language server.

The ``lsp-client`` skill ships a *client* transport (it spawns a server and
writes requests to it). A server reads requests and writes responses, so the
framing here is the inverse and is deliberately its own small module rather than
a shim over the client's transport.

⭐ **Opt-in is enforced inside the server, not at the manifest.** A
plugin-declared LSP server starts automatically when its plugin is enabled, so
"declare it and you are opted in" would make strictly-opt-in impossible on that
platform. Instead the server always starts, reads its own configuration, and
when it is not enabled advertises **no capabilities at all** and answers every
request with an empty result. An unconfigured project therefore sees a server
that does nothing and claims nothing — the documented no-op path.

Stdlib only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, BinaryIO

# JSON-RPC error codes used here (see the LSP specification).
METHOD_NOT_FOUND = -32601

Handler = Callable[[dict[str, Any]], Any]


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    """Read one ``Content-Length``-framed JSON-RPC message.

    Returns ``None`` at end of stream or on a header that never yields a length,
    which the serve loop treats as "the client is gone" rather than as an error.
    """
    content_length: int | None = None
    while True:
        line = stream.readline()
        if not line:
            return None
        header = line.decode('ascii', errors='replace').strip()
        if not header:
            break  # blank line terminates the header block
        name, _, value = header.partition(':')
        if name.strip().lower() == 'content-length':
            try:
                parsed = int(value.strip())
            except ValueError:
                return None
            # ⚠ A NEGATIVE length must be rejected, not passed through. Python's
            # ``read(-1)`` means *read to EOF*, so a negative Content-Length would
            # make the server swallow the rest of the stream — accepting a frame it
            # should refuse, and, on a live stdin that never closes, blocking
            # forever instead of answering. The length check below (``len(body) <
            # content_length``) cannot catch it either, since any real length is
            # greater than a negative one.
            if parsed < 0:
                return None
            content_length = parsed
    if content_length is None:
        return None
    body = stream.read(content_length)
    if body is None or len(body) < content_length:
        return None
    try:
        parsed = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def write_message(stream: BinaryIO, payload: dict[str, Any]) -> None:
    """Write one ``Content-Length``-framed JSON-RPC message."""
    body = json.dumps(payload).encode('utf-8')
    stream.write(f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii'))
    stream.write(body)
    stream.flush()


def no_op_capabilities() -> dict[str, Any]:
    """The capability set advertised when the server is NOT enabled.

    Deliberately empty: a client that reads capabilities correctly will never
    route a request here, so an unconfigured project's behaviour is unchanged.
    """
    return {}


def active_capabilities() -> dict[str, Any]:
    """The capability set advertised when the server IS enabled.

    ⚠ Diagnostics are absent on purpose. Live broken-reference diagnostics are
    plan 240's D3, hard-gated on the validator-precision work: the validator's
    current unresolved set is overwhelmingly false positives, so advertising a
    diagnostic provider would ship confident-wrong squiggles.
    """
    return {
        'definitionProvider': True,
        'referencesProvider': True,
        'hoverProvider': True,
        'textDocumentSync': 1,  # full-document sync
    }


class LspServer:
    """A minimal JSON-RPC server loop with per-method handlers."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.handlers: dict[str, Handler] = {}
        self.shutdown_requested = False

    def register(self, method: str, handler: Handler) -> None:
        self.handlers[method] = handler

    def capabilities(self) -> dict[str, Any]:
        return active_capabilities() if self.enabled else no_op_capabilities()

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Dispatch one message; return the response, or ``None`` for a notification."""
        method = message.get('method')
        message_id = message.get('id')
        params = message.get('params') or {}
        if not isinstance(params, dict):
            params = {}

        if method == 'exit':
            self.shutdown_requested = True
            return None
        if method == 'shutdown':
            self.shutdown_requested = True
            return _result(message_id, None)

        handler = self.handlers.get(method) if isinstance(method, str) else None
        if handler is None:
            if message_id is None:
                return None  # unknown notification — ignore, per the spec
            return _error(message_id, METHOD_NOT_FOUND, f'method not found: {method}')

        result = handler(params)
        if message_id is None:
            return None
        return _result(message_id, result)

    def serve(self, stdin: BinaryIO, stdout: BinaryIO) -> int:
        """Run the read/dispatch/write loop until the client exits."""
        while True:
            message = read_message(stdin)
            if message is None:
                return 0
            response = self.handle(message)
            if response is not None:
                write_message(stdout, response)
            if self.shutdown_requested and message.get('method') == 'exit':
                return 0


def _result(message_id: Any, result: Any) -> dict[str, Any]:
    return {'jsonrpc': '2.0', 'id': message_id, 'result': result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {'jsonrpc': '2.0', 'id': message_id, 'error': {'code': code, 'message': message}}
