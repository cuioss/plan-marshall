# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    cmd_compose,
    get_manifest_path,
    read_manifest,
)

# =============================================================================
# Schema + I/O tests
# =============================================================================


def test_compose_writes_manifest_to_expected_path(plan_context):
    cmd_compose(_compose_ns(plan_id='io-write'))
    manifest_path = get_manifest_path('io-write')
    assert manifest_path.exists()
    manifest = read_manifest('io-write')
    assert manifest is not None
    assert manifest['manifest_version'] == 1
    assert manifest['plan_id'] == 'io-write'
    assert isinstance(manifest['phase_5']['verification_steps'], list)
    assert isinstance(manifest['phase_6']['steps'], list)
