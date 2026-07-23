#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _build_server_protocol internals.

Drive the wire protocol and job/result schema helpers directly by inserting the
script-shared build scripts dir on sys.path (mirrors the executor PYTHONPATH the
daemon and client run under).
"""

from __future__ import annotations

import asyncio
import json
import socket
import sys
from typing import cast

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'script-shared', 'build/_build_server_protocol.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_server_protocol as proto  # noqa: E402


# =============================================================================
# Helpers
# =============================================================================


class _FakeWriter:
    """Minimal asyncio-StreamWriter stand-in capturing written bytes."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def write(self, data: bytes) -> None:
        self.buffer += data

    async def drain(self) -> None:
        return None


def _reader_from_bytes(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


# A payload with a nested structure AND multi-line error messages — the exact
# shape length-prefixed framing must round-trip losslessly where a
# newline-delimited framing would corrupt.
_MULTILINE_PAYLOAD = {
    'status': 'failure',
    'duration_seconds': 42,
    'log_file': '/tmp/build.log',
    'errors': [
        {
            'file': 'src/mod.py',
            'line': 10,
            'message': 'first line\nsecond line\nthird line',
            'category': 'type_error',
        },
        {
            'file': 'src/other.py',
            'line': None,
            'message': 'unterminated {\n  block',
            'category': 'syntax_error',
        },
    ],
    'nested': {'a': [1, 2, {'b': 'x\ny'}]},
}


# =============================================================================
# Frame codec — encode / decode layout
# =============================================================================


def test_encode_frame_layout_length_prefix_matches_body():
    payload = {'status': 'ok'}

    frame = proto.encode_frame(payload)

    prefix, body = frame[:4], frame[4:]
    (declared,) = proto._LENGTH_STRUCT.unpack(prefix)
    assert declared == len(body)
    assert json.loads(body.decode('utf-8')) == payload


def test_decode_payload_round_trips_body():
    payload = {'a': 1, 'b': [2, 3]}

    frame = proto.encode_frame(payload)

    assert proto.decode_payload(frame[4:]) == payload


def test_decode_payload_rejects_non_json():
    with pytest.raises(proto.FrameDecodeError):
        proto.decode_payload(b'not json at all')


def test_decode_payload_rejects_non_object():
    # Valid JSON, but a top-level array, not the object the frame contract
    # requires.
    with pytest.raises(proto.FrameDecodeError):
        proto.decode_payload(b'[1, 2, 3]')


# =============================================================================
# Frame codec — blocking socket round-trip
# =============================================================================


def test_blocking_round_trip_multiline_payload():
    left, right = socket.socketpair()
    try:
        proto.send_frame(left, _MULTILINE_PAYLOAD)
        received = proto.recv_frame(right)
    finally:
        left.close()
        right.close()

    assert received == _MULTILINE_PAYLOAD
    # Multi-line messages survive intact (the delimiter-in-payload case).
    assert received['errors'][0]['message'] == 'first line\nsecond line\nthird line'


def test_blocking_truncated_prefix_raises():
    left, right = socket.socketpair()
    try:
        left.sendall(b'\x00\x00')  # only 2 of the 4 prefix bytes
        left.close()
        with pytest.raises(proto.FrameTruncatedError):
            proto.recv_frame(right)
    finally:
        left.close()
        right.close()


def test_blocking_truncated_body_raises():
    left, right = socket.socketpair()
    try:
        # Declare a 100-byte body but send only 5 bytes, then close.
        left.sendall(proto._LENGTH_STRUCT.pack(100) + b'12345')
        left.close()
        with pytest.raises(proto.FrameTruncatedError):
            proto.recv_frame(right)
    finally:
        left.close()
        right.close()


def test_blocking_oversized_declared_length_rejected_before_body():
    left, right = socket.socketpair()
    try:
        # Send ONLY the header declaring an over-cap body; no body follows.
        # recv_frame must reject on the prefix without blocking to read a body.
        left.sendall(proto._LENGTH_STRUCT.pack(proto.MAX_FRAME_BYTES + 1))
        with pytest.raises(proto.FrameTooLargeError):
            proto.recv_frame(right)
    finally:
        left.close()
        right.close()


# =============================================================================
# Frame codec — asyncio stream round-trip
# =============================================================================


def test_async_write_then_read_round_trip():
    async def _run() -> dict:
        writer = _FakeWriter()
        await proto.write_frame(cast(asyncio.StreamWriter, writer), _MULTILINE_PAYLOAD)
        reader = _reader_from_bytes(bytes(writer.buffer))
        return await proto.read_frame(reader)

    received = asyncio.run(_run())
    assert received == _MULTILINE_PAYLOAD


def test_async_truncated_prefix_raises():
    async def _run() -> None:
        reader = _reader_from_bytes(b'\x00\x00')
        await proto.read_frame(reader)

    with pytest.raises(proto.FrameTruncatedError):
        asyncio.run(_run())


def test_async_truncated_body_raises():
    async def _run() -> None:
        reader = _reader_from_bytes(proto._LENGTH_STRUCT.pack(100) + b'123')
        await proto.read_frame(reader)

    with pytest.raises(proto.FrameTruncatedError):
        asyncio.run(_run())


def test_async_oversized_declared_length_rejected():
    async def _run() -> None:
        reader = _reader_from_bytes(proto._LENGTH_STRUCT.pack(proto.MAX_FRAME_BYTES + 1))
        await proto.read_frame(reader)

    with pytest.raises(proto.FrameTooLargeError):
        asyncio.run(_run())


# =============================================================================
# Frame codec — oversized encode
# =============================================================================


def test_encode_oversized_body_rejected(monkeypatch):
    # Shrink the cap so a modest payload trips it deterministically.
    monkeypatch.setattr(proto, 'MAX_FRAME_BYTES', 16)
    with pytest.raises(proto.FrameTooLargeError) as excinfo:
        proto.encode_frame({'message': 'x' * 1000})
    assert excinfo.value.limit_bytes == 16
    assert excinfo.value.declared_bytes > 16


# =============================================================================
# Job spec
# =============================================================================


def test_job_spec_to_from_dict_round_trip():
    spec = proto.JobSpec(
        command=['python3', '/tree/.plan/execute-script.py', 'a:b:c'],
        exec_path='/tree',
        project_path='/tree',
        plan_id='p1',
        fingerprint='deadbeef',
    )

    restored = proto.JobSpec.from_dict(spec.to_dict())

    assert restored == spec


def test_job_spec_from_dict_missing_field_raises():
    with pytest.raises(ValueError, match='missing required field'):
        proto.JobSpec.from_dict({'command': [], 'exec_path': '/t', 'project_path': '/t'})


def test_job_spec_from_dict_bad_command_raises():
    bad = {
        'command': 'not-a-list',
        'exec_path': '/t',
        'project_path': '/t',
        'plan_id': 'p',
    }
    with pytest.raises(ValueError, match='command must be a list'):
        proto.JobSpec.from_dict(bad)


def test_job_spec_from_dict_non_string_command_token_raises():
    bad = {
        'command': ['ok', 123],
        'exec_path': '/t',
        'project_path': '/t',
        'plan_id': 'p',
    }
    with pytest.raises(ValueError, match='command must be a list'):
        proto.JobSpec.from_dict(bad)


def test_compute_fingerprint_deterministic_and_sensitive():
    fp1 = proto.compute_fingerprint('p', ['a', 'b'], '/tree', '/tree')
    fp2 = proto.compute_fingerprint('p', ['a', 'b'], '/tree', '/tree')
    fp3 = proto.compute_fingerprint('p', ['a', 'c'], '/tree', '/tree')

    assert fp1 == fp2
    assert fp1 != fp3
    assert len(fp1) == 64  # sha256 hex


def test_make_job_spec_derives_fingerprint_when_absent():
    spec = proto.make_job_spec(['a'], '/tree', '/tree', 'p')

    assert spec.fingerprint
    assert spec.fingerprint == proto.compute_fingerprint('p', ['a'], '/tree', '/tree')


def test_make_job_spec_preserves_explicit_fingerprint():
    spec = proto.make_job_spec(['a'], '/tree', '/tree', 'p', fingerprint='explicit')

    assert spec.fingerprint == 'explicit'


# =============================================================================
# Status schema
# =============================================================================


def test_normalize_error_fills_defaults():
    normalized = proto.normalize_error({'message': 'boom'})

    assert normalized == {
        'file': '',
        'line': None,
        'message': 'boom',
        'category': '',
    }


def test_normalize_error_drops_extra_keys():
    normalized = proto.normalize_error(
        {'file': 'f', 'line': 1, 'message': 'm', 'category': 'c', 'extra': 'x'}
    )

    assert set(normalized) == set(proto.ERROR_FIELDS)


def test_normalize_errors_handles_none():
    assert proto.normalize_errors(None) == []


def test_wire_status_mapping_round_trip():
    assert proto.wire_status_from_result('success') == proto.STATUS_SUCCESS
    assert proto.wire_status_from_result('error') == proto.STATUS_FAILURE
    assert proto.wire_status_from_result('timeout') == proto.STATUS_TIMEOUT
    # Inverse
    assert proto.result_status_from_wire(proto.STATUS_FAILURE) == 'error'
    assert proto.result_status_from_wire(proto.STATUS_SUCCESS) == 'success'
    # Pass-through for statuses with no _build_result equivalent.
    assert proto.result_status_from_wire(proto.STATUS_KILLED) == proto.STATUS_KILLED


def test_status_payload_omits_absent_optionals():
    payload = proto.status_payload(proto.STATUS_RUNNING, eta=30)

    assert payload == {'status': proto.STATUS_RUNNING, 'eta': 30}
    assert 'log_file' not in payload
    assert 'errors' not in payload


def test_status_from_result_maps_error_to_failure():
    result = {
        'status': 'error',
        'exit_code': 1,
        'duration_seconds': 12,
        'log_file': '/tmp/x.log',
        'errors': [{'message': 'boom'}],
    }

    payload = proto.status_from_result(result)

    assert payload['status'] == proto.STATUS_FAILURE
    assert payload['exit_code'] == 1
    assert payload['duration_seconds'] == 12
    assert payload['log_file'] == '/tmp/x.log'
    assert payload['errors'] == [
        {'file': '', 'line': None, 'message': 'boom', 'category': ''}
    ]


def test_status_from_result_killed_overrides_status():
    result = {'status': 'success', 'exit_code': 0, 'duration_seconds': 1}

    payload = proto.status_from_result(result, killed=True)

    assert payload['status'] == proto.STATUS_KILLED


def test_terminal_statuses_membership():
    assert proto.STATUS_KILLED in proto.TERMINAL_STATUSES
    assert proto.STATUS_SUCCESS in proto.TERMINAL_STATUSES
    assert proto.STATUS_RUNNING not in proto.TERMINAL_STATUSES
    assert proto.STATUS_QUEUED not in proto.TERMINAL_STATUSES


# =============================================================================
# read_log_verdict — the relocated single shared verdict reader
# =============================================================================
# Relocated here from _marshalld_supervisor: this is now the ONE reader both the
# daemon's run_job narrowing and the client's _daemon_result_to_direct cross-check
# consume, so its unit coverage lives with the shared contract module.


class TestReadLogVerdict:
    """The pure job-log verdict reader, in its shared home."""

    def test_parses_status_and_exit_code(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('[EXEC] ./pw verify\nstatus: error\nexit_code: 7\nduration_seconds: 3\n')

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code == 7

    def test_ignores_indented_toon_rows(self, tmp_path):
        # The errors[] table rows are indented; only the top-level keys count.
        log = tmp_path / 'job.log'
        log.write_text('status: success\nexit_code: 0\nerrors[1]{file,line}:\n  status: error\n')

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'success'
        assert verdict.exit_code == 0

    def test_unquotes_a_quoted_scalar(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('status: "error"\nexit_code: 2\n')

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code == 2

    def test_last_occurrence_wins_over_progress_output(self, tmp_path):
        # The wrapper streams progress first, then emits its final result TOON to
        # the SAME log; the last top-level status:/exit_code: must win.
        log = tmp_path / 'job.log'
        log.write_text(
            'status: running\nexit_code: 0\n'
            '... more build chatter ...\n'
            'status: error\nexit_code: 5\n'
        )

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code == 5

    def test_unparseable_exit_code_degrades_to_none(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('status: error\nexit_code: -\n')

        verdict = proto.read_log_verdict(str(log))

        assert verdict is not None
        assert verdict.status == 'error'
        assert verdict.exit_code is None

    def test_log_without_status_line_returns_none(self, tmp_path):
        log = tmp_path / 'job.log'
        log.write_text('just some build chatter\n')

        assert proto.read_log_verdict(str(log)) is None

    def test_missing_log_returns_none(self, tmp_path):
        assert proto.read_log_verdict(str(tmp_path / 'absent.log')) is None

    def test_unreadable_log_returns_none(self, tmp_path):
        # A directory in place of a file raises OSError on open -> None (the
        # "unreadable" leg of the missing/unreadable/no-status contract).
        d = tmp_path / 'a_dir'
        d.mkdir()

        assert proto.read_log_verdict(str(d)) is None
