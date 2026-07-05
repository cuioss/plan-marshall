#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Execution-profile lane helpers for the execution manifest.

Extracted verbatim from ``manage-execution-manifest.py``: the lane enums and
class→tier table, the frontmatter ``lane:`` block parser, the per-element
override / effective-tier / keep-decision resolvers, and the execution-profile
and cost-size table reads. Log-free and patched by no test; the entry keeps the
patched :func:`_resolve_element_lane` and its callers and re-exports these.
"""

import json
from pathlib import Path

from _manifest_core import _strip_default_prefix
from constants import FILE_STATUS
from file_ops import get_marshal_path, get_plan_dir, read_json

LANE_TIERS = ('minimal', 'auto', 'full')
LANE_OVERRIDES = ('off', 'minimal', 'auto', 'full', 'ask')

# Lattice rank for the ``effective_tier ⊑ posture`` comparison.
_TIER_RANK = {'minimal': 0, 'auto': 1, 'full': 2}

# class → default tier (ext-point-lane-element.md § The closed lane.class enum).
_CLASS_DEFAULT_TIER = {
    'derived-state': 'minimal',
    'core': 'minimal',
    'adversarial': 'auto',
    'prunable': 'auto',
}

# Classes whose weakening (``off``) override is honored but emits a correctness
# warning (§5 — minimal must not SILENTLY drop required derived state).
_WARN_ON_DROP_CLASSES = ('derived-state', 'core')

# Absent posture → full → no lane pruning. This keeps every plan that never set
# an execution profile on the pre-lane composition path (back-compat default).
DEFAULT_EXECUTION_PROFILE = 'full'

# The six-size T-shirt table default (the home is phase-4-plan/standards/
# cost-sizing.md; mirrored here only as the fallback when marshal.json carries no
# override). Kept in sync with manage-config ``_config_defaults.py``.
_DEFAULT_COST_SIZE_TABLE = {
    'XS': '5K', 'S': '25K', 'M': '60K', 'L': '130K', 'XL': '260K', 'XXL': '520K',
}


def _read_frontmatter_lane(path: Path) -> dict[str, str] | None:
    """Parse the nested ``lane:`` frontmatter block from a markdown file.

    A minimal nested-block parser (PyYAML is intentionally avoided): scans the
    first ``---``-fenced block for a top-level ``lane:`` key and collects its
    2-space-indented scalar sub-keys (``class`` / ``tier`` / ``prunable_when`` /
    ``cost_size``) until the block dedents. Returns the sub-key dict, or ``None``
    when the file is missing, has no frontmatter, or declares no ``lane:`` block.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None
    if not text.startswith('---'):
        return None
    lane: dict[str, str] = {}
    in_lane = False
    for line in text.splitlines()[1:]:
        if line.strip() == '---':
            break
        if not in_lane:
            if line.rstrip() == 'lane:':
                in_lane = True
            continue
        if line.startswith('  ') and ':' in line:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            key, _, value = stripped.partition(':')
            lane[key.strip()] = value.strip().strip('"').strip("'")
        else:
            # A dedented (column-0) line ends the lane block.
            break
    return lane or None


def _lane_override_for(step_id: str, overrides: dict[str, dict] | None) -> str | None:
    """Resolve the per-element ``lane`` override from the marshal.json step map.

    The phase-6 candidate ids are bare-normalized; the marshal map keys preserve
    ``default:`` / ``project:`` prefixes, so match on the prefix-stripped key.
    Returns the override value when valid (``off|minimal|auto|full|ask``), else
    ``None``.
    """
    if not overrides:
        return None
    for key, params in overrides.items():
        if not isinstance(params, dict):
            continue
        if _strip_default_prefix(key) == step_id:
            value = params.get('lane')
            if isinstance(value, str) and value in LANE_OVERRIDES:
                return value
    return None


def _effective_lane_tier(lane: dict[str, str], override: str | None) -> tuple[str | None, bool]:
    """Resolve the effective tier per ext-point-lane-element § Per-element resolution.

    Precedence: per-element override ▸ declared ``lane.tier`` ▸ class default.
    Returns ``(effective_tier, is_off)`` where ``effective_tier`` is a lattice
    level, the sentinel ``'ask'``, or ``None`` (undeterminable); ``is_off`` is
    True when an explicit ``off`` override drops the element.
    """
    if override == 'off':
        return None, True
    if override in ('minimal', 'auto', 'full'):
        return override, False
    if override == 'ask':
        return 'ask', False
    declared = lane.get('tier')
    if declared in LANE_TIERS:
        return declared, False
    cls = lane.get('class')
    if cls in _CLASS_DEFAULT_TIER:
        return _CLASS_DEFAULT_TIER[cls], False
    return None, False


def _lane_keep_decision(lane: dict[str, str], override: str | None, posture: str) -> tuple[bool, str | None]:
    """Decide whether an element runs under ``posture`` — returns (keep, warning).

    An element runs iff ``effective_tier ⊑ posture``. An ``off`` override drops
    it (with a correctness warning for a ``derived-state`` / ``core`` floor
    element — honored, never silently). An ``ask`` effective tier keeps the
    element at compose time (the init dialogue owns the per-element prompt).
    """
    effective, is_off = _effective_lane_tier(lane, override)
    if is_off:
        cls = lane.get('class')
        warning = None
        if cls in _WARN_ON_DROP_CLASSES:
            warning = f"override 'off' drops {cls} floor element — honored, but weakening a required element"
        return False, warning
    if effective == 'ask' or effective is None:
        # ask → dialogue-resolved (keep at compose); undeterminable → keep.
        return True, None
    keep = _TIER_RANK[effective] <= _TIER_RANK.get(posture, _TIER_RANK['full'])
    return keep, None


def _read_execution_profile(plan_id: str) -> str:
    """Read the chosen posture from ``status.metadata.execution_profile``.

    Returns ``full`` (the no-prune default) when status.json is absent / malformed
    or carries no valid posture. A malformed-but-present status degrades to the
    default rather than crashing compose (same guard as ``_read_recipe_source``).
    """
    status_path = get_plan_dir(plan_id) / FILE_STATUS
    if not status_path.exists():
        return DEFAULT_EXECUTION_PROFILE
    try:
        status = read_json(status_path, default={})
    except (OSError, json.JSONDecodeError):
        return DEFAULT_EXECUTION_PROFILE
    if isinstance(status, dict):
        metadata = status.get('metadata', {})
        if isinstance(metadata, dict):
            value = metadata.get('execution_profile')
            if value in LANE_TIERS:
                return str(value)
    return DEFAULT_EXECUTION_PROFILE


def _parse_cost_magnitude(raw: str) -> int:
    """Parse a token-magnitude string (``5K`` / ``130K`` / ``520K`` / ``1.3M``) to int.

    Returns ``0`` for an unparseable value (the cost preview degrades gracefully
    rather than crashing).
    """
    from sensible_number import parse_sensible_int
    try:
        return parse_sensible_int(raw)
    except (ValueError, TypeError):
        return 0


def _read_cost_size_token_table() -> dict[str, str]:
    """Read ``plan.phase-5-execute.cost_size_token_table`` (six-size fallback)."""
    marshal_path = get_marshal_path()
    if marshal_path.exists():
        try:
            data = read_json(marshal_path, default={})
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict):
            plan = data.get('plan', {})
            if isinstance(plan, dict):
                execute_block = plan.get('phase-5-execute', {})
                if isinstance(execute_block, dict):
                    table = execute_block.get('cost_size_token_table')
                    if isinstance(table, dict) and table:
                        return table
    return dict(_DEFAULT_COST_SIZE_TABLE)
