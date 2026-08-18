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


class TestIntentCaptureNeverBreaksParsing:
    """Reading an intent must not narrow what a path is allowed to contain.

    This regex decides whether a bullet parses AT ALL, and a bullet that stops
    matching is reported as "Declaration heading present but no bullet
    parsed" — a ``fail`` at ``severity: error``. So a bullet that parsed before
    intents were read must still parse, with the same path, and yield no intent.
    An intermediate fix excluded ``(`` from the bare path class, which silently
    turned each of these into a hard error.
    """

    def test_parenthetical_that_is_not_an_intent_stays_in_the_path(self):
        outline = _outline([('src/a.py (New file)', None)], backticked=False)
        assert _cac.extract_affected_files_per_deliverable(outline) == ['src/a.py (New file)']
        assert _cac.extract_modification_intent_files(outline) == ['src/a.py (New file)']

    def test_parenthesis_inside_a_bare_path_is_preserved(self):
        outline = _outline([('src/mod(1).py', None)], backticked=False)
        assert _cac.extract_affected_files_per_deliverable(outline) == ['src/mod(1).py']

    def test_trailing_prose_after_a_bare_annotation_does_not_break_the_match(self):
        """Not an annotation — the marker must end the body to be read as one."""
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n- src/a.py (read) - trailing prose\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == [
            'src/a.py (read) - trailing prose'
        ]
        # No intent was read, so it is NOT filtered out as a read declaration.
        assert _cac.extract_modification_intent_files(content) == [
            'src/a.py (read) - trailing prose'
        ]

    def test_uppercase_parenthetical_after_a_backticked_path_yields_no_intent(self):
        outline = _outline([('src/a.py', 'New file')])
        assert _cac.extract_affected_files_per_deliverable(outline) == ['src/a.py']
        assert _cac.extract_modification_intent_files(outline) == ['src/a.py']

    def test_a_bullet_that_is_entirely_a_parenthetical_still_parses(self):
        """``- (none)`` must not reduce to an empty path and vanish.

        An entry whose path reduces to '' is dropped by the caller, which is
        observationally identical to the bullet never matching — the same hard
        `fail` at severity error, reached by a different route.
        """
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n- (none)\n- (read)\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == ['(none)', '(read)']

    def test_only_a_declared_intent_token_is_treated_as_a_marker(self):
        """A lowercase parenthetical that is not in the vocabulary is part of the path.

        Accepting any ``[a-z-]+`` token silently truncated ordinary paths, which
        changes which declared path is compared against the footprint.
        """
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n'
            '- reports/summary(final)\n- doc/notes (draft)\n- src/a.py (delete)\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == [
            'reports/summary(final)',
            'doc/notes (draft)',
            'src/a.py',
        ]

    def test_backticked_path_keeps_trailing_prose_tolerance(self):
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n- `src/a.py` (read) — see note\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == ['src/a.py']
        assert _cac.extract_modification_intent_files(content) == []


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
        assert 'No deliverable declares a file surface' in message
        # The message names all three headings, so a reader can tell this skip
        # from the every-declaration-is-read-intent one without knowing which
        # declaration form the outline used.
        assert 'Files expected to mutate' in message


class TestReadIntentExcludedIsPublishedOnEveryBranch:
    """The docs state this key lets a reader tell a small denominator from a
    filtered one. That is only true if every branch publishes it — an absent key
    reads as "nothing was filtered", which is the same absent-vs-zero collapse
    this plan exists to remove.
    """

    def test_published_on_the_unresolvable_footprint_branch(self, tmp_path):
        """The branch this plan is centrally about."""
        outline = _outline([('src/w.py', 'write-new'), ('src/r.py', 'read')])
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}), encoding='utf-8')

        status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'inconclusive'
        assert details['read_intent_excluded'] == 1

    def test_published_on_the_unparseable_fail_branch(self, tmp_path):
        """That verdict reads the UNFILTERED bullets, published under its own name.

        ``declared`` keeps one meaning on every branch so the reconstruction
        identity holds; the unfiltered population it actually consulted is
        reported as ``declared_unfiltered`` rather than by overloading it.
        """
        outline = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n\n### 2. Two\n\n'
            '**Affected files:**\n- `src/r.py` (read)\n'
        )
        plan_dir = _plan_dir(tmp_path, ['src/w.py'])

        status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'fail'
        assert details['declared'] == 0
        assert details['declared_unfiltered'] == 1
        assert details['read_intent_excluded'] == 1

    def test_published_on_the_unreadable_references_fail_branch(self, tmp_path):
        """The branch round 1 added the key to but never asserted."""
        outline = _outline([('src/w.py', 'write-new'), ('src/r.py', 'read')])
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text('{not json', encoding='utf-8')

        status, message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'fail'
        assert 'references.json unreadable' in message
        assert details['read_intent_excluded'] == 1

    def test_published_on_the_no_declaration_skip_branch(self, tmp_path):
        outline = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n'
            '## Deliverables\n\n### 1. One\n\nNo files.\n'
        )
        plan_dir = _plan_dir(tmp_path, ['src/a.py'])

        status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert status == 'skip'
        assert details['read_intent_excluded'] == 0

    def test_the_reconstruction_identity_recovers_distinct_declared_paths(self, tmp_path):
        """``declared + read_intent_excluded`` recovers the DISTINCT declared paths.

        The identity is what makes the key useful; a branch where ``declared``
        silently means something else double-counts. Both operands are set
        cardinalities, so the reconstructed total counts distinct paths and NOT
        bullets — this fixture declares one path twice to pin that difference,
        which a fixture of all-unique paths cannot express.
        """
        outline = _outline(
            [
                ('src/w.py', 'write-new'),
                ('src/w.py', 'write-new'),
                ('src/r.py', 'read'),
            ]
        )
        plan_dir = _plan_dir(tmp_path, ['src/w.py'])

        _status, _message, details = _cac.check_affected_files_recall(
            outline, plan_dir, _ONE_DELIVERABLE
        )

        assert len(_cac.extract_affected_files_per_deliverable(outline)) == 3, 'three bullets'
        assert details['declared'] + details['read_intent_excluded'] == 2, (
            'two DISTINCT declared paths, not three bullets'
        )


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
