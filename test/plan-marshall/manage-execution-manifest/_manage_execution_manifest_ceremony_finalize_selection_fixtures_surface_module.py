#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _CEREMONY_FINALIZE_STEPS,
    DEFAULT_PHASE_6_STEPS,
)


def _phase_6_with_ceremony_steps() -> str:
    """Default phase-6 candidates plus the ceremony-gated finalize steps."""
    steps = list(DEFAULT_PHASE_6_STEPS) + _CEREMONY_FINALIZE_STEPS
    return ','.join(steps)
