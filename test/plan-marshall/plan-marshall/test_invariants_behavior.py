#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit coverage for the smaller ``_invariants`` helpers and capture functions.

``test_invariants.py`` drives the task-graph / task-state / findings-blocking /
pr-title / layer-D surfaces end-to-end. This companion suite covers the
helpers and capture functions that had no direct test reference:

* ``_is_truthy_metadata`` — the bool/str/int coercion used for metadata flags.
* ``_hash_dict`` — the stable, key-order-independent 16-hex drift fingerprint.
* ``is_invariant_blocking_at_phase`` — the frozenset / blocking-at-every /
  informational-only / unknown-scope classification branches.
* ``_capture_main_sha`` / ``_capture_main_dirty`` — git-probe captures.
* ``_capture_worktree_sha`` / ``_capture_worktree_dirty`` — worktree-gated
  captures including the no-path ``None`` contract.
* ``_capture_config_hash`` — the unreachable / parseable / unparseable branches.
* ``_query_pending_count_for_type`` — the ``count`` fallback key and the
  unparseable / unreachable ``None`` contract.
* ``_capture_qgate_open_count`` — the unparseable ``None`` contract.
* ``capture_all`` — the not-applicable and value-``None`` skip branches.

All dependencies that would shell out (``_run_script``, ``git_head``,
``git_dirty_count``, ``parse_toon``) are monkeypatched to deterministic stubs so
each test asserts genuine return-value / branch behaviour, never a smoke check.
"""

from __future__ import annotations

import sys

import pytest

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-marshall', 'phase_handshake.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _invariants as inv  # noqa: E402


# =============================================================================
# _is_truthy_metadata
# =============================================================================


@pytest.mark.parametrize(
    'value,expected',
    [
        (True, True),
        (False, False),
        ('true', True),
        ('True', True),
        ('  TRUE  ', True),
        ('1', True),
        ('yes', True),
        ('false', False),
        ('no', False),
        ('', False),
        ('maybe', False),
        (1, True),
        (5, True),
        (0, False),
        (-1, True),
        (None, False),
        ([], False),
        ({'k': 'v'}, False),
    ],
)
def test_is_truthy_metadata_coercion(value, expected) -> None:
    """Bool/str/int forms coerce per the documented rule; others are falsy."""
    assert inv._is_truthy_metadata(value) is expected


# =============================================================================
# _hash_dict
# =============================================================================


def test_hash_dict_is_16_char_lowercase_hex() -> None:
    """The fingerprint is a 16-char lowercase hex SHA256 prefix."""
    h = inv._hash_dict({'a': 1, 'b': [2, 3]})
    assert isinstance(h, str)
    assert len(h) == 16
    assert all(c in '0123456789abcdef' for c in h)


def test_hash_dict_is_key_order_independent() -> None:
    """Recursive key-sorting makes insertion order irrelevant."""
    assert inv._hash_dict({'a': 1, 'b': 2}) == inv._hash_dict({'b': 2, 'a': 1})


def test_hash_dict_distinguishes_distinct_payloads() -> None:
    """Different payloads must produce different fingerprints."""
    assert inv._hash_dict({'a': 1}) != inv._hash_dict({'a': 2})


def test_hash_dict_handles_non_dict_payload() -> None:
    """The helper hashes any JSON-serializable payload (default=str fallback)."""
    assert inv._hash_dict('plain string') == inv._hash_dict('plain string')
    assert inv._hash_dict('one') != inv._hash_dict('two')


# =============================================================================
# is_invariant_blocking_at_phase
# =============================================================================


def test_blocking_frozenset_scope_blocks_only_at_named_phase() -> None:
    """``main_sha`` (frozenset({'5-execute'})) blocks at 5-execute only."""
    assert inv.is_invariant_blocking_at_phase('main_sha', '5-execute') is True
    for planning in ('1-init', '2-refine', '3-outline', '4-plan'):
        assert inv.is_invariant_blocking_at_phase('main_sha', planning) is False


def test_blocking_at_every_boundary_always_true() -> None:
    """A ``blocking_at_every_boundary`` invariant blocks at every phase."""
    for phase in ('1-init', '3-outline', '5-execute', '6-finalize'):
        assert inv.is_invariant_blocking_at_phase('references_valid', phase) is True


def test_unmapped_invariant_defaults_to_blocking() -> None:
    """An invariant absent from the scope map fails safe to blocking."""
    assert inv.is_invariant_blocking_at_phase('totally-unmapped', '5-execute') is True


def test_informational_only_scope_never_blocks(monkeypatch) -> None:
    """An ``informational_only`` scope is never blocking at any phase."""
    monkeypatch.setitem(inv.INVARIANT_BLOCKING_SCOPE, 'temp_info', 'informational_only')
    assert inv.is_invariant_blocking_at_phase('temp_info', '5-execute') is False
    assert inv.is_invariant_blocking_at_phase('temp_info', '1-init') is False


def test_unknown_scope_value_fails_safe_to_blocking(monkeypatch) -> None:
    """An unrecognized scope value fails safe to blocking (misconfig guard)."""
    monkeypatch.setitem(inv.INVARIANT_BLOCKING_SCOPE, 'temp_weird', 'bogus_scope')
    assert inv.is_invariant_blocking_at_phase('temp_weird', '5-execute') is True


# =============================================================================
# _capture_main_sha / _capture_main_dirty
# =============================================================================


def test_capture_main_sha_returns_git_head(monkeypatch) -> None:
    """The capture returns whatever ``git_head`` reports for the repo root."""
    monkeypatch.setattr(inv, 'git_head', lambda _root: 'deadbeefcafe')
    assert inv._capture_main_sha('p', {}, '5-execute') == 'deadbeefcafe'


def test_capture_main_dirty_returns_git_dirty_count(monkeypatch) -> None:
    """The capture returns the integer dirty-file count for the repo root."""
    monkeypatch.setattr(inv, 'git_dirty_count', lambda _root: 7)
    assert inv._capture_main_dirty('p', {}, '5-execute') == 7


# =============================================================================
# _capture_worktree_sha / _capture_worktree_dirty
# =============================================================================


def test_capture_worktree_sha_none_without_path() -> None:
    """No ``worktree_path`` → None (not-applicable column)."""
    assert inv._capture_worktree_sha('p', {}, '5-execute') is None
    assert inv._capture_worktree_sha('p', {'worktree_path': ''}, '5-execute') is None


def test_capture_worktree_sha_uses_path_when_present(monkeypatch) -> None:
    """A populated ``worktree_path`` is passed to ``git_head``."""
    seen = {}

    def _git_head(arg):
        seen['arg'] = arg
        return 'wt-sha-1234'

    monkeypatch.setattr(inv, 'git_head', _git_head)
    result = inv._capture_worktree_sha('p', {'worktree_path': '/tmp/wt'}, '5-execute')
    assert result == 'wt-sha-1234'
    assert seen['arg'] == '/tmp/wt'


def test_capture_worktree_dirty_none_without_path() -> None:
    """No ``worktree_path`` → None for the dirty-count capture too."""
    assert inv._capture_worktree_dirty('p', {}, '5-execute') is None


def test_capture_worktree_dirty_uses_path_when_present(monkeypatch) -> None:
    """A populated ``worktree_path`` is passed to ``git_dirty_count``."""
    monkeypatch.setattr(inv, 'git_dirty_count', lambda arg: 0 if arg == '/tmp/wt' else 99)
    assert inv._capture_worktree_dirty('p', {'worktree_path': '/tmp/wt'}, '5-execute') == 0


# =============================================================================
# _capture_config_hash
# =============================================================================


def test_capture_config_hash_none_when_executor_unreachable(monkeypatch) -> None:
    """A ``None`` stdout from ``_run_script`` propagates as ``None``."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: None)
    assert inv._capture_config_hash('p', {}, '5-execute') is None


def test_capture_config_hash_hashes_parsed_toon(monkeypatch) -> None:
    """Parseable config TOON yields a stable 16-hex fingerprint."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nmax_iterations: 5\n')
    h = inv._capture_config_hash('p', {}, '5-execute')
    assert isinstance(h, str)
    assert len(h) == 16


def test_capture_config_hash_changes_with_config(monkeypatch) -> None:
    """Distinct config payloads produce distinct fingerprints (drift sensitivity)."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nmax_iterations: 5\n')
    first = inv._capture_config_hash('p', {}, '5-execute')
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nmax_iterations: 9\n')
    second = inv._capture_config_hash('p', {}, '5-execute')
    assert first != second


def test_capture_config_hash_falls_back_to_raw_on_parse_failure(monkeypatch) -> None:
    """When ``parse_toon`` raises, the raw stripped stdout is hashed instead."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: '  raw config text  ')

    def _raise(_text):
        raise ValueError('unparseable')

    monkeypatch.setattr(inv, 'parse_toon', _raise)
    h = inv._capture_config_hash('p', {}, '5-execute')
    assert h == inv._hash_dict('raw config text')


# =============================================================================
# _query_pending_count_for_type
# =============================================================================


def test_query_pending_count_none_when_unreachable(monkeypatch) -> None:
    """Executor unreachable → ``None`` (not-applicable contract)."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: None)
    assert inv._query_pending_count_for_type('p', 'sonar-issue') is None


def test_query_pending_count_reads_filtered_count(monkeypatch) -> None:
    """The primary ``filtered_count`` field drives the returned count."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nfiltered_count: 4\n')
    assert inv._query_pending_count_for_type('p', 'lint-issue') == 4


def test_query_pending_count_falls_back_to_count_key(monkeypatch) -> None:
    """When ``filtered_count`` is absent, the ``count`` key is used instead."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\ncount: 6\n')
    assert inv._query_pending_count_for_type('p', 'build-error') == 6


def test_query_pending_count_none_when_no_count_field(monkeypatch) -> None:
    """Neither ``filtered_count`` nor ``count`` present → ``None``."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nother: x\n')
    assert inv._query_pending_count_for_type('p', 'pr-comment') is None


# =============================================================================
# _capture_qgate_open_count
# =============================================================================


def test_capture_qgate_open_count_none_when_count_field_missing(monkeypatch) -> None:
    """No ``filtered_count`` in the qgate list output → ``None``."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nfoo: bar\n')
    assert inv._capture_qgate_open_count('p', {}, '5-execute') is None


def test_capture_qgate_open_count_reads_filtered_count(monkeypatch) -> None:
    """A numeric ``filtered_count`` is returned as an int for non-init phases."""
    monkeypatch.setattr(inv, '_run_script', lambda _args: 'status: success\nfiltered_count: 2\n')
    assert inv._capture_qgate_open_count('p', {}, '3-outline') == 2


# =============================================================================
# capture_all skip branches
# =============================================================================


def test_capture_all_skips_non_applicable_invariant(monkeypatch) -> None:
    """An invariant whose ``applies_fn`` is False is omitted from the result."""
    narrowed = [('worktree_sha', inv._worktree_in_use, inv._capture_worktree_sha)]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    # No worktree_path → _worktree_in_use is False → invariant skipped entirely.
    assert inv.capture_all('p', {}, '3-outline') == {}


def test_capture_all_skips_none_capture_value(monkeypatch) -> None:
    """An applicable invariant returning ``None`` is omitted (empty column)."""
    narrowed = [('worktree_sha', inv._always, inv._capture_worktree_sha)]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    # applies_fn is _always (True) but the capture returns None (no path) → skip.
    assert inv.capture_all('p', {}, '5-execute') == {}


def test_capture_all_includes_applicable_non_none_value(monkeypatch) -> None:
    """A applicable invariant with a real value is included in the result."""
    monkeypatch.setattr(inv, 'git_head', lambda _root: 'sha-xyz')
    narrowed = [('main_sha', inv._always, inv._capture_main_sha)]
    monkeypatch.setattr(inv, 'INVARIANTS', narrowed)
    captured = inv.capture_all('p', {}, '5-execute')
    assert captured == {'main_sha': 'sha-xyz'}
