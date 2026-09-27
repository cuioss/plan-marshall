#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the compose-time per-step ``execution_tier`` stamping pass.

``_stamp_phase_5_step_execution_tier`` records every FINAL
``phase_5.verification_steps`` entry's ``execution_tier`` (``per_task`` |
``orchestrator``) as a uniform-array record list (``{step_id, tier}`` per step).

**The stamp is ADVISORY, not the routing authority.** The tier derives from TWO
run-config quantities ``manage-architecture``'s ``_lookup_bash_timeout`` reads:
whether the command key has been MEASURED at all, and the adaptive learned build
duration behind ``bash_timeout_seconds`` (``max(timeout_get(command_key, ...),
config.min_timeout)``, floored by the engine's OWN declared outer floor — Maven /
Gradle / npm: 300, pyproject: 330). Every intervening build moves both: the
measured-ness flips once, on a key's first observed run, and the learned duration
keeps moving after that. So a step's tier changes between compose and execute in
ordinary operation, and a compose-time snapshot cannot be a durable routing fact.
``phase-5-execute`` re-resolves the tier LIVE before running each verification
step and routes on that verdict; the stamp serves planning and observability.
``TestStampReflectsALiveResolvedCeilingVerdict`` below pins that volatility with
the production producers.

The FLOOR is what makes the first STAMP truthful rather than optimistic — the
bound can never be reported below what the run will measure against. The
MEASUREMENT is what decides the TIER: ``per_task`` only for a measured command
whose stamp stays within the ceiling, ``orchestrator`` otherwise, so an unmeasured
command fails closed on every engine rather than gambling an unobserved first run
in-leaf. The two are separate axes, and conflating them is precisely the defect
this suite now guards: deriving the tier from the floor let an over-provisioned
pyproject floor empty the leaf's runnable slice entirely.

The contract properties the stamping guarantees:

1. **Totality** — the record list is total over ``verification_steps``: one
   ``{step_id, tier}`` record per input step, in list order, every record carrying
   a resolved tier.
2. **Default per_task** — a built-in canonical-verify step (``verify:{canonical}``)
   resolves its tier via ``architecture resolve``; every OTHER step id (external
   ``project:`` / ``bundle:skill`` step, or a ``verify:{canonical}`` whose canonical
   is unresolvable) AND every resolve failure defaults to ``per_task``. This is the
   PERMISSIVE default, not a safe floor — ``per_task`` is the value that would put a
   long build inline where the host platform auto-backgrounds it and a leaf cannot
   reap it. It is acceptable only because the leaf re-resolves live before running.
3. **Fidelity at the ceiling** — a resolve that reports ``orchestrator`` is stamped
   ``orchestrator``; the stamping pass never downgrades it to ``per_task``.

The record-list form (rather than a keyed map) is dictated by the TOON storage
format: a step id (``verify:quality-gate``) contains a colon, which does NOT
round-trip as a TOON object key (``parse_toon`` mis-splits on the first colon),
whereas a quoted string value inside a uniform array round-trips exactly. The
round-trip regression test at the bottom of this file guards that design choice.

These tests drive the transform functions directly (Tier 2),
mirroring ``test_manage_execution_manifest_compose.py``. No live worktree, git history, or
architecture-resolve subprocess is involved: the resolver is monkeypatched, and the
ceiling-boundary tests obtain their resolve envelope from the REAL production
producers (``_classify_build_executable`` / ``_lookup_bash_timeout`` /
``_compute_execution_tier_fields`` in ``manage-architecture``'s
``_cmd_client_build.py``) rather than a hand-authored resolve-shaped dict literal —
a hand-built fixture is what let the four-field contract drift away from its
consumer unnoticed.
"""

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import run_config

from conftest import load_script_module

# Tier 2 direct imports, resolved by (bundle, skill, script).


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_execution_tier'
)
_core = load_script_module(
    'plan-marshall', 'manage-execution-manifest', '_manifest_core.py', module_name='_core_execution_tier'
)

# The PRODUCTION producers of the four-field execution-tier envelope. The
# ceiling-boundary regressions below assert against the fields these emit, so the
# assertions stay coupled to production rather than to a hand-authored literal.
_arch_build = load_script_module(
    'plan-marshall',
    'manage-architecture',
    '_cmd_client_build.py',
    '_arch_client_build_execution_tier',
)

_stamp = _mem._stamp_phase_5_step_execution_tier
_resolve_step_execution_tier = _mem._resolve_step_execution_tier


@pytest.fixture(autouse=True)
def _clear_arch_resolve_cache():
    """Reset the compose-scoped memos before/after each test.

    Two module-level memos live on the once-loaded module instances, so without a
    per-test reset a prior test's cached value would leak into a later test:

    - ``_invoke_architecture_resolve`` is lru-cached (keyed by ``(argv tuple, plan_id)``)
      and the memo lives on ``_mem``; a prior test's cached resolve would leak into a
      later test reusing the same ``(canonical, plan_id)`` key.
    - ``_manifest_validation._domain_appended_canonicals`` is ``@lru_cache(maxsize=1)``
      over ``discover_all_extensions()``; a prior test's cached domain-seeded canonical
      set would leak into a later test that re-mocks the extension discovery.

    ``cmd_compose`` clears BOTH in production; these direct-seam tests clear them here so
    each exercises its own stub.
    """
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()
    yield
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()


# A fake resolver keyed by canonical — a ceiling-exceeding module verify /
# coverage resolves orchestrator; the fast quality-gate resolves per_task.
_FAKE_TIER_BY_CANONICAL = {
    'quality-gate': 'per_task',
    'module-tests': 'orchestrator',
    'coverage': 'orchestrator',
    'verify': 'orchestrator',
}


def _fake_resolver(canonical: str, plan_id: str) -> str:
    return _FAKE_TIER_BY_CANONICAL.get(canonical, 'per_task')
