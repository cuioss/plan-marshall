# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _LARGE_FOOTPRINT,
    _SECURITY_STEP,
    _capture_decision_log,
    _compose,
    _composed_steps,
    _mem,
    _restore_patched_seams,
    _stub_footprint,
)


def test_a_second_step_declaring_the_persona_inherits_the_treatment(plan_context):
    """Any step declaring the persona gets the identical treatment — no production change.

    The population is derived per compose from each candidate's frontmatter, so a
    future second security-class finalize step is protected by declaring the same
    persona. This is pinned by making an ALREADY-RESOLVABLE candidate
    (``adr-propose``) read as security-class through the frontmatter-read seam —
    the derivation in ``_is_security_class_step`` stays under test, only the file
    read is stubbed — and asserting it receives the same fail-toward-inclusion and
    loud-omission treatment. Using an existing step id keeps the composed manifest
    past the step-resolution and ascending-order gates.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_read_frontmatter_scalar'. Did you mean: '_read_frontmatter_lane'?`` — the
    frontmatter-scalar seam this derivation depends on did not exist at all, and
    the population was a hardcoded step id no second step could join.
    """
    synthetic = 'adr-propose'
    original_reader = _mem._read_frontmatter_scalar

    def _reader(path, key):
        if key == 'persona' and path.stem == synthetic:
            return 'persona-security-expert'
        return original_reader(path, key)

    _mem._read_frontmatter_scalar = _reader

    # Fail toward inclusion: an excluded change type with a real change surface
    # keeps BOTH class members.
    _stub_footprint(_LARGE_FOOTPRINT)
    _capture_decision_log()
    kept = _compose('secclass-synthetic-kept', change_type='verification', affected_files_count=12)
    assert kept['security_class_omitted'] == []
    kept_steps = _composed_steps('secclass-synthetic-kept')
    assert _SECURITY_STEP in kept_steps
    assert synthetic in kept_steps

    # Loud omission: with no change surface, BOTH class members drop and BOTH are
    # named — while the personaless peer is governed by its own separate gate.
    _stub_footprint([])
    captured = _capture_decision_log()
    dropped = _compose('secclass-synthetic-dropped', change_type='feature', affected_files_count=0)
    dropped_steps = {record['step'] for record in dropped['security_class_omitted']}
    assert dropped_steps == {_SECURITY_STEP, synthetic}
    assert all(
        record['reason'] == 'no declared affected files and empty live footprint'
        for record in dropped['security_class_omitted']
    )
    composed = _composed_steps('secclass-synthetic-dropped')
    assert _SECURITY_STEP not in composed
    assert synthetic not in composed
    status_lines = [msg for pid, msg in captured if 'security_class_inactive' in msg]
    assert len(status_lines) == 2
    assert any(synthetic in msg for msg in status_lines)
