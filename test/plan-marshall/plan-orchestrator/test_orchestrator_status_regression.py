#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression tests for validation gaps.

Exercises both fixes from the user-visible angle via constructed argv through
``subprocess.run`` (``run_script``): the ``--status`` vocabulary gate on the
``queue`` surface and the claim-index parser that excludes operational bullets
on the ``corpus`` surface.

Five cases, each through the ``orchestrator.py`` entry point:

- ``queue --transition --status <invalid>`` is refused with ``invalid_field``.
- ``queue --add-row --status <invalid>`` is refused with ``invalid_field``.
- ``queue --transition --status staged`` succeeds.
- ``corpus set-verdict`` with the visible claim index after operational bullets
  succeeds and stamps the addressed claim.
- ``corpus verdicts`` returns visible claim indices when operational bullets are
  interleaved with claim bullets.
"""

import json
from pathlib import Path
from typing import Any

from conftest import get_script_path, run_script

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
_SHA = '9f3a1c2'
_PRODUCER = 'regression-epic/corpus'
_EVIDENCE = 'regression evidence text'


def _epic_dir(plan_context: Any, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _make_plan(plan_id: str, status: str = 'staged') -> dict[str, Any]:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context: Any, slug: str, plans: list[dict[str, Any]]) -> Path:
    doc: dict[str, Any] = {
        'kind': 'orchestrator',
        'title': 'Regression Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': plans,
        'resume_anchor': 'regression',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _spec_text(claim_lines: list[str]) -> str:
    head = ['# PLAN-01: Regression', '', '## Objective', '', 'Regression objective.', '']
    section = ['## Claim Labels', '', *claim_lines, '']
    tail = ['## Expected Surface', '', '- OBSERVED: `a.py` — `f`']
    return '\n'.join([*head, *section, *tail]) + '\n'


def _write_spec(plan_context: Any, slug: str, name: str, claim_lines: list[str]) -> Path:
    path = _epic_dir(plan_context, slug) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_spec_text(claim_lines), encoding='utf-8')
    return path


_CLAIM_A = '- OBSERVED: first claim — read at `a.py` § `f`'
_CLAIM_B = '- OBSERVED: second claim — read at `b.py` § `g`'
_OPERATIONAL = '- \u2699\ufe0f operational note: nightly sync runs elsewhere'


def _set_verdict_argv(slug: str, plan: str, claim_index: int) -> list[str]:
    return [
        'corpus',
        'set-verdict',
        '--slug',
        slug,
        '--plan',
        plan,
        '--claim-index',
        str(claim_index),
        '--verdict',
        'corroborated',
        '--checked-at',
        _SHA,
        '--by',
        _PRODUCER,
        '--rescoped',
        'n/a',
        '--evidence',
        _EVIDENCE,
    ]


class TestQueueStatusVocabularyRegression:
    def test_should_reject_invalid_status_on_transition_through_cli(self, plan_context: Any) -> None:
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        status_path = _write_status(plan_context, 'regression-status-epic', [_make_plan('PLAN-01')])

        result = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'regression-status-epic',
            '--transition',
            'PLAN-01',
            '--status',
            'bogus',
            env_overrides=env,
        )

        assert result.returncode == 0
        assert 'status: error' in result.stdout
        assert 'invalid_field' in result.stdout
        assert '--status must be one of' in result.stdout
        before = json.loads(status_path.read_text(encoding='utf-8'))
        assert before['plans'][0]['status'] == 'staged'

    def test_should_reject_invalid_status_on_add_row_through_cli(self, plan_context: Any) -> None:
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        status_path = _write_status(plan_context, 'regression-addrow-epic', [])

        result = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'regression-addrow-epic',
            '--add-row',
            'PLAN-07',
            '--slug-value',
            'plan-07',
            '--workstream',
            'WS-01',
            '--status',
            'bogus',
            env_overrides=env,
        )

        assert result.returncode == 0
        assert 'status: error' in result.stdout
        assert 'invalid_field' in result.stdout
        assert '--status must be one of' in result.stdout
        after = json.loads(status_path.read_text(encoding='utf-8'))
        assert after['plans'] == []

    def test_should_accept_staged_status_on_transition_through_cli(self, plan_context: Any) -> None:
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, 'regression-staged-epic', [_make_plan('PLAN-01', status='running')])

        result = run_script(
            SCRIPT_PATH,
            'queue',
            '--slug',
            'regression-staged-epic',
            '--transition',
            'PLAN-01',
            '--status',
            'staged',
            env_overrides=env,
        )

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'new_status: staged' in result.stdout


class TestClaimIndexRegression:
    def test_should_set_verdict_by_visible_claim_index_with_operational_bullets_through_cli(
        self, plan_context: Any
    ) -> None:
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        slug = 'regression-claim-epic'
        _write_status(plan_context, slug, [_make_plan('PLAN-01')])
        spec = _write_spec(plan_context, slug, 'PLAN-01-claims.md', [_CLAIM_A, _OPERATIONAL, _CLAIM_B])
        assert spec.is_file()

        result = run_script(SCRIPT_PATH, *_set_verdict_argv(slug, 'PLAN-01', 1), env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'claim_index: 1' in result.stdout
        assert 'claims_total: 2' in result.stdout
        text = spec.read_text(encoding='utf-8')
        assert _CLAIM_B in text
        assert text.count('  - verdict: corroborated') == 1
        assert text.index(_CLAIM_B) < text.index('  - verdict: corroborated')
        between = text[text.index(_CLAIM_A) : text.index(_CLAIM_B)]
        assert 'verdict:' not in between

    def test_should_report_visible_claim_indices_with_interleaved_operational_bullets_through_cli(
        self, plan_context: Any
    ) -> None:
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        slug = 'regression-verdicts-epic'
        _write_status(plan_context, slug, [_make_plan('PLAN-01')])
        _write_spec(plan_context, slug, 'PLAN-01-claims.md', [_CLAIM_A, _OPERATIONAL, _CLAIM_B])

        first = run_script(SCRIPT_PATH, *_set_verdict_argv(slug, 'PLAN-01', 0), env_overrides=env)
        second = run_script(SCRIPT_PATH, *_set_verdict_argv(slug, 'PLAN-01', 1), env_overrides=env)
        assert first.returncode == 0
        assert second.returncode == 0

        result = run_script(SCRIPT_PATH, 'corpus', 'verdicts', '--slug', slug, env_overrides=env)

        assert result.returncode == 0
        payload = result.toon()
        assert payload['specs_scanned'] == 1
        assert payload['claims_scanned'] == 2
        indices = sorted(row['claim_index'] for row in payload['claims'])
        assert indices == [0, 1]
