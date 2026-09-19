#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``corpus read`` verb of the plan-orchestrator script.

The sanctioned script-mediated read path for staged orchestrator specs
(``.plan/local/orchestrator/{slug}/plans/PLAN-NN-*.md``) — the use case the
``.plan/`` scripts-only rule did not cover, which forced five independent
direct-read violations before this verb existed (see PLAN-03).

Covers the read path against a SCAFFOLDED FIXTURE EPIC under ``PLAN_BASE_DIR``
isolation — never the live tree:

- ``corpus read`` success: resolves ``PLAN-NN`` to its spec file and returns
  the body with ``size_bytes`` / ``line_count`` populations.
- ``spec_not_found``: names ``available_specs`` and writes nothing (an absent
  spec is never rendered as an empty body).
- ``invalid_slug`` / ``invalid_plan``: unsafe inputs refused before any
  filesystem access (path traversal via ``..`` or ``/`` never reaches the
  store resolver).
- ``unreadable``: a spec that cannot be decoded is reported, never dropped.

Rejection tests assert BOTH the error envelope AND that the fixture tree is
byte-identical afterwards — read-only means read-only.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    get_script_path,
    load_script_module,
    parse_ns,
)

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

_orch = load_script_module('plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_corpus_read')

cmd_corpus_read = _orch.cmd_corpus_read

SLUG = 'fixture-corpus-read-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

SPEC_BODY = (
    '# PLAN-01: Fixture spec\n'
    '\n'
    'epic: fixture-corpus-read-epic\n'
    'workstream: WS-01\n'
    '\n'
    '## Objective\n'
    '\n'
    'A fixture body the read path must return verbatim.\n'
)

_OTHER_BODY = '# PLAN-02: Other fixture\n\nepic: fixture-corpus-read-epic\n'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_READ_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'corpus',
    'read',
    '--slug',
    SLUG,
    '--plan',
    'PLAN-01',
    register=False,
)


def _epic_dir(plan_context, slug: str = SLUG) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _write_status(plan_context, rows: list, slug: str = SLUG) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Corpus Read Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _row(plan_id: str, status: str = 'staged') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_spec(plan_context, filename: str, body: str, slug: str = SLUG) -> Path:
    path = _epic_dir(plan_context, slug) / 'plans' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _seed(plan_context) -> None:
    _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
    _write_spec(plan_context, 'PLAN-01-fixture.md', SPEC_BODY)
    _write_spec(plan_context, 'PLAN-02-other.md', _OTHER_BODY)


def _tree_snapshot(root: Path) -> dict:
    """Map every file under ``root`` to its bytes (the read-only assertion)."""
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


class TestCorpusReadSuccess:
    def test_returns_body_verbatim_with_populations(self, plan_context):
        _seed(plan_context)
        result = cmd_corpus_read(_READ_ARGS)
        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-read'
        assert result['slug'] == SLUG
        assert result['plan'] == 'PLAN-01'
        assert result['spec'] == 'PLAN-01-fixture.md'
        assert result['body'] == SPEC_BODY
        assert result['size_bytes'] == len(SPEC_BODY.encode('utf-8'))
        assert result['line_count'] == len(SPEC_BODY.splitlines())

    def test_prefix_match_resolves_suffixed_filename(self, plan_context):
        _seed(plan_context)
        result = cmd_corpus_read(_variant(_READ_ARGS, plan='PLAN-02'))
        assert result['status'] == 'success'
        assert result['spec'] == 'PLAN-02-other.md'
        assert result['body'] == _OTHER_BODY

    def test_read_is_read_only(self, plan_context):
        _seed(plan_context)
        root = _epic_dir(plan_context)
        before = _tree_snapshot(root)
        cmd_corpus_read(_READ_ARGS)
        assert _tree_snapshot(root) == before


class TestCorpusReadRefusals:
    def test_spec_not_found_names_available_specs(self, plan_context):
        _seed(plan_context)
        root = _epic_dir(plan_context)
        before = _tree_snapshot(root)
        result = cmd_corpus_read(_variant(_READ_ARGS, plan='PLAN-99'))
        assert result['status'] == 'error'
        assert result['error'] == 'spec_not_found'
        assert 'PLAN-01-fixture.md' in result['available_specs']
        assert 'PLAN-02-other.md' in result['available_specs']
        assert 'body' not in result
        assert _tree_snapshot(root) == before

    def test_invalid_slug_refused(self, plan_context):
        _seed(plan_context)
        result = cmd_corpus_read(_variant(_READ_ARGS, slug='not a slug!'))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    @pytest.mark.parametrize('bad_plan', ['', '../PLAN-01', 'PLAN-01/x', '..', 'a/b'])
    def test_invalid_plan_traversal_refused(self, plan_context, bad_plan):
        _seed(plan_context)
        root = _epic_dir(plan_context)
        before = _tree_snapshot(root)
        result = cmd_corpus_read(_variant(_READ_ARGS, plan=bad_plan))
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_plan'
        assert 'body' not in result
        assert _tree_snapshot(root) == before

    def test_missing_epic_tree_reports_not_found(self, plan_context):
        result = cmd_corpus_read(_READ_ARGS)
        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_unreadable_spec_reported_never_dropped(self, plan_context, monkeypatch):
        _seed(plan_context)

        def _broken(path: Path):
            return None, 'unreadable'

        monkeypatch.setattr(_orch, '_read_spec', _broken)
        result = cmd_corpus_read(_READ_ARGS)
        assert result['status'] == 'error'
        assert result['error'] == 'unreadable'
        assert result['spec'] == 'PLAN-01-fixture.md'
        assert 'body' not in result

    def test_absent_spec_never_renders_as_empty_body(self, plan_context):
        _seed(plan_context)
        result = cmd_corpus_read(_variant(_READ_ARGS, plan='PLAN-03'))
        assert result['status'] == 'error'
        assert result.get('body', None) is None


class TestCorpusReadNonVacuity:
    def test_body_hash_matches_fixture_bytes(self, plan_context):
        _seed(plan_context)
        result = cmd_corpus_read(_READ_ARGS)
        assert (
            hashlib.sha256(result['body'].encode('utf-8')).hexdigest()
            == hashlib.sha256(SPEC_BODY.encode('utf-8')).hexdigest()
        )

    def test_hyphen_boundary_plan_1_does_not_claim_plan_10(self, plan_context):
        _write_status(plan_context, [_row('PLAN-1'), _row('PLAN-10')])
        _write_spec(plan_context, 'PLAN-10-tenth.md', _OTHER_BODY)
        _write_spec(plan_context, 'PLAN-1-first.md', SPEC_BODY)
        result = cmd_corpus_read(_variant(_READ_ARGS, plan='PLAN-1'))
        assert result['status'] == 'success'
        assert result['spec'] == 'PLAN-1-first.md'
