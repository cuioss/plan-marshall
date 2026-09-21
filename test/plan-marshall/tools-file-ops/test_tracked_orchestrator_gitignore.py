#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests that the repository's own ``.gitignore`` tracks the orchestrator trees.

The subject is the ignore BEHAVIOUR, not the file's text. ``.gitignore`` is a
precedence-ordered rule language — a later rule wins, a negation cannot
re-include a path whose parent directory is still excluded — so a text assertion
("the negation line is present") can pass over a file whose rules resolve the
opposite way. Every assertion below therefore asks ``git check-ignore``, the
same evaluator ``git add`` consults.

Five paths are asked about, because the contract has five distinct halves:

- ``.plan/orchestrator/{slug}/epic.md`` and its archived twin must NOT be
  ignored. Both homes are un-ignored, not just the active one, because an
  epic's active and archived trees sit on one storage tier.
- ``logs/decision.log`` under each MUST be ignored. That re-exclusion is the
  one genuinely machine-local sub-path, and it is stated after the negations
  precisely so the later rule wins.
- An unrelated ``.plan/local/...`` path must STILL be ignored. This is the
  matched negative control, and it is what makes the two non-ignored verdicts
  readable: without it, a ``check-ignore`` invocation that silently matched
  nothing at all would report every path as un-ignored and the first two
  assertions would pass for a reason that has nothing to do with the negations.

The slug is synthetic on purpose. ``check-ignore`` evaluates a PATH against the
rules and never consults the filesystem or the index, so the verdicts are
properties of the rule set rather than of whichever epics happen to be
relocated in the checkout under test.
"""

import subprocess
from pathlib import Path

import pytest

#: A slug that no epic carries, so the verdicts below are rule properties rather
#: than observations about the checkout's current epic population.
_FIXTURE_SLUG = 'fixture-gitignore-probe-epic'

#: ``git check-ignore``'s two VERDICT exit codes. Anything else (notably ``128``)
#: is git failing to answer, which must never be read as either verdict.
_EXIT_IGNORED = 0
_EXIT_NOT_IGNORED = 1


def _repo_root() -> Path:
    """Resolve the checkout holding this test, via git rather than via cwd.

    pytest's working directory is not guaranteed, and a parent-count walk from
    ``__file__`` would silently describe the wrong tree if the test module were
    ever relocated. Asking git from the test file's own directory answers for
    the checkout that actually owns this file.
    """
    completed = subprocess.run(  # argv list, never a shell string; 'git' resolves via PATH so any CI runner works
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=Path(__file__).resolve().parent,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return Path(completed.stdout.strip())


REPO_ROOT = _repo_root()


def _check_ignore(relative_path: str) -> subprocess.CompletedProcess:
    """Ask git whether ``relative_path`` is ignored, keeping the matching rule.

    ``-v`` puts the deciding ``.gitignore`` line on stdout, so an assertion
    failure names the rule that produced the verdict instead of only the
    verdict. ``check=False`` because exit ``1`` is the "not ignored" ANSWER, not
    a failure to run.
    """
    return subprocess.run(  # argv list, never a shell string; 'git' resolves via PATH so any CI runner works
        ['git', 'check-ignore', '-v', '--no-index', relative_path],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _verdict(relative_path: str) -> subprocess.CompletedProcess:
    """``_check_ignore`` plus the guard that git actually rendered a verdict."""
    completed = _check_ignore(relative_path)
    assert completed.returncode in (_EXIT_IGNORED, _EXIT_NOT_IGNORED), (
        f'git check-ignore exited {completed.returncode} for {relative_path!r} — that is neither '
        f'verdict, so nothing is known about this path: {completed.stderr.strip()}'
    )
    return completed


#: ``{the id naming the case: the path under it}``. The two tracked homes are
#: parametrized together rather than written twice: the contract is that BOTH
#: are un-ignored, and a single-home test would pass over a ``.gitignore`` that
#: negated only one of them.
_TRACKED_EPIC_PATHS = {
    'the-active-home': f'.plan/orchestrator/{_FIXTURE_SLUG}/epic.md',
    'the-archived-home': f'.plan/archived-orchestrators/{_FIXTURE_SLUG}/epic.md',
}

#: ``{the id naming the case: (the log path, the rule that must decide it)}``.
#: The expected rule rides along so a log path ignored by the blanket
#: ``.plan/*`` — which would mean the negation above it never took effect —
#: cannot pass as the intended re-exclusion.
_MACHINE_LOCAL_LOG_PATHS = {
    'under-the-active-home': (
        f'.plan/orchestrator/{_FIXTURE_SLUG}/logs/decision.log',
        '.plan/orchestrator/*/logs/',
    ),
    'under-the-archived-home': (
        f'.plan/archived-orchestrators/{_FIXTURE_SLUG}/logs/decision.log',
        '.plan/archived-orchestrators/*/logs/',
    ),
}


class TestTrackedOrchestratorHomesAreNotIgnored:
    """Both orchestrator homes are git-tracked, repo-local state."""

    @pytest.mark.parametrize(
        'relative_path',
        list(_TRACKED_EPIC_PATHS.values()),
        ids=list(_TRACKED_EPIC_PATHS),
    )
    def test_an_epic_document_is_not_ignored(self, relative_path):
        completed = _verdict(relative_path)

        assert completed.returncode == _EXIT_NOT_IGNORED, (
            f'{relative_path} is ignored by {completed.stdout.strip()!r} — the orchestrator '
            'corpus is tracked state and must reach the index'
        )


class TestMachineLocalLogsStayIgnored:
    """The one sub-path of those trees that is NOT shared history."""

    @pytest.mark.parametrize(
        ('relative_path', 'expected_rule'),
        list(_MACHINE_LOCAL_LOG_PATHS.values()),
        ids=list(_MACHINE_LOCAL_LOG_PATHS),
    )
    def test_a_log_file_is_ignored_by_its_own_re_exclusion(self, relative_path, expected_rule):
        completed = _verdict(relative_path)

        assert completed.returncode == _EXIT_IGNORED, (
            f'{relative_path} reached the index — per-verb log churn is not shared history'
        )
        # The DECIDING rule matters, not merely the verdict: a log path caught by
        # the blanket `.plan/*` would be ignored for the pre-change reason, which
        # would mean the negation above it never took effect at all.
        assert expected_rule in completed.stdout, (
            f'{relative_path} was decided by {completed.stdout.strip()!r}, not by the {expected_rule!r} re-exclusion'
        )


class TestUnrelatedRuntimeStateStaysIgnored:
    """The matched negative control for the two verdicts above."""

    def test_a_plan_local_path_is_still_ignored(self):
        # Without this, a check-ignore call that matched nothing at all would
        # report every path as un-ignored and the un-ignored assertions would
        # pass for a reason unrelated to the negations they exist to pin.
        relative_path = f'.plan/local/plans/{_FIXTURE_SLUG}/status.json'

        completed = _verdict(relative_path)

        assert completed.returncode == _EXIT_IGNORED, (
            f'{relative_path} is no longer ignored — the un-ignored verdicts elsewhere in this '
            'module would then prove nothing about the orchestrator negations'
        )
