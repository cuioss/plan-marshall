#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The scope-creep guard's unmeasured state cannot render as a measured zero.

The defect (finding 5ebd40): ``scope_creep_check`` returned ``residual_count: 0``
together with ``reason: no_baseline_sha``. The count is the field consumers gate
on; the reason is advisory and trivially dropped. A caller branching on
``residual_count == 0`` therefore could not tell "compared, and found no scope
creep" from "never compared at all".

Every case below is a MATCHED PAIR: the negative half asserts that the key is
ABSENT (not merely a different value — absence is what stops a consumer reading
it), and the positive half asserts that the measured path still publishes it.
Without the positive half, the negative would be satisfied by a script that
removed ``residual_count`` unconditionally, which would be a different defect
rather than a fix.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import file_ops
from _resolve_project_dir_fixtures import worktree_query_result
from conftest import get_script_path
from toon_parser import parse_toon

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-5-execute', 'scope_creep_check.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scope_creep_check as scc  # noqa: E402


def _seed_plan(plan_context, *, with_baseline: bool):
    """Create a plan dir whose references.json may or may not carry a baseline."""
    plan_dir = plan_context.plan_dir_for('scope-creep-could-not-look')
    refs: dict = {'affected_files': ['src/a.py']}
    if with_baseline:
        refs['plan_creation_sha'] = 'deadbeef'
    (plan_dir / 'references.json').write_text(json.dumps(refs))
    return plan_dir


def _patch_environment(monkeypatch, changed_files):
    """Hold the worktree resolver and the git diff at fixed, known values."""
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda plan_id: worktree_query_result(True, str(Path.cwd())),
    )
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: list(changed_files))


def _run(threshold=None):
    return scc.cmd_check(
        Namespace(plan_id='scope-creep-could-not-look', threshold=threshold)
    )


class TestMissingBaselineCannotRenderAsAMeasuredZero:
    """The named finding, and the control that proves the measured path survives."""

    def test_absent_baseline_reports_could_not_look_without_a_count(
        self, plan_context, monkeypatch, capsys
    ):
        # NEGATIVE — the reproduced conditions: no plan_creation_sha.
        _seed_plan(plan_context, with_baseline=False)
        _patch_environment(monkeypatch, [])

        rc = _run()
        parsed = parse_toon(capsys.readouterr().out)

        assert rc == 0
        assert parsed['status'] == 'could_not_look'
        assert parsed['reason'] == 'no_baseline_sha'
        # The load-bearing assertion: the key a consumer gates on is ABSENT.
        assert 'residual_count' not in parsed

    def test_present_baseline_with_no_drift_still_reports_a_measured_zero(
        self, plan_context, monkeypatch, capsys
    ):
        # POSITIVE — the discriminator. A genuine zero is unchanged, so the
        # negative above cannot be satisfied by dropping the field outright.
        _seed_plan(plan_context, with_baseline=True)
        _patch_environment(monkeypatch, ['src/a.py'])

        rc = _run()
        parsed = parse_toon(capsys.readouterr().out)

        assert rc == 0
        assert parsed['status'] == 'success'
        assert parsed['residual_count'] == 0
        assert parsed['finding_emitted'] is False

    def test_present_baseline_with_drift_reports_the_measured_count(
        self, plan_context, monkeypatch, capsys
    ):
        # The second positive: a non-zero measurement also survives, so the
        # measured path is shown to report its real value rather than a constant.
        _seed_plan(plan_context, with_baseline=True)
        _patch_environment(monkeypatch, ['src/a.py', 'stray/one.py', 'stray/two.py'])

        rc = _run(threshold=10)
        parsed = parse_toon(capsys.readouterr().out)

        assert rc == 0
        assert parsed['status'] == 'success'
        assert parsed['residual_count'] == 2


class TestDisabledGuardCannotRenderAsAMeasuredZero:
    """``--threshold 0`` switches the guard off; a switched-off guard looked at
    nothing, so it reports the same could-not-look shape."""

    def test_disabled_guard_reports_could_not_look_without_a_count(
        self, plan_context, monkeypatch, capsys
    ):
        _seed_plan(plan_context, with_baseline=True)

        def _must_not_run(*_a, **_k):
            raise AssertionError('no diff may be computed when the guard is disabled')

        monkeypatch.setattr(scc, '_git_diff_files', _must_not_run)

        rc = _run(threshold=0)
        parsed = parse_toon(capsys.readouterr().out)

        assert rc == 0
        assert parsed['status'] == 'could_not_look'
        assert parsed['reason'] == 'guard_disabled'
        assert 'residual_count' not in parsed

    def test_enabled_guard_over_the_same_plan_does_measure(
        self, plan_context, monkeypatch, capsys
    ):
        # The matched half: the SAME plan and the SAME tree, differing only in
        # whether the guard is switched on — and only then is a count published.
        _seed_plan(plan_context, with_baseline=True)
        _patch_environment(monkeypatch, ['src/a.py', 'stray/one.py'])

        rc = _run(threshold=5)
        parsed = parse_toon(capsys.readouterr().out)

        assert rc == 0
        assert parsed['status'] == 'success'
        assert parsed['residual_count'] == 1


class TestCouldNotLookNamesItsCause:
    """A refusal that cannot say why is the opaque signal this replaces."""

    def test_every_could_not_look_carries_a_reason_and_a_detail(
        self, plan_context, monkeypatch, capsys
    ):
        _seed_plan(plan_context, with_baseline=False)
        _patch_environment(monkeypatch, [])

        _run()
        parsed = parse_toon(capsys.readouterr().out)

        assert parsed['reason']
        assert 'nothing was measured' in parsed['detail']
        # `finding_emitted` stays published because it is unambiguously true and
        # implies no comparison; `residual_count` does not have that property.
        assert parsed['finding_emitted'] is False
