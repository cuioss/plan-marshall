# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _resolved_role


def test_double_suffix_render_target_is_re_tested_not_recursed():
    """``x.template.template`` classifies against ``x.template``, not against ``x``.

    The single-suffix sibling is asserted alongside it deliberately: it
    delegates to ``documentation``, so the ``production`` verdict on the
    double-suffix path is the absence of recursion rather than a default that
    would have applied either way.
    """
    assert _resolved_role('docs/guide.md.template.template') == 'production'
    assert _resolved_role('docs/guide.md.template') == 'documentation'
