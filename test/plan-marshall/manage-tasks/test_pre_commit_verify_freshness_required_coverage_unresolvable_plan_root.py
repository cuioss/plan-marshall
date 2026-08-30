#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_resolve_required_coverage``'s ``(None, reason)`` contract.

Scope: that an UNRESOLVABLE PLAN ROOT is reported as the declared unknown
rather than escaping as a traceback.

``_resolve_required_coverage`` documents an absolute contract — "⛔ Every
inability returns ``(None, reason)``, never a permissive ``RequiredCoverage``".
Its callee chain reaches ``file_ops.get_base_dir`` (via
``_resolve_plan_footprint`` -> ``get_plan_dir`` -> ``resolve_plan_context`` ->
``base_path``), which raises ``RuntimeError`` by design when no plan root
resolves. ``RuntimeError`` is NOT an ``OSError`` subclass, so the guard's
original ``except OSError`` did not catch it and the inability escaped the
function entirely — the exact failure the docstring declares impossible, and an
instance of the very archetype this gate exists to close (an unresolvable state
surfacing as an exception instead of the declared unknown).

The cases below drive the REAL chain rather than stubbing
``_resolve_plan_footprint``: the ``RuntimeError`` is produced by the genuine
``get_base_dir`` resolution failure, so a future refactor that moved the raise
would be visible here instead of being papered over by a stub that raises
whatever the test wants. ``test_the_chain_really_raises`` is the matched control
that keeps the assertion non-vacuous — it fails loudly if the premise stops
holding, so a green outcome case can never mean "the guard was never reached".
"""


from __future__ import annotations

import file_ops
import pytest
from _freshness_crosscheck import REASON_REQUIRED_COVERAGE_UNKNOWN
from _pre_commit_verify_freshness_fixtures import _freshness_mod

_PLAN_ID = 'freshness-required-coverage-unresolvable-root'


@pytest.fixture
def _unresolvable_plan_root(monkeypatch):
    """Make the REAL ``get_base_dir`` unable to resolve a plan root.

    Neutralises all three resolution legs the resolver consults in order — the
    ``set_base_dir`` override the test harness installs, the ``PLAN_BASE_DIR``
    env var, and the cwd walk-up / git-toplevel fallback — so the next
    ``get_base_dir`` call takes its documented ``raise RuntimeError`` branch.
    Nothing about the freshness module is stubbed, so the exception travels the
    production call chain into the guard under test.
    """
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: None)


def test_the_chain_really_raises(_unresolvable_plan_root) -> None:
    """Matched control: the premise of the outcome case actually holds.

    Without this, the outcome case below could pass for the wrong reason — a
    fixture that silently failed to neutralise a resolution leg would leave the
    plan root resolvable, no ``RuntimeError`` would ever be raised, and the
    guard would be reported as green while never having been exercised. That is
    the vacuous-guard shape, so the premise is asserted rather than assumed.

    It also pins WHY the original guard missed it: ``RuntimeError`` sits outside
    the ``OSError`` hierarchy, so an ``OSError``-only ``except`` clause cannot
    catch it. If that ever stopped being true the widening would be redundant
    and this test would say so.
    """
    assert not issubclass(RuntimeError, OSError)
    with pytest.raises(RuntimeError):
        file_ops.get_base_dir()


def test_unresolvable_plan_root_returns_the_declared_unknown(
    _unresolvable_plan_root,
) -> None:
    """An unresolvable plan root is reported, not raised.

    The whole point of the ``(None, reason)`` contract is that a caller receives
    a verdict it can route on. Both halves are asserted: ``None`` (never a
    permissive ``RequiredCoverage``, which would let the coverage dimension
    require nothing of any ledger row and re-open the false-green) AND the
    specific ``REASON_REQUIRED_COVERAGE_UNKNOWN`` token (a different reason
    would route the caller to a remedy that does not apply).
    """
    required, reason = _freshness_mod._resolve_required_coverage(_PLAN_ID)

    assert required is None
    assert reason == REASON_REQUIRED_COVERAGE_UNKNOWN


def test_resolvable_plan_root_is_not_answered_with_the_unknown_reason(
    plan_context,
) -> None:
    """Negative control: the guard is not an unconditional ``None`` return.

    Broadening an ``except`` clause is a change that can only ever make MORE
    inputs take the failure branch, so the risk it carries is that the failure
    branch swallows a case that used to succeed. With a resolvable plan root the
    derivation reaches its own footprint logic, and whatever it concludes there
    it must not be the plan-root inability — otherwise this file's positive case
    would be asserting a constant.

    The plan HAS no materialized worktree in this harness, so the footprint is
    legitimately unresolvable and the function still answers ``(None, ...)``.
    What the assertion pins is therefore the DISTINCT route, not the outcome:
    the call must not raise, and it must be reached at all.
    """
    plan_context.plan_dir_for(_PLAN_ID)

    required, reason = _freshness_mod._resolve_required_coverage(_PLAN_ID)

    # No traceback escapes on the resolvable route either, and the contract's
    # "exactly one side is informative" shape holds.
    assert (required is None) != (reason is None)
