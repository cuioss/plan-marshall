#!/usr/bin/env python3
"""Tests for ``_classify_paths_via_extensions`` aggregator in manage-execution-manifest.py.

Covers per-extension dispatch, longest-glob-wins overlap resolution, the
alphabetical tie-break on domain key, the six-bucket plan-wide vocabulary,
the unclaimed-path ``unknown`` branch, and the empty-input default.

The legacy ``test_classify_affected_files.py`` and
``test_compose_docs_only_branch.py`` tests against the inline four-bucket
helper are rewritten under deliverable 5 (TASK-8) of the file-type-classifier
refactor plan.
"""

import importlib.util
from pathlib import Path

from extension_base import ExtensionBase  # type: ignore[import-not-found]

# =============================================================================
# Module loading
# =============================================================================

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
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_manifest_mod = _load_module('manage_execution_manifest', 'manage-execution-manifest.py')
_classify_paths_via_extensions = _manifest_mod._classify_paths_via_extensions


# =============================================================================
# Local FakeExtension (Deliverable 4's conftest fixture is built in a later
# task; this module uses inline fakes so it can run before that fixture lands.)
# =============================================================================


class _FakeExtension(ExtensionBase):
    """Minimal ExtensionBase subclass that returns canned classify_paths claims."""

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
        return [{
            'domain': {'key': self._domain_key, 'name': self._domain_key, 'description': ''},
            'profiles': {
                'core': {'defaults': [], 'optionals': []},
                'implementation': {'defaults': [], 'optionals': []},
                'module_testing': {'defaults': [], 'optionals': []},
                'quality': {'defaults': [], 'optionals': []},
            },
        }]

    def classify_paths(self, paths: list[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {
            'production': [], 'test': [], 'documentation': [], 'config': []
        }
        for role, role_paths in self._claims.items():
            result[role] = [p for p in role_paths if p in paths]
        return result

    def classify_path_specificity(self, path: str, role: str) -> int:
        return self._specificity.get((path, role), 0)


# =============================================================================
# Empty / boundary cases
# =============================================================================


def test_empty_paths_returns_documentation_only():
    """Empty path list defaults to documentation_only (no holistic verification needed)."""
    bucket, unclaimed = _classify_paths_via_extensions([], extensions=[])
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_no_extensions_produces_unknown_when_paths_nonempty():
    """With no extensions registered, every path is unclaimed → unknown bucket."""
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py'], extensions=[])
    assert bucket == 'unknown'
    assert unclaimed == ['scripts/foo.py']


# =============================================================================
# Six-bucket vocabulary
# =============================================================================


def test_production_only_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={'production': ['scripts/foo.py'], 'test': [], 'documentation': [], 'config': []},
    )
    bucket, unclaimed = _classify_paths_via_extensions(['scripts/foo.py'], extensions=[py_ext])
    assert bucket == 'production_only'
    assert unclaimed == []


def test_test_only_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={'production': [], 'test': ['test/foo_test.py'], 'documentation': [], 'config': []},
    )
    bucket, _ = _classify_paths_via_extensions(['test/foo_test.py'], extensions=[py_ext])
    assert bucket == 'test_only'


def test_documentation_only_bucket():
    docs_ext = _FakeExtension(
        'documentation',
        claims={'production': [], 'test': [], 'documentation': ['README.md'], 'config': []},
    )
    bucket, _ = _classify_paths_via_extensions(['README.md'], extensions=[docs_ext])
    assert bucket == 'documentation_only'


def test_mixed_code_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': ['test/foo_test.py'],
            'documentation': [],
            'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(
        ['scripts/foo.py', 'test/foo_test.py'], extensions=[py_ext]
    )
    assert bucket == 'mixed_code'


def test_mixed_with_docs_bucket():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': [],
        },
    )
    docs_ext = _FakeExtension(
        'documentation',
        claims={
            'production': [], 'test': [], 'documentation': ['README.md'], 'config': []
        },
    )
    bucket, _ = _classify_paths_via_extensions(
        ['scripts/foo.py', 'README.md'], extensions=[py_ext, docs_ext]
    )
    assert bucket == 'mixed_with_docs'


def test_mixed_with_docs_includes_test_role():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': [],
            'test': ['test/foo_test.py'],
            'documentation': [],
            'config': [],
        },
    )
    docs_ext = _FakeExtension(
        'documentation',
        claims={
            'production': [], 'test': [], 'documentation': ['README.md'], 'config': []
        },
    )
    bucket, _ = _classify_paths_via_extensions(
        ['test/foo_test.py', 'README.md'], extensions=[py_ext, docs_ext]
    )
    assert bucket == 'mixed_with_docs'


def test_unknown_bucket_for_partially_unclaimed():
    """At least one unclaimed path forces the entire plan-wide bucket to unknown."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [], 'documentation': [], 'config': [],
        },
    )
    bucket, unclaimed = _classify_paths_via_extensions(
        ['scripts/foo.py', 'mystery.xyz'], extensions=[py_ext]
    )
    assert bucket == 'unknown'
    assert unclaimed == ['mystery.xyz']


# =============================================================================
# Config role does NOT influence the plan-wide bucket
# =============================================================================


def test_config_only_collapses_to_documentation_only():
    """A plan touching only config files (no prod/test/docs) collapses to
    documentation_only — config alone does not warrant holistic Python verification.
    """
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': [], 'test': [], 'documentation': [], 'config': ['pyproject.toml']
        },
    )
    bucket, _ = _classify_paths_via_extensions(['pyproject.toml'], extensions=[py_ext])
    assert bucket == 'documentation_only'


def test_config_combined_with_production_yields_production_only():
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [],
            'documentation': [],
            'config': ['pyproject.toml'],
        },
    )
    bucket, _ = _classify_paths_via_extensions(
        ['scripts/foo.py', 'pyproject.toml'], extensions=[py_ext]
    )
    assert bucket == 'production_only'


# =============================================================================
# Overlap resolution: longest-glob-wins
# =============================================================================


def test_longest_glob_wins_pm_plugin_dev_beats_pm_documents_on_skill_md():
    """The pm-plugin-development extension wins SKILL.md paths over pm-documents
    via higher classify_path_specificity score."""
    path = 'marketplace/bundles/foo/skills/bar/SKILL.md'
    docs_ext = _FakeExtension(
        'documentation',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 0},  # *.md glob → 0 explicit segments
    )
    plugin_ext = _FakeExtension(
        'plan-marshall-plugin-dev',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 4},  # marketplace/bundles/*/skills/*/SKILL.md
    )
    bucket, unclaimed = _classify_paths_via_extensions(
        [path], extensions=[docs_ext, plugin_ext]
    )
    # Both claimed under documentation, so the resolved bucket is documentation_only.
    # The winner is plugin_ext (higher specificity).
    assert bucket == 'documentation_only'
    assert unclaimed == []


def test_overlap_resolution_higher_specificity_wins_across_roles():
    """When two extensions claim the same path under different roles, higher
    specificity wins and determines the final role for that path."""
    path = 'src/foo.py'
    py_ext = _FakeExtension(
        'python',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 1},
    )
    confused_ext = _FakeExtension(
        'confused',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 5},  # absurdly high
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[py_ext, confused_ext])
    # confused_ext wins → role becomes documentation → documentation_only
    assert bucket == 'documentation_only'


def test_overlap_resolution_alphabetical_tiebreak_on_equal_specificity():
    """When two extensions tie on specificity, the alphabetically earlier
    domain key wins."""
    path = 'foo.bar'
    a_ext = _FakeExtension(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 2},
    )
    z_ext = _FakeExtension(
        'zulu',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 2},
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[a_ext, z_ext])
    # alpha wins alphabetically → production → production_only
    assert bucket == 'production_only'


def test_overlap_resolution_is_extension_order_independent():
    """Result must be identical regardless of extension iteration order."""
    path = 'foo.bar'
    a_ext = _FakeExtension(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
        specificity={(path, 'production'): 5},
    )
    b_ext = _FakeExtension(
        'beta',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 1},
    )
    bucket_ab, _ = _classify_paths_via_extensions([path], extensions=[a_ext, b_ext])
    bucket_ba, _ = _classify_paths_via_extensions([path], extensions=[b_ext, a_ext])
    assert bucket_ab == bucket_ba == 'production_only'


# =============================================================================
# Unclaimed-path warning emission
# =============================================================================


def test_unknown_returns_unclaimed_paths_list():
    """The aggregator returns the unclaimed-paths list so callers can route the
    warning to the appropriate decision-log surface."""
    py_ext = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [], 'documentation': [], 'config': [],
        },
    )
    bucket, unclaimed = _classify_paths_via_extensions(
        ['scripts/foo.py', 'mystery1.xyz', 'mystery2.xyz'], extensions=[py_ext]
    )
    assert bucket == 'unknown'
    assert set(unclaimed) == {'mystery1.xyz', 'mystery2.xyz'}


def test_extension_raising_in_classify_paths_is_skipped():
    """An extension whose classify_paths raises must not abort the aggregator;
    the path falls through to unclaimed if no other extension claims it."""

    class _RaisingExt(_FakeExtension):
        def classify_paths(self, paths):
            raise RuntimeError('boom')

    bad = _RaisingExt('bad')
    good = _FakeExtension(
        'python',
        claims={
            'production': ['scripts/foo.py'],
            'test': [], 'documentation': [], 'config': [],
        },
    )
    bucket, _ = _classify_paths_via_extensions(
        ['scripts/foo.py'], extensions=[bad, good]
    )
    assert bucket == 'production_only'


def test_specificity_raising_is_treated_as_zero():
    """An extension whose classify_path_specificity raises is treated as score 0."""

    class _RaisingSpecExt(_FakeExtension):
        def classify_path_specificity(self, path, role):
            raise RuntimeError('boom')

    path = 'foo.bar'
    bad = _RaisingSpecExt(
        'alpha',
        claims={'production': [path], 'test': [], 'documentation': [], 'config': []},
    )
    good = _FakeExtension(
        'zulu',
        claims={'production': [], 'test': [], 'documentation': [path], 'config': []},
        specificity={(path, 'documentation'): 3},
    )
    bucket, _ = _classify_paths_via_extensions([path], extensions=[bad, good])
    # zulu specificity=3 beats bad specificity=0 → documentation_only
    assert bucket == 'documentation_only'
