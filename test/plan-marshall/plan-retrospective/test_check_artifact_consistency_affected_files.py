# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-artifact-consistency.py``.

Scope: the five affected-files agreement cases (exact, either superset, disjoint,
both empty) and the bullet extraction that feeds them, including what a deliverable
that will not parse does to recall.
"""


from __future__ import annotations

import json

from _check_artifact_consistency_fixtures import (
    SCRIPT_PATH,
    _check_by_name,
    _setup_exact_match_plan,
    _setup_multi_deliverable_plan,
)
from _plan_retrospective_fixtures import (  # noqa: E402
    build_happy_plan_dir,
)

from conftest import run_script  # noqa: E402


class TestAffectedFilesExactMatch:
    """Exercises the strict ``affected_files_exact_match`` top-level key.

    Each test verifies:
    - The key is present at the top level (peer to ``affected_files_recall``'s
      sibling in ``details``, NOT nested inside ``details``).
    - ``status`` matches the expected pass/warn outcome.
    - ``outline_only`` and ``references_only`` reflect the set difference.
    """

    def test_case_a_exact_match_passes(self, tmp_path, monkeypatch):
        """Outline and references declare identical files -> pass, empty lists."""
        files = ['src/foo.py', 'src/bar.py']
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=files,
            references_files=files,
            plan_id='retro-exact-a',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data, (
            'affected_files_exact_match must be a top-level TOON key, peer to affected_files_recall'
        )
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'pass'
        assert exact['outline_only'] == []
        assert exact['references_only'] == []

        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'pass'

    def test_case_b_outline_superset_warns(self, tmp_path, monkeypatch):
        """Outline has files references lacks -> warn, populated outline_only."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py', 'src/bar.py', 'src/baz.py'],
            references_files=['src/foo.py'],
            plan_id='retro-exact-b',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == ['src/bar.py', 'src/baz.py']
        assert exact['references_only'] == []

    def test_case_c_references_superset_warns(self, tmp_path, monkeypatch):
        """References has files outline lacks -> warn, populated references_only."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py'],
            references_files=['src/foo.py', 'src/bar.py', 'src/baz.py'],
            plan_id='retro-exact-c',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == []
        assert exact['references_only'] == ['src/bar.py', 'src/baz.py']

    def test_case_d_disjoint_sets_warn(self, tmp_path, monkeypatch):
        """Outline and references share no files -> warn, both lists populated."""
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=['src/foo.py', 'src/bar.py'],
            references_files=['src/alpha.py', 'src/beta.py'],
            plan_id='retro-exact-d',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['outline_only'] == ['src/bar.py', 'src/foo.py']
        assert exact['references_only'] == ['src/alpha.py', 'src/beta.py']

    def test_case_e_both_empty_is_inconclusive(self, tmp_path, monkeypatch):
        """No outline files and no references files -> inconclusive, never pass.

        Two empty sets are trivially equal whether the plan really touched no
        files or the bullet parser and the footprint resolver both failed, so
        the comparison substantiates no verdict. The check must report
        ``inconclusive`` and emit a warning finding rather than a vacuous
        ``pass``.
        """
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=[],
            references_files=[],
            plan_id='retro-exact-e',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert 'affected_files_exact_match' in data
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'inconclusive'
        assert exact['outline_only'] == []
        assert exact['references_only'] == []

        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'inconclusive'

        # The inconclusive verdict must be visible to the synthesizer.
        assert any(
            f.get('severity') == 'warning' and 'substantiates no verdict' in f.get('message', '')
            for f in data['findings']
        ), f'Expected a warning finding for the inconclusive verdict, got {data["findings"]}'

        # An inconclusive row lands in its own summary bucket — never absorbed
        # as a pass, and never counted nowhere at all.
        summary = data['summary']
        assert int(summary['inconclusive']) >= 1
        assert int(summary['passed']) + int(summary['failed']) + int(summary['skipped']) == sum(
            1 for c in data['checks'] if c['status'] in ('pass', 'fail', 'skip')
        )
        assert not any(c['status'] == 'pass' for c in data['checks'] if c['name'] == 'affected_files_exact_match')


class TestAffectedFilesBulletParsing:
    """Regression coverage for the ``Affected files:`` bullet parser.

    The canonical bullet form real solution outlines emit is
    ``- `path/to/file` (intent)``. The pre-fix regex anchored ``\\s*$``
    immediately after the optional closing backtick, so that form never
    matched and the declared set silently came back empty — which the two
    downstream verdicts then compounded into a false green.
    """

    def test_annotated_canonical_bullets_extract_the_bare_path(self, tmp_path, monkeypatch):
        """``- `path` (intent)`` yields the bare path; the marker does not leak into it.

        The marker itself is READ, not discarded — it drives the recall
        denominator's read-intent filter. This fixture annotates every path
        ``write-replace``, a modification intent, so all three stay in the
        denominator and the filter is not what this test measures; the
        read-intent behaviour is pinned in
        ``test_recall_read_intent_denominator.py``.
        """
        files = ['src/foo.py', 'src/bar.py', 'src/baz.py']
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=files,
            references_files=files,
            plan_id='retro-annotated-bullets',
            outline_annotation='write-replace',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        details = data['details']['affected_files_recall']
        assert int(details['declared']) == len(files), (
            'Annotated canonical bullets must extract; an empty declared set '
            'means the bullet regex regressed to the pre-fix anchor.'
        )
        assert int(details['found']) == len(files)

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] != 'skip'
        assert recall['status'] == 'pass'

        # The intent annotation must not leak into the extracted paths: an
        # exact match against the references set proves each path was stripped.
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'pass'
        assert exact['outline_only'] == []
        assert exact['references_only'] == []

    def test_bare_unannotated_bullets_still_extract(self, tmp_path, monkeypatch):
        """The regex change is additive — the bare ``- path`` form still parses."""
        files = ['src/foo.py', 'src/bar.py']
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'retro-bare-bullets'
        build_happy_plan_dir(plan_dir)
        outline = (
            '# Solution: Bare\n'
            'plan_id: bare\n\n'
            '## Summary\n\nBare fixture.\n\n'
            '## Overview\n\nOverview.\n\n'
            '## Deliverables\n\n'
            '### 1. Deliverable one\n\n'
            '**Affected files:**\n'
            '- src/foo.py\n'
            '- src/bar.py\n'
        )
        (plan_dir / 'solution_outline.md').write_text(outline, encoding='utf-8')
        tasks_dir = plan_dir / 'tasks'
        for leftover in tasks_dir.glob('TASK-*.json'):
            leftover.unlink()
        (tasks_dir / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'deliverable': 1, 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': files, 'domains': []}), encoding='utf-8'
        )
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', 'retro-bare-bullets', '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 2
        assert int(details['found']) == 2

    def test_deliverables_present_but_nothing_parsed_fails_recall(self, tmp_path, monkeypatch):
        """Heading declared + zero extractable bullets -> fail, never skip.

        A deliverable that declares an ``Affected files`` section yet yields no
        parseable bullet cannot substantiate any coverage verdict — the parser
        produced nothing, which is a parse failure the retrospective must
        surface naming the offending deliverable.
        """
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=[],
            references_files=[],
            plan_id='retro-unparsed-bullets',
            outline_empty_heading=True,
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        assert 'no bullet parsed' in recall['message']
        assert 'Deliverable one' in recall['message']
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 0
        assert int(details['deliverables']) >= 1

    def test_no_affected_heading_skips_recall(self, tmp_path, monkeypatch):
        """Sibling of the loud-fail case: heading absent -> skip, not fail.

        A deliverable that never claimed to declare files has nothing to parse,
        so no parse failure is substantiated and the empty aggregate is a
        genuine ``skip`` — pinned through the real argparse path.
        """
        plan_id, _ = _setup_exact_match_plan(
            tmp_path,
            monkeypatch,
            outline_files=[],
            references_files=[],
            plan_id='retro-no-affected-heading',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'skip'
        assert 'no deliverable declares' in recall['message'].lower()

    def test_sibling_declaration_does_not_absorb_unparseable_deliverable(
        self, tmp_path, monkeypatch
    ):
        """Sibling-absorption regression: a well-formed deliverable 1 must not
        mask deliverable 2's unparseable heading.

        Before the per-deliverable read, the checker compared only the flattened
        aggregate declared set: deliverable 1's bullets made it non-empty, so
        deliverable 2's heading-with-no-bullets slipped through into a recall
        computation instead of the parse failure it is.
        """
        declared = ['src/foo.py', 'src/bar.py']
        plan_id, _ = _setup_multi_deliverable_plan(
            tmp_path,
            monkeypatch,
            blocks=[declared, []],
            references_files=declared,
            plan_id='retro-sibling-absorption',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail', (
            'A sibling deliverable declaring files must not absorb deliverable 2 '
            "'s unparseable heading into a non-empty aggregate."
        )
        assert 'Deliverable 2' in recall['message']
        details = data['details']['affected_files_recall']
        assert [str(n) for n in details['unparseable_deliverables']] == ['2']

    def test_sibling_without_heading_does_not_trigger_parse_fail(self, tmp_path, monkeypatch):
        """Complement of the absorption regression: a deliverable carrying NO
        ``Affected files:`` heading is not a parse failure, and recall is
        computed from the declaring deliverable's set alone.
        """
        declared = ['src/foo.py', 'src/bar.py']
        plan_id, _ = _setup_multi_deliverable_plan(
            tmp_path,
            monkeypatch,
            blocks=[declared, None],
            references_files=declared,
            plan_id='retro-sibling-no-heading',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'pass'
        details = data['details']['affected_files_recall']
        assert 'unparseable_deliverables' not in details
        assert int(details['declared']) == len(declared)
        assert int(details['found']) == len(declared)
        assert float(details['recall_pct']) == 100.0
