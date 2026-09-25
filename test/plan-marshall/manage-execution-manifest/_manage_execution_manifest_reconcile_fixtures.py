#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest ``reconcile`` subcommand.

The execution manifest is a write-time snapshot: ``compose`` freezes the
phase-6 step list at outline time and ``phase-6-finalize`` consumes it verbatim
much later. A SELF-MODIFYING plan can invalidate its own frozen view in between
— it deletes a finalize step's standards doc and sweeps ``marshal.json``, and
its own already-frozen manifest still names the step.

Before ``reconcile`` the only comparison at finalize entry was
``validate-loadable``, which HARD-ABORTS on any unloadable step. That is the
wrong direction for exactly the population that produces the divergence: it
blocks a self-modifying plan from finalizing its own legitimate work.

``reconcile`` splits the two cases that ``validate-loadable`` conflated, and
that split IS the settled fail-direction:

- unloadable AND gone from live config  → **stale**: the frozen view is merely
  behind, live config agrees the step is gone. Drop it and carry on.
- unloadable AND still in live config    → **broken**: the original motivating
  failure (the doc was deleted without sweeping ``marshal.json``). Still fails
  loud, with the canonical actionable message.

Backfill is the mirror direction and is deliberately NARROW: only a live
candidate that did not exist in the candidate set ``compose`` selected FROM is
owed. A candidate the decision matrix deliberately dropped must NOT be
re-added, which is why ``compose`` now snapshots ``phase_6.candidate_steps``.
Without that snapshot (a manifest frozen before the field existed) backfill is
reported INDETERMINATE rather than guessed.
"""

# ruff: noqa: I001

from pathlib import Path
import json
from argparse import Namespace
from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_reconcile'
)
cmd_compose = _mem.cmd_compose
cmd_reconcile = _mem.cmd_reconcile
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

_mem._log_decision = lambda *a, **kw: None

# ``_emit_decision_log`` shells out to the executor, which no test may depend
# on — but stubbing it to a bare no-op would make emission UNOBSERVABLE, and
# "does a dry run write an audit record?" is exactly a question these tests must
# be able to ask. Record instead of discarding.
_EMITTED: list[tuple[str, str]] = []
_mem._emit_decision_log = lambda plan_id, message, *a, **kw: _EMITTED.append((plan_id, message))


# =============================================================================
# Helpers
# =============================================================================


def _write_marshal(fixture_dir: Path, phase_6_steps: list[str]) -> None:
    """Seed marshal.json with ``phase_6_steps`` as the LIVE candidate set."""
    data: dict = {
        'plan': {'phase-6-finalize': {'steps': {step: {} for step in phase_6_steps}}},
        'build': {},
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(data), encoding='utf-8')


def _reconcile_ns(plan_id: str, apply: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, apply=apply)


def _emitted_for(plan_id: str) -> list[str]:
    """Every decision-log message emitted for ``plan_id`` in this session.

    ``_EMITTED`` is never reset — filtering by plan id is what isolates one
    test from another, so each test that inspects emission MUST use a plan id
    no other test uses.
    """
    return [message for pid, message in _EMITTED if pid == plan_id]


def _seed_manifest(
    plan_id: str,
    frozen: list[str],
    candidate_steps: list[str] | None = None,
) -> None:
    """Write a manifest directly, so the frozen view is exactly ``frozen``.

    Writing it rather than composing it is deliberate: the divergence under
    test is between a manifest frozen EARLIER and config as it is NOW, which a
    single in-test compose cannot produce.
    """
    phase_6: dict = {'steps': list(frozen), 'step_params': dict.fromkeys(frozen)}
    if candidate_steps is not None:
        phase_6['candidate_steps'] = list(candidate_steps)
    write_manifest(
        plan_id,
        {
            'manifest_version': 1,
            'plan_id': plan_id,
            'phase_5': {'early_terminate': False, 'verification_steps': [], 'envelope_count': 1},
            'phase_6': phase_6,
        },
    )


# A step id that resolves to no standards doc — the "deleted doc" stand-in.
GHOST = 'ghost-step-deleted-by-this-plan'
# Two real built-in steps whose standards docs exist in the source tree.
REAL_A = 'push'
REAL_B = 'archive-plan'
