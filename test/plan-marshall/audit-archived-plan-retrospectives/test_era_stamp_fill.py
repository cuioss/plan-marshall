#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the era-stamp-fill finalize-step executor (era_stamp_fill.py).

Covers the contract of `project:finalize-step-era-stamp-fill`:
- the pure `normalize_pr_number` / `fill_pending_token` helpers
- the `run` orchestration over audit.py + its test mirror: fill in lock-step, the
  absent-token no-op (skipped), idempotency, concrete-value preservation, and the
  bad-pr-number / missing-file error paths.

The executor is stdlib-only and directly invocable, so the module is loaded by path
(no executor PYTHONPATH needed) and the filesystem cases use pytest's tmp_path.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / '.claude'
    / 'skills'
    / 'finalize-step-era-stamp-fill'
    / 'scripts'
    / 'era_stamp_fill.py'
)


def _load_era_module():
    spec = importlib.util.spec_from_file_location('era_stamp_fill', _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['era_stamp_fill'] = mod
    spec.loader.exec_module(mod)
    return mod


era = _load_era_module()


# =============================================================================
# Fixtures — synthetic audit.py + test mirror under a tmp worktree root
# =============================================================================

_AUDIT_REL = '.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py'
_TEST_REL = 'test/plan-marshall/audit-archived-plan-retrospectives/test_audit.py'

# A realistic CHECK_ERA snippet: the PR-PENDING sentinel on one check, a concrete
# #NNN on another, and a PR-PENDING mention in a COMMENT (must NOT be rewritten).
_AUDIT_WITH_PENDING = (
    'CHECK_ERA = {\n'
    '    # PR-PENDING is the finalize-resolved sentinel for this check.\n'
    '    "execution-context-manifest": "PR-PENDING",\n'
    '    "merge-window-accounting": "#877",\n'
    '}\n'
)
_TEST_WITH_PENDING = (
    'def test_era():\n'
    '    assert audit.CHECK_ERA["execution-context-manifest"] == "PR-PENDING"\n'
)


def _seed_worktree(root: Path, audit_text: str, test_text: str) -> tuple[Path, Path]:
    audit = root / _AUDIT_REL
    test = root / _TEST_REL
    audit.parent.mkdir(parents=True, exist_ok=True)
    test.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(audit_text, encoding='utf-8')
    test.write_text(test_text, encoding='utf-8')
    return audit, test


# =============================================================================
# Pure helper: normalize_pr_number
# =============================================================================


def test_normalize_pr_number_accepts_bare_digits():
    assert era.normalize_pr_number('877') == '#877'


def test_normalize_pr_number_accepts_hash_prefixed():
    assert era.normalize_pr_number('#877') == '#877'


def test_normalize_pr_number_strips_surrounding_whitespace():
    assert era.normalize_pr_number('  #42 ') == '#42'


def test_normalize_pr_number_rejects_non_numeric():
    import pytest

    with pytest.raises(ValueError):
        era.normalize_pr_number('abc')


# =============================================================================
# Pure helper: fill_pending_token
# =============================================================================


def test_fill_pending_token_replaces_quoted_sentinel():
    text = '    "check": "PR-PENDING",\n'
    new_text, count = era.fill_pending_token(text, '#901')
    assert count == 1
    assert '"PR-PENDING"' not in new_text
    assert '"#901"' in new_text


def test_fill_pending_token_counts_multiple_sites():
    text = '"a": "PR-PENDING", "b": "PR-PENDING"'
    new_text, count = era.fill_pending_token(text, '#5')
    assert count == 2
    assert 'PR-PENDING' not in new_text


def test_fill_pending_token_leaves_concrete_number_untouched():
    text = '    "check": "#877",\n'
    new_text, count = era.fill_pending_token(text, '#901')
    assert count == 0
    assert new_text == text


def test_fill_pending_token_ignores_unquoted_prose_mentions():
    # A comment mention of PR-PENDING (no surrounding double quotes) is not a map
    # value and must never be rewritten.
    text = '# PR-PENDING is the sentinel\n"check": "#877"\n'
    new_text, count = era.fill_pending_token(text, '#901')
    assert count == 0
    assert new_text == text


# =============================================================================
# Orchestration: run() over audit.py + test mirror
# =============================================================================


def test_run_fills_pending_in_lock_step(tmp_path, capsys):
    audit, test = _seed_worktree(tmp_path, _AUDIT_WITH_PENDING, _TEST_WITH_PENDING)

    rc = era.run(pr_number='#901', worktree_path=str(tmp_path))

    assert rc == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert 'filled_count: 2' in out
    assert 'skipped: false' in out
    # both files rewritten in lock-step
    audit_text = audit.read_text(encoding='utf-8')
    test_text = test.read_text(encoding='utf-8')
    assert '"PR-PENDING"' not in audit_text
    assert '"PR-PENDING"' not in test_text
    assert '"#901"' in audit_text
    assert '"#901"' in test_text
    # the concrete #877 on the sibling check is preserved
    assert '"#877"' in audit_text
    # the unquoted comment mention is preserved verbatim
    assert '# PR-PENDING is the finalize-resolved sentinel' in audit_text


def test_run_accepts_bare_pr_number(tmp_path, capsys):
    audit, _ = _seed_worktree(tmp_path, _AUDIT_WITH_PENDING, _TEST_WITH_PENDING)

    rc = era.run(pr_number='901', worktree_path=str(tmp_path))

    assert rc == 0
    assert '"#901"' in audit.read_text(encoding='utf-8')
    assert 'pr_number: #901' in capsys.readouterr().out


def test_run_no_op_when_token_absent(tmp_path, capsys):
    audit_text = 'CHECK_ERA = {"check": "#100"}\n'
    audit, test = _seed_worktree(tmp_path, audit_text, 'assert True\n')

    rc = era.run(pr_number='#5', worktree_path=str(tmp_path))

    assert rc == 0
    out = capsys.readouterr().out
    assert 'skipped: true' in out
    assert 'filled_count: 0' in out
    # files are untouched
    assert audit.read_text(encoding='utf-8') == audit_text


def test_run_is_idempotent(tmp_path, capsys):
    _seed_worktree(tmp_path, _AUDIT_WITH_PENDING, _TEST_WITH_PENDING)

    first = era.run(pr_number='#901', worktree_path=str(tmp_path))
    capsys.readouterr()  # drain
    second = era.run(pr_number='#901', worktree_path=str(tmp_path))

    assert first == 0
    assert second == 0
    out = capsys.readouterr().out
    # the second run finds no sentinel to resolve
    assert 'skipped: true' in out
    assert 'filled_count: 0' in out


def test_run_errors_on_bad_pr_number(tmp_path, capsys):
    _seed_worktree(tmp_path, _AUDIT_WITH_PENDING, _TEST_WITH_PENDING)

    rc = era.run(pr_number='not-a-number', worktree_path=str(tmp_path))

    assert rc == 1
    assert 'status: error' in capsys.readouterr().out


def test_run_errors_on_missing_target_file(tmp_path, capsys):
    # Seed only the audit.py; the test mirror is missing.
    audit = tmp_path / _AUDIT_REL
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(_AUDIT_WITH_PENDING, encoding='utf-8')

    rc = era.run(pr_number='#901', worktree_path=str(tmp_path))

    assert rc == 1
    out = capsys.readouterr().out
    assert 'status: error' in out
    # a missing file aborts BEFORE any write — the present file is left untouched
    assert '"PR-PENDING"' in audit.read_text(encoding='utf-8')


def test_main_run_wires_args(tmp_path, capsys):
    _seed_worktree(tmp_path, _AUDIT_WITH_PENDING, _TEST_WITH_PENDING)

    rc = era.main(['run', '--plan-id', 'p16', '--pr-number', '#901', '--worktree-path', str(tmp_path)])

    assert rc == 0
    assert 'filled_count: 2' in capsys.readouterr().out
