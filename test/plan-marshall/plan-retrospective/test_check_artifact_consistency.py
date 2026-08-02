# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-artifact-consistency.py``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import (  # noqa: E402
    build_happy_plan_dir,
    setup_archived_plan,
    setup_broken_plan,
    setup_live_plan,
)

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-artifact-consistency.py'
)


def _check_by_name(checks: list, name: str) -> dict | None:
    for c in checks:
        if c.get('name') == name:
            return c
    return None


class TestHappyPath:
    def test_all_required_checks_pass(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == 'artifact_consistency'

        checks = data['checks']
        assert _check_by_name(checks, 'solution_outline_sections')['status'] == 'pass'
        assert _check_by_name(checks, 'deliverable_count')['status'] == 'pass'
        assert _check_by_name(checks, 'task_deliverable_match')['status'] == 'pass'
        assert _check_by_name(checks, 'metrics_generated')['status'] == 'pass'

    def test_affected_files_recall_calculated(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        details = data['details']
        recall = details['affected_files_recall']
        assert int(recall['declared']) == 3
        assert int(recall['found']) == 3


class TestFaultInjection:
    def test_missing_deliverables_fail_and_missing_metrics_is_inconclusive(
        self, tmp_path, monkeypatch
    ):
        """Structural faults still ``fail``; the absent ``metrics.md`` does not.

        ``metrics.md`` is produced by ``default:record-metrics``, which the LIVE
        marketplace tree orders AFTER ``plan-marshall:plan-retrospective`` — so on
        this real ordering the artifact has not been produced yet and its absence
        substantiates no causal claim. The verdict is ``inconclusive``, and it
        reaches ``findings`` at ``severity: warning`` rather than being dropped by
        a ``fail``-only gate.
        """
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        checks = data['checks']
        sections_check = _check_by_name(checks, 'solution_outline_sections')
        assert sections_check['status'] == 'fail'

        metrics_check = _check_by_name(checks, 'metrics_generated')
        assert metrics_check['status'] == 'inconclusive', (
            'An absent metrics.md read BEFORE its producer has had its turn is '
            'unmeasurable, not a failure — a fail here re-asserts that '
            'record-metrics "did not run" about a step ordered later.'
        )
        assert 'ordered after' in metrics_check['message']

        summary = data['summary']
        assert int(summary['failed']) >= 2
        findings = data['findings']
        assert any(
            f.get('severity') == 'warning' and 'ordered after' in f.get('message', '')
            for f in findings
        ), f'The inconclusive metrics verdict must reach findings, got {findings}'

    def test_missing_solution_outline_emits_error(self, tmp_path, monkeypatch):
        plan_id = 'no-outline'
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / plan_id
        plan_dir.mkdir(parents=True)
        (plan_dir / 'tasks').mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        checks = data['checks']
        present = _check_by_name(checks, 'solution_outline_present')
        assert present is not None
        assert present['status'] == 'fail'

    def test_malformed_references_json_fails_recall(self, tmp_path, monkeypatch):
        """A corrupt references.json must fail affected-files recall gracefully."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        (plan_dir / 'references.json').write_text('{ not valid', encoding='utf-8')

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        assert 'unreadable' in recall['message'].lower()

    def test_partial_recall_below_threshold_fails(self, tmp_path, monkeypatch):
        """When references.json covers <70% of declared files, recall fails."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        # Fixture declares 3 files in outline (foo, bar, baz). Drop two of
        # them so recall = 1/3 ≈ 33%, which is below the 70% threshold.
        # Production-shape: ``check-artifact-consistency.py`` consults
        # ``modified_files``, so the partial-recall fixture must use the same
        # key — using ``affected_files`` would yield a 0% recall instead of
        # the 33% the test description claims.
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 1


class TestGateVerbReadFailClosed:
    """The artifact-consistency gate verb must fail closed on an I/O-boundary
    read failure: a ``solution_outline.md`` that passes ``.exists()`` but raises
    ``OSError`` on ``read_text()`` (permission denied, the path resolves to a
    directory, a mid-read deletion race) must surface a structured
    ``solution_outline_present`` FAIL verdict and a corresponding error finding —
    never an uncaught exception that crashes the consistency gate.

    OSError is injected portably by replacing ``solution_outline.md`` with a
    directory of the same name: ``Path.exists()`` returns ``True`` for a
    directory while ``Path.read_text()`` raises ``IsADirectoryError`` (an
    ``OSError`` subclass). This needs no permission bits and behaves identically
    for root and non-root test runners.
    """

    def test_unreadable_solution_outline_fails_closed(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        # Replace the regular file with a directory of the same name so the
        # production read_text() raises IsADirectoryError (an OSError) while
        # .exists() still passes.
        outline_path = plan_dir / 'solution_outline.md'
        outline_path.unlink()
        outline_path.mkdir()

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        # Fail closed: the gate returns a structured success-status TOON with a
        # FAIL check, NOT a crash. The script process must still exit cleanly.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'

        present = _check_by_name(data['checks'], 'solution_outline_present')
        assert present is not None
        assert present['status'] == 'fail'
        assert 'read_failed' in present['message']

        # The fail-closed read failure must also surface as an error finding so
        # the retrospective synthesizer flags the corrupt plan state.
        findings = data['findings']
        assert any('read_failed' in f.get('message', '') for f in findings), (
            f'Expected a read_failed finding, got {findings}'
        )

    def test_read_failure_does_not_emit_uncaught_exception(self, tmp_path, monkeypatch):
        """Regression sentinel: the OSError must be caught, not propagated.

        Before the fail-closed wrap, an unreadable ``solution_outline.md`` raised
        an uncaught ``OSError`` that ``safe_main`` would render as an
        ``internal_error`` TOON with a non-zero exit. This test pins the new
        behavior: clean exit, ``status: success``, no ``internal_error`` code.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        outline_path = plan_dir / 'solution_outline.md'
        outline_path.unlink()
        outline_path.mkdir()

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data.get('error') != 'internal_error'


class TestArchivedMode:
    def test_archived_plan_checks_pass(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert _check_by_name(data['checks'], 'deliverable_count')['status'] == 'pass'


class TestRegression:
    """Regression tests locking in the production-shape recall calculation.

    Before the fix, ``check_affected_files_recall`` consulted the legacy
    ``affected_files`` key in ``references.json`` and returned 0% recall
    against a production plan whose references were populated via
    ``modified_files``. These tests pin the computed ``recall_pct`` to the
    exact expected value so a regression to the old key name or a silent
    failure-path return is caught immediately.
    """

    def test_recall_pct_is_100_when_modified_files_matches_declared(self, tmp_path, monkeypatch):
        """Production-shape happy path: declared == modified_files → 100%.

        The happy-path fixture declares ``src/foo.py``, ``src/bar.py``,
        ``src/baz.py`` in the outline and populates the same three in
        ``references.json['modified_files']``. This test pins
        ``recall_pct`` to ``100.0`` so a regression to the old ``affected_files``
        lookup (which would yield ``0.0``) is caught.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 3
        # recall_pct serializes as a float; parse_toon may return int or str
        # depending on payload shape, so coerce before comparing.
        assert float(details['recall_pct']) == 100.0, (
            f'Expected recall_pct == 100.0 when modified_files matches '
            f'declared, got {details["recall_pct"]}. This regression means '
            f'check-artifact-consistency is reading the wrong key again.'
        )

    def test_recall_fails_when_modified_files_empty(self, tmp_path, monkeypatch):
        """Failure-path sibling: declared present, modified_files empty → 0%.

        Complements the happy-path pin above: ensures the check still
        fails correctly (not a false-positive pass) when the references
        file is missing the ``modified_files`` entries entirely.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': [], 'domains': []}),
            encoding='utf-8',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert int(details['declared']) == 3
        assert int(details['found']) == 0
        assert float(details['recall_pct']) == 0.0


def _outline_with_deliverable_blocks(blocks: list[list[str] | None]) -> str:
    """Build a multi-deliverable outline mixing per-deliverable declaration states.

    Each entry of ``blocks`` selects the declaration state of the deliverable at
    that position (1-based in the emitted document):

    - a non-empty list — the ``**Affected files:**`` heading followed by one
      backticked bullet per path (a well-formed declaration);
    - an empty list — the heading with NO bullets beneath it (the
      heading-present-but-unparseable, loud-fail shape);
    - ``None`` — no ``**Affected files:**`` heading at all.
    """
    parts = [
        '# Solution: Mixed',
        'plan_id: mixed',
        '',
        '## Summary',
        '',
        'Mixed-declaration fixture.',
        '',
        '## Overview',
        '',
        'Overview.',
        '',
        '## Deliverables',
        '',
    ]
    for index, declared in enumerate(blocks, start=1):
        parts.append(f'### {index}. Deliverable {index}')
        parts.append('')
        if declared is None:
            continue
        parts.append('**Affected files:**')
        parts.extend(f'- `{path}`' for path in declared)
        parts.append('')
    return '\n'.join(parts) + '\n'


def _outline_with_affected_files(
    files: list[str], *, annotation: str | None = None, empty_heading: bool = False
) -> str:
    """Build a solution_outline.md string that declares ``files`` as a single
    deliverable's Affected files bullets. When ``files`` is empty the outline
    still contains a valid Deliverables section but no Affected files block —
    unless ``empty_heading`` is set, which emits the heading with no bullets
    beneath it (the heading-present-but-unparseable, loud-fail shape).

    ``annotation`` selects the bullet form. ``None`` emits the plain backticked
    form ``- `path```; a string emits the canonical annotated form
    ``- `path` (annotation)`` that real solution outlines use.
    """
    suffix = f' ({annotation})' if annotation else ''
    bullets = ''.join(f'- `{p}`{suffix}\n' for p in files)
    if files:
        affected_block = '\n**Affected files:**\n' + bullets
    elif empty_heading:
        affected_block = '\n**Affected files:**\n'
    else:
        affected_block = ''
    return (
        '# Solution: ExactMatch\n'
        'plan_id: exact-match\n\n'
        '## Summary\n\n'
        'Exact-match fixture.\n\n'
        '## Overview\n\n'
        'Overview.\n\n'
        '## Deliverables\n\n'
        '### 1. Deliverable one\n'
        f'{affected_block}'
    )


def _setup_exact_match_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    outline_files: list[str],
    references_files: list[str],
    plan_id: str = 'retro-exact-match',
    outline_annotation: str | None = None,
    outline_empty_heading: bool = False,
) -> tuple[str, Path]:
    """Create a live plan whose outline and references.json are seeded with
    caller-supplied file lists. Reuses ``build_happy_plan_dir`` to keep the
    surrounding structural checks (metrics, tasks, status) green, then
    overwrites the two files the exact-match check consults.

    The ``references.json`` is populated under the ``modified_files`` key
    because the production peer (``check_affected_files_recall``) now
    reads that key; the exact-match port in this branch was realigned to
    use the same key after the base-branch change to recall.
    """
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)

    # Overwrite outline with a variant whose deliverable count matches the
    # default tasks fixture (a single deliverable) so task_deliverable_match
    # does not go red and drown out the check under test.
    (plan_dir / 'solution_outline.md').write_text(
        _outline_with_affected_files(
            outline_files,
            annotation=outline_annotation,
            empty_heading=outline_empty_heading,
        ),
        encoding='utf-8',
    )
    # Trim tasks to a single deliverable to match the outline above.
    tasks_dir = plan_dir / 'tasks'
    for leftover in tasks_dir.glob('TASK-*.json'):
        leftover.unlink()
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'deliverable': 1, 'status': 'done'}),
        encoding='utf-8',
    )

    # Overwrite references.json with the caller's list, keyed on the
    # production-shape ``modified_files`` field (see peer recall check).
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': references_files, 'domains': []}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


def _setup_multi_deliverable_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    blocks: list[list[str] | None],
    references_files: list[str],
    plan_id: str,
) -> tuple[str, Path]:
    """Create a live plan whose outline mixes per-deliverable declaration states.

    ``blocks`` is forwarded to :func:`_outline_with_deliverable_blocks`. The
    fixture writes one ``TASK-*.json`` per deliverable so
    ``task_deliverable_match`` stays green and cannot drown out the recall check
    under test — the multi-deliverable counterpart of what
    :func:`_setup_exact_match_plan` does for the single-deliverable case.
    """
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)

    (plan_dir / 'solution_outline.md').write_text(
        _outline_with_deliverable_blocks(blocks), encoding='utf-8'
    )

    tasks_dir = plan_dir / 'tasks'
    for leftover in tasks_dir.glob('TASK-*.json'):
        leftover.unlink()
    for index in range(1, len(blocks) + 1):
        (tasks_dir / f'TASK-{index:03d}.json').write_text(
            json.dumps({'number': index, 'deliverable': index, 'status': 'done'}),
            encoding='utf-8',
        )

    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': references_files, 'domains': []}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


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

    def test_annotated_canonical_bullets_extract_with_intent_stripped(self, tmp_path, monkeypatch):
        """``- `path` (intent)`` yields the bare path, annotation discarded."""
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


def _setup_archived_plan_with_references(tmp_path: Path, references: dict, *, name: str) -> Path:
    """Archived plan built from the happy fixture with ``references`` substituted.

    Archived mode passes ``plan_id=None``, so tier 1 is skipped exactly as it is
    for a real archived plan whose worktree finalize has already removed — which
    makes ``references`` the sole lever over the footprint's resolution state.
    """
    plan_dir = tmp_path / name
    build_happy_plan_dir(plan_dir)
    (plan_dir / 'references.json').write_text(json.dumps(references), encoding='utf-8')
    return plan_dir


def _run_archived(plan_dir: Path):
    return run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(plan_dir), '--mode', 'archived')


class TestUnresolvableFootprintIsUnmeasurable:
    """An unresolvable footprint yields ``inconclusive`` from BOTH peers.

    The pair ``affected_files_recall`` / ``affected_files_exact_match`` consumes
    one resolver, so hardening one alone leaves the other reporting confidently
    from the same unmeasured input. Each peer is asserted separately, and the
    resolved-but-empty control below proves the sentinel is not satisfied by
    making every footprint unmeasurable.
    """

    def test_recall_reports_inconclusive_not_zero_percent(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-recall'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'inconclusive'
        assert 'could not be resolved' in recall['message']

        details = data['details']['affected_files_recall']
        assert details['footprint_resolved'] is False
        assert 'recall_pct' not in details, (
            'An unresolved footprint must yield NO percentage — a reported 0% is '
            'the confident-zero defect this check exists to remove.'
        )

    def test_exact_match_peer_reports_inconclusive_not_set_mismatch(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-exact'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        exact = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'inconclusive', (
            'The exact-match peer consumes the same resolver; a confident '
            '"Set mismatch" here would leave the pair half-hardened.'
        )
        assert data['affected_files_exact_match']['status'] == 'inconclusive'
        assert data['affected_files_exact_match']['outline_only'] == []
        assert data['affected_files_exact_match']['references_only'] == []

    def test_both_inconclusive_verdicts_reach_findings(self, tmp_path):
        """Neither verdict may be dropped into silence on the way to the report."""
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-unresolvable-findings'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        unresolvable_findings = [
            f
            for f in data['findings']
            if f.get('severity') == 'warning' and 'could not be resolved' in f.get('message', '')
        ]
        assert len(unresolvable_findings) == 2, (
            f'Expected one warning finding per affected_files_* peer, got {data["findings"]}'
        )

    def test_resolved_but_empty_footprint_still_yields_a_measured_verdict(self, tmp_path):
        """Negative control: ``modified_files: []`` RESOLVED, so both peers measure.

        Without this control the deliverable could be satisfied by reporting
        everything as unmeasurable. A present-but-empty key is a real answer:
        recall measures 0% and fails, and the exact-match peer reports genuine
        one-sided drift.
        """
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'modified_files': [], 'domains': []}, name='archived-resolved-empty'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        recall = _check_by_name(data['checks'], 'affected_files_recall')
        assert recall['status'] == 'fail'
        details = data['details']['affected_files_recall']
        assert details['footprint_resolved'] is True
        assert float(details['recall_pct']) == 0.0

        exact = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert exact['status'] == 'warn'


class TestSummaryCountsEveryEmittedStatus:
    """``summary`` buckets reconcile against ``len(checks)`` — no verdict vanishes.

    A status that lands in no bucket reads to a summary consumer as a check that
    does not exist, which is the same unmeasurable-rendered-as-absent shape the
    ``inconclusive`` footprint verdict removes. The reconciliation is derived
    from the emitted ``checks``, never from a hardcoded status list, so a status
    introduced later is covered without editing this test.
    """

    def _assert_reconciles(self, data) -> None:
        summary = data['summary']
        assert sum(int(v) for v in summary.values()) == len(data['checks']), (
            f'Summary buckets {summary} do not reconcile against '
            f'{len(data["checks"])} checks: '
            f'{[(c["name"], c["status"]) for c in data["checks"]]}'
        )

    def test_reconciles_when_every_check_passes(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        self._assert_reconciles(result.toon())

    def test_reconciles_when_inconclusive_verdicts_are_emitted(self, tmp_path):
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'domains': []}, name='archived-summary-inconclusive'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['summary']['inconclusive']) == 2
        self._assert_reconciles(data)

    def test_reconciles_when_a_warn_verdict_is_emitted(self, tmp_path):
        """``warn`` had no bucket either — the repair covers the whole map."""
        plan_dir = _setup_archived_plan_with_references(
            tmp_path, {'modified_files': [], 'domains': []}, name='archived-summary-warn'
        )
        result = _run_archived(plan_dir)
        assert result.success, result.stderr
        data = result.toon()

        assert int(data['summary']['warn']) == 1
        self._assert_reconciles(data)

    def test_reconciles_when_a_broken_plan_fails_checks(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        self._assert_reconciles(result.toon())


# =============================================================================
# Unit tests for the three-tier footprint resolver (_resolve_footprint).
# =============================================================================

import importlib.util  # noqa: E402
import subprocess  # noqa: E402


def _load_check_module():
    spec = importlib.util.spec_from_file_location('_check_artifact_under_test', SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_check_mod = _load_check_module()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-b', 'main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test')


class TestResolveFootprintTiers:
    """``_resolve_footprint`` resolves live diff, then legacy key, then unresolvable.

    Tier 1 reaches the worktree through the ONE plan-context resolver
    (``_references_core.resolve_live_worktree``), keyed on ``plan_id``. It no
    longer re-reads ``status.metadata.worktree_path`` out of the plan's own
    status file, so these tests stub the resolver rather than writing a
    ``status.json`` the function does not consult.

    Tier 3 is UNRESOLVABLE, not empty: "resolved to a genuinely empty set" and
    "could not be resolved at all" are different answers, and the resolution
    state is read through :func:`footprint_resolved` rather than by testing
    emptiness. The resolved-empty control below is the negative half of that
    pair — without it, a sentinel that made everything unmeasurable would still
    satisfy the unresolvable assertions.
    """

    def test_tier1_live_diff_when_worktree_resolves(self, tmp_path, monkeypatch):
        """A resolvable worktree yields the live ``{base}...HEAD`` ∪ porcelain set."""
        repo = tmp_path / 'wt'
        _init_repo(repo)
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'base')
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'committed.py').write_text('print("x")\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'plan change')
        (repo / 'uncommitted.py').write_text('print("y")\n')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}))

        asked = []

        def _resolve(plan_id):
            asked.append(plan_id)
            return repo

        monkeypatch.setattr(_check_mod, 'resolve_live_worktree', _resolve)

        footprint = _check_mod._resolve_footprint(plan_dir, 'demo-plan')
        assert 'committed.py' in footprint
        assert 'uncommitted.py' in footprint
        assert 'base.txt' not in footprint
        assert asked == ['demo-plan'], (
            'tier 1 must reach the worktree through the resolver, keyed on plan_id'
        )

    def test_tier1_skipped_in_archived_mode(self, tmp_path, monkeypatch):
        """``plan_id=None`` skips tier 1 — an archived worktree no longer exists."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )

        asked = []

        def _resolve(plan_id):
            asked.append(plan_id)
            return None

        monkeypatch.setattr(_check_mod, 'resolve_live_worktree', _resolve)

        assert _check_mod._resolve_footprint(plan_dir, None) == {'legacy/a.py'}
        assert asked == [None]

    def test_status_metadata_worktree_path_is_no_longer_consulted(self, tmp_path):
        """A recorded ``worktree_path`` alone must NOT produce a live footprint.

        This pins the removal of the hand-rolled re-derivation: before the
        migration a ``status.json`` carrying a resolvable ``worktree_path`` was
        enough to reach tier 1. Now only the resolver can.
        """
        repo = tmp_path / 'wt'
        _init_repo(repo)
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'base')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'base_branch': 'main', 'modified_files': ['legacy/a.py']})
        )
        (plan_dir / 'status.json').write_text(
            json.dumps({'metadata': {'worktree_path': str(repo)}})
        )

        assert _check_mod._resolve_footprint(plan_dir, None) == {'legacy/a.py'}

    def test_tier2_legacy_key_when_no_worktree(self, tmp_path):
        """No worktree → fall back to the legacy ``modified_files`` key."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py', 'legacy/b.py']})
        )
        # No status.json at all → no worktree path resolvable.

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint == {'legacy/a.py', 'legacy/b.py'}

    def test_tier3_unresolvable_when_neither_resolves(self, tmp_path):
        """No worktree and no legacy key → UNRESOLVABLE, never an empty set.

        This is the confident-zero source: collapsing "could not resolve" into
        ``set()`` is what let a plan with a 21/21 exact footprint score a
        confident ``Recall 0%`` once ``branch-cleanup`` had deleted the
        worktree the resolver measures.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}))

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint is _check_mod.FOOTPRINT_UNRESOLVED
        assert not _check_mod.footprint_resolved(footprint)

    def test_present_but_empty_legacy_key_is_a_resolved_empty_footprint(self, tmp_path):
        """Negative control: ``modified_files: []`` RESOLVED — to an empty set.

        The positive sibling of the tier-3 assertion above. A present-but-empty
        key is a measured answer ("the plan touched no files"), so it must stay
        distinguishable from the absent key, and ``footprint_resolved`` — not
        emptiness — is what tells them apart.
        """
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'modified_files': []}))

        footprint = _check_mod._resolve_footprint(plan_dir)
        assert footprint == set()
        assert _check_mod.footprint_resolved(footprint)

    def test_tier1_diff_failure_reports_unresolvable_without_legacy_fallback(
        self, tmp_path, outside_repo_dir, monkeypatch
    ):
        """A resolved directory that is not a git tree reports UNRESOLVABLE.

        The worktree resolved but the diff did not, so the legacy key would
        answer a different question while presenting as the same measurement.
        The legacy key is deliberately populated here: the assertion is that it
        is NOT consulted, which is only checkable when it holds a value that
        would have been returned under the old fall-through.
        """
        # ``plain`` must be OUTSIDE the repo: pytest's tmp_path now roots under
        # the repo-local --basetemp, where it IS a git tree and the tier-1 live
        # footprint would resolve instead of failing.
        plain = outside_repo_dir / 'plain'
        plain.mkdir()

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )
        monkeypatch.setattr(_check_mod, 'resolve_live_worktree', lambda plan_id: plain)

        footprint = _check_mod._resolve_footprint(plan_dir, 'demo-plan')
        assert footprint is _check_mod.FOOTPRINT_UNRESOLVED
        assert not _check_mod.footprint_resolved(footprint)


class TestMetricsGeneratedOrderingDerivedVerdict:
    """``metrics_generated``'s absence verdict is derived from step ORDERING.

    An absent ``metrics.md`` only substantiates "the producing step did not run"
    once that step has had its turn. ``default:record-metrics`` is ordered after
    ``plan-marshall:plan-retrospective``, so the historical
    ``fail`` — "metrics.md missing — record-metrics step did not run" — was a
    causal claim about a step that had not yet been reached, and was structurally
    guaranteed to be wrong on a correctly-functioning run rather than
    occasionally wrong.

    The two verdicts are pinned as a MATCHED positive/negative control pair over
    the same input (no ``metrics.md`` on disk), differing ONLY in the resolved
    ordering: producer-later must be ``inconclusive`` and producer-earlier must
    be ``fail``. Without the negative half, the repair could be satisfied by
    making the check unconditionally inconclusive.

    The orders are injected by stubbing the discovery seam the production code
    queries, so the branches are driven through the SAME resolution path the real
    run uses. ``test_orders_are_read_from_real_discovery`` keeps that stubbing
    honest: it asserts the unstubbed resolver answers from the live registry, so
    a resolver that silently returned ``None`` everywhere could not make the
    stubbed branches read as green.
    """

    _PRODUCER = 'default:record-metrics'
    _CONSUMER = 'plan-marshall:plan-retrospective'

    def _plan_dir_without_metrics(self, tmp_path: Path) -> Path:
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        return plan_dir

    def _stub_orders(self, monkeypatch, *, producer, consumer) -> list[str]:
        """Stub discovery with the given orders; return the ext-points queried.

        ``None`` for either order omits that step from the discovered records —
        the not-discoverable case, which is distinct from a discovered step whose
        order happens to be low.
        """
        queried: list[str] = []
        records = []
        if producer is not None:
            records.append({'name': self._PRODUCER, 'order': producer})
        if consumer is not None:
            records.append({'name': self._CONSUMER, 'order': consumer})

        def _fake_find_implementors(ext_point):
            queried.append(ext_point)
            return records

        monkeypatch.setattr(_check_mod, 'find_implementors', _fake_find_implementors)
        return queried

    def test_producer_ordered_later_is_inconclusive_naming_the_ordering(
        self, tmp_path, monkeypatch
    ):
        """Positive half: producer after consumer → ``inconclusive``, ordering named."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        queried = self._stub_orders(monkeypatch, producer=998, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive', (
            'A producer ordered after the consuming retrospective has not had its '
            f'turn, so its artifact\'s absence is unmeasurable. Got: {status} — {message}'
        )
        assert self._PRODUCER in message
        assert self._CONSUMER in message
        assert '998' in message and '995' in message, (
            'The message must NAME the ordering it derived the verdict from, so a '
            f'reader can tell it apart from a genuine miss: {message}'
        )
        assert 'did not run' not in message, (
            'The retired causal claim must not survive on the inconclusive branch.'
        )
        assert queried == [_check_mod._FINALIZE_STEP_EXT_POINT] * 2, (
            'Both orders must be resolved from the finalize-step ext-point '
            f'registry the pipeline itself orders by, got {queried}'
        )

    def test_producer_ordered_earlier_is_fail(self, tmp_path, monkeypatch):
        """Negative half: producer before consumer → ``fail`` on the SAME input.

        Identical plan directory, identical absent artifact — only the resolved
        ordering differs. This is what stops the repair from being satisfied by
        an unconditionally-inconclusive check.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=10, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'fail', (
            'A producer ordered BEFORE the consumer has already had its turn, so a '
            f'missing artifact is a genuine miss. Got: {status} — {message}'
        )
        assert '10' in message and '995' in message

    def test_equal_orders_are_fail(self, tmp_path, monkeypatch):
        """Boundary: equal orders give no guarantee the producer runs later.

        Only a STRICTLY later producer substantiates "has not had its turn". At
        equal order the run sequence is unconstrained, so the check must not
        excuse the absence — it falls to the measured branch.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=995, consumer=995)

        status, _ = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'fail'

    def test_unresolvable_ordering_is_inconclusive_not_fail(self, tmp_path, monkeypatch):
        """An ordering that cannot be resolved is itself an unmeasurable input."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        self._stub_orders(monkeypatch, producer=None, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive', (
            'Whether the producer has had its turn is unknown when its order does '
            f'not resolve — a fail would be a confident claim from no input: {message}'
        )
        assert 'could not be resolved' in message

    def test_discovery_failure_is_inconclusive_not_a_crash(self, tmp_path, monkeypatch):
        """A raising registry degrades to unmeasurable, never an uncaught error.

        The consistency gate is fail-closed throughout: a discovery blow-up must
        surface as a structured verdict, not abort every remaining check.
        """
        plan_dir = self._plan_dir_without_metrics(tmp_path)

        def _boom(ext_point):
            raise RuntimeError('registry unavailable')

        monkeypatch.setattr(_check_mod, 'find_implementors', _boom)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'inconclusive'
        assert 'could not be resolved' in message

    def test_present_metrics_passes_whatever_the_ordering(self, tmp_path, monkeypatch):
        """Control: ordering only governs the ABSENCE branch, never presence."""
        plan_dir = self._plan_dir_without_metrics(tmp_path)
        (plan_dir / 'metrics.md').write_text('# Metrics\n', encoding='utf-8')
        self._stub_orders(monkeypatch, producer=998, consumer=995)

        status, message = _check_mod.check_metrics_generated(plan_dir)

        assert status == 'pass'
        assert message == 'metrics.md present'

    def test_orders_are_read_from_real_discovery(self):
        """Non-vacuity: the UNSTUBBED resolver answers from the live registry.

        Every branch above stubs the seam, so all of them would still read as
        green against a resolver that always returned ``None``. This asserts the
        real one resolves both steps to integers off the discovered records —
        which is also what makes the production verdict ordering-derived rather
        than literal-derived.
        """
        producer_order = _check_mod._resolve_step_order(self._PRODUCER)
        consumer_order = _check_mod._resolve_step_order(self._CONSUMER)

        assert isinstance(producer_order, int), (
            f'{self._PRODUCER} must be discoverable with an integer order; '
            'an unresolvable producer would make every stubbed branch above vacuous.'
        )
        assert isinstance(consumer_order, int), (
            f'{self._CONSUMER} must be discoverable with an integer order.'
        )

    def test_unknown_step_resolves_to_none(self):
        """The resolver reports not-discoverable rather than inventing a position."""
        assert _check_mod._resolve_step_order('default:no-such-finalize-step') is None
