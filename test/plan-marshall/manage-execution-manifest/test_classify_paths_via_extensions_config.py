# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _FakeExtension,
)

# =============================================================================
# Config role does NOT influence the plan-wide bucket
# =============================================================================


def test_config_only_collapses_to_documentation_only():
    """A plan touching only config files (no prod/test/docs) collapses to
    documentation_only — config alone does not warrant holistic Python verification.
    """
    py_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': [], 'documentation': [], 'config': ['pyproject.toml']},
    )
    bucket, _ = _classify_paths_via_extensions(['pyproject.toml'], extensions=[py_ext])
    assert bucket == 'documentation_only'



def test_config_combined_with_production_yields_production_only():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': ['pyproject.toml'],
        },
    )
    bucket, _ = _classify_paths_via_extensions(['scripts/foo.py', 'pyproject.toml'], extensions=[py_ext])
    assert bucket == 'production_only'
