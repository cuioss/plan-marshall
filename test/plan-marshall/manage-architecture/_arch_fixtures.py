# SPDX-License-Identifier: FSL-1.1-ALv2
"""Skill-scoped shared fixtures for ``manage-architecture`` tests.

Hoisted from per-file duplicate helper definitions (D5 in
solution_outline.md). Named ``_arch_fixtures.py`` (NOT bare
``_fixtures.py``) to avoid pytest module-name collision with
``test/plan-marshall/plan-retrospective/_fixtures.py``; pytest does not
use ``__init__.py`` here, so identical bare module names would resolve
to whichever helper is imported first. The helpers are loaded explicitly
via import and never shadow ``test/conftest.py``. See
``plan-marshall:persona-module-tester`` for the canonical
sibling-fixtures convention.

Two canonical helpers:

* :func:`setup_test_project` — seeds ``_project.json`` plus per-module
  ``derived.json`` and, by default, empty per-module ``enriched.json``
  stubs. The default enrichment stub is the **superset** shape (8 fields)
  used by ``_cmd_enrich`` callers; ``test_cmd_suggest`` / ``test_enrich_*``
  tolerate the extra keys because their assertions consult only specific
  fields.
* :func:`create_test_project` — accepts a ``shape`` keyword to dispatch
  between the two genuinely-distinct module fixtures used by
  ``test_cmd_client`` (``"command_variety"``: three modules with varying
  command sets) and ``test_cmd_manage`` (``"metadata_rich"``: two modules
  with metadata, packages, dependencies, and stats).

The third candidate — ``create_test_project`` in
``test/plan-marshall/build-operations/test_extension_implementations.py``
— intentionally stays local. Its signature is
``create_test_project(build_system: str) -> Path`` and it seeds a
build-system fixture tree on disk, sharing only the name with the helpers
hoisted here. Per the D5 outline, that copy is retained with a
justification comment in its own file.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_architecture_core = _load_module('_architecture_core', '_architecture_core.py')

_save_project_meta = _architecture_core.save_project_meta
_save_module_derived = _architecture_core.save_module_derived
_save_module_enriched = _architecture_core.save_module_enriched


def _default_enrichment_stub() -> dict:
    """Superset enrichment stub shape.

    Includes every field referenced by any consumer of
    ``setup_test_project`` in this directory. ``test_cmd_enrich`` callers
    rely on the four list-shaped fields (``key_dependencies`` through
    ``best_practices``); ``test_cmd_suggest`` / ``test_enrich_*`` callers
    only consult ``skills_by_profile`` and ``skills_by_profile_reasoning``
    and tolerate the extra keys.
    """
    return {
        'responsibility': '',
        'purpose': '',
        'key_packages': {},
        'skills_by_profile': {},
        'skills_by_profile_reasoning': '',
        'key_dependencies': [],
        'internal_dependencies': [],
        'tips': [],
        'insights': [],
        'best_practices': [],
    }


_DEFAULT_SETUP_MODULE: dict[str, dict] = {
    'module-a': {
        'name': 'module-a',
        'build_systems': ['maven'],
        'paths': {'module': 'module-a', 'sources': ['src/main/java'], 'tests': ['src/test/java']},
        'metadata': {},
        'packages': {},
        # cdi-api dependency is required for test_cmd_suggest's default
        # path (suggests CDI domain). Other consumers (test_enrich_all,
        # test_cmd_enrich) are agnostic to ``dependencies`` content so the
        # superset is safe as the shared baseline.
        'dependencies': ['jakarta.enterprise.cdi-api:jakarta.enterprise:compile'],
        'commands': {},
        'stats': {'source_files': 10, 'test_files': 5},
    }
}


def seed_project(
    tmpdir: str,
    modules: dict[str, dict],
    *,
    with_enrichment_stubs: bool = False,
    enrichment_stub: dict | None = None,
) -> None:
    """Write ``_project.json`` plus per-module ``derived.json`` files.

    When ``with_enrichment_stubs`` is true, also writes a per-module
    ``enriched.json`` using ``enrichment_stub`` (defaulting to the
    superset stub from :func:`_default_enrichment_stub`).

    Drops the process-lifetime crawl memo (``crawl_all_modules`` caches by
    resolved project_dir) so a re-seed of the same tmpdir within one test is
    observed by the next crawl rather than returning a stale snapshot.
    """
    _architecture_core.invalidate_crawl_cache()
    _save_project_meta(
        {
            'name': 'test-project',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {name: {} for name in modules},
        },
        tmpdir,
    )
    for name, data in modules.items():
        _save_module_derived(name, data, tmpdir)
        if with_enrichment_stubs:
            _save_module_enriched(
                name,
                enrichment_stub if enrichment_stub is not None else _default_enrichment_stub(),
                tmpdir,
            )


def setup_test_project(
    tmpdir: str,
    modules: dict[str, dict] | None = None,
    *,
    enrichment_stub: dict | None = None,
) -> None:
    """Seed ``_project.json`` plus per-module ``derived.json`` and
    ``enriched.json`` stubs for every module.

    Canonical signature unifying the three identical definitions formerly
    in ``test_cmd_suggest.py``, ``test_enrich_add_domain.py``, and
    ``test_enrich_all.py``, plus the zero-arg variant in
    ``test_cmd_enrich.py``. Defaults to a single ``module-a`` so the
    zero-arg call site works unchanged.
    """
    if modules is None:
        modules = _DEFAULT_SETUP_MODULE
    seed_project(
        tmpdir,
        modules,
        with_enrichment_stubs=True,
        enrichment_stub=enrichment_stub,
    )


_CREATE_PROJECT_COMMAND_VARIETY: dict[str, dict] = {
    'module-a': {
        'name': 'module-a',
        'build_systems': ['maven'],
        'paths': {'module': 'module-a'},
        'commands': {'module-tests': 'python3 ...', 'verify': 'python3 ...', 'quality-gate': 'python3 ...'},
    },
    'module-b': {
        'name': 'module-b',
        'build_systems': ['maven'],
        'paths': {'module': 'module-b'},
        'commands': {'module-tests': 'python3 ...', 'verify': 'python3 ...'},
    },
    'module-c': {
        'name': 'module-c',
        'build_systems': ['npm'],
        'paths': {'module': 'module-c'},
        'commands': {'build': 'npm run build'},
    },
}


_CREATE_PROJECT_METADATA_RICH: dict[str, dict] = {
    'module-a': {
        'name': 'module-a',
        'build_systems': ['maven'],
        'paths': {
            'module': 'module-a',
            'descriptor': 'module-a/pom.xml',
            'sources': ['module-a/src/main/java'],
            'tests': ['module-a/src/test/java'],
            'readme': 'module-a/README.md',
        },
        'metadata': {'artifact_id': 'module-a', 'description': 'Module A description'},
        'packages': {'com.example.a': {'path': 'module-a/src/main/java/com/example/a'}},
        'dependencies': ['org.example:dep1:compile'],
        'stats': {'source_files': 10, 'test_files': 5},
        'commands': {
            'module-tests': 'python3 .plan/execute-script.py ...',
            'verify': 'python3 .plan/execute-script.py ...',
        },
    },
    'module-b': {
        'name': 'module-b',
        'build_systems': ['maven'],
        'paths': {'module': 'module-b'},
        'metadata': {},
        'packages': {},
        'dependencies': [],
        'stats': {},
        'commands': {},
    },
}


def create_test_project(tmpdir: str, *, shape: str) -> dict[str, dict]:
    """Seed a canonical fixture project and return its module dict.

    Replaces two same-named-but-structurally-different helpers:

    * ``shape='command_variety'`` — three modules (``module-a``,
      ``module-b``, ``module-c``) with varying command sets. Used by
      ``test_cmd_client.py`` for ``get_modules_with_command`` and
      ``cmd_modules`` tests.
    * ``shape='metadata_rich'`` — two modules with full metadata,
      package, dependency, and stats fields. Used by
      ``test_cmd_manage.py`` for ``api_discover`` /
      ``api_get_derived`` tests.
    """
    if shape == 'command_variety':
        modules = {name: dict(data) for name, data in _CREATE_PROJECT_COMMAND_VARIETY.items()}
    elif shape == 'metadata_rich':
        modules = {name: dict(data) for name, data in _CREATE_PROJECT_METADATA_RICH.items()}
    else:
        raise ValueError(
            f"Unknown create_test_project shape: {shape!r}. "
            f"Expected one of: 'command_variety', 'metadata_rich'."
        )

    seed_project(tmpdir, modules)
    return modules
