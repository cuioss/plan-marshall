#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _mem, pytest


@pytest.fixture(autouse=True)
def _restore_footprint_seams_module_wide():
    """Restore BOTH footprint seams after every test in this module.

    ``_stub_footprint`` is called from tests inside AND outside
    ``TestPrePushQualityGatePreFilter``, whose own class-scoped restore fixture
    therefore cannot cover them all. ``extension_base`` is a shared cross-skill
    module, so an unrestored stub does not merely leak within this file — it
    reaches unrelated test modules in the same xdist worker and makes a sibling
    asserting the REAL resolver observe this file's stub instead. Restoring
    module-wide closes that at the source.
    """
    import extension_base

    original_mem = _mem._resolve_footprint
    original_plan_footprint = extension_base._resolve_plan_footprint
    yield
    _mem._resolve_footprint = original_mem
    extension_base._resolve_plan_footprint = original_plan_footprint
