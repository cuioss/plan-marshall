# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``check-artifact-consistency.py``.

The existing ``test_check_artifact_consistency.py`` drives the script through
the ``run_script`` subprocess harness (which exercises the real argparse path
but does not count for in-process coverage) plus a handful of direct
``_resolve_footprint`` unit calls. This module complements it by calling
``cmd_run`` and the individual ``check_*`` analyzers IN-PROCESS against crafted
``tmp_path`` plan directories, asserting the structural verdicts each branch
produces — including the manifest-aware downgrade branch, the task/recall/
exact-match edge cases, and the ``resolve_plan_dir`` error paths that the
subprocess suite never reaches in-process.
"""


from __future__ import annotations

import json

import pytest
from _check_artifact_consistency_behavior_fixtures import _ONE_DELIVERABLE, _cac, _outline


class TestResolvePlanDir:
    """``resolve_plan_dir`` validates its mode/argument combinations."""

    def test_live_without_plan_id_raises(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _cac.resolve_plan_dir('live', None, None)

    def test_archived_without_path_raises(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _cac.resolve_plan_dir('archived', None, None)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _cac.resolve_plan_dir('frobnicate', 'p', None)

    def test_archived_returns_supplied_path(self, tmp_path):
        result = _cac.resolve_plan_dir('archived', None, str(tmp_path))
        assert result == tmp_path


class TestLoadReferences:
    """``_load_references`` is defensive: any read/parse error degrades to {}."""

    def test_missing_file_returns_empty(self, tmp_path):
        assert _cac._load_references(tmp_path) == {}

    def test_malformed_json_returns_empty(self, tmp_path):
        (tmp_path / 'references.json').write_text('{ not json', encoding='utf-8')
        assert _cac._load_references(tmp_path) == {}

    def test_non_dict_top_level_returns_empty(self, tmp_path):
        (tmp_path / 'references.json').write_text('[1, 2, 3]', encoding='utf-8')
        assert _cac._load_references(tmp_path) == {}

    def test_valid_dict_returned(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['a.py']}), encoding='utf-8'
        )
        assert _cac._load_references(tmp_path) == {'modified_files': ['a.py']}


class TestSectionAndDeliverableChecks:
    def test_sections_pass_when_all_present(self):
        status, message = _cac.check_solution_outline_sections(_outline())
        assert status == 'pass'
        assert 'present' in message.lower()

    def test_sections_fail_lists_missing(self):
        content = '# Solution\n\n## Summary\n\nonly summary\n'
        status, message = _cac.check_solution_outline_sections(content)
        assert status == 'fail'
        assert 'overview' in message
        assert 'deliverables' in message

    def test_deliverable_count_fails_without_section(self):
        content = '# Solution\n\n## Summary\n\nno deliverables here\n'
        status, message, deliverables = _cac.check_deliverable_count(content)
        assert status == 'fail'
        assert deliverables == []

    def test_deliverable_count_fails_with_empty_section(self):
        content = '# Solution\n\n## Deliverables\n\nprose but no headings\n'
        status, _message, deliverables = _cac.check_deliverable_count(content)
        assert status == 'fail'
        assert deliverables == []

    def test_deliverable_count_passes_and_counts(self):
        status, message, deliverables = _cac.check_deliverable_count(_outline(deliverables=2))
        assert status == 'pass'
        assert len(deliverables) == 2
        assert '2 deliverables' in message


class TestExtractAffectedFiles:
    def test_collects_bullets_under_affected_block(self):
        files = _cac.extract_affected_files_per_deliverable(
            _outline(affected=['src/a.py', 'src/b.py'])
        )
        assert files == ['src/a.py', 'src/b.py']

    def test_collects_annotated_canonical_bullets_with_intent_stripped(self):
        """The canonical ``- `path` (intent)`` form extracts the bare path.

        The un-annotated case above is exactly why the pre-fix regex defect
        survived: its ``\\s*$`` anchor sat immediately after the closing
        backtick, so only un-annotated bullets ever matched.
        """
        files = _cac.extract_affected_files_per_deliverable(
            _outline(affected=['src/a.py', 'src/b.py'], annotation='write-replace')
        )
        assert files == ['src/a.py', 'src/b.py']

    def test_collects_bare_unbackticked_bullets(self):
        """The bare ``- path`` form remains supported — the fix is additive."""
        content = (
            '# Solution\n\n## Summary\n\ns\n\n## Overview\n\no\n\n## Deliverables\n\n'
            '### 1. One\n\n**Affected files:**\n- src/a.py\n- src/b.py\n'
        )
        assert _cac.extract_affected_files_per_deliverable(content) == ['src/a.py', 'src/b.py']

    def test_no_affected_block_yields_empty(self):
        assert _cac.extract_affected_files_per_deliverable(_outline()) == []


class TestAffectedFilesRecall:
    """The declaration state is read per deliverable, so an empty declared set
    is discriminated by whether any deliverable actually carried the
    ``Affected files:`` heading: a heading that parsed to zero bullets is a
    ``fail`` naming that deliverable, while no deliverable declaring a section
    at all is a substantiated ``skip``.
    """

    def test_skip_when_outline_declares_no_deliverables(self, tmp_path):
        """Genuine no-deliverables outline → skip; nothing could be declared."""
        status, message, details = _cac.check_affected_files_recall(
            _outline(deliverables=0), tmp_path, []
        )
        assert status == 'skip'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 0
        assert 'no deliverable declares' in message.lower()

    def test_fail_when_deliverables_present_but_nothing_parsed(self, tmp_path):
        """Heading present but zero bullets extracted → fail, not skip.

        This is the vacuous-skip defect: the deliverable declared an
        ``Affected files`` section yet the bullet parser produced nothing, so
        no coverage verdict is substantiated and the check must say so, naming
        the offending deliverable.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(empty_affected_heading=True), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 1
        assert '1. Deliverable 1' in message
        assert details['unparseable_deliverables'] == [1]

    def test_skip_when_single_deliverable_declares_no_affected_section(self, tmp_path):
        """Heading absent on the only deliverable → skip, not a parse fail.

        Sibling of the loud-fail case above: a deliverable that never claimed
        to declare files has nothing to parse, so no parse failure is
        substantiated and the aggregate empty set is a genuine ``skip``.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'skip'
        assert int(details['declared']) == 0
        assert int(details['deliverables']) == 1
        assert 'unparseable_deliverables' not in details
        assert 'no deliverable declares' in message.lower()

    def test_pass_when_footprint_covers_declared(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'pass'
        assert int(details['found']) == 2
        assert float(details['recall_pct']) == 100.0

    def test_pass_when_annotated_bullets_cover_declared(self, tmp_path):
        """The canonical annotated bullet form yields the same recall verdict."""
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py', 'src/b.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py'], annotation='write-replace'),
            tmp_path,
            _ONE_DELIVERABLE,
        )
        assert status == 'pass'
        assert int(details['declared']) == 2
        assert int(details['found']) == 2

    def test_fail_when_recall_below_threshold(self, tmp_path):
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': ['src/a.py']}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py', 'src/b.py', 'src/c.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert int(details['found']) == 1
        assert sorted(details['missing']) == ['src/b.py', 'src/c.py']

    def test_fail_when_references_unreadable(self, tmp_path):
        (tmp_path / 'references.json').write_text('{ broken', encoding='utf-8')
        status, message, _details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert 'unreadable' in message.lower()

    def test_inconclusive_when_footprint_unresolvable(self, tmp_path):
        """No footprint could be resolved → inconclusive, and NO percentage.

        A recall figure computed from an unresolved footprint is a confident
        claim about an input that was never measured; ``0%`` is the shape that
        defect takes.
        """
        status, message, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'inconclusive'
        assert 'unmeasurable' in message
        assert details['footprint_resolved'] is False
        assert 'recall_pct' not in details

    def test_measured_verdict_when_footprint_resolved_to_empty(self, tmp_path):
        """Control: a present-but-empty ``modified_files`` still measures 0%.

        Without this the inconclusive sentinel could be satisfied by treating
        every empty footprint as unmeasurable, which would silence a genuine
        zero-coverage failure.
        """
        (tmp_path / 'references.json').write_text(
            json.dumps({'modified_files': []}), encoding='utf-8'
        )
        status, _msg, details = _cac.check_affected_files_recall(
            _outline(affected=['src/a.py']), tmp_path, _ONE_DELIVERABLE
        )
        assert status == 'fail'
        assert details['footprint_resolved'] is True
        assert float(details['recall_pct']) == 0.0
