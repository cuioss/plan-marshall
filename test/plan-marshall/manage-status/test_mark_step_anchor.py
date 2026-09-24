#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unfabricable completion anchors: `--head-at-completion` must resolve to a commit.

``mark-step-done`` used to persist any SHA-shaped string as the completion
anchor without consulting the object store, so a fabricated
``--head-at-completion`` resolving to no commit entered the record and later
rounds scoped their delta against a ref nobody can locate in history. The
handler now resolves the supplied SHA via ``git cat-file -e {sha}^{commit}``
before persisting and refuses unknown SHAs fail-closed with
``unknown_head_at_completion``, writing nothing.

These tests pin the resolution and its matched controls:

(a) A ``done`` with a FABRICATED anchor (hex-valid, resolves to nothing) is
    refused with ``unknown_head_at_completion``, AND nothing is written. The
    write assertion is separate from the status assertion on purpose: a
    refusal that still persisted a partial record would satisfy the error
    check while leaving exactly the fabricated anchor the refusal exists to
    prevent.
(b) A ``done`` with a REAL HEAD anchor is written — the positive control
    that keeps (a) from passing because the verb rejects every SHA.
(c) A ``done`` with a NON-COMMIT object anchor (a tree SHA that resolves but
    is not a commit) is refused — the peel is ``^{commit}``, not mere
    existence, so "resolves to something" is not enough.
(d) A NON-``done`` outcome with a fabricated anchor is written — the
    resolution binds ``done`` alone, so a ``failed`` record stays writable
    without an anchor that means anything.
(e) A ``done`` with NO anchor on a non-head-dependent step is written — the
    resolution only constrains a SUPPLIED anchor; absence is governed by the
    pre-existing ``missing_head_at_completion`` rule, unchanged here.
(f) A SYMBOLIC anchor (``HEAD``, a branch name) persists as the RESOLVED
    full-hex object ID, never the supplied spelling — a moving reference
    must not stand as the delta anchor. A leading-``-`` revision is refused
    before reaching git.

The SHAs are derived from the LIVE repo (HEAD commit, HEAD tree), never
hardcoded, so the suite cannot go vacuously green on a stale literal: the
positive control resolves because the object store holds it, the tree
control resolves-but-is-not-a-commit for the same reason, and the
fabricated control (forty zeroes) resolves to nothing in any repo.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace

import pytest

from conftest import load_script_module

_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_anchor_mark_step')
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_anchor_lifecycle')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_anchor_core')

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status

#: Hex-valid, resolves to nothing in any repo — the fabricated anchor.
_FABRICATED = '0' * 40


def _git_rev_parse(rev: str) -> str:
    """Resolve ``rev`` against the live repo or fail the fixture loudly."""
    proc = subprocess.run(
        ['git', 'rev-parse', rev],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f'Cannot resolve {rev!r} for the anchor fixtures: {proc.stderr.strip()}'
    return proc.stdout.strip()


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Anchor Resolution Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _args(
    plan_id: str,
    outcome: str,
    head_at_completion: str | None = None,
    display_detail: str | None = 'test detail',
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        phase='6-finalize',
        step='anchor-probe-step',
        outcome=outcome,
        force=False,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=None,
        fact=None,
    )


def _recorded_steps(plan_id: str) -> dict:
    """The persisted ``6-finalize`` step records, or an empty dict."""
    persisted: dict = read_status(plan_id)
    metadata: dict = persisted.get('metadata', {})
    phase_steps: dict = metadata.get('phase_steps', {})
    recorded: dict = phase_steps.get('6-finalize', {})
    return recorded


# ---------------------------------------------------------------------------
# (a) the refusal, and the nothing-was-written half of it
# ---------------------------------------------------------------------------


def test_done_with_fabricated_anchor_is_refused(plan_context):
    plan_id = 'anchor-fabricated-refused'
    _make_plan(plan_id)

    result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion=_FABRICATED))

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_head_at_completion'
    assert 'head-at-completion' in result['message']


def test_fabricated_refusal_writes_nothing(plan_context):
    """The refusal is total — no partial record survives it."""
    plan_id = 'anchor-fabricated-no-write'
    _make_plan(plan_id)

    cmd_mark_step_done(_args(plan_id, 'done', head_at_completion=_FABRICATED))

    assert _recorded_steps(plan_id) == {}


# ---------------------------------------------------------------------------
# (b) positive control — a real HEAD anchor is written
# ---------------------------------------------------------------------------


def test_done_with_real_head_anchor_is_written(plan_context):
    plan_id = 'anchor-real-accepted'
    _make_plan(plan_id)
    head = _git_rev_parse('HEAD')

    result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion=head))

    assert result['status'] == 'success'
    assert result['head_at_completion'] == head
    assert _recorded_steps(plan_id)['anchor-probe-step']['head_at_completion'] == head


# ---------------------------------------------------------------------------
# (c) resolves-but-is-not-a-commit is refused
# ---------------------------------------------------------------------------


def test_done_with_tree_anchor_is_refused(plan_context):
    """A tree SHA exists in the store but is not a commit — the ``^{commit}``
    peel must fail it.

    Without this control, a handler that checked bare existence (``git
    cat-file -e {sha}`` with no peel) would satisfy the fabricated-SHA
    refusal while accepting any blob or tree as an "anchor" no delta can
    scope against.
    """
    plan_id = 'anchor-tree-refused'
    _make_plan(plan_id)
    tree = _git_rev_parse('HEAD^{tree}')

    result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion=tree))

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_head_at_completion'
    assert _recorded_steps(plan_id) == {}


# ---------------------------------------------------------------------------
# (d) the resolution binds `done` alone
# ---------------------------------------------------------------------------


def test_non_done_outcome_with_fabricated_anchor_is_written(plan_context):
    """A ``failed`` record carrying a bogus anchor stays writable.

    The resolution validates the anchor of a terminal ``done`` verdict. A
    ``failed`` record is not a verdict scoped against a tree, so refusing it
    would break the loop-back path that records failures freely.
    """
    plan_id = 'anchor-failed-fabricated'
    _make_plan(plan_id)

    result = cmd_mark_step_done(_args(plan_id, 'failed', head_at_completion=_FABRICATED))

    assert result['status'] == 'success'
    assert 'anchor-probe-step' in _recorded_steps(plan_id)


# ---------------------------------------------------------------------------
# (f) symbolic anchors persist as the resolved object ID, not the spelling
# ---------------------------------------------------------------------------


def test_done_with_head_spelling_persists_resolved_object_id(plan_context):
    """`HEAD` is accepted but the record carries the commit it named.

    Without canonicalization the record would carry the four characters
    `HEAD`, and every later round scoping its delta against the record would
    compare a moving reference rather than the tree the verdict examined.
    """
    plan_id = 'anchor-head-canonical'
    _make_plan(plan_id)
    expected = _git_rev_parse('HEAD^{commit}')

    result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion='HEAD'))

    assert result['status'] == 'success'
    assert result['head_at_completion'] == expected
    assert result['head_at_completion'] != 'HEAD'
    assert _recorded_steps(plan_id)['anchor-probe-step']['head_at_completion'] == expected


def test_done_with_branch_spelling_persists_resolved_object_id(plan_context):
    """A branch name is accepted but the record carries its tip commit."""
    import subprocess

    plan_id = 'anchor-branch-canonical'
    _make_plan(plan_id)
    branch = 'tmp-anchor-canonical-branch'
    create = subprocess.run(
        ['git', 'branch', branch, 'HEAD'],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert create.returncode == 0, f'Cannot create temp branch for the anchor test: {create.stderr.strip()}'
    try:
        expected = _git_rev_parse('HEAD^{commit}')

        result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion=branch))

        assert result['status'] == 'success'
        assert result['head_at_completion'] == expected
        assert _recorded_steps(plan_id)['anchor-probe-step']['head_at_completion'] == expected
    finally:
        subprocess.run(
            ['git', 'branch', '-D', branch],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


def test_leading_dash_anchor_is_refused_without_reaching_git(plan_context):
    """A revision starting with `-` is refused as unresolvable.

    The value can never name a commit, and passing it to git would risk
    option-flag parsing — so it is rejected before any subprocess runs, and
    nothing is written.
    """
    plan_id = 'anchor-leading-dash'
    _make_plan(plan_id)

    result = cmd_mark_step_done(_args(plan_id, 'done', head_at_completion='--upload-pack=touch'))

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_head_at_completion'
    assert _recorded_steps(plan_id) == {}


# ---------------------------------------------------------------------------
# (e) absence is governed by the pre-existing rule, not the resolution
# ---------------------------------------------------------------------------


def test_done_without_anchor_on_plain_step_is_written(plan_context):
    """No anchor at all on a non-head-dependent step still records.

    The resolution constrains a SUPPLIED anchor; it does not manufacture an
    anchor requirement. Absence stays governed by the
    ``missing_head_at_completion`` rule, which fires only for steps declaring
    ``head_dependent: true``.
    """
    plan_id = 'anchor-absent-plain-step'
    _make_plan(plan_id)

    result = cmd_mark_step_done(_args(plan_id, 'done'))

    assert result['status'] == 'success'
    assert 'anchor-probe-step' in _recorded_steps(plan_id)
