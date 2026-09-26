#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import Namespace
from _manage_execution_manifest_ceremony_finalize_selection_fixtures_surface_module import (
    _phase_6_with_ceremony_steps,
)


def _compose_ns(
    plan_id: str = 'ceremony-test',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps if phase_6_steps is not None else _phase_6_with_ceremony_steps(),
        commit_and_push=commit_and_push,
    )
