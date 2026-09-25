# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)


def test_mixed_code_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': ['test/foo_test.py'],
            'documentation': [],
            'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(['scripts/foo.py', 'test/foo_test.py'], extensions=[py_ext])
    assert bucket == 'mixed_code'



def test_mixed_with_docs_bucket():
    """A production .py (extension-claimed) plus a generic .md doc yields
    mixed_with_docs — the doc role comes from the generic suffix rule, not an
    extension."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(['scripts/foo.py', 'README.md'], extensions=[py_ext])
    assert bucket == 'mixed_with_docs'



def test_mixed_with_docs_includes_test_role():
    """A test .py (extension-claimed) plus a generic .md doc yields
    mixed_with_docs."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': [],
            'test': ['test/foo_test.py'],
            'documentation': [],
            'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(['test/foo_test.py', 'README.md'], extensions=[py_ext])
    assert bucket == 'mixed_with_docs'
