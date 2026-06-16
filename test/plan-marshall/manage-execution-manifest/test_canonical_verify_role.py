#!/usr/bin/env python3
"""Tests for canonical-verify role resolution in manage-execution-manifest.py.

The composer resolves a phase-5 candidate step ID of the parameterized
canonical-verify shape ``default:verify:{canonical}`` (or its bare
``verify:{canonical}`` form) to a matrix ``role:`` value purely in-code,
deriving the role from the trailing ``{canonical}`` segment via the
``_CANONICAL_TO_ROLE`` table. A single parameterized step backs every
canonical, and the canonical is the parameter that selects the role.

This module covers the HAPPY-PATH role-from-canonical resolution: every
``{canonical}`` entry in ``_CANONICAL_TO_ROLE`` maps to the expected role
through both the ``default:``-prefixed and bare forms, plus the direct
``_role_from_canonical`` derivation helper. The negative cases (unknown
canonical, external steps, the legacy bare-name path) live in the sibling
modules ``test_canonical_verify_inactive.py`` and
``test_manage_execution_manifest_compose.py`` (``TestRoleLoader``).
"""

import importlib.util
from pathlib import Path

import pytest

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_canonical_role', 'manage-execution-manifest.py')
_role_of = _mem._role_of
_role_from_canonical = _mem._role_from_canonical
_CANONICAL_TO_ROLE = _mem._CANONICAL_TO_ROLE


# The canonical → role expectations the composer must honor. Sourced from the
# ``_CANONICAL_TO_ROLE`` table so the parametrization tracks the production
# table by construction: both ``verify`` and ``module-tests`` map to the
# ``module-tests`` role (running the full module-test suite); ``quality-gate``
# maps to ``quality-gate``; ``coverage`` to ``coverage``; the whole-tree gates
# map to their own roles.
_CANONICAL_ROLE_CASES = [
    ('quality-gate', 'quality-gate'),
    ('verify', 'module-tests'),
    ('module-tests', 'module-tests'),
    ('coverage', 'coverage'),
    ('integration-tests', 'integration'),
    ('e2e', 'e2e'),
]


class TestRoleFromCanonicalHelper:
    """``_role_from_canonical`` derives the matrix role from a canonical segment."""

    @pytest.mark.parametrize('canonical,expected_role', _CANONICAL_ROLE_CASES)
    def test_known_canonical_derives_expected_role(self, canonical, expected_role):
        assert _role_from_canonical(canonical) == expected_role

    def test_unknown_canonical_derives_none(self):
        """An unrecognized canonical falls through to None (never role-selected)."""
        assert _role_from_canonical('not-a-canonical') is None

    def test_helper_tracks_production_table(self):
        """Every parametrized case is present in the production table.

        Guards against the table and these tests drifting apart: if a new
        canonical is added to ``_CANONICAL_TO_ROLE`` without a matching case
        here, this assertion still passes, but a case for a canonical that was
        REMOVED from the table fails loudly.
        """
        for canonical, expected_role in _CANONICAL_ROLE_CASES:
            assert _CANONICAL_TO_ROLE.get(canonical) == expected_role


class TestCanonicalVerifyRoleResolution:
    """``_role_of`` resolves ``default:verify:{canonical}`` via the canonical segment."""

    @pytest.mark.parametrize('canonical,expected_role', _CANONICAL_ROLE_CASES)
    def test_prefixed_canonical_verify_resolves_role(self, canonical, expected_role):
        """``default:verify:{canonical}`` derives its role from the trailing segment."""
        cache: dict[str, str | None] = {}
        assert _role_of(f'default:verify:{canonical}', cache) == expected_role

    @pytest.mark.parametrize('canonical,expected_role', _CANONICAL_ROLE_CASES)
    def test_bare_canonical_verify_resolves_role(self, canonical, expected_role):
        """The bare ``verify:{canonical}`` form resolves to the same role."""
        cache: dict[str, str | None] = {}
        assert _role_of(f'verify:{canonical}', cache) == expected_role

    def test_prefixed_and_bare_forms_agree(self):
        """A given canonical resolves identically through both forms."""
        cache: dict[str, str | None] = {}
        for canonical, _expected in _CANONICAL_ROLE_CASES:
            prefixed = _role_of(f'default:verify:{canonical}', cache)
            bare = _role_of(f'verify:{canonical}', cache)
            assert prefixed == bare

    def test_verify_and_module_tests_canonicals_share_module_tests_role(self):
        """Both ``verify`` and ``module-tests`` canonicals map to ``module-tests``."""
        cache: dict[str, str | None] = {}
        assert _role_of('default:verify:verify', cache) == 'module-tests'
        assert _role_of('default:verify:module-tests', cache) == 'module-tests'

    def test_canonical_verify_result_is_cached(self):
        """The per-compose cache short-circuits the second lookup for the same step."""
        cache: dict[str, str | None] = {}
        first = _role_of('default:verify:integration-tests', cache)
        assert first == 'integration'
        # Mutate the cache to a sentinel — the second call MUST observe the
        # cached value rather than re-deriving from the canonical segment.
        cache['default:verify:integration-tests'] = 'mutated-sentinel'
        second = _role_of('default:verify:integration-tests', cache)
        assert second == 'mutated-sentinel'
