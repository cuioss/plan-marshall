# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)


def test_test_only_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': ['test/foo_test.py'], 'documentation': [], 'config': []},
    )
    bucket, _ = _classify_paths_via_extensions(['test/foo_test.py'], extensions=[py_ext])
    assert bucket == 'test_only'
