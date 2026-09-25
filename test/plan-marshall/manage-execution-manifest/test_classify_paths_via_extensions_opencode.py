# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _OPENCODE_CONFIG_JSON,
    _OPENCODE_CONFIG_JSONC,
    _OPENCODE_SUFFIX_SIBLING_JSON,
    _classify_paths_via_extensions,
    _is_infrastructure_config_path,
    _real_build_extensions,
    _resolved_role,
)


def test_opencode_config_files_resolve_to_the_config_role_through_the_full_aggregator():
    """The opencode tool's root config files stop resolving to ``unknown``.

    Asserted through the FULL aggregator against the REAL discovered extension
    set rather than against the bare predicate, because three separate facts
    have to hold and only one of them is the predicate's: that no shipped
    build extension claims the path first (so it reaches the stage-3 fallback
    at all — asserted explicitly per extension below, since a claim with role
    ``config`` would produce the same final role as the fallback and hide a
    build-ownership regression), and that the role it emerges with is
    ``config``. The ``unclaimed`` assertion is the no-unknown-warning half:
    the aggregator emits the unclaimed warning exactly when ``unclaimed`` is
    non-empty, so an empty list is the observable absence of that warning.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    for path in (_OPENCODE_CONFIG_JSON, _OPENCODE_CONFIG_JSONC):
        for ext in extensions:
            try:
                claims = ext.classify_paths([path])
            except Exception:
                continue
            claiming = sorted(role for role, role_paths in claims.items() if path in role_paths)
            assert not claiming, (
                f'{path} is claimed as {claiming} by a discovered build extension — '
                'it must reach the stage-3 fallback unclaimed'
            )

        bucket, unclaimed = _classify_paths_via_extensions([path], extensions=extensions)

        assert unclaimed == [], f'{path} must not reach the unclaimed set'
        assert bucket != 'unknown'
        assert _resolved_role(path, extensions=extensions) == 'config'



def test_opencode_recognition_is_root_anchored_not_basenamed():
    """A nested ``opencode.json`` is not tool configuration.

    The root-anchored rule reaches exactly the root config files the opencode
    CLI resolves by name: a nested copy (e.g. ``fixtures/opencode.json`` —
    test data, not tool configuration) is not a member, so it does not
    resolve to ``config`` through the fallback.
    """
    assert not _is_infrastructure_config_path('fixtures/opencode.json')
    assert not _is_infrastructure_config_path('fixtures/opencode.jsonc')



def test_opencode_recognition_is_a_basename_rule_not_a_json_suffix_rule():
    """The matched negative control that keeps the opencode entries anchored.

    An arbitrary repo-root ``.json`` that no tool resolves by a fixed name is
    NOT a member and still reaches ``unknown``. Without this case the two
    basename entries would be indistinguishable from a bare ``*.json`` suffix
    rule — which would additionally reclassify every git-tracked JSON file in
    the tree, the collateral reach the basename anchoring was chosen to avoid.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    assert not _is_infrastructure_config_path(_OPENCODE_SUFFIX_SIBLING_JSON)

    bucket, unclaimed = _classify_paths_via_extensions([_OPENCODE_SUFFIX_SIBLING_JSON], extensions=extensions)

    assert bucket == 'unknown'
    assert unclaimed == [_OPENCODE_SUFFIX_SIBLING_JSON]
