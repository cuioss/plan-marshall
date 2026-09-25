#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _LANE_REPORT_MARSHAL_STEPS,
    create_marshal_json,
)


def _seed_lane_report_marshal(plan_context, steps: dict[str, dict] | None = None) -> None:
    """Write the project-wide declaration channel: marshal.json's phase-6 step map.

    ``nest_in_plan_dir=False`` is the layout ``plan_context`` sets up — it points
    ``MARSHAL_PATH`` at ``fixture_dir/'marshal.json'`` directly, so a nested write
    would land where the script under test never looks.
    """
    create_marshal_json(
        plan_context.fixture_dir,
        config={
            'skill_domains': {'system': {}},
            'system': {'retention': {}},
            'plan': {
                'phase-6-finalize': {
                    'steps': dict(_LANE_REPORT_MARSHAL_STEPS if steps is None else steps),
                },
            },
        },
        nest_in_plan_dir=False,
    )
