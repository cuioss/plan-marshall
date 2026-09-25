#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import _mem, pytest


@pytest.fixture(autouse=True)
def _restore_footprint_resolver():
    """Snapshot + restore BOTH footprint seams so a stub never leaks across tests.

    ``_stub_footprint`` replaces two module attributes, so restoring only
    ``_mem._resolve_footprint`` left ``extension_base._resolve_plan_footprint``
    pinned for the rest of the worker process. Because ``extension_base`` is a
    shared cross-skill module, that leak reached UNRELATED test modules — a
    sibling asserting the real resolver's return observed this file's stub
    instead. Both seams are snapshotted and restored, symmetrically with the pair
    that ``_stub_footprint`` sets.
    """
    import extension_base

    original = _mem._resolve_footprint
    original_plan_footprint = extension_base._resolve_plan_footprint
    yield
    _mem._resolve_footprint = original
    extension_base._resolve_plan_footprint = original_plan_footprint
