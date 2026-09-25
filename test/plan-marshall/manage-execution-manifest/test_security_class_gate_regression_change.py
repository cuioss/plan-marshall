# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_security_class_gate_regression_fixtures import (
    _mem,
    _restore_patched_seams,
)


def test_change_type_is_not_a_parameter_of_the_security_gate(plan_context):
    """Structural pin: the security gate's signature carries no change_type.

    The behavioural tests above can only sample change-type values. This one
    closes the sampling gap — the parameter is absent, so no value can reach the
    gate.

    Pre-fix failure (observed against pre-fix HEAD): ``AttributeError: module
    '_mem_script_security_class_regression' has no attribute
    '_apply_security_class_inactive'. Did you mean: '_apply_security_audit_inactive'?``
    — the pre-fix helper's signature DID carry ``change_type``.
    """
    varnames = _mem._apply_security_class_inactive.__code__.co_varnames
    assert 'change_type' not in varnames
    assert 'affected_files_count' in varnames
    assert 'live_footprint_count' in varnames
