#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end coverage of the OpenCode measurement path against a real store.

A fixture ``opencode.db`` — one plan tree, its sub-agent sessions and a second
captured root — is driven through ``manage-metrics enrich`` and ``generate``.
The store, the reader, the per-phase composer, the persistence and the report
are all the production code; only the process boundary that launches the runtime
op is stubbed, because that argv hop is covered by the CLI plumbing tests.

The point is the shape the store actually has: ``content[]`` tool parts inside
assistant messages, ``tokens.reasoning``, and a per-message cost. A test that
invents a row type the store never carries cannot fail when the reader stops
reading the real one.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import opencode_runtime
import pytest
from _manage_metrics_fixtures import ns_enrich, ns_generate
from _manage_metrics_module_fixtures import (
    _seed_guarded_plan_dirs,
    cmd_enrich,
    cmd_generate,
    manage_metrics,
)

_BASE = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
_WINDOWS = (
    ('5-execute', _BASE, _BASE + timedelta(hours=1)),
    ('6-finalize', _BASE + timedelta(hours=1), _BASE + timedelta(hours=2)),
)


def _at(minutes: int) -> int:
    """Return the epoch-millisecond stamp *minutes* after the fixed clock."""
    return int((_BASE + timedelta(minutes=minutes)).timestamp() * 1000)


def _iso(value: datetime) -> str:
    """Return *value* as the ISO stamp the metrics store carries."""
    return value.isoformat()


def _parse(toon_str: str) -> dict:
    """Parse a TOON string and assert it is a non-empty dict."""
    from toon_parser import parse_toon

    parsed = parse_toon(toon_str)
    assert isinstance(parsed, dict), f'parse_toon returned non-dict: {toon_str!r}'
    return parsed


class _FakeCompleted:
    """Minimal stand-in for ``subprocess.CompletedProcess``."""

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.returncode = 0
        self.stderr = ''


def _run_runtime_op_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive the runtime op itself instead of launching a child interpreter.

    The stub reads the same argv the production call builds, so the op receives
    the session id, the windows file and the output file exactly as it would from
    the real subprocess; only the interpreter launch is skipped.
    """

    def _fake_run(argv: list[str], *_args: Any, **_kwargs: Any):
        session_id = argv[argv.index('--session-id') + 1]
        windows_file = Path(argv[argv.index('--windows-file') + 1])
        output_file = argv[argv.index('--output-file') + 1]
        windows = [tuple(entry) for entry in json.loads(windows_file.read_text(encoding='utf-8'))]
        stdout = opencode_runtime.OpenCodeRuntime().metrics_normalized_tokens(session_id, windows, output_file)
        return _FakeCompleted(stdout)

    monkeypatch.setattr(manage_metrics.subprocess, 'run', _fake_run)


def _write_store(db_path: Path, worktree: Path) -> None:
    """Create the fixture store: two roots, their sub-agents and their messages."""
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            'CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT, directory TEXT,'
            ' tokens_input INTEGER, tokens_output INTEGER, tokens_cache_read INTEGER,'
            ' tokens_cache_write INTEGER, cost REAL)'
        )
        sessions = [
            ('root-a', None, 300, 40, 0, 0, 0.2),
            ('sub-a1', 'root-a', 1000, 500, 0, 100, 0.5),
            ('sub-a2', 'root-a', 2000, 300, 0, 0, 0.7),
            ('root-b', None, 300, 40, 0, 0, 0.2),
            ('sub-b1', 'root-b', 4000, 900, 0, 0, 1.0),
        ]
        connection.executemany(
            'INSERT INTO session_v2 (id, parent_id, model, directory, tokens_input,'
            ' tokens_output, tokens_cache_read, tokens_cache_write, cost)'
            ' VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)',
            [(session_id, parent, str(worktree), *usage) for session_id, parent, *usage in sessions],
        )
        connection.execute('CREATE TABLE session_message (session_id TEXT, type TEXT, time_created INTEGER, data TEXT)')
        messages = [
            (
                'root-a',
                'assistant',
                _at(10),
                {
                    'tokens': {'input': 100, 'output': 50, 'reasoning': 10},
                    'cost': 0.1,
                    'content': [{'type': 'tool', 'tool': 'bash'}, {'type': 'tool', 'tool': 'read'}],
                },
            ),
            (
                'sub-a1',
                'assistant',
                _at(20),
                {
                    'tokens': {'input': 1000, 'output': 500, 'reasoning': 25, 'cache': {'write': 100}},
                    'cost': 0.5,
                    'content': [{'type': 'tool', 'tool': 'bash'}, {'type': 'tool', 'tool': 'grep'}, {'type': 'tool'}],
                },
            ),
            (
                'sub-a2',
                'assistant',
                _at(40),
                {
                    'tokens': {'input': 2000, 'output': 300},
                    'cost': 0.7,
                    'content': [{'type': 'tool', 'tool': 'read'}],
                },
            ),
            (
                'root-b',
                'assistant',
                _at(70),
                {
                    'tokens': {'input': 300, 'output': 40, 'reasoning': 5},
                    'cost': 0.2,
                    'content': [{'type': 'tool', 'tool': 'bash'}],
                },
            ),
            (
                'sub-b1',
                'assistant',
                _at(90),
                {
                    'tokens': {'input': 4000, 'output': 900},
                    'cost': 1.0,
                    'content': [{'type': 'tool', 'tool': 'bash'}, {'type': 'tool', 'tool': 'write'}],
                },
            ),
        ]
        connection.executemany(
            'INSERT INTO session_message (session_id, type, time_created, data) VALUES (?, ?, ?, ?)',
            [
                (session_id, message_type, created, json.dumps(data))
                for session_id, message_type, created, data in messages
            ],
        )
        connection.commit()
    finally:
        connection.close()


def _seed_plan(plan_id: str) -> None:
    """Seed the plan's two phase windows with no recorded totals of their own."""
    manage_metrics.write_metrics(
        plan_id,
        {
            'plan_id': plan_id,
            'phases': {phase: {'start_time': _iso(start), 'end_time': _iso(end)} for phase, start, end in _WINDOWS},
        },
    )


def test_enrich_and_generate_measure_a_real_fixture_store(plan_context, monkeypatch, tmp_path):
    """The whole reader-to-landing chain is measured from one fixture database.

    Dispatched ledger tests that stub the op's buckets cannot fail when the
    reader mis-reads the store's shape; this one cannot pass unless the reader,
    the composer, the persistence and the report all agree about a store shaped
    the way OpenCode writes one.
    """
    plan_id = 'opencode-fixture-store'
    _seed_plan(plan_id)
    worktree = tmp_path / 'worktree'
    worktree.mkdir()
    db_path = tmp_path / 'opencode.db'
    _write_store(db_path, worktree)
    monkeypatch.setenv('OPENCODE_DB', str(db_path))
    monkeypatch.chdir(worktree)
    _run_runtime_op_in_process(monkeypatch)

    result = cmd_enrich(ns_enrich(plan_id, 'root-a', 'root-b'))

    assert result['status'] == 'success'
    assert result['enriched'] is True
    assert result['sessions_measured'] == 2
    assert result['four_field_phases_attributed'] == 2

    phases = manage_metrics.read_metrics_raw(plan_id)['phases']
    execute = phases['5-execute']
    # main-context (100 + 50) + sub-agent (1000+500+100 and 2000+300).
    assert execute['inline_main_context_tokens'] == 150
    assert execute['subagent_total_tokens'] == 3900
    assert execute['total_tokens'] == 4050
    assert execute['total_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT
    assert execute['subagent_samples'] == 2
    assert execute['subagent_tool_uses'] == 4
    assert execute['measured_tool_uses'] == 6
    assert execute['reasoning_tokens'] == 10 + 25
    assert execute['cost_usd'] == pytest.approx(0.1 + 0.5 + 0.7)

    finalize = phases['6-finalize']
    assert finalize['total_tokens'] == 340 + 4900
    assert finalize['measured_tool_uses'] == 3

    generated = cmd_generate(ns_generate(plan_id))
    assert generated['total_tokens'] == 4050 + 5240
    assert generated['totals_tokens_population'] == manage_metrics.POPULATION_MAIN_PLUS_SUBAGENT
    report = (plan_context.plan_dir_for(plan_id) / 'metrics.md').read_text(encoding='utf-8')
    assert '9,290' in report
