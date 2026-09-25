# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    cmd_compose,
    read_manifest,
)


def test_docs_shaped_candidates_keep_phase_5_and_retain_review_gates(plan_context):
    """A docs-shaped candidate set no longer empties Phase 5 by inference.

    The retired ``docs_only`` row read "no module-tests / coverage role among the
    candidates" as proof the plan was docs-only and cleared Phase 5 on that
    inference. Build necessity is settled by the footprint authority, never by the
    shape of a candidate list, so this input now falls through to the scope row
    and KEEPS its ``quality-gate`` candidate.

    Review gates (automatic-review, sonar-roundtrip) are RETAINED either way, and
    only the legacy 'ci-wait' step ID is defensively narrowed out (against project
    marshal.json files that still list it).
    """
    # Inject legacy ci-wait into candidates to assert defensive narrowing.
    candidates_with_legacy = list(DEFAULT_PHASE_6_STEPS) + ['ci-wait']
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-docs',
            change_type='tech_debt',
            scope_estimate='surgical',
            affected_files_count=3,
            # docs-shaped candidate set: only quality-gate, no module-tests/coverage.
            phase_5_steps='verify:quality-gate',
            phase_6_steps=','.join(candidates_with_legacy),
        )
    )
    assert result is not None and result['rule_fired'] == 'surgical_tech_debt'
    assert result['phase_5']['verification_steps_count'] == 1
    manifest = read_manifest('matrix-docs')
    assert manifest is not None
    # Review gates RETAINED.
    assert 'automatic-review' in manifest['phase_6']['steps']
    assert 'sonar-roundtrip' in manifest['phase_6']['steps']
    # Legacy ci-wait still defensively narrowed out.
    assert 'ci-wait' not in manifest['phase_6']['steps']
