#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``mark step done`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for the mark-step-done subcommand of manage-status.
"""

from argparse import Namespace

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_mark_step_lifecycle')


_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_mark_step_cmd')


_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_mark_step_core')


cmd_create = _lifecycle.cmd_create


cmd_mark_step_done = _mark_step.cmd_mark_step_done


read_status = _status_core.read_status


write_status = _status_core.write_status


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Mark Step Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _real_head(rev: str = 'HEAD') -> str:
    """Resolve ``rev`` against the live repo — a real anchor for `done` records.

    `mark-step-done` resolves a supplied `--head-at-completion` against the
    object store (unfabricable-anchor rule) and refuses fabricated SHAs, so
    fixtures that record a `done` with an anchor must carry SHAs the local
    repo actually holds. A fixed literal is refused as fabricated.
    """
    import subprocess

    proc = subprocess.run(
        ['git', 'rev-parse', rev],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f'Cannot resolve {rev!r} for the anchor fixture: {proc.stderr.strip()}'
    sha = proc.stdout.strip()
    assert sha
    return sha


def _tmp_repo_two_heads(tmp_path, monkeypatch) -> tuple[str, str]:
    """Create a throwaway repo with two commits and pin cwd into it.

    Returns ``(new_sha, old_sha)`` — two DISTINCT real commits guaranteed to
    exist regardless of the caller checkout's depth. Tests that assert on two
    different anchors (overwrite, re-fire trails) must use this instead of
    ``_real_head('HEAD~1')``: CI checks out with a depth-1 history where the
    parent does not exist and the helper would assert. The cwd pin matters:
    `mark-step-done` resolves anchors in the inherited cwd, so the two SHAs
    must live in the repo the handler sees.
    """
    import subprocess

    repo = tmp_path / 'two-heads-repo'
    repo.mkdir(exist_ok=True)

    def _git(*argv: str) -> None:
        proc = subprocess.run(
            ['git', *argv],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert proc.returncode == 0, f'git {" ".join(argv)} failed: {proc.stderr.strip()}'

    _git('init')
    _git('config', 'user.email', 'fixture@example.test')
    _git('config', 'user.name', 'fixture')
    (repo / 'f.txt').write_text('one', encoding='utf-8')
    _git('add', '.')
    _git('commit', '-m', 'one')
    (repo / 'f.txt').write_text('two', encoding='utf-8')
    _git('add', '.')
    _git('commit', '-m', 'two')
    monkeypatch.chdir(repo)
    return _real_head('HEAD'), _real_head('HEAD~1')


def _args(
    plan_id: str,
    phase: str,
    step: str,
    outcome: str,
    force: bool = False,
    display_detail: str | None = None,
    head_at_completion: str | None = None,
    loop_back_target: str | None = None,
    fact: list[str] | None = None,
) -> Namespace:
    """Build the mark-step-done Namespace.

    ``fact`` mirrors the CLI's ``action='append'`` accumulation: a list of raw
    ``KEY=VALUE`` tokens, or ``None`` when the caller passed no ``--fact`` at all.
    """
    return Namespace(
        plan_id=plan_id,
        phase=phase,
        step=step,
        outcome=outcome,
        force=force,
        display_detail=display_detail,
        head_at_completion=head_at_completion,
        loop_back_target=loop_back_target,
        fact=fact,
    )
