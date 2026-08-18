# SPDX-License-Identifier: FSL-1.1-ALv2
"""The recall check reads a survey-scope deliverable's declaration.

``phase-3-outline/standards/outline-workflow-detail.md`` states that
``affected_files_recall`` "runs against the ``Files expected to mutate:``
subset". These tests pin that as behaviour rather than as prose: a
survey-scope deliverable declares ``Files to survey:`` + ``Files expected to
mutate:`` and NO ``Affected files:`` list, which is the form that standard
mandates, and the recall check must grade it.

The failure this closes is silent by construction. A path declared under a
heading no parser reads belongs to no declared set, and recall measures the
footprint against the declared set — so a path the declaration never named can
never be reported as missing from it. The check reported ``skip`` ("nothing to
compare") on a plan that had declared its whole mutation surface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import build_happy_plan_dir  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'check-artifact-consistency.py'
)

_SURVEY_OUTLINE = """# Solution: Demo
plan_id: demo

## Summary

Demo plan used by plan-retrospective tests.

## Overview

Overview text goes here.

## Deliverables

### 1. Survey the loggers and classify each

**Files to survey:**
- `src/surveyed_only.py`

**Files expected to mutate:**
- `src/foo.py`
- `src/bar.py`
"""


def _check_by_name(checks: list, name: str) -> dict | None:
    for entry in checks:
        if entry.get('name') == name:
            return entry
    return None


def _setup(tmp_path: Path, monkeypatch, modified: list[str]) -> str:
    """Build a live plan whose sole deliverable uses the survey-scope form."""
    plan_id = 'retro-survey-scope'
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    (plan_dir / 'solution_outline.md').write_text(_SURVEY_OUTLINE, encoding='utf-8')
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': modified, 'domains': ['plan-marshall-plugin-dev']}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id


def test_expected_to_mutate_paths_enter_the_recall_denominator(tmp_path, monkeypatch):
    """Both mutation-scope paths are graded; the surveyed-only path is not.

    The denominator is asserted positively as 2 — not merely "non-zero" — so a
    regression that folded the survey pool into the modification set would
    change the number and fail here rather than pass a weaker inequality.
    """
    plan_id = _setup(tmp_path, monkeypatch, ['src/foo.py', 'src/bar.py'])

    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

    assert result.success, result.stderr
    data = result.toon()
    details = data['details']['affected_files_recall']
    assert details['declared'] == 2, 'Files expected to mutate is the recall denominator'
    assert details['read_intent_excluded'] == 1, 'the survey pool is declared but not graded'
    assert details['found'] == 2
    assert _check_by_name(data['checks'], 'affected_files_recall')['status'] == 'pass'


def test_a_missed_mutation_scope_path_is_reported(tmp_path, monkeypatch):
    """A declared expected-to-mutate path absent from the footprint drags recall down.

    This is the whole point of reading the heading: with only one of two
    declared mutations realized, recall is 50% — below the 70% threshold — so
    the check fails. While the heading was unread the same plan reported
    ``skip``, because nothing had been declared as far as the check could see.
    """
    plan_id = _setup(tmp_path, monkeypatch, ['src/foo.py'])

    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

    assert result.success, result.stderr
    data = result.toon()
    check = _check_by_name(data['checks'], 'affected_files_recall')
    assert check['status'] == 'fail'
    details = data['details']['affected_files_recall']
    assert details['declared'] == 2
    assert details['found'] == 1
    assert details['recall_pct'] == 50.0


def test_survey_only_paths_are_never_expected_modifications(tmp_path, monkeypatch):
    """A surveyed-but-unmutated path never counts against recall.

    Asserted through the verdict, not only the count: were the survey pool
    graded, the same footprint would yield 2/3 = 67% and fail the threshold.
    """
    plan_id = _setup(tmp_path, monkeypatch, ['src/foo.py', 'src/bar.py'])

    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

    assert result.success, result.stderr
    data = result.toon()
    details = data['details']['affected_files_recall']
    assert details['recall_pct'] == 100.0
    assert _check_by_name(data['checks'], 'affected_files_recall')['status'] == 'pass'


def test_an_unparseable_survey_declaration_fails_loudly_not_silently(tmp_path, monkeypatch):
    """A survey heading whose bullets do not parse is a ``fail``, never a ``skip``.

    ``artifact-consistency.md`` states the obligation normatively: "a declaration
    heading present in a deliverable's own content but yielding no parsed bullet
    is treated as a parse failure". That exists because a borrowed parser's
    silence is indistinguishable from a genuine absence — the check re-parses a
    grammar it does not own, so an under-match reads as "the plan declared
    nothing" rather than as "this reader could not read it".

    The obligation was widened to all three headings while ``heading_present``
    still looked for ``**Affected files:**`` alone. A survey-scope deliverable
    with an unparseable list therefore took the SILENT branch: `skip`, "nothing
    to compare", over a plan that had declared its whole mutation surface.

    The two verdicts are asserted positively and are opposites, so a regression
    reaches the wrong one rather than a differently-worded right one.
    """
    plan_id = 'retro-survey-unparseable'
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    # The heading is present; the entries below it are prose, not bullets, so
    # nothing parses out of it.
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution: Demo\nplan_id: demo\n\n## Summary\n\ns\n\n## Overview\n\no\n\n'
        '## Deliverables\n\n### 1. Survey the loggers\n\n'
        '**Files expected to mutate:**\n\nTBD — to be filled in during execution.\n',
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(
        json.dumps({'modified_files': ['src/foo.py'], 'domains': ['plan-marshall-plugin-dev']}),
        encoding='utf-8',
    )
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))

    result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

    assert result.success, result.stderr
    check = _check_by_name(result.toon()['checks'], 'affected_files_recall')
    assert check['status'] == 'fail'
    assert 'no bullet parsed' in check['message']
