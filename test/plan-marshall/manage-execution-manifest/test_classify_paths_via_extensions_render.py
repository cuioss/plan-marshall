# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _FakeExtension, _resolved_role


def test_render_target_is_never_re_offered_to_the_build_extensions():
    """Delegation consults the two in-process predicates ONLY.

    The fake claims the RENDER TARGET (``pkg/scripts/x.py``) under ``test`` — a
    role the stage's terminal can never produce — and does not claim the template
    path itself. A stage that re-ran ``classify_paths()`` over the stripped set
    would therefore report ``test``; the terminal reports ``production``.
    """
    template_path = 'pkg/scripts/x.py.template'
    render_target = 'pkg/scripts/x.py'
    target_claiming_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': [render_target], 'documentation': [], 'config': []},
    )

    assert _resolved_role(template_path, extensions=[target_claiming_ext]) == 'production'
