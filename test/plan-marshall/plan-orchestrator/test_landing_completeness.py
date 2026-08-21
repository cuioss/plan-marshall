#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Contract tests for the landing drain-completeness check (plan 302 D5).

The terminal ``kind: landing`` message must carry a machine-readable
``landing-facts`` block (plan 302 D4). ``check_landing_completeness`` is the
drain-side validator that lets the orchestrator turn "the queue is empty" into
"every REQUIRED fact drained": it reports whether a drained landing carried that
block with every required fact key SUPPLIED — non-empty, and not a sanctioned
degraded value for the keys that cannot legitimately be unknown. It does NOT
reach the optional keys (the per-step typed facts, the wall-clock, the repository
end-state), so a ``complete: true`` landing may carry none of them and the check
never establishes that nothing whatsoever is outstanding.

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

import re
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


#: A representative value per required fact key. This is a SAMPLE table, not a
#: second copy of the required-key list: :func:`_facts_block` iterates
#: ``LANDING_REQUIRED_KEYS`` and looks each key up here, so a key added to the
#: constant with no sample fails loudly instead of silently dropping out of every
#: "complete" fixture — which would leave the completeness assertions green while
#: exercising an incomplete block.
_SAMPLE_FACT_VALUES: dict[str, str] = {
    'schema': LANDING_FACTS_SCHEMA,
    'plan_id': 'truthful-signals-302',
    'pr': '#1234',
    'merge_state': 'merged',
    'deliverables_total': '6',
    'deliverables_done': '6',
    'total_tokens': '512000',
    'steps': 'push:done,create-pr:done,archive-plan:done',
}


def _facts_block(**overrides: str) -> str:
    """Build a complete ``landing-facts`` block, with optional key overrides.

    The default key set is ``LANDING_REQUIRED_KEYS`` itself — iterated, not
    transcribed — so a key added to the constant is present in every fixture
    automatically. An override of ``''`` drops a key's value (to exercise the
    missing-key branch) and an override to a non-``None`` value replaces it.
    """
    unmapped = [key for key in LANDING_REQUIRED_KEYS if key not in _SAMPLE_FACT_VALUES]
    assert not unmapped, (
        f'LANDING_REQUIRED_KEYS carries {unmapped}, for which _SAMPLE_FACT_VALUES has no '
        'sample. Add one — omitting it would silently build an INCOMPLETE block and every '
        'assertion that a complete landing passes would be exercising the wrong input.'
    )
    values = {key: _SAMPLE_FACT_VALUES[key] for key in LANDING_REQUIRED_KEYS}
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
# A sanctioned degraded value is MISSING, not a fact
# =============================================================================
#
# ``emit-landing.md`` sanctions writing ``n/a`` for a fact the producer could not
# read. ``n/a`` is a truthy string, so a presence-only check accepts a landing
# whose token total, step list and deliverable counts all failed to read and
# reports ``complete: true`` over it. The expectations below are stated as EXACT
# literal key lists rather than derived from the module's sentinel-rejecting key
# set: deriving them would make both sides move together, so dropping a key from
# that set would leave every assertion green.


class TestDegradedSentinelFacts:
    def test_degraded_counts_tokens_and_steps_are_reported_missing(self):
        """A landing whose mechanisable facts all read ``n/a`` is INCOMPLETE.

        The four keys below can never legitimately be unknown for a landed plan,
        so a sanctioned degraded value for any of them is a gap the drain must
        record — not a fact it may reconcile against.
        """
        landing = _facts_landing(
            deliverables_total='n/a',
            deliverables_done='n/a',
            total_tokens='n/a',
            steps='n/a',
        )

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == [
            'deliverables_total',
            'deliverables_done',
            'total_tokens',
            'steps',
        ]

    def test_degraded_plan_id_is_reported_missing(self):
        """``plan_id`` identifies the landing; a degraded one is not an identity."""
        landing = _facts_landing(plan_id='n/a')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['plan_id']

    def test_degraded_pr_and_merge_state_stay_complete(self):
        """The asymmetry: ``pr`` / ``merge_state`` MAY be ``n/a``.

        "No PR exists" is a real end state the payload spec names, so a degraded
        value there is an answer rather than a gap. Pinning this alongside the
        rejection cases is what keeps the sentinel rule from being widened into a
        blanket ban.
        """
        landing = _facts_landing(pr='n/a', merge_state='n/a')

        complete, missing = check_landing_completeness(landing)

        assert complete is True
        assert missing == []

    def test_sentinel_match_ignores_case_and_surrounding_space(self):
        """A producer's ``N/A`` is the same sanctioned degraded value as ``n/a``."""
        landing = _facts_landing(total_tokens='  N/A  ')

        complete, missing = check_landing_completeness(landing)

        assert complete is False
        assert missing == ['total_tokens']

    def test_a_genuine_zero_count_is_not_a_degraded_value(self):
        """``0`` is a real count, and must not be swept up by the sentinel rule."""
        landing = _facts_landing(deliverables_done='0')

        complete, missing = check_landing_completeness(landing)

        assert complete is True
        assert missing == []


# =============================================================================
# The two DOCUMENTED enumerations agree with the constant
# =============================================================================
#
# ``LANDING_REQUIRED_KEYS`` is restated twice in prose: the payload spec's
# required-key table, and the producer's Step 2 enumeration. Nothing derived
# either from the constant, so a key added to or removed from the constant left
# both documents describing a payload shape the validator no longer enforces —
# and a producer following the stale enumeration emits a landing the drain
# rejects. Both parsers extract the documented set and assert EQUALITY, so a
# divergence in either direction fails.

_EMIT_LANDING_DOC: Path = _PLAN_MARSHALL / 'phase-6-finalize' / 'standards' / 'emit-landing.md'

#: A backticked code span. Used to pull key names out of a prose enumeration.
_CODE_SPAN = re.compile(r'`([^`]+)`')

#: A fact KEY as written in either enumeration: lowercase words and underscores,
#: optionally followed by ``=`` and a sample value (the spec writes the schema
#: marker as ``schema=landing-facts/1``). Anything else a code span may hold — a
#: fence info-string (``landing-facts``), a placeholder (``{step}:{outcome}``), a
#: sentinel (``n/a``) — fails to match and is excluded by construction.
_FACT_KEY = re.compile(r'^([a-z][a-z0-9_]*)(?:=.*)?$')


def _keys_from_code_spans(text: str) -> set[str]:
    """Every fact key named by a backticked code span in ``text``."""
    keys = set()
    for span in _CODE_SPAN.findall(text):
        match = _FACT_KEY.match(span.strip())
        if match:
            keys.add(match.group(1))
    return keys


def _spec_table_keys() -> set[str]:
    """The `Key` column of the payload spec's required-fact-keys table.

    The section is located by its heading and bounded by the next heading, so a
    table added elsewhere in the document is not folded in.
    """
    text = _PAYLOAD_SPEC.read_text(encoding='utf-8')
    section = re.search(
        r'^## Required machine-readable fact keys$(.*?)(?=^## |\Z)',
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert section, (
        f'{_PAYLOAD_SPEC.name} carries no "## Required machine-readable fact keys" '
        'section, so this guard would read an empty table.'
    )
    keys = set()
    for row in re.finditer(r'^\|\s*`([^`]+)`\s*\|', section.group(1), re.MULTILINE):
        keys.add(row.group(1).strip())
    return keys


def _emit_landing_enumeration_keys() -> set[str]:
    """The required keys enumerated in emit-landing.md's Step 2 body part 2.

    The enumeration is truncated at ``Optional keys``, which introduces the keys a
    landing MAY carry: folding those in would make the set a superset of the
    required one and the equality assertion could never hold.
    """
    text = _EMIT_LANDING_DOC.read_text(encoding='utf-8')
    item = re.search(r'^2\. \*\*The required.*$', text, re.MULTILINE)
    assert item, (
        f'{_EMIT_LANDING_DOC.name} carries no Step 2 "The required `landing-facts` fenced '
        'block" enumeration item, so this guard would read nothing.'
    )
    body = item.group(0)
    optional_at = body.find('Optional keys')
    assert optional_at != -1, (
        'The Step 2 enumeration no longer names "Optional keys", so the truncation that '
        'separates required from optional has nothing to cut at and the extracted set '
        'would silently include the optional keys.'
    )
    return _keys_from_code_spans(body[:optional_at])


class TestDocumentedEnumerationsMatchTheConstant:
    def test_the_extractors_are_not_vacuous(self):
        """Both parsers must find something, or the equalities below prove nothing."""
        assert _spec_table_keys(), 'the payload-spec table parser extracted no keys'
        assert _emit_landing_enumeration_keys(), (
            'the emit-landing Step 2 enumeration parser extracted no keys'
        )

    def test_payload_spec_table_names_exactly_the_required_keys(self):
        assert _spec_table_keys() == set(LANDING_REQUIRED_KEYS), (
            'The payload spec\'s "Required machine-readable fact keys" table and '
            '`LANDING_REQUIRED_KEYS` disagree. A key in the table but not the constant is '
            'documented as required and enforced by nothing; a key in the constant but not '
            'the table is enforced by the drain and documented nowhere, so a producer '
            f'following the spec emits a landing the drain rejects. Table: '
            f'{sorted(_spec_table_keys())}; constant: {sorted(LANDING_REQUIRED_KEYS)}.'
        )

    def test_emit_landing_enumeration_names_exactly_the_required_keys(self):
        assert _emit_landing_enumeration_keys() == set(LANDING_REQUIRED_KEYS), (
            "emit-landing.md's Step 2 enumeration and `LANDING_REQUIRED_KEYS` disagree. "
            'The enumeration is what the PRODUCER follows, so a key it omits is one the '
            'emitted landing will not carry and the drain will reject. Enumeration: '
            f'{sorted(_emit_landing_enumeration_keys())}; constant: '
            f'{sorted(LANDING_REQUIRED_KEYS)}.'
        )

    def test_the_two_documents_agree_with_each_other(self):
        """Transitively implied by the two equalities, asserted for a direct message."""
        assert _spec_table_keys() == _emit_landing_enumeration_keys()


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
