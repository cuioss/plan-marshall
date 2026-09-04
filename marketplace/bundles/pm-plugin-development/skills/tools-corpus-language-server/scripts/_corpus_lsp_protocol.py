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
import sys
import traceback
from collections.abc import Callable
from typing import Any, BinaryIO

# JSON-RPC error codes used here (see the LSP specification).
METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603

Handler = Callable[[dict[str, Any]], Any]


class FrameError(Exception):
    """A frame that could not be decoded — distinct from the stream ending.

    ⛔ **The distinction is the whole point.** ``read_message`` used to return
    ``None`` for both, and the serve loop reads ``None`` as "the client is gone".
    So a single malformed frame ended a resident session **silently**, with
    nothing on stderr — the one failure shape the surface is named for
    surviving, and the only one it did not survive.

    ``recoverable`` says whether the stream is still frame-aligned. It is
    ``True`` when the declared body was read whole and only its *content* was
    bad, so the next read starts on a frame boundary and the session can go on.
    It is ``False`` when the length itself was unusable or the body was short,
    because the reader then has no idea where the next frame begins: continuing
    would resynchronise on arbitrary bytes, which is worse than stopping. An
    unrecoverable frame still ends the session — but loudly, never silently.
    """

    def __init__(self, detail: str, recoverable: bool) -> None:
        super().__init__(detail)
        self.detail = detail
        self.recoverable = recoverable


def read_message(stream: BinaryIO) -> dict[str, Any] | None:
    """Read one ``Content-Length``-framed JSON-RPC message.

    Returns ``None`` **only** at end of stream — the client is gone.

    Raises:
        FrameError: the bytes were not a decodable frame. See that class for
            what ``recoverable`` means and why the two cases must not be
            collapsed into one another, or into end-of-stream.
    """
    content_length: int | None = None
    while True:
        line = stream.readline()
        if not line:
            # True end of stream. If a header block had already begun, the
            # client died mid-frame; either way there is nothing more to read.
            return None
        header = line.decode('ascii', errors='replace').strip()
        if not header:
            break  # blank line terminates the header block
        name, _, value = header.partition(':')
        if name.strip().lower() == 'content-length':
            try:
                parsed = int(value.strip())
            except ValueError:
                raise FrameError(f'non-integer Content-Length {value.strip()!r}', recoverable=False) from None
            # ⚠ A NEGATIVE length must be rejected, not passed through. Python's
            # ``read(-1)`` means *read to EOF*, so a negative Content-Length would
            # make the server swallow the rest of the stream — accepting a frame it
            # should refuse, and, on a live stdin that never closes, blocking
            # forever instead of answering. The length check below (``len(body) <
            # content_length``) cannot catch it either, since any real length is
            # greater than a negative one.
            if parsed < 0:
                raise FrameError(f'negative Content-Length {parsed}', recoverable=False)
            content_length = parsed
    if content_length is None:
        raise FrameError('header block carried no Content-Length', recoverable=False)
    body = stream.read(content_length)
    if body is None or len(body) < content_length:
        raise FrameError(
            f'body ended after {0 if body is None else len(body)} of {content_length} bytes',
            recoverable=False,
        )
    # From here the declared body has been consumed in full, so the stream is
    # back on a frame boundary whatever the content turns out to be: these are
    # the shapes a session can genuinely skip and carry on from.
    try:
        parsed = json.loads(body.decode('utf-8'))
    except UnicodeDecodeError:
        raise FrameError('body is not valid UTF-8', recoverable=True) from None
    except json.JSONDecodeError as exc:
        raise FrameError(f'body is not valid JSON: {exc.msg}', recoverable=True) from None
    if not isinstance(parsed, dict):
        raise FrameError(f'body decoded to {type(parsed).__name__}, not a JSON-RPC object', recoverable=True)
    return parsed


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
    plan 240's D3, gated on validator precision: advertising a diagnostic
    provider binds this surface to it. ⛔ The ~97 % false-positive figure the gate
    was argued on no longer holds; see :mod:`corpus_lsp`'s module docstring and
    the recorded proposal.
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
        # Set for the duration of `serve` so a handler can push a
        # server-to-client notification (see `notify`). Absent outside a serve
        # loop, where there is no client to notify.
        self._stdout: BinaryIO | None = None

    def register(self, method: str, handler: Handler) -> None:
        self.handlers[method] = handler

    def notify(self, method: str, params: dict[str, Any]) -> None:
        """Push a server-to-client notification, if a client is connected.

        A no-op outside a `serve` loop, so a handler may call it unconditionally
        and stay directly callable in a test.
        """
        if self._stdout is not None:
            write_message(self._stdout, {'jsonrpc': '2.0', 'method': method, 'params': params})

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

        try:
            result = handler(params)
        except Exception as exc:  # a resident server must survive any handler defect
            # A resident server whose justification is residency cannot be
            # killed by one bad request. Every handler exception becomes a
            # JSON-RPC error for a request, or a logged no-op for a
            # notification, so the session continues and the frame stream stays
            # well-formed. The trigger observed was `Path.read_text` raising
            # `ValueError` on a null byte in a URI, but the shape is general:
            # ANY handler exception used to end the process.
            _log_exception(method, exc)
            if message_id is None:
                return None
            return _error(message_id, INTERNAL_ERROR, f'{method} failed: {type(exc).__name__}: {exc}')
        if message_id is None:
            return None
        return _result(message_id, result)

    def serve(self, stdin: BinaryIO, stdout: BinaryIO) -> int:
        """Run the read/dispatch/write loop until the client exits.

        Two independent boundaries, because a session dies at two layers and
        only one of them was ever guarded:

        * **the frame**, below — a malformed frame whose declared body was read
          whole leaves the stream aligned, so it is logged and skipped and the
          session goes on. One whose length was unusable leaves the reader with
          no idea where the next frame starts, so the session ends — but it says
          so on stderr rather than presenting as a client that hung up;
        * **the handler**, in the inner ``try`` — :meth:`handle` already
          contains every handler defect, so what reaches there is a defect in
          dispatch or in serialising a response, still not a reason to end a
          session a client is holding open.
        """
        self._stdout = stdout
        try:
            while True:
                try:
                    message = read_message(stdin)
                except FrameError as frame_error:
                    _log_frame_error(frame_error)
                    if frame_error.recoverable:
                        continue
                    return 0
                if message is None:
                    return 0
                try:
                    response = self.handle(message)
                    if response is not None:
                        write_message(stdout, response)
                except Exception as exc:  # one bad frame must not end the session
                    _log_exception(message.get('method'), exc)
                    continue
                if self.shutdown_requested and message.get('method') == 'exit':
                    return 0
        finally:
            self._stdout = None


def _log_frame_error(frame_error: FrameError) -> None:
    """Report an undecodable frame on **stderr**, whether or not it ends the session.

    ⛔ Both arms log. A skipped frame is evidence of a client defect that an
    operator needs even though the session survived; an unrecoverable one is the
    difference between "the client hung up" and "the client sent something this
    server could not parse", which is the whole reason the session must not end
    in silence.
    """
    outcome = 'skipping the frame' if frame_error.recoverable else 'ending the session — the stream is not frame-aligned'
    print(f'[corpus-lsp] malformed frame: {frame_error.detail}; {outcome}', file=sys.stderr)
    sys.stderr.flush()


def _log_exception(method: Any, exc: BaseException) -> None:
    """Report a contained exception on **stderr**, never on the frame stream.

    The boundary above swallows exceptions so the session survives; without this
    line it would also swallow the evidence, and a real defect would present as
    a request that quietly returns nothing. stderr is the only channel available:
    stdout is the protocol.
    """
    print(f'[corpus-lsp] handler error in {method!r}: {type(exc).__name__}: {exc}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()


def _result(message_id: Any, result: Any) -> dict[str, Any]:
    return {'jsonrpc': '2.0', 'id': message_id, 'result': result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {'jsonrpc': '2.0', 'id': message_id, 'error': {'code': code, 'message': message}}
