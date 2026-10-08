#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``_classify_paths_via_extensions`` aggregator in manage-execution-manifest.py.

Covers per-extension dispatch, longest-glob-wins overlap resolution, the
alphabetical tie-break on domain key, the six-bucket plan-wide vocabulary,
the unclaimed-path ``unknown`` branch, the empty-input default, the
stage-3 generic owner-less infrastructure-config fallback (its family
membership, its never-steal-a-claim ordering, and the D3(b) Q-Gate-outcome
assertion against the real discovered build-extension set), and the stage-3b
generic owner-less template rule (render-target delegation to the two
in-process predicates, the fail-closed ``production`` terminal, exactly-once
suffix stripping, never-steal ordering, and the suffix-only membership bound).

``_classify_paths_via_extensions`` is the seed-source aggregator consumed by the
build_map seeding path; the advisory docs-only compose branch that previously
also consumed it has been removed (see ``test_compose_docs_only_branch.py``).
"""

from extension_base import BuildExtensionBase

# =============================================================================
# Module loading
# =============================================================================
from conftest import load_script_module

_manifest_mod = load_script_module(
    'plan-marshall',
    'manage-execution-manifest',
    'manage-execution-manifest.py',
    module_name='manage_execution_manifest',
)
_classify_paths_via_extensions = _manifest_mod._classify_paths_via_extensions
_is_infrastructure_config_path = _manifest_mod._is_infrastructure_config_path
_is_template_path = _manifest_mod._is_template_path
_strip_template_suffix = _manifest_mod._strip_template_suffix

# Silence the best-effort decision-log subprocess in the aggregator tests.
_manifest_mod._emit_decision_log = lambda *a, **kw: None

# =============================================================================
# Local FakeExtension — this module defines its own inline fakes rather than
# depending on a shared conftest fixture, so it stands alone.
# =============================================================================


class _FakeExtension(BuildExtensionBase):
    """Minimal BuildExtensionBase subclass returning canned classify_paths claims.

    The aggregator iterates *build* extensions (Axis-B), so a fake that models
    a build extension's production / test / config claims subclasses
    ``BuildExtensionBase`` — the home of ``classify_paths`` /
    ``classify_path_specificity`` after the Axis-B strip moved those methods off
    the language ``ExtensionBase`` hierarchy. Documentation is NOT modelled here:
    doc recognition is the aggregator's generic ``_DOC_SUFFIXES`` rule, owned by
    no extension.
    """

    def __init__(
        self,
        domain_key: str,
        claims: dict[str, list[str]] | None = None,
        specificity: dict[tuple[str, str], int] | None = None,
    ) -> None:
        self._domain_key = domain_key
        self._claims = claims or {'production': [], 'test': [], 'documentation': [], 'config': []}
        # Keyed by (path, role) -> int
        self._specificity = specificity or {}

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': self._domain_key, 'name': self._domain_key, 'description': ''},
                'profiles': {
                    'core': {'defaults': [], 'optionals': []},
                    'implementation': {'defaults': [], 'optionals': []},
                    'module_testing': {'defaults': [], 'optionals': []},
                    'quality': {'defaults': [], 'optionals': []},
                },
            }
        ]

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {'production': [], 'test': [], 'documentation': [], 'config': []}
        for role, role_paths in self._claims.items():
            result[role] = [p for p in role_paths if p in paths]
        return result

    def classify_path_specificity(self, path: str, role: str) -> int:
        return self._specificity.get((path, role), 0)


# =============================================================================
# Stage 3 — generic owner-less infrastructure-config recognition (fallback)
# =============================================================================

# One representative of each infrastructure-config anchoring group.
_CI_WORKFLOW_YAML = '.github/workflows/python-verify.yml'
_COMPOSE_YAML = 'docker-compose.yml'
_CONTAINER_SERVICE_YAML = 'src/main/docker/application.yaml'
_REVIEW_BOT_DESCRIPTOR = '.pr_agent.toml'
_PLANNING_SYSTEM_CONFIG = '.plan/marshal.json'

#: The matched negative control for the planning-system entries. A JSON file
#: directly under ``.plan/`` — the SAME directory as :data:`_PLANNING_SYSTEM_CONFIG`,
#: a different basename, and OUTSIDE the architecture-data tree. It is the control
#: against two wider rules at once: it would be recognized only if the planning
#: system were matched by a ``('.plan',)`` directory rule or by a ``.json`` suffix
#: rule, rather than by the basename entry and the two-segment tree entry it is.
_PLANNING_SYSTEM_SIBLING_JSON = '.plan/notes.json'

#: The planning system's tracked architecture data, recognized by LOCATION: every
#: file under ``.plan/project-architecture/`` at any depth. One constant per depth
#: — the index file directly under the tree, and a per-module file one level down.
_ARCHITECTURE_INDEX_JSON = '.plan/project-architecture/_project.json'
_ARCHITECTURE_MODULE_JSON = '.plan/project-architecture/plan-marshall-opencode/enriched.json'

#: The matched negative control for the architecture-data tree entry: the same
#: tree name WITHOUT the ``.plan`` parent. The entry is a two-segment run, so a
#: ``project-architecture/`` directory elsewhere is not a member.
_ARCHITECTURE_TREE_WITHOUT_PLAN_PARENT = 'project-architecture/_project.json'

#: The opencode tool's own configuration — the two basenames the opencode CLI
#: resolves at the project root by that fixed name. Root-anchored (not merely
#: basename-anchored): only a root-level path is a member, so the entry
#: reaches exactly the root config files, never the host-side
#: ``.opencode/plugin/**`` tree and never a nested copy such as
#: ``fixtures/opencode.json`` (test data, not tool configuration).
_OPENCODE_CONFIG_JSON = 'opencode.json'
_OPENCODE_CONFIG_JSONC = 'opencode.jsonc'

#: The matched negative control for the opencode entries. A repo-root `.json`
#: that no tool resolves by a fixed name is NOT a member — otherwise the
#: basename entries would be indistinguishable from a bare ``*.json`` suffix rule.
_OPENCODE_SUFFIX_SIBLING_JSON = 'settings.json'

# A footprint consisting exclusively of infrastructure-config paths, spanning
# every group the table declares. Used by the D3(b) Q-Gate-outcome assertion.
_INFRA_ONLY_FOOTPRINT = (
    _CI_WORKFLOW_YAML,
    '.github/dependabot.yml',
    '.circleci/config.yml',
    _COMPOSE_YAML,
    'compose.yaml',
    '.gitlab-ci.yml',
    _CONTAINER_SERVICE_YAML,
    '.hadolint.yaml',
    '.trivyignore',
    '.dockerignore',
    _REVIEW_BOT_DESCRIPTOR,
    '.coderabbit.yaml',
    '.coderabbit.yml',
    _PLANNING_SYSTEM_CONFIG,
    _ARCHITECTURE_INDEX_JSON,
    _OPENCODE_CONFIG_JSON,
    _OPENCODE_CONFIG_JSONC,
)


def _real_build_extensions() -> list:
    """Return the REAL discovered build-extension instances (not fakes).

    Mirrors the aggregator's own lazy-import discovery path so an assertion
    made against this list is an assertion about the SHIPPED extension set —
    a fake-extension assertion could pass while the real extensions still
    leave the paths unclaimed.
    """
    from extension_discovery import discover_build_extensions

    discovered = discover_build_extensions()
    return [entry.get('module') for entry in discovered if entry.get('module') is not None]


# =============================================================================
# Stage 3b — generic owner-less template recognition (fallback)
# =============================================================================

#: The one ``.template`` file in the tree, and the path whose blocking
#: ``unknown`` classification this rule exists to clear. Copied verbatim.
_EXECUTOR_TEMPLATE = (
    'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
)

#: A production probe an inline fake claims, used by :func:`_resolved_role` to
#: separate the three roles stage 3b can assign. Deliberately not a template and
#: not a doc so it contributes exactly one ``production`` role and nothing else.
_PROD_PROBE = 'pkg/prod_probe.py'


def _resolved_role(path: str, extensions=()) -> str:
    """Return the footprint role the classifier assigned to ``path``.

    The aggregator exposes only the plan-wide bucket, and the collapse is lossy:
    a lone ``config`` and a lone ``documentation`` both read as
    ``documentation_only``. Two probes separate them, because ``config`` is
    excluded from the collapse while ``documentation`` is not:

    Reading ``[path]`` alone, then ``[probe, path]``:

    * ``production`` -> production_only, production_only
    * ``test`` -> test_only, mixed_code
    * ``documentation`` -> documentation_only, mixed_with_docs
    * ``config`` -> documentation_only, production_only

    Reading the role through the PUBLIC classifier output — rather than reaching
    into ``per_path_role`` — keeps these assertions statements about the
    aggregator's observable behaviour.
    """
    alone, unclaimed = _classify_paths_via_extensions([path], extensions=list(extensions))
    if unclaimed:
        return 'unknown'
    if alone == 'production_only':
        return 'production'
    if alone == 'test_only':
        return 'test'

    probe_ext = _FakeExtension(
        'probe',
        claims={'production': [_PROD_PROBE], 'test': [], 'documentation': [], 'config': []},
    )
    paired, _ = _classify_paths_via_extensions([_PROD_PROBE, path], extensions=[probe_ext, *extensions])
    if paired == 'mixed_with_docs':
        return 'documentation'
    if paired == 'production_only':
        return 'config'
    return f'indeterminate(alone={alone}, paired={paired})'
