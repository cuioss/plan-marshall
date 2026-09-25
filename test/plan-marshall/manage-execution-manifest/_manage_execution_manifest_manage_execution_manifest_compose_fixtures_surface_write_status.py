#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import DEFAULT_PHASE_6_STEPS


def _phase_6_with_every_commit_push_gate() -> str:
    """Candidate CSV carrying all three steps ``commit_push_disabled`` can drop."""
    steps = list(DEFAULT_PHASE_6_STEPS)
    insert_at = steps.index('push')
    for extra in ('pre-push-quality-gate', 'pre-submission-self-review'):
        if extra not in steps:
            steps.insert(insert_at, extra)
    return ','.join(steps)
