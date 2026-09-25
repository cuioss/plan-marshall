#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Namespace

# --- cmd_lanes_preview -------------------------------------------------------


def _lanes_preview_ns(plan_id: str, steps: list[str]) -> Namespace:
    return Namespace(plan_id=plan_id, phase_6_steps=','.join(steps))
