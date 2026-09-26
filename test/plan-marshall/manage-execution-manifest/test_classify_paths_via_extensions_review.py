# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _classify_paths_via_extensions,
    _is_infrastructure_config_path,
)


def test_review_bot_descriptors_are_recognized_by_basename():
    """The review-bot descriptor group is a member of the basename family.

    Each name is one an external reviewer resolves at a fixed location, so the
    file is that tool's configuration wherever it sits.
    """
    for path in ('.pr_agent.toml', '.coderabbit.yaml', '.coderabbit.yml'):
        assert _is_infrastructure_config_path(path), path


def test_review_bot_recognition_is_an_enumeration_not_a_toml_suffix_rule():
    """The negative control for the widening.

    An arbitrary repo-root ``.toml`` that no reviewer resolves by name is NOT a
    member and still reaches ``unknown``. Without this case the widening would be
    indistinguishable from a bare ``*.toml`` suffix rule, which is exactly the
    shape the family is anchored to avoid.
    """
    assert not _is_infrastructure_config_path('settings.toml')
    assert not _is_infrastructure_config_path('config/arbitrary.toml')

    bucket, unclaimed = _classify_paths_via_extensions(['settings.toml'], extensions=[])
    assert bucket == 'unknown'
    assert unclaimed == ['settings.toml']
