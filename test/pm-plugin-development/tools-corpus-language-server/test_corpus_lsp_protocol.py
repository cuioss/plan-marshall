#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the server-side JSON-RPC framing and dispatch."""

from __future__ import annotations

import io
import json
import sys

from conftest import get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-corpus-language-server')
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _corpus_lsp_protocol as protocol  # noqa: E402


def framed(payload: dict) -> bytes:
    body = json.dumps(payload).encode('utf-8')
    return f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii') + body


class TestFraming:
    def test_round_trips_a_message(self) -> None:
        message = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}
        out = io.BytesIO()
        protocol.write_message(out, message)
        assert protocol.read_message(io.BytesIO(out.getvalue())) == message

    def test_end_of_stream_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(b'')) is None

    def test_missing_content_length_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(b'X-Other: 1\r\n\r\n{}')) is None

    def test_non_integer_content_length_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(b'Content-Length: abc\r\n\r\n{}')) is None

    def test_truncated_body_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(b'Content-Length: 100\r\n\r\n{"a":1}')) is None

    def test_malformed_json_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(b'Content-Length: 5\r\n\r\n{not}')) is None

    def test_non_object_payload_yields_none(self) -> None:
        assert protocol.read_message(io.BytesIO(framed_list())) is None


def framed_list() -> bytes:
    body = json.dumps([1, 2]).encode('utf-8')
    return f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii') + body


class TestCapabilities:
    def test_disabled_server_advertises_nothing(self) -> None:
        assert protocol.LspServer(enabled=False).capabilities() == {}

    def test_enabled_server_advertises_the_three_verbs(self) -> None:
        capabilities = protocol.LspServer(enabled=True).capabilities()
        assert capabilities['definitionProvider'] is True
        assert capabilities['referencesProvider'] is True
        assert capabilities['hoverProvider'] is True

    def test_no_diagnostic_provider_while_d3_is_gated(self) -> None:
        assert 'diagnosticProvider' not in protocol.active_capabilities()


class TestDispatch:
    def test_registered_handler_answers_a_request(self) -> None:
        server = protocol.LspServer(enabled=True)
        server.register('custom/echo', lambda params: params.get('value'))
        response = server.handle({'jsonrpc': '2.0', 'id': 7, 'method': 'custom/echo', 'params': {'value': 42}})
        assert response == {'jsonrpc': '2.0', 'id': 7, 'result': 42}

    def test_notification_produces_no_response(self) -> None:
        server = protocol.LspServer(enabled=True)
        server.register('custom/note', lambda params: 'ignored')
        assert server.handle({'jsonrpc': '2.0', 'method': 'custom/note'}) is None

    def test_unknown_request_returns_method_not_found(self) -> None:
        server = protocol.LspServer(enabled=True)
        response = server.handle({'jsonrpc': '2.0', 'id': 3, 'method': 'nope'})
        assert response is not None
        assert response['error']['code'] == protocol.METHOD_NOT_FOUND

    def test_unknown_notification_is_ignored(self) -> None:
        assert protocol.LspServer(enabled=True).handle({'jsonrpc': '2.0', 'method': 'nope'}) is None

    def test_non_dict_params_are_tolerated(self) -> None:
        server = protocol.LspServer(enabled=True)
        server.register('custom/echo', lambda params: sorted(params))
        response = server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'custom/echo', 'params': ['bad']})
        assert response == {'jsonrpc': '2.0', 'id': 1, 'result': []}

    def test_shutdown_returns_null_and_flags(self) -> None:
        server = protocol.LspServer(enabled=True)
        response = server.handle({'jsonrpc': '2.0', 'id': 9, 'method': 'shutdown'})
        assert response == {'jsonrpc': '2.0', 'id': 9, 'result': None}
        assert server.shutdown_requested

    def test_exit_produces_no_response(self) -> None:
        server = protocol.LspServer(enabled=True)
        assert server.handle({'jsonrpc': '2.0', 'method': 'exit'}) is None
        assert server.shutdown_requested


class TestServeLoop:
    def test_serves_until_exit(self) -> None:
        server = protocol.LspServer(enabled=True)
        server.register('initialize', lambda params: {'capabilities': server.capabilities()})
        stdin = io.BytesIO(
            framed({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
            + framed({'jsonrpc': '2.0', 'method': 'exit'})
        )
        stdout = io.BytesIO()
        assert server.serve(stdin, stdout) == 0
        replayed = protocol.read_message(io.BytesIO(stdout.getvalue()))
        assert replayed is not None
        assert replayed['result']['capabilities']['definitionProvider'] is True

    def test_returns_zero_when_the_client_disappears(self) -> None:
        server = protocol.LspServer(enabled=True)
        assert server.serve(io.BytesIO(b''), io.BytesIO()) == 0
