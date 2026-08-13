#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the landing drain-completeness check (plan 302 D5).

The terminal ``kind: landing`` message must carry a machine-readable
``landing-facts`` block (plan 302 D4). ``check_landing_completeness`` is the
drain-side validator that lets the orchestrator turn "the queue is empty" into
"nothing material is outstanding": it reports whether a drained landing carried
that block with every required fact key.

The single most important assertion here is that the check is **SEEN to fail on
a known-incomplete input** — a PRE-FIX, prose-only landing (the historical
narrative shape) carries no ``landing-facts`` block, so the check reports it
incomplete. A completeness check that passed on a prose-only landing would be
the vacuous guard this check exists to replace, so that case is pinned
first and explicitly.

Covered:

- Pure ``check_landing_completeness`` / ``parse_landing_facts`` over the pre-fix
  prose landing (FAILS), a complete facts landing (PASSES), a wrong-schema block
  (fail-closed), and a missing-key block (names the gap).
- The CLI verb ``orchestrator inbox landing-check`` end-to-end: a written
  prose landing reports ``complete: false``, a written facts landing reports
  ``complete: true``.
- The payload-spec doc (D3) derives the delta and classifies the seven control
  findings, keeping the false-merge report NARRATIVE-ONLY.
"""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT, get_script_path, load_script_module, run_script

_inbox = load_script_module(
    'plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox'
)
check_landing_completeness = _inbox.check_landing_completeness
parse_landing_facts = _inbox.parse_landing_facts
LANDING_REQUIRED_KEYS = _inbox.LANDING_REQUIRED_KEYS
LANDING_FACTS_SCHEMA = _inbox.LANDING_FACTS_SCHEMA

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_PLAN_MARSHALL = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_PAYLOAD_SPEC: Path = _PLAN_MARSHALL / 'plan-orchestrator' / 'standards' / 'landing-payload-spec.md'

EPIC = 'completeness-epic'
SENDER = 'completeness-plan'

_FENCE = '```'

#: The PRE-FIX landing shape: the historical narrative body, with NO
#: ``landing-facts`` block. This is the known-incomplete input the check MUST
#: fail on — a prose-only landing transmits none of the mechanisable delta.
_PRE_FIX_PROSE_LANDING = (
    '## What landed\n\n'
    'The plan shipped as PR #123 and merged. Residue: watch the fourth token '
    'total, it was 3.4% off the others.\n'
)


def _facts_block(**overrides: str) -> str:
    """Build a complete ``landing-facts`` block, with optional key overrides.

    Every required key is present with a non-empty value by default; an override
    of ``''`` drops a key's value (to exercise the missing-key branch) and an
    override to a non-``None`` value replaces it.
    """
    values = {
        'schema': LANDING_FACTS_SCHEMA,
        'plan_id': 'truthful-signals-302',
        'pr': '#1234',
        'merge_state': 'merged',
        'deliverables_total': '6',
        'deliverables_done': '6',
        'total_tokens': '512000',
        'steps': 'push:done,create-pr:done,archive-plan:done',
    }
    values.update(overrides)
    lines = '\n'.join(f'{key}={value}' for key, value in values.items())
    return f'{_FENCE}landing-facts\n{lines}\n{_FENCE}'


def _facts_landing(**overrides: str) -> str:
    return (
        '## What landed\n\ntruthful-signals-302 shipped as #1234 (merged).\n\n'
        f'{_facts_block(**overrides)}\n\n## Residue\n\nnone\n'
    )


# =============================================================================
# The check is SEEN to fail on the known-incomplete input (the D5 crux)
# =============================================================================


class TestSeenToFailOnPreFixLanding:
    def test_pre_fix_prose_landing_is_reported_incomplete(self):
        """The crux: a prose-only landing (no facts block) FAILS the check.

        This is what makes the guard non-vacuous — the exact known-incomplete
        input plan 302 exists to catch, pinned explicitly.
        """
        complete, missing = check_landing_completeness(_PRE_FIX_PROSE_LANDING)

        assert complete is False
        # No block at all -> every required key is reported missing.
        assert set(missing) == set(LANDING_REQUIRED_KEYS)

    def test_parse_returns_none_when_no_block_is_present(self):
        assert parse_landing_facts(_PRE_FIX_PROSE_LANDING) is None

    def test_complete_facts_landing_passes(self):
        complete, missing = check_landing_completeness(_facts_landing())

        assert complete is True
        assert missing == []

    def test_wrong_schema_is_fail_closed(self):
        landing = _facts_landing(schema='landing-facts/99')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['schema']

    def test_a_missing_required_key_is_named(self):
        landing = _facts_landing(total_tokens='')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['total_tokens']

    def test_required_key_set_is_the_shared_module_constant(self):
        # The producer (emit-landing) and this validator share ONE source.
        assert 'schema' in LANDING_REQUIRED_KEYS
        assert 'total_tokens' in LANDING_REQUIRED_KEYS
        assert 'steps' in LANDING_REQUIRED_KEYS


# =============================================================================
# The CLI verb transports the verdict end-to-end
# =============================================================================


def _env(plan_context) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}


def _scaffold(plan_context):
    return run_script(SCRIPT_PATH, 'scaffold', '--slug', EPIC, env_overrides=_env(plan_context))


def _write_landing(plan_context, tmp_path: Path, body: str, name: str) -> str:
    payload = tmp_path / name
    payload.write_text(body, encoding='utf-8')
    run_script(
        SCRIPT_PATH,
        'inbox', 'write',
        '--slug', EPIC,
        '--sender-type', 'plan',
        '--sender-id', SENDER,
        '--kind', 'landing',
        '--payload-file', str(payload),
        env_overrides=_env(plan_context),
    )
    return f'{SENDER}-001.md'


def _landing_check(plan_context, message: str):
    return run_script(
        SCRIPT_PATH,
        'inbox', 'landing-check',
        '--slug', EPIC,
        '--message', message,
        env_overrides=_env(plan_context),
    )


class TestLandingCheckCli:
    def test_prose_landing_reports_incomplete_end_to_end(self, plan_context, tmp_path):
        _scaffold(plan_context)
        message = _write_landing(plan_context, tmp_path, _PRE_FIX_PROSE_LANDING, 'prose.md')

        result = _landing_check(plan_context, message)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'complete: false' in result.stdout

    def test_facts_landing_reports_complete_end_to_end(self, plan_context, tmp_path):
        _scaffold(plan_context)
        message = _write_landing(plan_context, tmp_path, _facts_landing(), 'facts.md')

        result = _landing_check(plan_context, message)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'complete: true' in result.stdout

    def test_missing_message_is_file_not_found(self, plan_context):
        _scaffold(plan_context)

        result = _landing_check(plan_context, f'{SENDER}-404.md')

        assert 'error: file_not_found' in result.stdout


# =============================================================================
# The payload spec (D3) derives the delta and classifies the seven findings
# =============================================================================


class TestPayloadSpecDoc:
    def _text(self) -> str:
        return _PAYLOAD_SPEC.read_text(encoding='utf-8')

    def test_spec_exists_and_names_both_classes(self):
        text = self._text()

        assert 'MECHANISABLE' in text
        assert 'NARRATIVE-ONLY' in text

    def test_spec_carries_the_seven_findings_control(self):
        text = self._text()

        # The seven known report-only findings are the non-empty control.
        for anchor in (
            'fourth token total',
            'housekeeping',
            'RUNTIME step order',
            'merged: true',
            'three-way disagreement',
            'split guard',
            'review-bot withdrawal',
        ):
            assert anchor in text, anchor

    def test_false_merge_is_classified_narrative_only(self):
        """The control item the plan flags as 'may not be mechanisable at all'."""
        text = self._text()
        # The false-merge row must NOT force the report into a fact.
        assert 'arrived as operator narrative, not as a step fact' in text

    def test_spec_states_the_empirical_sample_was_not_taken(self):
        text = self._text()

        assert 'The empirical sample was not' in text
