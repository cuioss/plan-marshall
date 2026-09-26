# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _PEER_STEP,
    _SECURITY_STEP,
    _mem,
    _restore_patched_seams,
)

# =============================================================================
# (d) The protected population is derived from step metadata, not a step id
# =============================================================================


def test_population_discriminator_reads_real_frontmatter(plan_context):
    """``persona: persona-security-expert`` is what puts a step in the class — read live.

    No stubbing: this reads the two real standards docs. It is the anchor the
    stubbed test below depends on — if the discriminator ever stops matching the
    shipped frontmatter, this fails first and names why.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_is_security_class_step'`` — the pre-fix population was the hardcoded step id
    ``'finalize-step-security-audit'`` passed into ``_apply_code_step_inactive``.
    """
    assert _mem._is_security_class_step(_SECURITY_STEP) is True
    # The structural peer declares no ``persona`` key at all — it is NOT protected,
    # which is what keeps the out-of-scope simplify gate out of this class.
    assert _mem._is_security_class_step(_PEER_STEP) is False
    # An external bundle:skill step has no project-local source and is never in the class.
    assert _mem._is_security_class_step('plan-marshall:plan-retrospective') is False
