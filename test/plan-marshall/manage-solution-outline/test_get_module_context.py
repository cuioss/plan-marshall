#!/usr/bin/env python3
"""Tests for ``manage-solution-outline get-module-context`` (per-module layout).

Pins the D3 reader contract: ``cmd_get_module_context`` reads the per-module
project-architecture layout (top-level ``_project.json`` plus per-module
``derived.json`` / ``enriched.json``) and returns a structured context for
solution-outline placement decisions.

Covers two branches:

* **happy path** — at least two modules with mixed enrichment fields, asserting
  the returned ``modules`` list pins the documented shape (``name``, ``path``,
  ``purpose``, ``responsibility``, plus the optional ``key_packages``,
  ``tips``, ``insights``, ``skills_by_profile`` fields).
* **not_found** — ``_project.json`` is absent, so the command returns the
  documented ``not_found`` status with a remediation suggestion.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import get_script_path

# =============================================================================
# Module Loading
# =============================================================================

# manage-solution-outline.py has hyphens, so importlib is required.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py')
_spec = importlib.util.spec_from_file_location('manage_solution_outline', str(SCRIPT_PATH))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_get_module_context = _mod.cmd_get_module_context

# _architecture_core helpers — used to seed the per-module layout under the
# fixture's project_dir without round-tripping through the discover/init
# commands. The conftest PYTHONPATH bootstrap puts the scripts/ directories on
# sys.path so a normal import resolves the module.
_ARCH_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)
_arch_spec = importlib.util.spec_from_file_location(
    '_architecture_core_test_module', str(_ARCH_SCRIPTS_DIR / '_architecture_core.py')
)
_arch_core = importlib.util.module_from_spec(_arch_spec)
sys.modules.setdefault('_architecture_core_test_module', _arch_core)
_arch_spec.loader.exec_module(_arch_core)

save_project_meta = _arch_core.save_project_meta
save_module_derived = _arch_core.save_module_derived
save_module_enriched = _arch_core.save_module_enriched


# =============================================================================
# Fixtures
# =============================================================================


def _ns(project_dir: str) -> Namespace:
    """Build the Namespace shape that ``cmd_get_module_context`` expects."""
    return Namespace(project_dir=project_dir)


def _seed_two_module_project(project_dir: Path) -> None:
    """Seed a per-module layout with two modules at ``project_dir``.

    ``core`` carries the full optional-field set (``key_packages``, ``tips``,
    ``insights``, ``skills_by_profile``); ``web`` carries only the required
    fields, exercising the optional-field omission path.
    """
    save_project_meta(
        {
            'name': 'multi-module-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'core': {}, 'web': {}},
        },
        str(project_dir),
    )

    save_module_derived(
        'core',
        {
            'name': 'core',
            'paths': {'module': 'core'},
            'packages': [],
        },
        str(project_dir),
    )
    save_module_enriched(
        'core',
        {
            'purpose': 'Domain layer',
            'responsibility': 'Encapsulates business rules and entities',
            'key_packages': {
                'de.cuioss.core.domain': 'Aggregate roots',
                'de.cuioss.core.value': 'Value objects',
            },
            'tips': ['Keep entities free of framework annotations'],
            'insights': ['Repository abstractions live in service layer'],
            'skills_by_profile': {
                'implementation': ['pm-dev-java:java-core'],
                'unit-testing': ['pm-dev-java:junit-core'],
            },
        },
        str(project_dir),
    )

    save_module_derived(
        'web',
        {
            'name': 'web',
            'paths': {'module': 'web'},
            'packages': [],
        },
        str(project_dir),
    )
    save_module_enriched(
        'web',
        {
            'purpose': 'HTTP entry points',
            'responsibility': 'Expose REST endpoints and translate DTOs',
        },
        str(project_dir),
    )


# =============================================================================
# Happy Path
# =============================================================================


def test_get_module_context_returns_per_module_entries(tmp_path):
    """Reader returns a structured context with one entry per module.

    Pins the contract: ``status`` is ``success``, ``module_count`` reflects the
    ``_project.json`` index, and ``modules`` carries one entry per module with
    the documented shape.
    """
    # Arrange
    _seed_two_module_project(tmp_path)

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert
    assert result['status'] == 'success'
    assert result['module_count'] == 2
    modules = result['modules']
    assert len(modules) == 2
    # Modules come back in the order ``iter_modules`` yields (sorted by name).
    names = [m['name'] for m in modules]
    assert names == ['core', 'web']


def test_get_module_context_pins_optional_field_shape(tmp_path):
    """The optional fields surface verbatim from the per-module ``enriched.json``.

    ``core`` carries every optional field; the test pins the shape the script
    documents — ``key_packages`` is a list of package names (the dict keys),
    while ``tips``, ``insights`` and ``skills_by_profile`` flow through
    untouched.
    """
    # Arrange
    _seed_two_module_project(tmp_path)

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert — required fields
    core = next(m for m in result['modules'] if m['name'] == 'core')
    assert core['path'] == 'core'
    assert core['purpose'] == 'Domain layer'
    assert core['responsibility'] == 'Encapsulates business rules and entities'

    # Assert — optional fields are present and carry the documented shape
    assert core['key_packages'] == ['de.cuioss.core.domain', 'de.cuioss.core.value']
    assert core['tips'] == ['Keep entities free of framework annotations']
    assert core['insights'] == ['Repository abstractions live in service layer']
    assert core['skills_by_profile'] == {
        'implementation': ['pm-dev-java:java-core'],
        'unit-testing': ['pm-dev-java:junit-core'],
    }


def test_get_module_context_omits_optionals_when_enrichment_lacks_them(tmp_path):
    """Modules without optional enrichment fields omit them from the entry.

    ``web`` only declares ``purpose`` and ``responsibility``; the contract
    requires the optional keys to be absent (rather than defaulted to empty
    values) so callers can branch on presence.
    """
    # Arrange
    _seed_two_module_project(tmp_path)

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert
    web = next(m for m in result['modules'] if m['name'] == 'web')
    assert web['name'] == 'web'
    assert web['path'] == 'web'
    assert web['purpose'] == 'HTTP entry points'
    assert web['responsibility'] == 'Expose REST endpoints and translate DTOs'
    for optional_key in ('key_packages', 'tips', 'insights', 'skills_by_profile'):
        assert optional_key not in web, f"web entry should omit '{optional_key}' when absent"


def test_get_module_context_uses_default_path_when_module_lacks_paths(tmp_path):
    """Modules whose derived data lacks ``paths.module`` fall back to ``'.'``.

    The reader documents this fallback explicitly so callers always see a
    non-empty ``path`` field even when discovery wrote a sparse derived shape.
    """
    # Arrange
    save_project_meta(
        {
            'name': 'sparse-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'root': {}},
        },
        str(tmp_path),
    )
    # Note: derived.json without ``paths`` key — the reader must still resolve.
    save_module_derived('root', {'name': 'root'}, str(tmp_path))
    save_module_enriched(
        'root',
        {'purpose': 'Project root', 'responsibility': 'Top-level aggregator'},
        str(tmp_path),
    )

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert
    assert result['status'] == 'success'
    root = result['modules'][0]
    assert root['path'] == '.'


def test_get_module_context_treats_missing_module_derived_as_empty(tmp_path):
    """``_project.json`` lists a module whose ``derived.json`` is missing.

    The reader catches ``DataNotFoundError`` per-module, treats the derived
    shape as empty, and still emits a stable entry for that module so callers
    don't see a partial response.
    """
    # Arrange — index lists 'orphan' but no derived.json is written for it.
    save_project_meta(
        {
            'name': 'half-written-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'orphan': {}},
        },
        str(tmp_path),
    )
    save_module_enriched(
        'orphan',
        {'purpose': 'Late arrival', 'responsibility': 'Pending discovery'},
        str(tmp_path),
    )

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert
    assert result['status'] == 'success'
    assert result['module_count'] == 1
    orphan = result['modules'][0]
    assert orphan['name'] == 'orphan'
    assert orphan['path'] == '.'  # default when derived has no paths
    assert orphan['purpose'] == 'Late arrival'
    assert orphan['responsibility'] == 'Pending discovery'


# =============================================================================
# not_found Branch
# =============================================================================


def test_get_module_context_returns_not_found_when_project_meta_absent(tmp_path):
    """Reader returns ``status='not_found'`` when ``_project.json`` is missing.

    The contract: ``not_found`` keys off the existence of ``_project.json``,
    which is the canonical source-of-truth file for "which modules exist".
    The response includes a discover suggestion so callers know how to
    remediate.
    """
    # Arrange — tmp_path has no .plan/project-architecture/ at all.

    # Act
    result = cmd_get_module_context(_ns(str(tmp_path)))

    # Assert
    assert result['status'] == 'not_found'
    assert 'message' in result
    assert 'suggestion' in result
    assert 'architecture discover' in result['suggestion']


@pytest.mark.parametrize(
    'project_dir_arg',
    [
        # Default invocation falls back to '.' — but in tests we pass an
        # explicit absent tmp_path subdirectory to keep cwd clean.
        'definitely-missing-subdir',
    ],
)
def test_get_module_context_not_found_message_references_data_dir(tmp_path, project_dir_arg):
    """The ``not_found`` branch surfaces the absent data-directory path.

    Pins the user-facing remediation contract: the ``file`` field reports the
    project-architecture directory the reader looked in, so callers can
    surface the exact path that needs ``architecture discover``.
    """
    # Arrange — point at a subdirectory that does not exist on disk.
    missing = tmp_path / project_dir_arg

    # Act
    result = cmd_get_module_context(_ns(str(missing)))

    # Assert
    assert result['status'] == 'not_found'
    # The reader returns the parent of _project.json (i.e., the data dir).
    assert 'project-architecture' in result['file']
