#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Test fixtures for classifier tests in manage-execution-manifest.

Provides a reusable ``FakeExtension`` subclass of ``ExtensionBase`` with
canned ``classify_paths`` claims and per-(path, role) specificity scores,
plus a ``fake_extensions`` helper that constructs the standard set of
fakes used by the rewritten legacy classifier tests.

The module is named ``_execution_manifest_fixtures.py`` (NOT ``conftest.py``)
per the plan-marshall sibling-conftest ban — a sibling ``conftest.py`` under
``test/<bundle>/<skill>/`` would shadow the top-level ``test/conftest.py``
and silently disable shared fixtures. The basename is bundle-unique (rather
than a bare ``_fixtures.py``) to avoid a basename collision in the
plan-marshall test-collection namespace. See
``plan-marshall:persona-module-tester`` for the authoritative
``_fixtures.py`` convention.

Tests import the fixtures explicitly::

    from test.plan_marshall.manage_execution_manifest._execution_manifest_fixtures import (
        FakeExtension, fake_extensions,
    )
"""

from extension_base import ExtensionBase


class FakeExtension(ExtensionBase):
    """ExtensionBase subclass with canned classify_paths claims.

    Args:
        domain_key: The first-domain ``key`` returned by
            :meth:`get_skill_domains`. Used as the alphabetical tie-breaker
            during overlap resolution.
        claims: A four-role dict (``production`` / ``test`` /
            ``documentation`` / ``config``) of paths this fake claims. The
            fake intersects the input paths with these claims at
            ``classify_paths`` time, so the fixture is reusable across
            multiple inputs.
        specificity: Mapping from ``(path, role)`` tuples to integer
            specificity scores. Returned verbatim by
            :meth:`classify_path_specificity`. Missing entries fall back
            to ``0`` (the default).
    """

    def __init__(
        self,
        domain_key: str,
        claims: dict[str, list[str]] | None = None,
        specificity: dict[tuple[str, str], int] | None = None,
    ) -> None:
        self._domain_key = domain_key
        self._claims = claims or {
            'production': [],
            'test': [],
            'documentation': [],
            'config': [],
        }
        self._specificity = specificity or {}

    def get_skill_domains(self) -> list[dict]:
        return [{
            'domain': {
                'key': self._domain_key,
                'name': self._domain_key,
                'description': '',
            },
            'profiles': {
                'core': {'defaults': [], 'optionals': []},
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }]

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        path_set = set(paths)
        result: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for role, claimed in self._claims.items():
            result[role] = [p for p in claimed if p in path_set]
        return result

    def classify_path_specificity(self, path: str, role: str) -> int:
        return self._specificity.get((path, role), 0)


def fake_python_extension(
    production: list[str] | None = None,
    tests: list[str] | None = None,
    config: list[str] | None = None,
) -> FakeExtension:
    """Build a FakeExtension that mimics pm-dev-python's claims."""
    claims = {
        'production': production or [],
        'test': tests or [],
        'documentation': [],
        'config': config or [],
    }
    specificity = {(p, 'production'): 1 for p in claims['production']}
    specificity.update({(p, 'test'): 1 for p in claims['test']})
    specificity.update({(p, 'config'): 1 for p in claims['config']})
    return FakeExtension('python', claims=claims, specificity=specificity)


def fake_documentation_extension(documentation: list[str] | None = None) -> FakeExtension:
    """Build a FakeExtension that mimics pm-documents (specificity 0)."""
    claims = {
        'production': [],
        'test': [],
        'documentation': documentation or [],
        'config': [],
    }
    return FakeExtension('documentation', claims=claims)


def fake_plugin_dev_extension(documentation: list[str] | None = None) -> FakeExtension:
    """Build a FakeExtension that mimics pm-plugin-development (specificity 4)."""
    claims = {
        'production': [],
        'test': [],
        'documentation': documentation or [],
        'config': [],
    }
    specificity = {(p, 'documentation'): 4 for p in claims['documentation']}
    return FakeExtension(
        'plan-marshall-plugin-dev',
        claims=claims,
        specificity=specificity,
    )


def fake_lane_blocks() -> dict[str, dict[str, str]]:
    """Return canned ``lane:`` frontmatter blocks for the lane-resolver tests.

    A reusable fixture spanning all four ``lane.class`` values and both tier
    deviations, keyed by phase-6 step id. The lane-resolver tests monkeypatch
    ``manage-execution-manifest._resolve_element_lane`` to return blocks from this
    table so the posture cutoff is exercised deterministically without depending
    on the real frontmatter of the shipped finalize-step docs. The cost sizes
    (``XS``/``L``) drive the ``lanes preview`` cost-sum assertions (XS=5K, L=130K).
    """
    return {
        'push': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
        'archive-plan': {'class': 'core', 'tier': 'minimal', 'cost_size': 'XS'},
        'sonar-roundtrip': {
            'class': 'prunable', 'tier': 'auto', 'prunable_when': 'no_code_delta', 'cost_size': 'L',
        },
        'finalize-step-security-audit': {'class': 'adversarial', 'tier': 'full', 'cost_size': 'L'},
        'plan-marshall:plan-retrospective': {'class': 'prunable', 'tier': 'full', 'cost_size': 'L'},
        'project:finalize-step-deploy-target': {
            'class': 'derived-state', 'tier': 'minimal', 'cost_size': 'XS',
        },
    }
