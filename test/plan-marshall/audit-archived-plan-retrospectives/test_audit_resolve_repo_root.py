#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Repo-root resolution — the ADR-002 cwd walk-up finds the repository root from a
nested working directory and fails closed when no root is reachable.
"""

import tempfile
from pathlib import Path

import pytest
from _audit_fixtures import audit


class TestResolveRepoRoot:
    """``_resolve_repo_root`` walks up to the nearest ancestor carrying ``.plan/local``.

    Every repo-root-anchored read and write in ``audit.py`` — the corpus scan
    roots, the lessons-corpus read, the global-log read, the retire-on-quiet run
    history, and the persisted report — hangs off this resolver, so the branch
    that matters is (b): invoked from a subdirectory, the resolver must return
    the project root rather than the working directory.

    All three branches drive the REAL resolver through ``monkeypatch.chdir``
    into a constructed sandbox. ``Path.cwd`` itself is never stubbed or
    monkeypatched, which is what makes branch (b) fail against a revert to
    ``repo_root = Path.cwd()`` instead of passing against a mock.
    """

    def test_cwd_is_the_marker_bearing_root_returns_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (a): cwd IS the root
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        resolved = audit._resolve_repo_root()

        assert resolved == Path.cwd()
        assert (resolved / '.plan' / 'local').is_dir()

    def test_nested_cwd_walks_up_to_the_marker_bearing_ancestor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (b): cwd is BELOW the root — the branch a Path.cwd() derivation fails
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        nested = tmp_path / 'marketplace' / 'bundles' / 'plan-marshall'
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        resolved = audit._resolve_repo_root()

        assert resolved == tmp_path.resolve()
        assert resolved != Path.cwd()

    def test_no_marker_bearing_ancestor_falls_back_to_cwd(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (c): nothing qualifies — stay anchored where we were invoked, which
        # is what keeps an out-of-project invocation inside its own sandbox.
        #
        # Deliberately NOT `tmp_path`: pytest's basetemp is configured under this
        # project's own `.plan/temp/`, so every `tmp_path` HAS a `.plan/local`-bearing
        # ancestor (the repo root) and the no-marker branch is unconstructible there.
        # The system temp dir is the nearest thing to a genuinely out-of-project cwd;
        # the precondition below fails loudly rather than silently passing vacuously
        # if that ever stops holding.
        with tempfile.TemporaryDirectory() as raw:
            bare = Path(raw).resolve() / 'outside-any-project'
            bare.mkdir()
            assert not any(
                (ancestor / '.plan' / 'local').is_dir()
                for ancestor in (bare, *bare.parents)
            ), 'system temp dir sits inside a .plan/local tree — branch (c) unconstructible'
            monkeypatch.chdir(bare)

            resolved = audit._resolve_repo_root()

            assert resolved == Path.cwd()
