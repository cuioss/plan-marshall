# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)

# =============================================================================
# Six-bucket vocabulary
# =============================================================================


def test_production_only_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={'production': ['scripts/foo.py'], 'test': [], 'documentation': [], 'config': []},
    )
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py'], extensions=[py_ext])
    assert bucket == 'production_only'
    assert unclaimed == []
