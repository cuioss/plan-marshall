#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral unit tests for extension_discovery.py uncovered branches.

Loaded in-process via ``load_script_module`` (real filename → coverage counts).
These tests drive the extension-loading primitives, the per-aggregator helpers
that fan a discovered extension list out into skill-domains / workflow-extensions
/ retrospective-aspects / config-defaults, and the CLI handlers + main() routing
— branches the existing build-map / find_implementors / find_extension_path
suite does not reach. The aggregator helpers are exercised against in-process
stub extension modules (no dependency on the live marketplace tree) so error
paths and skip branches are deterministic.
"""

import os
import re
import types
from pathlib import Path

import file_ops
import pytest

from conftest import load_script_module


@pytest.fixture()
def plan_root_at_tmp(tmp_path, monkeypatch):
    """Resolve the plan root to an isolated tmp_path."""
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: tmp_path)


_disc = load_script_module('plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_behavior')


# =============================================================================
# Stub extension modules
# =============================================================================


class _FullStubModule:
    """A stub Axis-A extension exposing every callback the aggregators query."""

    def __init__(self, *, domains=None, triage=None, outline=None, aspects=None, raises=None):
        self._domains = domains or []
        self._triage = triage
        self._outline = outline
        self._aspects = aspects or []
        self._raises = raises or set()
        self.config_defaults_calls = []

    def get_skill_domains(self):
        if 'get_skill_domains' in self._raises:
            raise RuntimeError('boom-domains')
        return self._domains

    def provides_triage(self):
        if 'provides_triage' in self._raises:
            raise RuntimeError('boom-triage')
        return self._triage

    def provides_outline_skill(self):
        if 'provides_outline_skill' in self._raises:
            raise RuntimeError('boom-outline')
        return self._outline

    def provides_retrospective_aspects(self):
        if 'provides_retrospective_aspects' in self._raises:
            raise RuntimeError('boom-aspects')
        return self._aspects

    def config_defaults(self, project_root):
        if 'config_defaults' in self._raises:
            raise RuntimeError('boom-config')
        self.config_defaults_calls.append(project_root)


class _NoConfigDefaultsModule:
    """A module that deliberately lacks a config_defaults attribute."""


# =============================================================================
# load_extension_module — Axis-A loader
# =============================================================================


def _loaded_class_name(instance) -> str | None:
    """The loaded instance's class name, or ``None`` when nothing was loaded."""
    return None if instance is None else type(instance).__name__


@pytest.mark.parametrize(
    ('module_source', 'expected_class_name'),
    [
        ('class Extension:\n    pass\n', 'Extension'),
        ('VALUE = 1\n', None),
        ('raise RuntimeError("explode at import")\n', None),
    ],
    ids=['exposes-extension-class', 'no-extension-class', 'raises-during-exec'],
)
def test_load_extension_module(tmp_path, module_source, expected_class_name):
    """An Axis-A extension loads to an ``Extension`` instance, or to ``None``.

    Both failure rows return ``None`` rather than propagating: a bundle whose
    ``extension.py`` exposes no ``Extension`` class, and one that raises while
    executing. The positive row is their matched control, so a loader that had
    collapsed to always returning ``None`` fails here rather than satisfying both.
    """
    ext = tmp_path / 'extension.py'
    ext.write_text(module_source, encoding='utf-8')

    instance = _disc.load_extension_module(ext, 'my-bundle')

    assert _loaded_class_name(instance) == expected_class_name


# =============================================================================
# load_build_extension_module — Axis-B loader
# =============================================================================


@pytest.mark.parametrize(
    ('module_source', 'expected_class_name'),
    [
        ('class BuildExtension:\n    pass\n', 'BuildExtension'),
        ('class NotIt:\n    pass\n', None),
        ('1 / 0\n', None),
    ],
    ids=['exposes-build-extension-class', 'no-build-extension-class', 'raises-during-exec'],
)
def test_load_build_extension_module(tmp_path, module_source, expected_class_name):
    """An Axis-B extension loads to a ``BuildExtension`` instance, or to ``None``.

    The same three outcomes as the Axis-A loader above, against the class name
    that hierarchy requires — a module exposing some OTHER class is as unusable
    here as one exposing none.
    """
    ext = tmp_path / 'extension.py'
    ext.write_text(module_source, encoding='utf-8')

    instance = _disc.load_build_extension_module(ext, 'build-foo')

    assert _loaded_class_name(instance) == expected_class_name


# =============================================================================
# get_skill_domains_from_extensions
# =============================================================================


def test_get_skill_domains_collects_and_attributes_bundle():
    """Each returned domain is copied and stamped with its owning bundle."""
    module = _FullStubModule(domains=[{'domain': 'general-dev', 'profiles': {}}])
    extensions = [{'bundle': 'pm-x', 'module': module}]

    domains = _disc.get_skill_domains_from_extensions(extensions)

    assert domains == [{'domain': 'general-dev', 'profiles': {}, 'bundle': 'pm-x'}]


def test_get_skill_domains_skips_entries_without_module():
    """An extension entry lacking a module contributes no domains."""
    domains = _disc.get_skill_domains_from_extensions([{'bundle': 'pm-x', 'module': None}])

    assert domains == []


def test_get_skill_domains_skips_domain_without_domain_key():
    """A domain dict missing the 'domain' key is skipped."""
    module = _FullStubModule(domains=[{'profiles': {}}, {'domain': 'java', 'profiles': {}}])
    extensions = [{'bundle': 'pm-x', 'module': module}]

    domains = _disc.get_skill_domains_from_extensions(extensions)

    assert domains == [{'domain': 'java', 'profiles': {}, 'bundle': 'pm-x'}]


def test_get_skill_domains_swallows_callback_exception():
    """An extension whose get_skill_domains raises is skipped, not propagated."""
    raising = _FullStubModule(raises={'get_skill_domains'})
    good = _FullStubModule(domains=[{'domain': 'python', 'profiles': {}}])
    extensions = [
        {'bundle': 'bad', 'module': raising},
        {'bundle': 'good', 'module': good},
    ]

    domains = _disc.get_skill_domains_from_extensions(extensions)

    assert domains == [{'domain': 'python', 'profiles': {}, 'bundle': 'good'}]


# =============================================================================
# get_workflow_extensions_from_extensions
# =============================================================================


def test_get_workflow_extensions_collects_triage_and_outline():
    """A module declaring triage + outline skill surfaces both under its bundle."""
    module = _FullStubModule(triage='pm-x:ext-triage-x', outline='pm-x:ext-outline-x')
    extensions = [{'bundle': 'pm-x', 'module': module}]

    result = _disc.get_workflow_extensions_from_extensions(extensions)

    assert result == {'pm-x': {'triage': 'pm-x:ext-triage-x', 'outline_skill': 'pm-x:ext-outline-x'}}


def test_get_workflow_extensions_omits_bundle_with_no_declarations():
    """A module declaring neither triage nor outline contributes no entry."""
    module = _FullStubModule(triage=None, outline=None)
    extensions = [{'bundle': 'pm-x', 'module': module}]

    assert _disc.get_workflow_extensions_from_extensions(extensions) == {}


def test_get_workflow_extensions_swallows_callback_exceptions():
    """Exceptions from the provides_* callbacks are swallowed per-callback."""
    module = _FullStubModule(raises={'provides_triage'}, outline='pm-x:ext-outline-x')
    extensions = [{'bundle': 'pm-x', 'module': module}]

    result = _disc.get_workflow_extensions_from_extensions(extensions)

    # provides_triage raised (swallowed); outline still collected.
    assert result == {'pm-x': {'outline_skill': 'pm-x:ext-outline-x'}}


def test_get_workflow_extensions_skips_entries_without_module():
    """An entry with no module is skipped before any callback runs."""
    assert _disc.get_workflow_extensions_from_extensions([{'bundle': 'pm-x', 'module': None}]) == {}


# =============================================================================
# get_retrospective_aspects_from_extensions
# =============================================================================


def test_get_retrospective_aspects_collects_and_attributes_bundle():
    """Each declared aspect is copied and stamped with its bundle."""
    module = _FullStubModule(aspects=[{'aspect': 'token-economics', 'domain': 'system'}])
    extensions = [{'bundle': 'pm-x', 'module': module}]

    aspects = _disc.get_retrospective_aspects_from_extensions(extensions)

    assert aspects == [{'aspect': 'token-economics', 'domain': 'system', 'bundle': 'pm-x'}]


def test_get_retrospective_aspects_skips_aspect_without_aspect_key():
    """An aspect dict lacking the 'aspect' key is skipped."""
    module = _FullStubModule(aspects=[{'domain': 'system'}, {'aspect': 'x', 'domain': 'd'}])
    extensions = [{'bundle': 'pm-x', 'module': module}]

    aspects = _disc.get_retrospective_aspects_from_extensions(extensions)

    assert aspects == [{'aspect': 'x', 'domain': 'd', 'bundle': 'pm-x'}]


def test_get_retrospective_aspects_swallows_callback_exception():
    """A module whose callback raises is skipped (logged, continue)."""
    raising = _FullStubModule(raises={'provides_retrospective_aspects'})
    good = _FullStubModule(aspects=[{'aspect': 'y', 'domain': 'd'}])
    extensions = [
        {'bundle': 'bad', 'module': raising},
        {'bundle': 'good', 'module': good},
    ]

    aspects = _disc.get_retrospective_aspects_from_extensions(extensions)

    assert aspects == [{'aspect': 'y', 'domain': 'd', 'bundle': 'good'}]


def test_get_retrospective_aspects_skips_entries_without_module():
    """An entry with no module contributes nothing."""
    assert _disc.get_retrospective_aspects_from_extensions([{'bundle': 'pm-x', 'module': None}]) == []


# =============================================================================
# apply_config_defaults — pre_discovered path (applicability already filtered)
# =============================================================================


def test_apply_config_defaults_calls_each_applicable_module(tmp_path):
    """With pre_discovered extensions, config_defaults is invoked once per module."""
    module = _FullStubModule()
    result = _disc.apply_config_defaults(tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': module}])

    assert result['extensions_called'] == 1
    assert result['extensions_skipped'] == 0
    assert result['errors'] == []
    assert module.config_defaults_calls == [str(tmp_path)]


def test_apply_config_defaults_skips_module_without_callback(tmp_path):
    """A module lacking config_defaults is counted as skipped."""
    result = _disc.apply_config_defaults(
        tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': _NoConfigDefaultsModule()}]
    )

    assert result['extensions_called'] == 0
    assert result['extensions_skipped'] == 1


def test_apply_config_defaults_skips_entry_without_module(tmp_path):
    """An extension entry with no module is skipped."""
    result = _disc.apply_config_defaults(tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': None}])

    assert result['extensions_skipped'] == 1
    assert result['extensions_called'] == 0


def test_apply_config_defaults_records_callback_error(tmp_path):
    """A config_defaults that raises is recorded in the errors list."""
    module = _FullStubModule(raises={'config_defaults'})
    result = _disc.apply_config_defaults(tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': module}])

    assert result['extensions_called'] == 0
    assert len(result['errors']) == 1
    assert result['errors'][0].startswith('pm-x:')


# =============================================================================
# CLI handlers + main() routing
# =============================================================================


def test_cmd_apply_config_defaults_errors_on_missing_project_dir(tmp_path, capsys):
    """cmd_apply_config_defaults emits an error TOON when the project dir is absent."""
    missing = tmp_path / 'does-not-exist'
    args = types.SimpleNamespace(project_dir=str(missing))

    rc = _disc.cmd_apply_config_defaults(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert 'error' in out
    assert 'Project directory not found' in out


def test_cmd_implementors_emits_zero_count_for_unknown_ext_point(capsys):
    """cmd_implementors prints a count:0 TOON for an ext-point no doc declares."""
    args = types.SimpleNamespace(ext_point='plan-marshall:extension-api/standards/ext-point-does-not-exist')

    rc = _disc.cmd_implementors(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert 'count: 0' in out


def test_main_implementors_dispatch_returns_zero(monkeypatch, capsys):
    """main() routes the implementors subcommand (no project routing) and returns 0."""
    monkeypatch.setattr(
        _disc.sys,
        'argv',
        [
            'extension_discovery.py',
            'implementors',
            '--ext-point',
            'plan-marshall:extension-api/standards/ext-point-does-not-exist',
        ],
    )

    rc = _disc.main()

    assert rc == 0
    assert 'status: success' in capsys.readouterr().out


def test_main_mutually_exclusive_plan_id_and_project_dir_returns_two(monkeypatch, capsys):
    """main() returns 2 when both --plan-id and an explicit --project-dir are given."""
    monkeypatch.setattr(
        _disc.sys,
        'argv',
        [
            'extension_discovery.py',
            'apply-config-defaults',
            '--project-dir',
            '/some/explicit/path',
            '--plan-id',
            'some-plan',
        ],
    )

    rc = _disc.main()

    assert rc == 2
    # The mutually-exclusive error is serialized to stdout as TOON.
    assert capsys.readouterr().out.strip() != ''


# =============================================================================
# _scan_project_for_implementors — cache-tree discovery fix (Bug A)
# =============================================================================
#
# Regression coverage for the project-local finalize-step discovery fix: the
# scanner anchors on the PROJECT root resolved cwd-relatively via
# ``file_ops._resolve_plan_root`` — NOT on the running script's ``__file__``.
# The former ``configurable_contract._repo_root()`` anchor resolved into the
# plugin cache tree when the scanning code shipped from the cache, where
# ``.claude/skills/`` does not exist, so every ``project:finalize-step-*`` step
# was silently missed. These tests pin the project-root-anchored behavior by
# monkeypatching ``_resolve_plan_root`` (the resolver the fix introduced).

_FINALIZE_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-finalize-step'
_VERIFY_STEP_EXT_POINT = 'plan-marshall:extension-api/standards/ext-point-build-verify-step'


def _write_finalize_step(skills_root, dir_name, *, implements, name=None, order=0):
    """Create a project-local ``{dir_name}/SKILL.md`` declaring ``implements``.

    ``skills_root`` and parents are created on demand so callers pass a
    not-yet-existing ``.claude/skills`` path.
    """
    step_dir = skills_root / dir_name
    step_dir.mkdir(parents=True, exist_ok=True)
    lines = ['---', f'implements: {implements}']
    if name is not None:
        lines.append(f'name: {name}')
    lines.extend([f'order: {order}', '---', '', '# Body', ''])
    (step_dir / 'SKILL.md').write_text('\n'.join(lines), encoding='utf-8')


def test_scan_project_discovers_step_from_cwd_resolved_root(tmp_path, plan_root_at_tmp):
    """Bug A regression: a project-local finalize step is discovered from the
    PROJECT root resolved by ``_resolve_plan_root``, independent of the scanning
    script's ``__file__``. The discovered record's ``path`` is anchored under the
    cwd-resolved project root — the property that makes discovery correct from a
    plugin-cache execution context, where a ``__file__``-derived anchor would miss
    it.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(skills_root, 'finalize-step-foo', implements=_FINALIZE_STEP_EXT_POINT, name='foo', order=10)

    records = _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT)

    assert len(records) == 1
    rec = records[0]
    # Step id is PATH-derived (``project:{skill-dir}``), not the SKILL.md name.
    assert rec['name'] == 'project:finalize-step-foo'
    assert rec['source'] == 'project'
    assert rec['order'] == 10
    # Anchored under the cwd-resolved project root, NOT the script's __file__ tree.
    assert rec['path'].startswith(str(tmp_path))


def test_scan_project_returns_empty_when_root_unresolvable(monkeypatch):
    """The None-guard the fix added: an unresolvable project root yields no
    records (rather than raising or anchoring on ``__file__``).
    """
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: None)

    assert _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT) == []


def test_scan_project_returns_empty_when_no_claude_skills_dir(plan_root_at_tmp):
    """A resolved project root without a ``.claude/skills/`` directory yields no
    records — the consumer-project case (no meta-project project-local steps).
    """

    assert _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT) == []


def test_scan_project_skips_step_not_declaring_ext_point(tmp_path, plan_root_at_tmp):
    """Per-ext-point filtering keeps surfaces disjoint: a ``finalize-step-*`` dir
    declaring a DIFFERENT ext-point is not returned for a finalize-step query.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(skills_root, 'finalize-step-match', implements=_FINALIZE_STEP_EXT_POINT, name='match')
    _write_finalize_step(skills_root, 'finalize-step-other', implements=_VERIFY_STEP_EXT_POINT, name='other')

    records = _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT)

    assert [rec['name'] for rec in records] == ['project:finalize-step-match']


def test_scan_project_ignores_non_finalize_step_dirs(tmp_path, plan_root_at_tmp):
    """Only ``finalize-step-*`` directories are scanned — a sibling skill dir that
    declares the ext-point but is not named ``finalize-step-*`` is ignored.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(skills_root, 'some-other-skill', implements=_FINALIZE_STEP_EXT_POINT, name='nope')

    assert _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT) == []


# =============================================================================
# _scan_skills_roots_for_implementors — versioned-cache-layout discovery fix
# =============================================================================
#
# Regression coverage for the bundle-optional implementor discovery fix: the scan
# resolves each bundle's ``skills`` root version-dir-aware via
# ``_resolve_bundle_skills_root`` — probing the flat source layout
# (``{bundle}/skills``) AND the deployed plugin cache layout
# (``{bundle}/{version}/skills``). A flat-only probe silently found ZERO
# bundle-optional implementors when the scan ran from the cache (where
# ``{bundle}/skills`` does not exist), blocking manifest compose on the
# ``plan-marshall:plan-retrospective`` / ``plan-marshall:automatic-review`` steps.


def test_resolve_bundle_skills_root_prefers_flat_source(tmp_path):
    """The flat source layout ``{bundle}/skills`` wins when present."""
    bundle_dir = tmp_path / 'plan-marshall'
    (bundle_dir / 'skills').mkdir(parents=True)
    assert _disc._resolve_bundle_skills_root(bundle_dir) == bundle_dir / 'skills'


def test_resolve_bundle_skills_root_picks_newest_versioned(tmp_path):
    """With no flat layout, the newest ``{version}/skills`` dir is chosen."""
    bundle_dir = tmp_path / 'plan-marshall'
    for version in ('0.1.1068', '0.1.1105', '0.1.1090'):
        (bundle_dir / version / 'skills').mkdir(parents=True)
    # 0.1.1105 is numerically newest, not lexicographically first.
    assert _disc._resolve_bundle_skills_root(bundle_dir) == bundle_dir / '0.1.1105' / 'skills'


def test_resolve_bundle_skills_root_none_when_no_skills(tmp_path):
    """A bundle dir with neither a flat nor a versioned ``skills`` root yields None."""
    bundle_dir = tmp_path / 'plan-marshall'
    (bundle_dir / '0.1.1105' / 'not-skills').mkdir(parents=True)
    assert _disc._resolve_bundle_skills_root(bundle_dir) is None


def test_scan_skills_roots_discovers_bundle_optional_from_versioned_cache(tmp_path, monkeypatch):
    """A bundle-optional finalize step is discovered from the versioned CACHE layout
    (``{bundle}/{version}/skills/...``) even when the source-tree root contributes
    nothing — the property that makes discovery correct from a plugin-cache
    execution context, where a flat ``{bundle}/skills`` probe found nothing.
    """
    cache_root = tmp_path / 'cache'
    versioned_skills = cache_root / 'plan-marshall' / '0.1-BETA' / 'skills'
    _write_finalize_step(
        versioned_skills,
        'plan-retrospective',
        implements=_FINALIZE_STEP_EXT_POINT,
        name='plan-retrospective',
    )
    # Source root contributes nothing (nonexistent), so the cache root is the only
    # scannable root — forcing the versioned-layout branch.
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: tmp_path / 'no-source')
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: (str(cache_root),))

    records = _disc._scan_skills_roots_for_implementors(_FINALIZE_STEP_EXT_POINT)

    names = [rec['name'] for rec in records]
    assert 'plan-marshall:plan-retrospective' in names
    rec = next(r for r in records if r['name'] == 'plan-marshall:plan-retrospective')
    assert rec['source'] == 'bundle-optional'


def test_scan_skills_roots_discovers_from_flat_source(tmp_path, monkeypatch):
    """The flat source layout still resolves after the fix (both layouts work)."""
    source_root = tmp_path / 'src'
    flat_skills = source_root / 'plan-marshall' / 'skills'
    _write_finalize_step(
        flat_skills,
        'plan-retrospective',
        implements=_FINALIZE_STEP_EXT_POINT,
        name='plan-retrospective',
    )
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: source_root)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: ())

    records = _disc._scan_skills_roots_for_implementors(_FINALIZE_STEP_EXT_POINT)

    assert 'plan-marshall:plan-retrospective' in [rec['name'] for rec in records]


def test_scan_skills_roots_dedups_bundle_seen_in_both_layouts(tmp_path, monkeypatch):
    """A bundle:skill present in BOTH the flat source root and the versioned cache
    root is emitted ONCE — the step_id dedup survives the version-dir nesting.
    """
    source_root = tmp_path / 'src'
    _write_finalize_step(
        source_root / 'plan-marshall' / 'skills',
        'plan-retrospective',
        implements=_FINALIZE_STEP_EXT_POINT,
        name='plan-retrospective',
    )
    cache_root = tmp_path / 'cache'
    _write_finalize_step(
        cache_root / 'plan-marshall' / '0.1-BETA' / 'skills',
        'plan-retrospective',
        implements=_FINALIZE_STEP_EXT_POINT,
        name='plan-retrospective',
    )
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: source_root)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: (str(cache_root),))

    records = _disc._scan_skills_roots_for_implementors(_FINALIZE_STEP_EXT_POINT)

    matches = [rec for rec in records if rec['name'] == 'plan-marshall:plan-retrospective']
    assert len(matches) == 1


# =============================================================================
# get_marketplace_bundles_path — prefers the cwd-relative SOURCE tree
# =============================================================================


def test_get_marketplace_bundles_path_prefers_cwd_source(tmp_path, monkeypatch):
    """The source ``marketplace/bundles`` resolved cwd-relatively wins over the
    ``Path(__file__)``-derived fallback, keeping meta-project discovery on the
    fresh authored tree.
    """
    sentinel = tmp_path / 'some' / 'marketplace' / 'bundles'
    sentinel.mkdir(parents=True)
    monkeypatch.setattr(_disc, 'find_marketplace_path', lambda: sentinel)
    assert _disc.get_marketplace_bundles_path() == sentinel


def test_get_marketplace_bundles_path_falls_back_when_no_source(monkeypatch):
    """When no cwd source tree resolves, it falls back to the ``__file__`` /
    cache resolution rather than raising.
    """
    monkeypatch.setattr(_disc, 'find_marketplace_path', lambda: None)
    result = _disc.get_marketplace_bundles_path()
    assert result.is_dir()


# =============================================================================
# Declaration surface == read surface (ext-point-finalize-step)
# =============================================================================
#
# The ext-point document is the DECLARATION and ``find_implementors()``'s record
# is the READ. Both directions are asserted, and both are DERIVED — from the live
# discovered population and from the document's own tables — never from a
# hand-written key list here. A field added later is therefore covered with no
# edit to this module, which is the whole point: a literal list in the test would
# reintroduce exactly the hand-maintained enumeration the ext-point exists to
# remove. Per ADR-017 each assertion resolves its contract from the target's own
# declaration and FAILS CLOSED when it cannot resolve it, so an unparseable doc
# or an empty population is a failure rather than a vacuous pass.

_IDENT_RE = re.compile(r'`([A-Za-z_][A-Za-z0-9_]*)`')


def _ext_point_doc_text() -> str:
    """The finalize-step ext-point document's text, via the module's own resolver.

    Fails closed: an unresolvable document is a failure, not an empty contract.
    """
    doc = (
        _disc.get_marketplace_bundles_path()
        / 'plan-marshall'
        / 'skills'
        / 'extension-api'
        / 'standards'
        / 'ext-point-finalize-step.md'
    )
    assert doc.is_file(), f'ext-point doc unresolvable at {doc}; declaration surface cannot be derived'
    # ``_disc`` is loaded dynamically, so the path chain above is untyped; str()
    # pins the declared return rather than leaking Any into every caller.
    return str(doc.read_text(encoding='utf-8'))


def _markdown_table_rows(text: str, header_first_cell: str) -> list[list[str]]:
    """Every body row of the first markdown table whose first header cell matches.

    Returns each row as its list of stripped cells. Selecting the table by its
    first HEADER cell — not by the presence of some column — is what keeps this
    pointed at one table in a document that carries several.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if not cells or cells[0].lower() != header_first_cell.lower():
            continue
        rows: list[list[str]] = []
        for raw in lines[index + 2 :]:  # +2 skips the header separator row
            if not raw.startswith('|'):
                break
            rows.append([cell.strip() for cell in raw.strip().strip('|').split('|')])
        return rows
    return []


def test_every_record_key_is_declared_in_the_ext_point_document():
    """No undeclared read: every key the live record carries is declared.

    The record key set is the UNION over the discovered population rather than
    one record's keys, because ``verification_profile`` is surfaced only when a
    doc declares it — reading a single record would miss a conditionally-present
    key entirely. Fails when a key is added to the record without a matching row
    in either the Implementor-Frontmatter table or the record-key provenance
    table.
    """
    records = _disc.find_implementors(_FINALIZE_STEP_EXT_POINT)
    assert records, 'no finalize-step implementors discovered; the population is unresolvable, so nothing is asserted'

    record_keys: set[str] = set()
    for record in records:
        record_keys.update(record)

    text = _ext_point_doc_text()
    frontmatter_keys = {ident for row in _markdown_table_rows(text, 'Field') for ident in _IDENT_RE.findall(row[0])}
    provenance_keys = {ident for row in _markdown_table_rows(text, 'Record key') for ident in _IDENT_RE.findall(row[0])}
    assert frontmatter_keys, 'Implementor-Frontmatter table not found; declaration surface unresolvable'
    assert provenance_keys, 'record-key provenance table not found; derived-key declarations unresolvable'

    undeclared = record_keys - (frontmatter_keys | provenance_keys)
    assert not undeclared, (
        f'record keys carried but never declared in ext-point-finalize-step.md: {sorted(undeclared)}. '
        'Add a row declaring each, or stop emitting it.'
    )


#: Repo root, derived from the marketplace/bundles path this module already
#: resolves — used to scan both ``marketplace/`` and ``test/`` for real
#: frontmatter-field consumers, never hand-maintained as a second path.
def _repo_root() -> Path:
    # ``_disc`` is loaded dynamically, so the path chain is untyped; Path()
    # pins the declared return rather than leaking Any into every caller —
    # the same pattern _ext_point_doc_text() uses above.
    return Path(_disc.get_marketplace_bundles_path()).parent.parent


def _code_read_keys(candidate_keys: set[str]) -> set[str]:
    """The subset of ``candidate_keys`` with a REAL Python consumer somewhere
    in the shipped tree — script or test alike.

    A field counts as code-read when its bare name appears as a quoted string
    literal (``'name'`` or ``"name"``) in some ``.py`` file under
    ``marketplace/`` or ``test/``. That shape catches every way this codebase
    actually reads a frontmatter field: a ``_read_frontmatter_fields(doc,
    (KEY,))`` call site, a step's own lightweight direct parser (e.g.
    ``mutates_source``'s plugin-doctor analyzer, which never goes through the
    shared helper), and a guard test that parses the field to assert against
    it. A field mentioned only in prose or a docstring — never as a quoted
    dict-key literal — does NOT count; that distinction is exactly what
    the refuted premise this test replaces conflated.
    """
    patterns = {key: re.compile(f"""['"]{re.escape(key)}['"]""") for key in candidate_keys}
    remaining = set(candidate_keys)
    found: set[str] = set()
    repo_root = _repo_root()
    py_files = sorted(repo_root.glob('marketplace/**/*.py')) + sorted(repo_root.glob('test/**/*.py'))
    for py_file in py_files:
        if not remaining:
            break
        content = py_file.read_text(encoding='utf-8')
        matched = {key for key in remaining if patterns[key].search(content)}
        found |= matched
        remaining -= matched
    return found


#: The word an agent-only reader's declared contract names its reader by — the
#: shape the ``advances_main_via_rebase`` exception already uses ("the
#: orchestrating agent follows directly"). Checked per SENTENCE, not per
#: paragraph: the field's own introductory list sentence names every
#: Conditional/Optional field in one breath, so a paragraph-wide co-occurrence
#: would credit all of them with whichever ONE field's sentence names "agent".
_AGENT_CONSUMER_TOKEN = 'agent'

#: A sentence boundary in this document's prose — punctuation followed by
#: whitespace and either a capital letter or a backtick-quoted identifier,
#: which is how a new sentence starts here.
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z`])')


def _agent_declared_keys(candidate_keys: set[str], text: str) -> set[str]:
    """Fields whose consuming contract is EXPLICITLY named as agent-only.

    Per field: the field's backtick-quoted name must co-occur with
    :data:`_AGENT_CONSUMER_TOKEN` inside the SAME sentence somewhere in the
    document — a checkable fact naming that one field's reader, not an
    inference from the Required column and not credited to it merely by
    sharing a paragraph with a sentence that names a DIFFERENT field's reader.
    """
    sentences = _SENTENCE_SPLIT.split(text)
    declared: set[str] = set()
    for key in candidate_keys:
        marker = f'`{key}`'
        if any(marker in sentence and _AGENT_CONSUMER_TOKEN in sentence for sentence in sentences):
            declared.add(key)
    return declared


def test_every_declared_field_has_a_reader():
    """No unread declaration: every declared field is resolved by some consumer.

    Two mechanically distinct arms, never a Required-column marking alone —
    the refuted premise this test replaces treated ``Conditional`` / ``Optional``
    / ``Never`` as its own proof of a reader, which this plan's own self-review
    (finding a9de78) disproved for ``advances_main_via_rebase``: a complete-
    coverage sweep found it in NO Python file at all, so a field marked
    ``Optional`` with no consumer of any kind would have passed unnoticed.

    - **Code-read**: a real quoted-literal consumer exists somewhere in
      ``marketplace/`` or ``test/`` (:func:`_code_read_keys`).
    - **Agent-only**: no code consumer exists, but the document explicitly
      names an agent-followed contract for that field
      (:func:`_agent_declared_keys`) — a declared, checkable fact, not an
      inference from the Required column.

    Both populations publish their size so a zero cannot pass as a clean
    sweep, and the fields covered by neither arm are the unread declarations.
    """
    text = _ext_point_doc_text()
    rows = _markdown_table_rows(text, 'Field')
    assert rows, 'Implementor-Frontmatter table not found; declaration surface unresolvable'

    declared_keys: dict[str, str] = {}
    for row in rows:
        idents = _IDENT_RE.findall(row[0])
        if not idents:
            continue
        declared_keys[idents[0]] = row[2] if len(row) > 2 else ''

    assert declared_keys, 'No field rows parsed from the Implementor-Frontmatter table'

    always_on_keys = set(_disc._IMPLEMENTOR_FRONTMATTER_KEYS)
    candidate_keys = set(declared_keys) - always_on_keys

    code_read = _code_read_keys(candidate_keys)
    still_candidate = candidate_keys - code_read
    agent_declared = _agent_declared_keys(still_candidate, text)

    unread = sorted(candidate_keys - code_read - agent_declared)

    print(
        f'field-reader populations: always_on={len(always_on_keys)} '
        f'code_read={len(code_read)} agent_declared={len(agent_declared)} '
        f'unread={len(unread)}'
    )

    assert not unread, (
        f'fields declared in ext-point-finalize-step.md with no code consumer '
        f'({sorted(candidate_keys - code_read)}) AND no explicit agent-only '
        f'contract naming them alongside {_AGENT_CONSUMER_TOKEN!r}: {unread}. '
        'Either wire a reader, name the agent-followed contract explicitly, or '
        'drop the row — a Required-column marking alone is not evidence of a reader.'
    )


# =============================================================================
# _implementor_scan_surfaces_resolve — bundle-root readability
# =============================================================================
#
# The bundle ``skills`` roots surface is index 2 of the returned list (see the
# function docstring): the marketplace bundles root plus every plugin cache root,
# reduced to one bool. ``is_dir()`` is true for a directory that exists but
# denies ``iterdir()``, and the scanner swallows that ``OSError`` and skips the
# root — so a probe that stopped at ``is_dir()`` reported the surface resolved
# while the scan ran over nothing, the fail-open state the discriminator exists
# to prevent.

_BUNDLE_ROOTS_SURFACE_INDEX = 2


def test_readable_bundle_root_resolves_the_bundle_surface(tmp_path, monkeypatch):
    """Positive control: a readable bundle root resolves the bundle-roots surface.

    Without this direction a probe that had collapsed to always returning
    ``False`` would satisfy the unreadable-root tests below.
    """
    bundles = tmp_path / 'bundles'
    (bundles / 'a-bundle' / 'skills' / 'a-skill').mkdir(parents=True)
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: bundles)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: [])

    assert _disc._implementor_scan_surfaces_resolve()[_BUNDLE_ROOTS_SURFACE_INDEX] is True


@pytest.mark.skipif(
    hasattr(os, 'geteuid') and os.geteuid() == 0,
    reason='a root host bypasses the file mode, so iterdir() cannot be made to fail',
)
@pytest.mark.parametrize('unreadable_kind', ['bundles', 'cache'])
def test_unreadable_root_leaves_the_bundle_surface_unresolved(tmp_path, monkeypatch, unreadable_kind):
    """A bundle OR cache root that exists but denies ``iterdir()`` is unresolved.

    Both root kinds are covered: an unreadable marketplace bundles root (the
    "source tree exists but cannot be read" case) and an unreadable plugin cache
    root (the deployed-cache counterpart). ``is_dir()`` alone would report the
    surface resolved in both, while the scanner silently dropped the root's
    implementors and ``find_implementors_with_status`` reported a complete scan.
    """
    denied = tmp_path / 'denied'
    denied.mkdir()
    if unreadable_kind == 'bundles':
        bundles, cache_roots = denied, []
    else:
        # The bundles root is absent, so only the cache root is probed.
        bundles, cache_roots = tmp_path / 'absent-bundles', [str(denied)]
    monkeypatch.setattr(_disc, 'get_marketplace_bundles_path', lambda: bundles)
    monkeypatch.setattr(_disc, 'get_bundle_cache_roots', lambda: list(cache_roots))

    original_mode = denied.stat().st_mode
    try:
        os.chmod(denied, 0o000)
        assert _disc._implementor_scan_surfaces_resolve()[_BUNDLE_ROOTS_SURFACE_INDEX] is False
        status = _disc.find_implementors_with_status(_FINALIZE_STEP_EXT_POINT)
    finally:
        os.chmod(denied, original_mode)

    assert status['status'] == 'unresolved'


# =============================================================================
# _implementor_scan_surfaces_resolve — phase-6 / phase-5 step-doc surfaces
# =============================================================================
#
# Surfaces 0 and 1 are the phase-6-finalize step-doc root and the phase-5-execute
# verify-step standards root. The phase-6 scan walks the skill dir's `workflow/`
# AND `standards/` subdirectories, so a skill dir that exists but lacks one of
# them is a PARTIAL scan: every step doc rooted in the missing subdirectory
# (`default:push` lives in `workflow/`) is invisible to it, while the old
# `is_dir()`-only probe reported the surface resolved. The probe must require
# both subdirectories, readable, and every `*.md` step document readable — an
# unreadable doc is swallowed to `[]` by `read_implements_field`, so the step
# would otherwise read as dead.

_PHASE6_SURFACE_INDEX = 0
_PHASE5_SURFACE_INDEX = 1

# A minimal finalize-step body doc: declares the ext-point and an int order, so
# a scan that reaches it surfaces a live step record.
_PARTIAL_STEP_DOC = (
    '---\n'
    'name: default:partial-live-step\n'
    'order: 10\n'
    'implements: plan-marshall:extension-api/standards/ext-point-finalize-step\n'
    '---\n\n'
    '# Partial live step\n'
)


def test_partial_phase6_dir_without_workflow_leaves_the_surface_unresolved(tmp_path, monkeypatch):
    """A phase-6 dir carrying only `standards/` is a partial scan — unknown, not dead.

    The deliverable's core shape: the fixture skill directory has a readable
    `standards/` (the scan DOES find a live step there) but no `workflow/`, so
    every workflow-rooted step (`default:push`) cannot be enumerated. Finding
    some implementors is still not an answered scan.
    """
    import configurable_contract as cc

    skill_dir = tmp_path / 'phase-6-finalize'
    (skill_dir / 'standards').mkdir(parents=True)
    (skill_dir / 'standards' / 'partial-live-step.md').write_text(_PARTIAL_STEP_DOC, encoding='utf-8')
    monkeypatch.setattr(cc, '_phase_6_skill_dir', lambda: skill_dir)

    assert _disc._implementor_scan_surfaces_resolve()[_PHASE6_SURFACE_INDEX] is False

    status = _disc.find_implementors_with_status(_FINALIZE_STEP_EXT_POINT)
    assert status['status'] == 'unresolved'
    # The partial scan DID find the standards-rooted step — "found something" is
    # still not "scanned the whole surface".
    assert any(rec['name'] == 'default:partial-live-step' for rec in status['implementors'])


def test_complete_readable_phase6_dir_resolves_the_surface(tmp_path, monkeypatch):
    """Positive control: `workflow/` + `standards/`, both readable, resolve surface 0.

    Without this direction a probe that had collapsed to always returning
    ``False`` would satisfy the partial-dir and unreadable tests below.
    """
    import configurable_contract as cc

    skill_dir = tmp_path / 'phase-6-finalize'
    for sub in ('workflow', 'standards'):
        (skill_dir / sub).mkdir(parents=True)
    (skill_dir / 'standards' / 'partial-live-step.md').write_text(_PARTIAL_STEP_DOC, encoding='utf-8')
    monkeypatch.setattr(cc, '_phase_6_skill_dir', lambda: skill_dir)

    assert _disc._implementor_scan_surfaces_resolve()[_PHASE6_SURFACE_INDEX] is True


@pytest.mark.skipif(
    hasattr(os, 'geteuid') and os.geteuid() == 0,
    reason='a root host bypasses the file mode, so the read cannot be made to fail',
)
@pytest.mark.parametrize('denied_kind', ['workflow-dir', 'standards-dir', 'workflow-step-doc'])
def test_unreadable_phase6_part_leaves_the_surface_unresolved(tmp_path, monkeypatch, denied_kind):
    """An unreadable subdir OR step doc leaves the phase-6 surface unresolved.

    ``Path.is_dir()`` is true for a directory that denies ``iterdir()``, and
    ``read_implements_field`` swallows an unreadable doc's ``OSError`` to
    ``[]`` — a probe that stopped at ``is_dir()`` reported the surface resolved
    while the scan ran over a missing subdirectory's steps or an unreadable step
    doc. Both subdirs and step docs are covered.
    """
    import configurable_contract as cc

    skill_dir = tmp_path / 'phase-6-finalize'
    for sub in ('workflow', 'standards'):
        (skill_dir / sub).mkdir(parents=True)
    (skill_dir / 'workflow' / 'rooted-step.md').write_text(_PARTIAL_STEP_DOC, encoding='utf-8')
    (skill_dir / 'standards' / 'partial-live-step.md').write_text(_PARTIAL_STEP_DOC, encoding='utf-8')
    monkeypatch.setattr(cc, '_phase_6_skill_dir', lambda: skill_dir)

    denied = {
        'workflow-dir': skill_dir / 'workflow',
        'standards-dir': skill_dir / 'standards',
        'workflow-step-doc': skill_dir / 'workflow' / 'rooted-step.md',
    }[denied_kind]

    original_mode = denied.stat().st_mode
    try:
        os.chmod(denied, 0o000)
        assert _disc._implementor_scan_surfaces_resolve()[_PHASE6_SURFACE_INDEX] is False
    finally:
        os.chmod(denied, original_mode)


def test_readable_phase5_standards_root_resolves_the_surface(tmp_path, monkeypatch):
    """Positive control for surface 1 (the phase-5 verify-step standards root)."""
    skills_root = tmp_path / 'skills'
    (skills_root / 'phase-5-execute' / 'standards').mkdir(parents=True)
    monkeypatch.setattr(_disc, 'resolve_skills_root', lambda _script_file: skills_root)

    assert _disc._implementor_scan_surfaces_resolve()[_PHASE5_SURFACE_INDEX] is True


@pytest.mark.skipif(
    hasattr(os, 'geteuid') and os.geteuid() == 0,
    reason='a root host bypasses the file mode, so iterdir() cannot be made to fail',
)
def test_unreadable_phase5_standards_root_leaves_the_surface_unresolved(tmp_path, monkeypatch):
    """An unreadable phase-5 standards root is unresolved, not a resolved-empty scan."""
    skills_root = tmp_path / 'skills'
    standards = skills_root / 'phase-5-execute' / 'standards'
    standards.mkdir(parents=True)
    monkeypatch.setattr(_disc, 'resolve_skills_root', lambda _script_file: skills_root)

    original_mode = standards.stat().st_mode
    try:
        os.chmod(standards, 0o000)
        assert _disc._implementor_scan_surfaces_resolve()[_PHASE5_SURFACE_INDEX] is False
    finally:
        os.chmod(standards, original_mode)
