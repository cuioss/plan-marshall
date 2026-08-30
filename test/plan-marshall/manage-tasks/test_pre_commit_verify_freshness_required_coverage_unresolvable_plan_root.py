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

The unresolvable case drives the REAL chain rather than stubbing
``_resolve_plan_footprint``: the ``RuntimeError`` is produced by the genuine
``get_base_dir`` resolution failure, so a future refactor that moved the raise
would be visible here instead of being papered over by a stub that raises
whatever the test wants. ``test_the_chain_really_raises`` is the matched control
that keeps the assertion non-vacuous — it fails loudly if the premise stops
holding, so a green outcome case can never mean "the guard was never reached".

Two DIFFERENT results are asserted across the file, and that is what gives the
pair its discriminating power. Widening an ``except`` clause can only ever route
MORE inputs to the failure branch, so the mirror-image risk is a function that
answers the declared unknown UNCONDITIONALLY — and no assertion that the unknown
itself satisfies can detect that.
``test_a_resolvable_footprint_yields_coverage_with_no_reason`` therefore supplies
a footprint the derivation can actually measure and asserts the OTHER side of the
``(required, reason)`` contract: a populated ``RequiredCoverage`` with ``reason is
None``. One input must produce the unknown and the other must not, so a function
that returned the unknown for everything fails here even while it passes above.

Only the footprint seam is supplied for that case, on
``extension_base._resolve_plan_footprint`` — the same seam the build-decision
authority's own tests drive, and the one input whose production resolution needs
a materialized worktree and a live git diff. Everything downstream of it is
production code: the analysis vocabulary, the registered-module enumeration,
``resolve_test_scope`` and ``required_coverage`` all run for real, so the
assertions are on a coverage requirement the shipped derivation computed rather
than on a shape the test handed it.
"""


from __future__ import annotations

import extension_base
import file_ops
import pytest
from _freshness_crosscheck import (
    REASON_REQUIRED_COVERAGE_UNKNOWN,
    RequiredCoverage,
    load_analysis_vocabulary,
)
from _pre_commit_verify_freshness_fixtures import _freshness_mod

_PLAN_ID = 'freshness-required-coverage-unresolvable-root'

#: A footprint the coverage derivation can measure end to end: one ``.py`` file
#: owned by a registered bundle and touching no cross-module build
#: infrastructure. Each of ``required_coverage``'s branches is then decided by a
#: real input rather than defaulted — the module resolves, so ``whole_tree`` is
#: False; the path ends in ``.py``, so the compile and lint analyses join the
#: unconditional test one.
_RESOLVABLE_FOOTPRINT = (
    'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/'
    '_cmd_pre_commit_verify_freshness.py'
)

#: The registered bundle ``_RESOLVABLE_FOOTPRINT`` resolves to (path segment 2
#: under ``marketplace/bundles/``).
_FOOTPRINT_MODULE = 'plan-marshall'


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


def test_a_resolvable_footprint_yields_coverage_with_no_reason(
    plan_context, monkeypatch
) -> None:
    """Negative control: the declared unknown is CONDITIONAL, not the only answer.

    Broadening an ``except`` clause can only ever make MORE inputs take the
    failure branch, so the risk it carries is that the branch swallows a case
    that used to succeed. Detecting that requires an input the function must
    answer with a ``RequiredCoverage`` — an assertion the unknown result itself
    satisfies proves nothing, because a function returning the unknown
    unconditionally would satisfy it too.

    So the requirement is measured for real and BOTH sides of the contract are
    pinned on the informative half: ``reason is None`` (no inability was
    reported) and a ``RequiredCoverage`` whose content matches what the shipped
    derivation computes from this footprint. The content assertions are what stop
    a permissive constant from passing: an empty ``RequiredCoverage`` requires
    nothing of any ledger row, which is the false-green the whole coverage
    dimension exists to close.
    """
    plan_context.plan_dir_for(_PLAN_ID)
    vocabulary, vocabulary_reason = load_analysis_vocabulary()
    assert vocabulary is not None, vocabulary_reason
    monkeypatch.setattr(
        extension_base, '_resolve_plan_footprint', lambda _plan: [_RESOLVABLE_FOOTPRINT]
    )

    required, reason = _freshness_mod._resolve_required_coverage(_PLAN_ID)

    assert reason is None
    assert isinstance(required, RequiredCoverage)
    assert required.modules == frozenset({_FOOTPRINT_MODULE})
    assert required.whole_tree is False
    assert required.analyses == frozenset({vocabulary.test, vocabulary.compile, vocabulary.lint})
