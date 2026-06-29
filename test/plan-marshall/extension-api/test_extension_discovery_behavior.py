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

import types

import file_ops

from conftest import load_script_module

_disc = load_script_module(
    'plan-marshall', 'extension-api', 'extension_discovery.py', 'extension_discovery_behavior'
)


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


def test_load_extension_module_returns_instance(tmp_path):
    """A loadable extension.py exposing an Extension class returns an instance."""
    ext = tmp_path / 'extension.py'
    ext.write_text('class Extension:\n    pass\n', encoding='utf-8')

    instance = _disc.load_extension_module(ext, 'my-bundle')

    assert instance is not None
    assert type(instance).__name__ == 'Extension'


def test_load_extension_module_none_when_no_extension_class(tmp_path):
    """A module without an Extension class yields None (and logs a warning)."""
    ext = tmp_path / 'extension.py'
    ext.write_text('VALUE = 1\n', encoding='utf-8')

    assert _disc.load_extension_module(ext, 'my-bundle') is None


def test_load_extension_module_none_on_exec_error(tmp_path):
    """A module that raises during exec is caught and yields None."""
    ext = tmp_path / 'extension.py'
    ext.write_text('raise RuntimeError("explode at import")\n', encoding='utf-8')

    assert _disc.load_extension_module(ext, 'my-bundle') is None


# =============================================================================
# load_build_extension_module — Axis-B loader
# =============================================================================


def test_load_build_extension_module_returns_instance(tmp_path):
    """A build extension.py with a BuildExtension class returns an instance."""
    ext = tmp_path / 'extension.py'
    ext.write_text('class BuildExtension:\n    pass\n', encoding='utf-8')

    instance = _disc.load_build_extension_module(ext, 'build-foo')

    assert instance is not None
    assert type(instance).__name__ == 'BuildExtension'


def test_load_build_extension_module_none_when_no_class(tmp_path):
    """A build module without a BuildExtension class yields None."""
    ext = tmp_path / 'extension.py'
    ext.write_text('class NotIt:\n    pass\n', encoding='utf-8')

    assert _disc.load_build_extension_module(ext, 'build-foo') is None


def test_load_build_extension_module_none_on_exec_error(tmp_path):
    """A build module raising during exec is caught and yields None."""
    ext = tmp_path / 'extension.py'
    ext.write_text('1 / 0\n', encoding='utf-8')

    assert _disc.load_build_extension_module(ext, 'build-foo') is None


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
    result = _disc.apply_config_defaults(
        tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': module}]
    )

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
    result = _disc.apply_config_defaults(
        tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': None}]
    )

    assert result['extensions_skipped'] == 1
    assert result['extensions_called'] == 0


def test_apply_config_defaults_records_callback_error(tmp_path):
    """A config_defaults that raises is recorded in the errors list."""
    module = _FullStubModule(raises={'config_defaults'})
    result = _disc.apply_config_defaults(
        tmp_path, pre_discovered=[{'bundle': 'pm-x', 'module': module}]
    )

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
    args = types.SimpleNamespace(
        ext_point='plan-marshall:extension-api/standards/ext-point-does-not-exist'
    )

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


def test_scan_project_discovers_step_from_cwd_resolved_root(tmp_path, monkeypatch):
    """Bug A regression: a project-local finalize step is discovered from the
    PROJECT root resolved by ``_resolve_plan_root``, independent of the scanning
    script's ``__file__``. The discovered record's ``path`` is anchored under the
    cwd-resolved project root — the property that makes discovery correct from a
    plugin-cache execution context, where a ``__file__``-derived anchor would miss
    it.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(
        skills_root, 'finalize-step-foo', implements=_FINALIZE_STEP_EXT_POINT, name='foo', order=10
    )
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: tmp_path)

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


def test_scan_project_returns_empty_when_no_claude_skills_dir(tmp_path, monkeypatch):
    """A resolved project root without a ``.claude/skills/`` directory yields no
    records — the consumer-project case (no meta-project project-local steps).
    """
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: tmp_path)

    assert _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT) == []


def test_scan_project_skips_step_not_declaring_ext_point(tmp_path, monkeypatch):
    """Per-ext-point filtering keeps surfaces disjoint: a ``finalize-step-*`` dir
    declaring a DIFFERENT ext-point is not returned for a finalize-step query.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(
        skills_root, 'finalize-step-match', implements=_FINALIZE_STEP_EXT_POINT, name='match'
    )
    _write_finalize_step(
        skills_root, 'finalize-step-other', implements=_VERIFY_STEP_EXT_POINT, name='other'
    )
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: tmp_path)

    records = _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT)

    assert [rec['name'] for rec in records] == ['project:finalize-step-match']


def test_scan_project_ignores_non_finalize_step_dirs(tmp_path, monkeypatch):
    """Only ``finalize-step-*`` directories are scanned — a sibling skill dir that
    declares the ext-point but is not named ``finalize-step-*`` is ignored.
    """
    skills_root = tmp_path / '.claude' / 'skills'
    _write_finalize_step(
        skills_root, 'some-other-skill', implements=_FINALIZE_STEP_EXT_POINT, name='nope'
    )
    monkeypatch.setattr(file_ops, '_resolve_plan_root', lambda: tmp_path)

    assert _disc._scan_project_for_implementors(_FINALIZE_STEP_EXT_POINT) == []
