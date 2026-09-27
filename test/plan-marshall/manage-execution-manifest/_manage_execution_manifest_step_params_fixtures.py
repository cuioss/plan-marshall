#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``step-params get`` / ``step-params set`` verbs of
manage-execution-manifest.py.

These verbs read/write the plan-local per-step param snapshot the composer
writes into the manifest body (``body[phase].step_params``). ``step-params get``
returns the complete param object for a step in a single call; ``step-params
set`` writes a per-plan override that wins over the marshal.json compose-time
default for subsequent reads. Both operate on the persisted manifest, never on
marshal.json.

Covers:
- ``step-params get`` returns the full snapshotted param object in one call.
- ``step-params set`` writes a per-plan override that round-trips through
  ``step-params get`` and wins over the marshal.json compose-time default.
- The absent-step-id / missing-manifest / invalid-phase error paths.
- The ``lane`` / ``lane_requested`` pair: the snapshot records the EFFECTIVE
  lane, preserving a request that did not bind beside it, so a step present in
  ``phase_6.steps`` never carries a bare ``lane: off``.
"""

import json
from argparse import Namespace
from pathlib import Path

from _execution_manifest_fixtures import fake_lane_blocks
from _manifest_lanes import _IMMUNE_TO_OFF_CLASSES

# Tier 2 direct imports, resolved by (bundle, skill, script).
from conftest import load_script_module

_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_script'
)
cmd_compose = _mem.cmd_compose
cmd_step_params_get = _mem.cmd_step_params_get
cmd_step_params_set = _mem.cmd_step_params_set
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest
get_manifest_path = _mem.get_manifest_path
_denormalize_step_params_for_write = _mem._denormalize_step_params_for_write
_normalize_step_params_block = _mem._normalize_step_params_block

# Quiet down the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None

# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(plan_id: str, phase_6_steps: str | None = None) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=11,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


def _get_ns(plan_id: str, phase: str, step_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, step_id=step_id)


def _set_ns(plan_id: str, phase: str, step_id: str, param: str, value: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, step_id=step_id, param=param, value=value)


def _seed_marshal_with_branch_cleanup_params(fixture_dir: Path) -> None:
    """Write a marshal.json whose phase-6-finalize steps map carries nested params."""
    marshal_path = fixture_dir / 'marshal.json'
    data = {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
                    'default:sonar-roundtrip': {
                        'touched_file_cleanup': 'new_code_only',
                        'do_transition': False,
                        'ce_wait_timeout_seconds': 600,
                    },
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {
                        'pr_merge_strategy': 'squash',
                        'final_merge_without_asking': False,
                        'auto_rebase_threshold': 'no_overlap_only',
                    },
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                }
            }
        }
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


# =============================================================================
# `lane` is the outcome; `lane_requested` is the request
# =============================================================================
#
# A stored `lane` is a REQUEST, and the lane machinery does not always grant it:
# a weakening `off` on a `core` / `derived-state` floor element is neutralized,
# so the element is kept and resolves at its class-default tier while the stored
# value still reads `off`. Snapshotting the request verbatim produced a manifest
# whose two halves disagreed — the step was listed in `phase_6.steps` while its
# `step_params` recorded `lane: off`. The snapshot therefore records the
# EFFECTIVE lane under `lane` and preserves the request under `lane_requested`
# only when the two differ.

#: Canned `lane:` frontmatter blocks for these tests. The shared fixture table
#: supplies the four classes and both tier deviations; `lessons-capture` is added
#: here as the matched negative on the CLASS axis — `prunable`, carrying the
#: `prunable_when` predicate its shipped frontmatter declares and NO declared
#: tier, so it resolves at the class default (`standard`) and its `off` genuinely
#: binds. Neither element's class is restated from memory:
#: `test_the_canned_lane_blocks_agree_with_the_shipped_classification` holds both
#: to the live resolver.
_LANE_BLOCKS: dict[str, dict[str, str]] = {
    **fake_lane_blocks(),
    'lessons-capture': {'class': 'prunable', 'prunable_when': 'linear_change', 'cost_size': 'M'},
}

#: The neutralization case's subject — a genuine floor element, so a weakening
#: `off` on it is ignored and the element is kept at the tier it resolves to.
_FLOOR_LANE_STEP = 'archive-plan'

#: The matched negative — off the floor, so the same `off` binds and drops it.
_OPT_OUT_LANE_STEP = 'lessons-capture'


def _seed_marshal_with_lane_overrides(fixture_dir: Path, lanes: dict[str, str]) -> None:
    """Write a marshal.json whose phase-6 steps map carries per-step ``lane`` overrides.

    ``lanes`` maps a FULL-prefixed key of the seeded candidate set to the ``lane``
    value stored for that step; every other candidate keeps the param object the
    sibling seed helper writes. The candidate set is identical to
    :func:`_seed_marshal_with_branch_cleanup_params`'s, because a marshal.json
    ``steps`` map is the AUTHORITATIVE candidate list (preferred over the
    ``--phase-6-steps`` CSV) and every key in it must resolve to a real step doc.
    """
    steps: dict[str, dict] = {
        'default:push': {},
        'default:create-pr': {},
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
        'default:sonar-roundtrip': {'touched_file_cleanup': 'new_code_only'},
        'default:lessons-capture': {},
        'default:branch-cleanup': {'pr_merge_strategy': 'squash'},
        'default:record-metrics': {},
        'default:archive-plan': {},
    }
    for key, lane in lanes.items():
        steps[key] = {**steps.get(key, {}), 'lane': lane}
    (fixture_dir / 'marshal.json').write_text(
        json.dumps({'plan': {'phase-6-finalize': {'steps': steps}}}), encoding='utf-8'
    )


def _patch_lane_resolution(monkeypatch, posture: str) -> None:
    """Drive the lane pass from the canned block table under ``posture``.

    Both seams are patched through ``monkeypatch`` so each is restored on BOTH
    arms — the element-lane resolver (so the cutoff is exercised without
    depending on the shipped docs' real frontmatter) and the posture read (so the
    profile is the test's variable rather than a fixture's status.json).
    """
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step_id: _LANE_BLOCKS.get(step_id))
    monkeypatch.setattr(_mem, '_read_execution_profile', lambda plan_id: posture)
