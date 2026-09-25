# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _PLANNING_SYSTEM_CONFIG,
    _classify_paths_via_extensions,
    _real_build_extensions,
    _resolved_role,
)


def test_marshal_json_resolves_to_the_config_role_through_the_full_aggregator():
    """The planning system's own project configuration stops resolving to ``unknown``.

    Asserted through the FULL aggregator against the REAL discovered extension
    set rather than against the bare predicate, because two separate facts have to
    hold and only one of them is the predicate's: that no shipped build extension
    claims the path first (so it reaches the stage-3 fallback at all), and that the
    role it emerges with is ``config``. A ``_is_infrastructure_config_path``
    assertion alone would leave the first unobserved.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions([_PLANNING_SYSTEM_CONFIG], extensions=extensions)

    assert unclaimed == [], 'marshal.json must not reach the unclaimed set'
    assert bucket != 'unknown'
    assert _resolved_role(_PLANNING_SYSTEM_CONFIG, extensions=extensions) == 'config'
