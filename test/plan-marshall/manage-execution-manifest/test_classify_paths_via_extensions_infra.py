# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _ARCHITECTURE_INDEX_JSON,
    _ARCHITECTURE_MODULE_JSON,
    _ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT,
    _CI_WORKFLOW_YAML,
    _COMPOSE_YAML,
    _CONTAINER_SERVICE_YAML,
    _OPENCODE_CONFIG_JSON,
    _OPENCODE_CONFIG_JSONC,
    _OPENCODE_SUFFIX_SIBLING_JSON,
    _PLANNING_SYSTEM_CONFIG,
    _PLANNING_SYSTEM_SIBLING_JSON,
    _REVIEW_BOT_DESCRIPTOR,
    _classify_paths_via_extensions,
    _FakeExtension,
    _is_infrastructure_config_path,
)


def test_infra_config_family_is_location_or_basename_anchored_never_bare_suffix():
    """Family membership is anchored on location or basename, never on ``.yml``.

    The predicate backs the stage-3 fallback; a bare-suffix rule would sweep in
    build-owned resources, so the negative cases are as load-bearing as the
    positive ones.
    """
    for path in (
        '.github/workflows/python-verify.yml',
        '.github/dependabot.yml',
        '.circleci/config.yml',
        'docker-compose.yml',
        'docker-compose.override.yaml',
        'compose.yaml',
        '.gitlab-ci.yml',
        'src/main/docker/application.yaml',
        'docker/entrypoint.sh',
        '.hadolint.yaml',
        '.trivyignore',
        '.dockerignore',
        '.pr_agent.toml',
        '.coderabbit.yaml',
        '.coderabbit.yml',
        _PLANNING_SYSTEM_CONFIG,
        _ARCHITECTURE_INDEX_JSON,
        _ARCHITECTURE_MODULE_JSON,
        _OPENCODE_CONFIG_JSON,
        _OPENCODE_CONFIG_JSONC,
    ):
        assert _is_infrastructure_config_path(path), path

    for path in (
        'conf/application.yml',
        'src/main/resources/application.yml',
        'marketplace/bundles/foo/skills/bar/scripts/thing.py',
        'mystery.xyz',
        _PLANNING_SYSTEM_SIBLING_JSON,
        _ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT,
        _OPENCODE_SUFFIX_SIBLING_JSON,
    ):
        assert not _is_infrastructure_config_path(path), path


def test_each_infra_config_family_resolves_to_a_non_unknown_bucket():
    """Each anchoring group is recognized generically — no extension needed."""
    for path in (
        _CI_WORKFLOW_YAML,
        _COMPOSE_YAML,
        _CONTAINER_SERVICE_YAML,
        _REVIEW_BOT_DESCRIPTOR,
        _PLANNING_SYSTEM_CONFIG,
        _ARCHITECTURE_INDEX_JSON,
        _ARCHITECTURE_MODULE_JSON,
        _OPENCODE_CONFIG_JSON,
        _OPENCODE_CONFIG_JSONC,
    ):
        bucket, unclaimed = _classify_paths_via_extensions([path], extensions=[])
        assert bucket != 'unknown', path
        assert unclaimed == [], path


def test_infra_only_footprint_resolves_documentation_only():
    """An infra-only footprint collapses to documentation_only.

    The stage-3 rule assigns the ``config`` role, and ``config`` is excluded
    from the plan-wide bucket collapse — so infra config never warrants
    holistic Python verification on its own.
    """
    bucket, unclaimed = _classify_paths_via_extensions(
        [_CI_WORKFLOW_YAML, _COMPOSE_YAML, _CONTAINER_SERVICE_YAML], extensions=[]
    )
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_infra_config_neither_inflates_nor_dilutes_the_code_bucket():
    """An infra path riding alongside production code leaves the bucket at production_only."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py', _CI_WORKFLOW_YAML], extensions=[py_ext])
    assert bucket == 'production_only'
    assert unclaimed == []


def test_infra_fallback_narrows_unknown_without_eliminating_it():
    """A genuinely undeclared file type still resolves to ``unknown``."""
    bucket, unclaimed = _classify_paths_via_extensions(['mystery.xyz'], extensions=[])
    assert bucket == 'unknown'
    assert unclaimed == ['mystery.xyz']
