#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end regression coverage: an orchestrated plan spec routes on its WHOLE body.

This module is deliberately distinct from ``test_planning_lane.py``. That module
unit-tests the pure helpers (``scope_estimate_from_request_pure``,
``_read_request_body``, ``_distinct_paths``). This one drives the **command entry
points** — ``cmd_scope_estimate_heuristic`` and ``cmd_planning_lane_route`` —
against a ``request.md`` fixture shaped like a real ingested orchestrator plan
spec, so the regression is pinned at the surface phase-1-init actually calls.

The defect being regressed
--------------------------

``request.md`` embeds an ingested orchestrator plan spec verbatim under
``## Original Input``, and that spec legitimately carries its own ``## ``
headings. A section-scoped read terminated the section at the spec's first
nested heading, so the router scored only the preamble — a title, an ``epic:``
line, and the plan-spec template's blockquote citation of a governing document.
The one path token in that preamble is a **citation**, never a target, so a
seven-target plan could score ``surgical`` on the strength of boilerplate.

Every fixture below is built so the truncated reading and the whole-body reading
give **different answers**, which is what makes these assertions regressions
rather than restatements.

Scenarios
---------

1. ``test_orchestrated_spec_with_many_paths_and_glob_scores_single_module`` —
   the spec's dropped region names more than three distinct paths and a glob.
2. ``test_absent_request_declares_unknown_and_routes_deep`` — an unscoreable
   body yields a declared unknown that fires S2 and resolves ``deep``
   (fail-closed).
3. ``test_bare_filename_is_excluded_from_the_count_by_the_counter_not_the_reader``
   — the bare-filename exclusion is a counter decision, asserted as intended.

No ``conftest.py`` is introduced and no fixture code is shared with
``test_planning_lane.py``; the helpers below are local to this module.
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
# `single_module` for some unrelated reason. That keeps each assertion below
# attributable to the read seam.
_CITATION = 'persona-marshall-orchestrator/standards/orchestration-model.md'

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


def test_orchestrated_spec_with_many_paths_and_glob_scores_single_module(plan_context):
    """An orchestrated spec with N>3 paths and a glob bands single_module, not surgical.

    The regression, stated as the two readings of one file:

    - truncated  -> 1 path (the boilerplate citation), no glob -> ``surgical``
    - whole body -> 5 distinct paths and a glob marker         -> ``single_module``

    Both the band and ``distinct_path_count`` are asserted. The count is the
    falsifiable half: a band alone could come out right for the wrong reason
    (the glob short-circuit fires before any counting), so pinning the count
    proves the scored text actually reached the surface list rather than merely
    tripping the fan-out marker.
    """
    plan_dir = plan_context.plan_dir_for('plrb-many-paths')
    _write_orchestrated_request(plan_dir, _MANY_PATHS_REGION)
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-many-paths', persist=True))

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'single_module'
    assert result['scope_resolved'] is True
    # 4 explicit targets + the boilerplate citation. The glob entry contributes
    # the fan-out marker but no path.
    assert result['distinct_path_count'] == 5, sorted(result['distinct_paths'])
    assert _CITATION in result['distinct_paths']
    assert (
        'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py'
        in result['distinct_paths']
    )
    # The persisted value is what the router's S2 signal later reads.
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'single_module'


# =============================================================================
# Scenario 2 — an unscoreable body declares unknown and fails closed to deep
# =============================================================================


def test_absent_request_declares_unknown_and_routes_deep(plan_context):
    """An unscoreable body yields a DECLARED UNKNOWN and routes deep, not a band.

    Runs the real phase-1-init order: classify-and-persist, then route. The
    unknown must be distinguishable **on the return payload** — asserting only
    that "some band came back" is exactly the blindness this plan removes, so
    ``scope_resolved`` is asserted alongside the value.

    Fail-closed direction matters as much as the label: ``none`` is a
    deep-biasing S2 value, so a request nobody could score widens the lane
    instead of narrowing it.
    """
    plan_dir = plan_context.plan_dir_for('plrb-absent-request')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_references(plan_dir)
    _write_status(plan_dir)
    # No request.md is written at all.

    scope_result = cmd_scope_estimate_heuristic(
        _scope_args('plrb-absent-request', persist=True)
    )

    assert scope_result['scope_estimate'] == 'none'
    assert scope_result['scope_resolved'] is False, (
        'the unknown must be distinguishable on the payload, not inferred from the label'
    )
    assert scope_result['distinct_path_count'] == 0

    route_result = cmd_planning_lane_route(_route_args('plrb-absent-request'))

    assert route_result['status'] == 'success'
    assert route_result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in route_result['fired_signals'], (
        'the declared unknown must fire S2 itself, not merely ride S1/S5 to deep'
    )
    assert route_result['signals']['scope_estimate'] == 'none'


def test_empty_request_file_declares_unknown(plan_context):
    """A present-but-empty request.md is unscoreable too, and declares the unknown.

    Distinct from the absent-file case above: the file exists and reads cleanly,
    so the emptiness is a property of the content rather than of the filesystem.
    Both must reach the same declared unknown.
    """
    plan_dir = plan_context.plan_dir_for('plrb-empty-request')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text('', encoding='utf-8')
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-empty-request', persist=True))

    assert result['scope_estimate'] == 'none'
    assert result['scope_resolved'] is False


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


def test_bare_filename_is_excluded_from_the_count_by_the_counter_not_the_reader(
    plan_context,
):
    """A bare filename contributes zero to the count — the DELIBERATE, settled exclusion.

    This is NOT an accidental pin of a defect. ``_PATH_RE`` requires a directory
    separator by design, settled in this plan's D1/D2 investigation: a bare
    filename cannot be resolved to a repo location without the directory
    discovery this module is defined to exclude, and matching bare ``word.word``
    tokens would sweep in ordinary prose (``e.g.``, version numbers,
    sentence-final abbreviations). The resulting under-count biases toward the
    WIDER band, which is the safe direction.

    What makes this a regression rather than a restatement is *where* the
    exclusion happens. Before the whole-body read, a bare filename below a
    nested heading was uncounted for an entirely different reason — the reader
    never saw it — and the two causes were indistinguishable from the outside.
    The count moving from 1 to 3 proves the reader now reaches the surface list,
    while the bare names staying out of ``distinct_paths`` proves the counter,
    not the reader, is what excludes them.
    """
    plan_dir = plan_context.plan_dir_for('plrb-bare-filename')
    _write_orchestrated_request(plan_dir, _BARE_FILENAME_REGION)
    _write_references(plan_dir)

    result = cmd_scope_estimate_heuristic(_scope_args('plrb-bare-filename', persist=True))

    counted = set(result['distinct_paths'])
    # The reader reached the surface list: both directory-qualified targets are in.
    assert 'pkg/alpha/target_one.py' in counted
    assert 'pkg/beta/target_two.py' in counted
    # The counter excluded both bare names, though the reader delivered them.
    assert 'retro_sections.py' not in counted
    assert 'agents.md' not in counted
    # Citation + two qualified targets. Four names were listed; three are paths.
    assert result['distinct_path_count'] == 3, sorted(counted)
    # Three distinct paths and no glob still reads as surgical.
    assert result['scope_estimate'] == 'surgical'
    assert result['scope_resolved'] is True
