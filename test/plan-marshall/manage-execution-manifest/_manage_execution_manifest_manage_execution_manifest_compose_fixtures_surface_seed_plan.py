#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Namespace


def _lane_report_ns(plan_id: str | None = None) -> Namespace:
    """Preview namespace whose ``plan_id`` is OPTIONAL — ``None`` is the no-plan read."""
    return Namespace(plan_id=plan_id, phase_6_steps=None)


def _lane_report_row(result: dict, step: str) -> dict:
    """Return the one ``lane_report`` row for ``step``.

    Asserts the row is unique rather than taking the first match: a duplicated row
    would let a later assertion pass against whichever copy happened to be first.
    """
    rows: list[dict] = [row for row in result['lane_report'] if row['step'] == step]
    assert len(rows) == 1, f'expected exactly one lane_report row for {step}, got {len(rows)}'
    return rows[0]
