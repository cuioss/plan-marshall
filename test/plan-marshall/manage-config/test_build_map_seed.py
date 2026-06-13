#!/usr/bin/env python3
"""Tests for the marshal.json build_map seed under the top-level build block.

Covers the relocated, required build_map cluster and the three behaviours the
build_map-seed-scope fix introduces:

- build-map seed writes the aggregated {domain: [{glob, role, build_class}]}
  structure under ``build.map`` (relocated from the top level).
- Write-once: a re-seed never clobbers an existing seed, so a user correction
  made directly to the seeded entries survives.
- merge_build_map reads from ``build.map`` and fails closed
  (raises) when the block is absent — there is no override layer.
- Regression: ``build.map`` is present after seed, and the retired
  ``build_map_overrides`` / ``activation_globs`` keys are never written.

It also covers the seed AGGREGATOR WIRING: ``aggregate_build_map`` collects every
registered extension's explicit ``(pattern, role)`` routes (``classify_globs()``)
through the ``script-shared`` route deriver (``derive_globs_from_tree``, reached
via the ``extension_discovery.derive_build_map_globs`` bridge) — so a production
``.py`` file living OUTSIDE ``scripts/`` is caught because a declared route covers
it. These tests drive the aggregator end-to-end against a deterministic extension
(no ``_FAKE_AGGREGATED`` patch) so the wiring itself — not a stub — is exercised.

The three fix-specific suites at the end cover:

- **Applicability-scoping** — ``aggregate_build_map`` includes a domain's routes
  only when that domain's ``applies_to_module()`` is applicable for at least one
  discovered project module; non-applicable domains are dropped even though they
  declare routes, and an empty discovered-module set yields an empty aggregation.
- **Init-seed removal** — ``cmd_init`` / ``get_default_config()`` no longer seed
  ``build.map``; the block is materialised at wizard Step 8b
  (``build-map seed``) after architecture discovery.
- **Force reseed** — ``build-map seed --force`` clears any existing block and
  re-derives it (``action: re-derived``); the default seed stays write-once
  (``action: preserved``), and a user correction is overwritten by ``--force``.
"""

# ruff: noqa: I001, E402

import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_build_map_mod = _load_module('_cmd_build_map_for_build_map_test', '_cmd_build_map.py')
_cmd_init_mod = _load_module('_cmd_init_for_build_map_test', '_cmd_init.py')

# Resolve the SAME _config_core module the handler imported its helpers from, so
# patching aggregate_build_map there is what seed_build_map_into() actually sees.
# (_cmd_build_map does `from _config_core import seed_build_map_into`, binding the
# function to that module's globals — not to any importlib-renamed copy.)
_config_core_mod = sys.modules[_cmd_build_map_mod.seed_build_map_into.__module__]

# The _config_defaults module backing get_default_config() — exercised directly
# by the init-seed-removal suite. Resolved via _cmd_init's import so the test
# asserts against the same module object the init handler uses.
_config_defaults_mod = importlib.import_module('_config_defaults')


# A deterministic fake aggregation result so the seed tests do not depend on the
# live extension set. Mirrors the real {domain: [{glob, role, build_class}]} shape.
_FAKE_AGGREGATED = {
    'python': [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
    ],
}


def _patch_aggregate(monkeypatch):
    """Patch aggregate_build_map on the _config_core module the handler resolves
    against, so seed_build_map_into() consumes the deterministic fake."""
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED)


# =============================================================================
# Pure read/merge logic (no extension discovery)
# =============================================================================


def test_merge_build_map_returns_seed_from_build_block():
    """merge_build_map returns a deep copy of build.map unchanged."""
    # Arrange — build_map lives under the top-level build block (relocated).
    config = {'build': {'map': _FAKE_AGGREGATED}}

    # Act
    merged = _config_core_mod.merge_build_map(config)

    # Assert — same structure, deep-copied (mutating result must not touch config)
    assert merged == _FAKE_AGGREGATED
    merged['python'][0]['build_class'] = 'mutated'
    assert config['build']['map']['python'][0]['build_class'] == 'compile'


def test_merge_build_map_fails_closed_when_build_map_absent():
    """merge_build_map raises BuildMapMissingError when build.map is absent.

    There is no override layer and no silent empty-dict fallback — a missing seed
    surfaces as a structured error (fail-closed) instead of a silent no-build.
    """
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({})


def test_merge_build_map_fails_closed_when_build_block_lacks_map():
    """A build block without a map key still fails closed."""
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({'build': {'other': {}}})


@pytest.mark.parametrize('corrupt_build_map', [[], ['glob'], 'a string', 42, {'python': None}, {'python': 'not a list'}])
def test_merge_build_map_fails_closed_when_build_map_is_non_dict(corrupt_build_map):
    """A present-but-corrupt build.map raises BuildMapMissingError.

    Regression: merge_build_map previously assigned build['map'] to
    seed without a type check, so a corrupt non-dict value crashed the subsequent
    .items() deep-copy with an untyped AttributeError. Partially corrupt dicts
    (e.g. {'python': None} or {'python': 'not a list'}) also crash the inner list
    comprehension with an untyped TypeError. The hardened fail-closed guard now
    treats all corrupt build_map shapes the same as an absent one.
    """
    config = {'build': {'map': corrupt_build_map}}
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map(config)


def test_get_build_map_returns_empty_when_absent():
    """get_build_map returns {} (not an error) when build.map is absent."""
    assert _config_core_mod.get_build_map({}) == {}
    assert _config_core_mod.get_build_map({'build': {}}) == {}


def test_get_build_map_returns_relocated_block():
    """get_build_map locates the relocated build_map under the top-level build block."""
    config = {'build': {'map': _FAKE_AGGREGATED}}
    assert _config_core_mod.get_build_map(config) == _FAKE_AGGREGATED


# =============================================================================
# Seed write-once semantics (handler path)
# =============================================================================


def test_build_map_seed_writes_aggregated_structure_under_build_block(plan_context, monkeypatch):
    """build-map seed writes the aggregated {domain: [...]} structure under build.map.

    Init no longer seeds build_map, so a bare init leaves the block absent; the
    first explicit seed against the deterministic fake is the authoritative write.
    """
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — handler reports a seed action and the persisted block matches
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'
    assert result['domain_count'] == 1

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    # build_map is relocated under the top-level build block — NOT under skill_domains.
    assert config['build']['map'] == _FAKE_AGGREGATED
    assert 'build_map' not in config.get('skill_domains', {})


def test_build_map_seed_is_write_once(plan_context, monkeypatch):
    """A re-seed preserves an existing seed (write-once) — never clobbers it."""
    # Arrange — first seed writes the fake map (init no longer pre-seeds)
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    assert first['action'] == 'seeded'

    # Mutate the persisted seed to emulate a user correction (directly on the
    # seeded entries — there is no separate override layer).
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — re-seed preserved the user correction, did not clobber
    assert second['action'] == 'preserved'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['build']['map']['python'][0]['build_class'] == 'none'


def test_user_correction_survives_reseed_and_wins_at_read(plan_context, monkeypatch):
    """A direct correction to build.map survives a re-seed and wins at read."""
    # Arrange — seed, then correct an entry directly on the seeded block.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed (write-once preserves the corrected seed), then read.
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    read_result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — correction survived re-seed and wins at read
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert persisted['build']['map']['python'][0]['build_class'] == 'none'
    assert read_result['status'] == 'success'
    merged_python = {e['glob']: e for e in read_result['build_map']['python']}
    assert merged_python['scripts/*.py']['build_class'] == 'none'


def test_build_map_read_returns_seed(plan_context, monkeypatch):
    """build-map read returns the seed from build.map unchanged."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Act
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert
    assert result['status'] == 'success'
    assert result['build_map'] == _FAKE_AGGREGATED
    assert result['domain_count'] == 1


def test_build_map_read_fails_closed_when_seed_absent(plan_context):
    """build-map read returns a structured error when build.map is absent.

    Init no longer seeds the block, so a bare init already leaves build_map absent
    — read must fail closed without any pre-read stripping.
    """
    # Arrange — bare init leaves the config without a build.map block.
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — fail-closed surfaces as a structured error, not an empty success.
    assert result['status'] == 'error'
    assert 'build.map' in result['error']


# =============================================================================
# Regression: relocation + retired-key removal
# =============================================================================


def test_seed_never_writes_retired_override_keys(plan_context, monkeypatch):
    """No retired build_map_overrides key is written by the seed path.

    The override layer was dropped: the build_map under the top-level build block
    is the single source of truth, and user corrections are made directly to the
    seeded entries. The build_map cluster no longer carries any activation_globs of
    its own — pre-push activation derives from the build_map's per-entry globs.
    """
    # Arrange / Act
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — the retired override key never appears anywhere in the persisted config.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'build_map_overrides' not in config
    assert 'build_map_overrides' not in config.get('build', {})
    # The build_map cluster under build carries no activation_globs key —
    # activation derives from the per-entry globs, not a separate cluster list.
    # (The unrelated plan.phase-6-finalize.pre_push_quality_gate.activation_globs
    # field is a distinct knob and is NOT covered by this assertion.)
    assert 'activation_globs' not in config['build']
    build_map = config['build']['map']
    assert 'activation_globs' not in build_map


# =============================================================================
# Seed aggregator wiring — real tree-derivation (no _FAKE_AGGREGATED patch)
# =============================================================================
#
# These tests exercise the actual wiring: aggregate_build_map() hands every
# registered extension's portable classify_globs() vocabulary to the
# script-shared tree-deriver (derive_globs_from_tree) against the REAL tree, so
# a production .py OUTSIDE scripts/ is caught because it exists in the tree.
# Unlike the write-once tests above, NO _FAKE_AGGREGATED stub is patched — the
# aggregator runs for real against a synthetic fixture tree, with only its
# environmental collaborators redirected: the extension set it discovers and the
# project modules it scopes against (applicability ground truth).

from extension_base import (  # type: ignore[import-not-found]  # noqa: E402
    ROLE_PRODUCTION,
    ROLE_TEST,
    BuildExtensionBase,
)

# The extension_discovery module that aggregate_build_map() resolves
# derive_build_map_globs / discover_all_extensions / discover_project_modules
# from at call time. Importing it here gives the tests the same object to
# monkeypatch.
_extension_discovery_mod = importlib.import_module('extension_discovery')


# An applicable module set — one synthetic discovered module. aggregate_build_map's
# applicability filter calls discover_project_modules(project_root) and iterates
# modules.values(); the value shape only needs to round-trip through each fake
# extension's applies_to_module(), so a minimal dict suffices.
_APPLICABLE_MODULES = {'status': 'success', 'modules': {'core': {'name': 'core'}}}
_NO_MODULES = {'status': 'success', 'modules': {}}


class _PythonRouteExtension(BuildExtensionBase):
    """A real build extension declaring explicit .py routes under domain key 'python'.

    Mirrors the python domain's explicit (pattern, role) routes: an out-of-scripts
    production route (``marketplace/targets/*.py``, an fnmatch glob) plus a test
    route. The deriver collects the declared routes verbatim, so a production .py
    outside scripts/ is covered by declaring a route whose pattern matches it.
    Declares itself applicable so the applicability filter keeps its routes.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/targets/*.py', ROLE_PRODUCTION),
            ('test/*.py', ROLE_TEST),
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}


class _NoRouteExtension(BuildExtensionBase):
    """A python-domain build extension that declares no routes at all (base default).

    Declares itself applicable so the omission is attributable to the empty route
    set, not to the applicability filter.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}


# Tracked files matching the stub extensions' routes. The route deriver
# (derive_globs_from_tree) now prunes any route whose pattern matches no
# git-tracked file, so the aggregator's project_root must be a git tree carrying
# one file per route the stub declares (marketplace/targets/*.py production and
# test/*.py test), or every route would be pruned as dead.
_STUB_ROUTE_TRACKED_FILES = ['marketplace/targets/generate.py', 'test/sample_test.py']


def _make_tracked_project_root(rel_paths: list[str]) -> Path:
    """Create a git-tracked fixture tree and return its root.

    aggregate_build_map() resolves ``project_root = get_tracked_config_dir().parent``
    and the route deriver runs ``git ls-files`` under it, pruning routes whose
    pattern matches no tracked file. This builds a throwaway git repo carrying a
    file for each supplied repo-relative path so the stub routes survive the
    tree-presence filter.
    """
    root = Path(tempfile.mkdtemp(prefix='build-map-seed-tree-'))
    subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'T'], check=True)
    for rel in rel_paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    return root


def _wire_real_aggregator(
    monkeypatch,
    extension: BuildExtensionBase,
    modules: dict | None = None,
    tracked_files: list[str] | None = None,
) -> None:
    """Redirect aggregate_build_map()'s extension-set, module-discovery, and project root.

    aggregate_build_map() resolves derive_build_map_globs + discover_build_extensions
    + discover_all_extensions + discover_project_modules from the extension_discovery
    module at call time, and derives ``project_root`` from
    ``get_tracked_config_dir().parent``. The single supplied fake is wired as BOTH the
    build-extension set (route + build_class source via discover_build_extensions) AND
    the language-extension set (applicability source via discover_all_extensions) —
    each fake is a BuildExtensionBase subclass overriding classify_globs /
    get_skill_domains / applies_to_module, so it serves both roles. The discovered
    module set is patched to ``modules`` (default: one applicable module).

    The route deriver now reads the project tree to prune dead globs, so this also
    points ``project_root`` at a git-tracked fixture carrying a file for each stub
    route (``tracked_files`` defaults to the standard stub-route corpus). The
    ``PLAN_TRACKED_CONFIG_DIR`` override resolves ``get_tracked_config_dir()`` to a
    ``.plan`` subdir of that fixture, so its ``.parent`` is the tracked tree.
    """
    fake_build_entries = [{'skill': 'fake', 'path': 'fake/extension.py', 'module': extension}]
    fake_lang_entries = [{'bundle': 'fake', 'path': 'fake/extension.py', 'module': extension}]
    monkeypatch.setattr(
        _extension_discovery_mod, 'discover_build_extensions', lambda: fake_build_entries
    )
    monkeypatch.setattr(
        _extension_discovery_mod, 'discover_all_extensions', lambda: fake_lang_entries
    )
    monkeypatch.setattr(
        _extension_discovery_mod,
        'discover_project_modules',
        lambda project_root: _APPLICABLE_MODULES if modules is None else modules,
    )

    files = _STUB_ROUTE_TRACKED_FILES if tracked_files is None else tracked_files
    tracked_root = _make_tracked_project_root(files)
    # get_tracked_config_dir() returns this path; aggregate_build_map() takes its
    # .parent as project_root, so make the tracked tree the parent.
    monkeypatch.setenv('PLAN_TRACKED_CONFIG_DIR', str(tracked_root / '.plan'))


def test_aggregate_build_map_collects_route_matching_out_of_scripts_production_py(monkeypatch):
    """The aggregator collects a route matching a production .py OUTSIDE scripts/.

    This is the regression the deliverable fixes: a production file at
    ``marketplace/targets/generate.py`` (not under ``scripts/``) is covered by the
    explicit route ``marketplace/targets/*.py`` — the old static-glob seed
    would have silently missed it.
    """
    # Arrange — an extension declaring an out-of-scripts production route.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    # Act — run the REAL aggregator.
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — a production-role route in the python domain matches the
    # out-of-scripts file.
    assert 'python' in aggregated
    prod_globs = [
        entry['glob'] for entry in aggregated['python'] if entry['role'] == 'production'
    ]
    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'no declared route matched the out-of-scripts production file; globs={prod_globs}'
    )


def test_aggregate_build_map_stamps_each_entry_with_a_build_class(monkeypatch):
    """Each collected (glob, role) route is stamped with its domain's build_class.

    The aggregator's second leg: after the route deriver collects (glob, role),
    the aggregator queries the owning extension's classify_build_class(glob, role)
    and records it. A production route therefore carries the compile build_class,
    not a bare (glob, role) tuple. The build_class NAMES the canonical command
    directly (no name-to-name indirection).
    """
    # Arrange
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    # Act
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — every entry carries the three keys and a sensible build_class.
    entries = aggregated['python']
    for entry in entries:
        assert set(entry.keys()) == {'glob', 'role', 'build_class'}
    by_role = {entry['role']: entry['build_class'] for entry in entries}
    assert by_role['production'] == 'compile'
    assert by_role['test'] == 'module-tests'


def test_seed_cli_persists_route_for_out_of_scripts_glob(plan_context, monkeypatch):
    """The seed CLI persists the out-of-scripts route under build.map.

    End-to-end through the seed handler (cmd_build_map_seed): init, then seed
    against an extension declaring an out-of-scripts production route. The
    persisted build.map must carry a python-domain glob matching
    that file. Init no longer pre-seeds, so the seed writes the derived block.
    """
    # Arrange — init, wire the real aggregator against an extension declaring an
    # out-of-scripts production route.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    # Act — seed through the CLI handler.
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — handler seeded, and the persisted block carries the matching glob.
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    build_map = config['build']['map']
    assert 'python' in build_map
    prod_globs = [e['glob'] for e in build_map['python'] if e['role'] == 'production']

    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'seeded build_map missing a glob for the out-of-scripts file; globs={prod_globs}'
    )


def test_read_cli_returns_route_seed(plan_context, monkeypatch):
    """The read CLI returns the route seed, with the out-of-scripts glob intact.

    Seed against an extension declaring an out-of-scripts route, then read back
    through cmd_build_map_read: the merged build_map the read CLI returns must
    carry the python-domain glob that matches the out-of-scripts production .py.
    """
    # Arrange — init, wire, seed.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Act — read back through the CLI.
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — read succeeds and surfaces the matching glob.
    assert result['status'] == 'success'
    assert 'python' in result['build_map']
    prod_globs = [e['glob'] for e in result['build_map']['python'] if e['role'] == 'production']

    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'read CLI did not return a glob for the out-of-scripts file; globs={prod_globs}'
    )


def test_aggregate_build_map_omits_domain_with_no_routes(monkeypatch):
    """A domain whose extension declares no routes is omitted entirely.

    An extension at the base ``classify_globs()`` default (empty list) contributes
    no entries, so the python domain is dropped from the aggregated map (rather
    than appearing with an empty list). The extension declares itself applicable,
    so the omission is attributable to the empty route set — not the filter.
    """
    # Arrange — an applicable extension declaring no routes at all.
    _wire_real_aggregator(monkeypatch, _NoRouteExtension())

    # Act
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — the python domain contributed nothing and is omitted.
    assert 'python' not in aggregated


# =============================================================================
# Applicability scoping — applies_to_module() over discovered modules
# =============================================================================
#
# aggregate_build_map() includes a domain's routes only when that domain's owning
# extension's applies_to_module() returns applicable: True for at least one
# discovered project module. These tests redirect both the extension set AND the
# discovered module set so the filter is driven deterministically — a domain that
# declares routes but applies to no discovered module is dropped, and an empty
# discovered-module set yields an empty aggregation (the seed runs only after
# architecture discovery).


class _NonApplicablePythonExtension(BuildExtensionBase):
    """A python-domain build extension declaring routes but never applicable.

    Mirrors the leak the fix closes: an installed bundle whose domain does not
    apply to the project's modules (e.g. java/oci on a python-only project). It
    declares real routes via classify_globs() but its applies_to_module() always
    returns not-applicable, so the aggregator must drop its routes entirely.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('marketplace/targets/*.py', ROLE_PRODUCTION)]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}


class _RaisingApplicabilityExtension(BuildExtensionBase):
    """A python-domain build extension whose applies_to_module() raises.

    The aggregator defends each applies_to_module() call so one misbehaving
    extension cannot crash the seed — the raising extension is simply treated as
    not-applicable and dropped.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [('marketplace/targets/*.py', ROLE_PRODUCTION)]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        raise RuntimeError('boom — applies_to_module misbehaved')


def test_aggregate_includes_applicable_domain(monkeypatch):
    """A domain applicable for a discovered module keeps its routes.

    The positive control for the applicability filter: with at least one discovered
    module for which applies_to_module() is applicable, the python domain's routes
    survive aggregation unchanged.
    """
    # Arrange — an applicable extension with one discovered module.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension(), modules=_APPLICABLE_MODULES)

    # Act
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — applicable domain's routes are present.
    assert 'python' in aggregated
    by_role = {entry['role']: entry['build_class'] for entry in aggregated['python']}
    assert by_role['production'] == 'compile'
    assert by_role['test'] == 'module-tests'


def test_aggregate_excludes_non_applicable_domain_with_routes(monkeypatch):
    """An installed domain that applies to no discovered module is excluded.

    The core fix: even though the extension declares real routes via
    classify_globs(), its applies_to_module() is not-applicable for every
    discovered module, so its routes are dropped — a python-only project never
    receives routes from a domain that does not apply to its modules.
    """
    # Arrange — a route-declaring extension that is never applicable.
    _wire_real_aggregator(monkeypatch, _NonApplicablePythonExtension(), modules=_APPLICABLE_MODULES)

    # Act
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — the non-applicable domain contributed nothing.
    assert 'python' not in aggregated
    assert aggregated == {}


def test_aggregate_empty_when_no_modules_discovered(monkeypatch):
    """An empty discovered-module set yields an empty aggregation.

    With no discovered modules the applicability filter has nothing to match
    against, so the aggregation is empty rather than the unscoped full set — the
    seed runs only after architecture discovery (wizard Step 8b / sync-defaults).
    """
    # Arrange — an applicable, route-declaring extension but NO discovered modules.
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension(), modules=_NO_MODULES)

    # Act
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — no modules → empty aggregation regardless of declared routes.
    assert aggregated == {}


def test_aggregate_tolerates_raising_applies_to_module(monkeypatch):
    """A misbehaving applies_to_module() does not crash the seed; its domain drops.

    The defensive try/except around the applies_to_module() call treats a raising
    extension as not-applicable rather than propagating the exception — the seed
    completes and the raising domain is simply omitted.
    """
    # Arrange — an extension whose applies_to_module() raises, with a discovered module.
    _wire_real_aggregator(monkeypatch, _RaisingApplicabilityExtension(), modules=_APPLICABLE_MODULES)

    # Act — must not raise.
    aggregated = _config_core_mod.aggregate_build_map()

    # Assert — the raising domain is dropped; aggregation is empty.
    assert aggregated == {}


# =============================================================================
# Init-seed removal — init / get_default_config() no longer seed build_map
# =============================================================================
#
# The premature init-time auto-seed was removed: build_map is materialised only at
# wizard Step 8b (build-map seed) after architecture discovery, so the
# applicability filter has discovered modules to scope against. A bare init must
# leave the build.map block absent.


def test_fresh_init_does_not_seed_build_map(plan_context):
    """`manage-config init` no longer seeds build.map.

    Regression for the seed-ordering fix: init runs before architecture discovery,
    so it must NOT seed the (applicability-scoped) build_map. The block is absent
    after a bare init and is materialised later at wizard Step 8b.
    """
    # Arrange / Act — fresh init.
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Assert — the build.map block is absent after a bare init.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'map' not in config.get('build', {}), (
        'init must NOT seed build.map (seeded at Step 8b after architecture discovery)'
    )


def test_get_default_config_has_skill_domains_without_build_map():
    """get_default_config() returns skill_domains present but build.map absent.

    The default config no longer ships a build_map block — get_default_config()
    must return skill_domains (with at least the system domain) and no build.map
    block.
    """
    # Act
    config = _config_defaults_mod.get_default_config()

    # Assert — skill_domains present, build.map absent.
    assert 'skill_domains' in config
    assert 'system' in config['skill_domains']
    assert 'map' not in config.get('build', {})


# =============================================================================
# Force reseed — `build-map seed --force` clears and re-derives
# =============================================================================
#
# The default seed is write-once; `--force` is the explicit clear-and-re-derive
# escape hatch (the meta-project migration path). A forced reseed reports
# action: re-derived (distinct from seeded / preserved) and overwrites any
# existing block, including a user correction.


def test_force_reseed_clears_and_rederives_existing_block(plan_context, monkeypatch):
    """`seed --force` over an existing block clears and re-derives it.

    With a build_map already present, a default seed would preserve it; `--force`
    bypasses the write-once guard and re-derives the block from the current
    aggregation, reporting action: re-derived.
    """
    # Arrange — seed once (deterministic fake), so a block already exists.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))
    assert first['action'] == 'seeded'

    # Act — forced reseed.
    forced = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=True))

    # Assert — re-derived (not preserved), and the persisted block matches the
    # current aggregation.
    assert forced['status'] == 'success'
    assert forced['action'] == 're-derived'
    assert forced['domain_count'] == 1

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['map'] == _FAKE_AGGREGATED


def test_default_seed_without_force_preserves_existing_block(plan_context, monkeypatch):
    """`seed` without `--force` still preserves an existing block (write-once).

    The negative control for the force path: with an existing block, a default
    seed (force=False) reports action: preserved and leaves the block untouched.
    """
    # Arrange — seed once so a block exists.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    # Act — re-seed without force.
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    # Assert — preserved, not re-derived.
    assert second['action'] == 'preserved'


def test_force_reseed_overwrites_user_correction(plan_context, monkeypatch):
    """A user correction is overwritten by `--force` (NOT write-once).

    The default seed preserves a hand-edited entry, but `--force` is the documented
    migration escape hatch: it discards stale or hand-edited entries and re-derives
    a clean block from the current aggregation.
    """
    # Arrange — seed, then hand-edit an entry directly on the seeded block.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — forced reseed.
    forced = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=True))

    # Assert — the correction was overwritten by the re-derived aggregation.
    assert forced['action'] == 're-derived'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['build']['map']['python'][0]['build_class'] == 'compile'


# =============================================================================
# Seed-boundary dead-glob regression — the user-visible contract of D1's filter
# =============================================================================
#
# The end-to-end guarantee deliverable 1's per-route tree-presence filter exists
# to provide: after a build.map seeding pass, a declared route whose file type is
# absent from the project tree (a dead glob) does NOT appear in the persisted
# build.map, while a live route (whose pattern matches a tracked file) survives.
# This drives the REAL seed pipeline (cmd_build_map_seed → aggregate_build_map →
# derive_globs_from_tree → persisted build.map) against a deterministic extension
# declaring BOTH a live and a dead route — distinct from the unit-level filter
# coverage in test_extension_base_classify_paths.py / test_extension_base.py.


class _LiveAndDeadRouteExtension(BuildExtensionBase):
    """A python-domain build extension declaring one LIVE and one DEAD route.

    The live route (``marketplace/targets/*.py``) matches a tracked fixture file;
    the dead route (``vendor/*.tsx``) matches nothing in the fixture tree. The
    seed must persist the live glob and prune the dead one. Declares itself
    applicable so the applicability filter keeps the domain.
    """

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': 'python', 'name': 'Python', 'description': 'Test'}, 'profiles': {}}]

    def classify_globs(self) -> list[tuple[str, str]]:
        return [
            ('marketplace/targets/*.py', ROLE_PRODUCTION),  # live — fixture has a match
            ('vendor/*.tsx', ROLE_PRODUCTION),  # dead — no .tsx anywhere in the fixture
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return {'applicable': True, 'confidence': 'high', 'signals': [], 'additive_to': None, 'skills_by_profile': {}}


def test_seed_persists_live_glob_and_prunes_dead_glob(plan_context, monkeypatch):
    """End-to-end: the seeded build.map carries the live glob and NOT the dead glob.

    Genuine regression coverage for the build-map-seed-prune-dead-globs fix: against
    the unfixed deriver the dead ``vendor/*.tsx`` route would survive into the
    persisted build.map; with D1's tree-presence filter it is pruned at seed time.
    The fixture tree carries only the live route's file, so the dead route matches
    nothing and must be absent from the output.
    """
    # Arrange — init, then wire the real aggregator over a tracked tree that
    # carries the LIVE route's file but no file for the DEAD route.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(
        monkeypatch,
        _LiveAndDeadRouteExtension(),
        tracked_files=['marketplace/targets/generate.py'],
    )

    # Act — seed through the real CLI pipeline.
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'

    # Assert — the persisted build.map carries ONLY the live glob; the dead glob is absent.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    build_map = config['build']['map']
    assert 'python' in build_map
    globs = [entry['glob'] for entry in build_map['python']]
    assert 'marketplace/targets/*.py' in globs, f'live glob was pruned; globs={globs}'
    assert 'vendor/*.tsx' not in globs, f'dead glob leaked into seeded build.map; globs={globs}'
