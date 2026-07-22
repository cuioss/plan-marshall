#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Regression tests pinning the confident-false-negative fix in ``find`` / ``which-module``.

The defect: ``architecture find --pattern "test/plan-marshall/manage-status/*"``
returned ``status: success, count: 0`` while the files existed on disk. The
reader flattened an over-cap category's 100-path ``sample`` as if it were the
whole list, so a real file sorting PAST the sample horizon was invisible — a
confident false negative.

The invariant these tests pin is *a negative is never confident*: an in-scope
elided category is either self-scanned uncapped (the real hit surfaces,
``truncated: false``) or reported as ``truncated: true`` when the self-scan is
impossible — never a bare ``count: 0`` / ``module: null`` with ``truncated:
false``. These tests fail against the pre-fix ``_cmd_client_handlers`` (which
returned only the sample and never emitted ``truncated`` / ``elided``).

The fixtures are sized from the imported ``_FILES_CATEGORY_CAP`` (``cap + 1``),
so a future cap change cannot silently make the genuine elision — and thus the
self-scan under test — vacuous. The reader seam treats every elided in-scope
category identically; the defect surfaced on the ``test`` category, but a plain
generic ``source`` category exercises exactly the same code path and keeps the
fixture free of build-descriptor discovery ambiguity.
"""

import sys
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import seed_project  # noqa: E402

_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

_post_process_files = _cmd_manage._post_process_files
cmd_find = _cmd_client.cmd_find
cmd_which_module = _cmd_client.cmd_which_module

# Sorts after every ``pkg/s*.py`` entry, so it lands in the elided tail past the
# strided sample's last entry — only an uncapped self-scan can surface it.
_PAST_HORIZON = 'pkg/zzz_past_horizon.py'
_TRUNCATION_ELIDED_COUNT = 4242


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _seed_over_cap_self_scan_project(tmpdir: str) -> None:
    """Seed a module whose ``source`` category GENUINELY exceeds the cap on disk.

    Creates ``cap + 1`` real ``.py`` files (derived from the imported constant,
    never a literal) so the category elides for real, with a target file that
    sorts past the strided sample horizon. The genuinely-elided ``derived.json``
    is built by the real post-processor and persisted, so the reader loads a real
    elision shape and MUST self-scan the worktree to answer the query. There is
    no build descriptor, so module discovery finds nothing and the reader falls
    back to the seeded derived (the proven fixture path).
    """
    cap = _cmd_manage._FILES_CATEGORY_CAP
    project = Path(tmpdir)
    pkg = project / 'pkg'
    for i in range(cap):
        _write(pkg / f's{i:05d}.py', f'x = {i}\n')
    _write(pkg / 'zzz_past_horizon.py', 'target = True\n')

    modules = {'pkg': {'name': 'pkg', 'paths': {'module': 'pkg'}}}
    _post_process_files(modules, str(project))
    seed_project(tmpdir, modules)


def _seed_truncation_project(tmpdir: str) -> None:
    """Seed a module whose derived carries an elided ``source`` bucket but has NO
    real worktree directory — the self-scan-impossible (disk-derived / fixture)
    path that must degrade to a truthful truncation. The sample deliberately omits
    the past-horizon file."""
    modules = {
        'pkg': {
            'name': 'pkg',
            'paths': {'module': 'pkg'},
            'files': {
                'source': {
                    'elided': _TRUNCATION_ELIDED_COUNT,
                    'sample': ['pkg/s00000.py'],
                },
            },
        },
    }
    seed_project(tmpdir, modules)


def test_self_scan_arm_returns_past_horizon_hit_untruncated():
    """A real over-cap module is self-scanned uncapped — the past-horizon hit surfaces."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_over_cap_self_scan_project(tmpdir)

        args = Namespace(project_dir=tmpdir, pattern=_PAST_HORIZON, category=None)
        result = cmd_find(args)

        assert result['status'] == 'success'
        assert result['count'] == 1
        assert result['results'][0]['path'] == _PAST_HORIZON
        assert result['truncated'] is False
        assert result['elided'] == []


def test_truthful_truncation_arm_never_confident_negative():
    """A self-scan-impossible elided module reports a TRUTHFUL truncation, not a bare negative."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_truncation_project(tmpdir)

        args = Namespace(project_dir=tmpdir, pattern=_PAST_HORIZON, category=None)
        result = cmd_find(args)

        assert result['status'] == 'success'
        # The past-horizon file is absent from the sample and cannot be
        # self-scanned, so it is not found...
        assert result['count'] == 0
        # ...but the negative is explicitly qualified as truncated.
        assert result['truncated'] is True
        assert result['elided'][0]['module'] == 'pkg'
        assert result['elided'][0]['category'] == 'source'
        assert result['elided'][0]['elided_count'] == _TRUNCATION_ELIDED_COUNT
        # Explicit anti-shape assertion: NEVER the bare confident negative
        # (status: success / count: 0 / truncated: False) that was the defect.
        assert not (result['count'] == 0 and result['truncated'] is False)


def test_which_module_arm_self_scan_resolves_owner():
    """which-module self-scans a real over-cap module and resolves the owning module."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_over_cap_self_scan_project(tmpdir)

        args = Namespace(project_dir=tmpdir, path=_PAST_HORIZON)
        result = cmd_which_module(args)

        assert result['status'] == 'success'
        assert result['module'] == 'pkg'
        assert result['truncated'] is False
        assert result['elided'] == []


def test_which_module_arm_truncation_qualifies_null():
    """which-module on the self-scan-impossible fixture carries ``truncated: true``.

    A truthful ``truncated: true`` — never an unqualified ``module: null`` — when
    the path sits past the sample horizon and the module cannot be self-scanned.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_truncation_project(tmpdir)

        args = Namespace(project_dir=tmpdir, path=_PAST_HORIZON)
        result = cmd_which_module(args)

        assert result['status'] == 'success'
        assert result['truncated'] is True
        assert result['elided'][0]['elided_count'] == _TRUNCATION_ELIDED_COUNT
        assert not (result['module'] is None and result['truncated'] is False)
