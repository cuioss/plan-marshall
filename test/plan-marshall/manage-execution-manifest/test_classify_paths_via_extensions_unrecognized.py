# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _resolved_role


def test_unrecognized_render_target_takes_the_fail_closed_production_terminal():
    """Neither predicate matching yields ``production`` — never ``documentation_only``.

    The paired assertion against the delegating siblings above is what makes this
    a terminal rather than a blanket default: the same stage returns three
    different roles depending on what the render target is.
    """
    assert _resolved_role('pkg/mystery.xyz.template') == 'production'
