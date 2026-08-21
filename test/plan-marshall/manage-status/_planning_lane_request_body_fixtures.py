#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``planning lane request body`` test module.

Holds the module-level loads, constants and helpers it uses, so
the module itself carries the import and not the preamble.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_request_body'
)


cmd_scope_estimate_heuristic = _mod.cmd_scope_estimate_heuristic


cmd_planning_lane_route = _mod.cmd_planning_lane_route


# =============================================================================
# Local fixture authoring (module-local by contract — nothing shared)
# =============================================================================

# The plan-spec template's boilerplate citation. It is the ONLY path token in the
# preamble, and it is a citation of a governing document — never a work target.
# The preamble is deliberately free of markdown bold and of any glob marker, so
# the truncated reading lands on `surgical` (1 path, no glob) rather than on
# `single_module` for some unrelated reason. That keeps each assertion
# attributable to the read seam.
_CITATION = 'persona-plan-orchestrator/standards/orchestration-model.md'


_SPEC_PREAMBLE = (
    '# PLAN-102: Route an orchestrated spec on its whole body\n'
    '\n'
    'epic: truthful-signals\n'
    'workstream: WS-01\n'
    '\n'
    '> Staged plan spec, one shippable unit of work. See\n'
    f'> `{_CITATION}` for the tier and hand-off contract.\n'
)


def _write_orchestrated_request(plan_dir: Path, dropped_region: str) -> None:
    """Author a ``request.md`` holding an ingested spec under ``## Original Input``.

    ``dropped_region`` is the part of the spec that begins at its first nested
    ``## `` heading — precisely the text a section-scoped read discards. There is
    no ``## Clarified Request`` section: the scope heuristic runs at
    phase-1-init, before refine authors one.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request: Route an orchestrated spec on its whole body\n'
        '\n'
        f'plan_id: {plan_dir.name}\n'
        'source: description\n'
        '\n'
        '## Original Input\n'
        '\n'
        f'{_SPEC_PREAMBLE}'
        '\n'
        f'{dropped_region}'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_references(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main'}), encoding='utf-8'
    )


def _write_marshal(fixture_dir: Path) -> None:
    """Write the minimal marshal.json every route-level fixture below relies on.

    Written explicitly rather than relying on the file's absence: S4 reads
    ``plan.phase-2-refine.compatibility`` and the gate reads
    ``plan.phase-1-init.deep_lane``, so an absent file would leave both route
    verdicts depending on default-resolution behaviour instead of on stated
    inputs. ``deprecation`` keeps S4 quiet and ``auto`` lets the signal set decide,
    which is what makes each lane assertion attributable to the band alone.
    """
    (fixture_dir / 'marshal.json').write_text(
        json.dumps(
            {
                'plan': {
                    'phase-1-init': {'deep_lane': 'auto'},
                    'phase-2-refine': {'compatibility': 'deprecation'},
                }
            },
            indent=2,
        ),
        encoding='utf-8',
    )


def _write_status(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


def _scope_args(plan_id: str, *, persist: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, persist=persist)


def _route_args(plan_id: str, *, persist: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, lane_override=None, persist=persist)


# =============================================================================
# Scenario 1 — many paths plus a glob, all below the first nested heading
# =============================================================================

# Four explicit repo-relative targets plus a glob marker, every one of them
# living below `## Objective` where the truncating read could never reach.
# `marketplace/bundles/*/plugin.json` supplies the glob without adding a path:
# `_PATH_RE` requires a directory separator between word characters, so the `*`
# segment prevents it from matching as a path.
_MANY_PATHS_REGION = (
    '## Objective\n'
    '\n'
    'Make the router score the request rather than its preamble.\n'
    '\n'
    '## Deliverables\n'
    '\n'
    '1. Fix the read seam.\n'
    '2. Settle the counter.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py`\n'
    '- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md`\n'
    '- `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md`\n'
    '- `test/plan-marshall/manage-status/test_planning_lane.py`\n'
    '- every `marketplace/bundles/*/plugin.json` in the tree\n'
)


# =============================================================================
# Scenario 2 — a bold-saturated spec with exactly three paths stays surgical
# =============================================================================

# A realistically bold-saturated orchestrated spec whose whole body carries
# exactly THREE distinct paths — the preamble citation plus TWO directory-qualified
# targets — and no fan-out marker. Bold is applied to headings, labels and the path
# list entries, the shapes an orchestrator spec actually uses, because a bare `**`
# alternative in `_GLOB_RE` matched every one of them.
_BOLDED_TWO_TARGET_REGION = (
    '## Objective\n'
    '\n'
    '**Make the band scale-truthful.** The sensor must stop reading **bold** prose\n'
    'as a glob, because the marker check short-circuits **ahead of** the count.\n'
    '\n'
    '## Deliverables\n'
    '\n'
    '1. **Tighten the marker** so it requires path adjacency.\n'
    '2. **Extend the band** with a real large band.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- **`pkg/alpha/one.py`** — the sensor\n'
    '- **`pkg/beta/two.py`** — its caller\n'
)


# =============================================================================
# Scenario 3 — a bolded spec naming ten paths is large, and must route deep
# =============================================================================

# The live reproduction: a bold-saturated spec naming TEN directory-qualified
# targets and NO fan-out marker, so the band is decided purely by the path count
# crossing the multi_module floor.
_BOLDED_TEN_PATH_REGION = (
    '## Objective\n'
    '\n'
    '**Sweep the tier value across the tree.** Ten modules are **in scope** here.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    + ''.join(f'- **`pkg/mod{i}/file{i}.py`** — target {i}\n' for i in range(10))
)


# =============================================================================
# Scenario 4 — a genuine glob is the ONLY fan-out signal, and still widens
# =============================================================================

# One counted path (the preamble citation) and one genuine `test/**` glob. Under
# the pre-fix table a real glob banded `single_module` — narrow — so this shape
# routed light with a minimal posture despite declaring an unbounded file set.
_REAL_GLOB_ONLY_REGION = (
    '## Objective\n'
    '\n'
    'Rewrite the fixtures wholesale.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- everything under `test/plan-marshall/manage-status/**`\n'
)


# =============================================================================
# Scenario 3 — the bare-filename exclusion is a COUNTER decision
# =============================================================================

# Two real repo-relative targets and two bare filenames, all below the first
# nested heading. The bare names carry no directory separator.
_BARE_FILENAME_REGION = (
    '## Objective\n'
    '\n'
    'Rewrite retro_sections.py and agents.md, and update the two modules below.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- `pkg/alpha/target_one.py`\n'
    '- `pkg/beta/target_two.py`\n'
    '- `retro_sections.py` (named without a directory)\n'
    '- `agents.md` (named without a directory)\n'
)
