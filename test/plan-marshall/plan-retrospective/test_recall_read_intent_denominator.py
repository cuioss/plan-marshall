# SPDX-License-Identifier: FSL-1.1-ALv2
"""The recall denominator counts declared MODIFICATIONS, not declared reads.

``Affected files:`` bullets carry a declared intent (``read``, ``write-new``,
``write-replace``, ``delete``). The footprint both comparisons grade against is a
diff, so a ``(read)``-intent declaration can never appear in it. Counting one as
an expected modification caps achievable recall below the pass threshold **by
construction** — a plan that declares the files it intends to read is penalised
for not modifying them, and no execution of such a plan can pass.

These tests pin the denominator (and the exact-match check that shares it) to the
modification-intent subset, in both directions: read-intent declarations are
excluded, and everything else — including an unannotated declaration, which
states no intent and must not be assumed read-only — still counts.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import load_script_module

_cac = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-artifact-consistency.py', 'cac_read_intent_mod'
)

#: The check passes at or above this recall. Restated from the module under test
#: so a threshold change surfaces here as a failure rather than silently
#: re-tuning what these fixtures prove.
_THRESHOLD = 0.70

_ONE_DELIVERABLE = [{'number': '1', 'title': 'Deliverable 1'}]


def _outline(entries: list[tuple[str, str | None]], *, backticked: bool = True) -> str:
    """Build a one-deliverable outline whose bullets carry per-file intents.

    ``entries`` is ``(path, intent)``; an intent of ``None`` emits the
    unannotated bullet form. ``backticked`` selects the canonical
    ``- `path` (intent)`` form or the bare ``- path (intent)`` form.
    """
    bullets = []
    for path, intent in entries:
        rendered = f'`{path}`' if backticked else path
        suffix = f' ({intent})' if intent else ''
        bullets.append(f'- {rendered}{suffix}')
    return (
        '# Solution: Intent\n\n'
        '## Summary\n\nFixture.\n\n'
        '## Overview\n\nOverview.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliverable 1\n\n'
        '**Affected files:**\n' + '\n'.join(bullets) + '\n'
    )


def _plan_dir(tmp_path: Path, footprint: list[str]) -> Path:
    """Seed a plan dir whose footprint resolves from the tier-2 capture.

    Using ``realized_footprint`` keeps the fixture deterministic: the resolver
    answers from the file, so no worktree or git history is involved.
    """
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    (plan_dir / 'references.json').write_text(
        json.dumps({'realized_footprint': footprint}), encoding='utf-8'
    )
    return plan_dir


class TestReadIntentExcludedFromDenominator:
    def test_read_heavy_plan_can_reach_passing_recall(self, tmp_path):
        """The fixture that could not previously pass.

        Two modification-intent files, both realized, alongside three read-intent
        declarations. Counting all five caps recall at 40% — below the 70%
        threshold — so the plan fails no matter how perfectly it executed.
        Counting the two it intended to modify yields 100%.
        """
        outline = _outline(
            [
                ('src/written_a.py', 'write-replace'),
                ('src/written_b.py', 'write-new'),
                ('src/read_a.py', 'read'),
                ('src/read_b.py', 'read'),
                ('src/read_c.py', 'read'),
            ]
        )
        plan_dir = _plan_dir(tmp_path, ['src/written_a.py', 'src/written_b.py'])

        status, message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'pass', message
        assert details['declared'] == 2
        assert details['found'] == 2
        assert details['recall_pct'] == 100.0
        assert details['read_intent_excluded'] == 3

    def test_every_modification_intent_still_counts(self, tmp_path):
        """``write-new``/``write-replace``/``delete`` all remain in the denominator.

        The filter excludes exactly one intent. A filter that dropped any other
        would shrink the denominator and manufacture a vacuously high recall.
        """
        outline = _outline(
            [
                ('src/new.py', 'write-new'),
                ('src/replaced.py', 'write-replace'),
                ('src/gone.py', 'delete'),
            ]
        )
        plan_dir = _plan_dir(tmp_path, ['src/new.py'])

        status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert details['declared'] == 3
        assert details['found'] == 1
        assert details['read_intent_excluded'] == 0
        assert status == 'fail', 'One of three realized is a measured 33%, below threshold'

    def test_unannotated_declaration_is_not_assumed_read_only(self, tmp_path):
        """A bullet with no ``(intent)`` states no intent — it still counts.

        Treating an unannotated declaration as read-only would silently shrink
        the denominator, producing the opposite error: a confident high recall
        derived from a population the plan never narrowed.
        """
        outline = _outline([('src/a.py', None), ('src/b.py', None)])
        plan_dir = _plan_dir(tmp_path, ['src/a.py'])

        _status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert details['declared'] == 2
        assert details['read_intent_excluded'] == 0

    def test_bare_unbackticked_bullet_carries_its_intent(self, tmp_path):
        """The bare ``- path (read)`` form is filtered too, not only the canonical one."""
        outline = _outline(
            [('src/written.py', 'write-replace'), ('src/read_only.py', 'read')],
            backticked=False,
        )
        plan_dir = _plan_dir(tmp_path, ['src/written.py'])

        status, message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert details['declared'] == 1
        assert details['read_intent_excluded'] == 1
        assert status == 'pass', message

    def test_extractors_split_unfiltered_from_modification_intent(self):
        """The two projections are distinct, and only one is intent-filtered."""
        outline = _outline([('src/w.py', 'write-new'), ('src/r.py', 'read')])

        assert _cac.extract_affected_files_per_deliverable(outline) == ['src/w.py', 'src/r.py']
        assert _cac.extract_modification_intent_files(outline) == ['src/w.py']


class TestAllReadIntentIsSkippedNotFailed:
    def test_all_read_intent_yields_skip_with_its_own_reason(self, tmp_path):
        """No expected modification is not a 0% recall — it is nothing to compare.

        This is distinct from the no-declaration skip: the plan DID declare its
        surface. Grading it would divide by a denominator the plan never claimed.
        """
        outline = _outline([('src/r1.py', 'read'), ('src/r2.py', 'read')])
        plan_dir = _plan_dir(tmp_path, ['src/other.py'])

        status, message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'skip'
        assert 'read intent' in message
        assert details['read_intent_excluded'] == 2

    def test_read_only_deliverable_is_not_a_parse_failure(self, tmp_path):
        """The declaration-parseability check reads UNFILTERED bullets.

        A deliverable declaring only read-intent files has still declared files.
        Reporting it as "heading present but no bullet parsed" would be a false
        finding introduced by the intent filter.
        """
        outline = _outline([('src/r1.py', 'read')])
        plan_dir = _plan_dir(tmp_path, [])

        status, message, _details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'skip'
        assert 'no bullet parsed' not in message

    def test_no_declaration_keeps_its_distinct_skip_reason(self, tmp_path):
        """The two skip branches stay distinguishable by message."""
        outline = (
            '# Solution: None\n\n## Summary\n\ns\n\n## Overview\n\no\n\n'
            '## Deliverables\n\n### 1. Deliverable 1\n\nNo files here.\n'
        )
        plan_dir = _plan_dir(tmp_path, ['src/a.py'])

        status, message, _details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'skip'
        assert 'No deliverable declares an Affected files section' in message


class TestExactMatchSharesTheFilteredDenominator:
    def test_read_intent_declaration_is_not_reported_as_drift(self, tmp_path):
        """The peer consumer of the same declaration set filters identically.

        An unfiltered declaration would surface every read-intent path as
        ``outline_only`` — a confident "Set mismatch" derived from paths nothing
        was ever going to modify.
        """
        outline = _outline([('src/w.py', 'write-replace'), ('src/r.py', 'read')])

        outline_files = set(_cac.extract_modification_intent_files(outline))
        status, _message, outline_only, references_only = _cac.check_affected_files_exact_match(
            outline_files, {'src/w.py'}
        )

        assert status == 'pass'
        assert outline_only == []
        assert references_only == []
