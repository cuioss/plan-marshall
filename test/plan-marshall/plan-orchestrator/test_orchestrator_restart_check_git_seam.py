#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the read-only contract of ``cleanup restart-check``'s single git seam.

The verb is a readiness PROBE, so its one git seam must be incapable of writing
— not merely uninvoked with a write today. The operation-to-argv table in the
module is the authority for what git is asked to do, and every assertion here is
made against that table.
"""

import pytest
from _restart_check_fixtures import CLEAN_SHA, SCRIPT_PATH, _git_stub, _orch, install_parity_stores


@pytest.fixture(autouse=True)
def parity_stores(tmp_path, monkeypatch):
    """Point the parity arm of every test at fixture stores that are in parity."""
    return install_parity_stores(tmp_path, monkeypatch)


#: Git subcommands that only OBSERVE. The seam's declared operations are checked
#: against this set rather than against a list of forbidden mutators, because an
#: allowlist fails closed: a mutating subcommand nobody thought to forbid is
#: rejected by default instead of slipping through a denylist's gaps.
READ_ONLY_GIT_SUBCOMMANDS = frozenset(
    {
        'rev-parse',
        'status',
        'log',
        'show',
        'diff',
        'ls-files',
        'ls-tree',
        'cat-file',
        'describe',
        'symbolic-ref',
        'for-each-ref',
        'rev-list',
    }
)


class TestGitSeamIsReadOnlyByConstruction:
    """`cleanup restart-check` is a readiness PROBE, so its one git seam must be
    incapable of writing — not merely uninvoked with a write today."""

    def test_the_declared_operation_population_is_non_empty(self):
        # Non-empty-population guard: every assertion below iterates this table,
        # so an empty one would make all of them vacuously pass.
        operations = _orch._GIT_READ_OPERATIONS

        assert operations, 'the seam declares no read operations'
        assert set(operations) == {'head-sha', 'worktree-status'}, (
            f'the declared operation set changed: {sorted(operations)}'
        )

    def test_every_declared_operation_expands_to_a_read_only_subcommand(self):
        operations = _orch._GIT_READ_OPERATIONS

        offenders = {
            name: argv for name, argv in operations.items() if not argv or argv[0] not in READ_ONLY_GIT_SUBCOMMANDS
        }

        assert offenders == {}, (
            f'of {len(operations)} declared operation(s), these do not expand to a read-only '
            f'git subcommand: {offenders}'
        )

    def test_an_undeclared_operation_fails_loud_rather_than_reporting_git_unreadable(self):
        # The truthfulness half. Degrading an unknown operation to the seam's
        # `(None, reason)` unobservable path would report a defect in this module
        # as an environmental one — a caller would read "git is not readable" and
        # investigate the repository instead of the code.
        try:
            _orch._git_read('no-such-operation')
        except KeyError:
            return
        raise AssertionError('an undeclared operation did not fail loud')

    def test_no_caller_supplies_git_arguments(self):
        # The structural half: callers must NAME an operation. A surviving
        # `_git_read([...])` call site would mean the argv is composed at the
        # call site again, which is exactly what the table exists to prevent.
        source = SCRIPT_PATH.read_text(encoding='utf-8')

        assert '_git_read(' in source, 'the scan did not read the module under test'
        assert '_git_read([' not in source, 'a caller still passes argv to the git seam'

    def test_the_stub_covers_every_declared_read_operation(self):
        # Keeps the double honest against the seam it doubles: a newly declared
        # operation that the stub does not answer would silently return the
        # porcelain fall-through, and every test using the stub would assert
        # against a value the real seam never produces.
        operations = _orch._GIT_READ_OPERATIONS
        stub = _git_stub(porcelain=' M a/b.py\n')

        answers = {name: stub(name) for name in operations}

        assert len(answers) == len(operations)
        assert answers['head-sha'] == (CLEAN_SHA, '')
        assert answers['worktree-status'] == (' M a/b.py\n', '')
        for name in operations:
            assert stub(name)[0] is not None, f'the stub does not answer {name!r}'
