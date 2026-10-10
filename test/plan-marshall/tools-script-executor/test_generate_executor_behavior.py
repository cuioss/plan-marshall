#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral unit tests for generate_executor.py uncovered branches.

These tests load the script in-process via ``load_script_module`` (so the real
filename is traced and the exercised lines count toward coverage) and call the
target functions directly. They cover the notation→path / marshal-target
resolution helpers, the target-aware resolver selection, project-local script
discovery, the template-substituting writer (dry-run + real-write), the
state/checksum/path helpers, the notation-drift detector, and the command
handlers / main() dispatch — all paths the existing subprocess-and-fixture suite
leaves untouched.
"""

import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
import target_context
from _executor_template_render import TEMPLATE_PATH, render_executor_template

from conftest import _MARKETPLACE_SCRIPT_DIRS, PROJECT_ROOT, load_script_module


@pytest.fixture()
def derived_surfaces(monkeypatch):
    """Pin the surface-derivation result the generator consumes."""
    monkeypatch.setattr(_gen, 'derive_script_surfaces', lambda *a, **k: ({}, _stats(1, 0, 0)))


@pytest.fixture()
def previous_surfaces(monkeypatch):
    """Pin the previously-generated surface set the generator reads.

    The stub returns a :class:`PreviousSurfaces`, not the bare mapping this
    reader used to hand back: the generator consumes ``previous.outcome``
    alongside ``previous.surfaces``, and the whole point of that record is that
    an empty mapping alone cannot say whether the previous executor verifiably
    carried nothing or simply could not be read. ``read`` is the outcome here —
    the block was found and parsed, and it held the one entry below.
    """
    monkeypatch.setattr(
        _gen,
        'read_previous_surfaces',
        lambda executor: _gen.PreviousSurfaces({'a:b:c': _surface_literal()}, 'read', ''),
    )


@pytest.fixture()
def plan_base_dir_at_tmp(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at an isolated tmp_path and return that root."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    return tmp_path


# Unique module_name so the in-process load is distinct from the existing
# test module's ``load_module()`` exec-based load (which traces as <string>
# and does NOT count for coverage).
_gen = load_script_module('plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_behavior')


# The build-class change-ledger boundary lives in the executor TEMPLATE (the
# generated executor), not in generate_executor.py. Rendering the template into
# an importable module is the established pattern for unit-testing its dispatch
# boundary helpers (mirrors ``_load_template_module`` in test_generate_executor.py).
def _load_template_module() -> types.ModuleType:
    """Render the executor template with inert placeholders and exec it as a module.

    Rendered through the directory's shared renderer: every ``{{...}}`` token
    takes an inert stand-in (empty mappings, no target-aware resolver body), the
    version and fingerprint take the fresh-install empty sentinel, and
    ``{{LOGGING_DIR}}`` points at the real manage-logging scripts so the
    module-level ``from plan_logging import ...`` succeeds. The template's
    ``_ledger_core`` / ``worktree_sha`` / ``toon_parser`` imports resolve without
    a bootstrap, because the root conftest already put the shared script dirs on
    ``sys.path``. ``main()`` is guarded by ``__name__ == '__main__'`` so exec
    does not dispatch anything.
    """
    source = render_executor_template(generated_version='', mappings_fingerprint='')

    # No bootstrap: the root conftest already put every entry of
    # ``_MARKETPLACE_SCRIPT_DIRS`` on ``sys.path`` at its own import time, so the
    # exec'd template's transitive imports resolve.

    module = types.ModuleType('executor_template_ledger_boundary')
    module.__dict__['__file__'] = str(TEMPLATE_PATH)
    exec(compile(source, str(TEMPLATE_PATH), 'exec'), module.__dict__)
    return module


# =============================================================================
# Shared target resolution — the cascade the generator's verbs all read through
# =============================================================================
#
# The old reader these cases replace was ``generate_executor.read_marshal_target``:
# a marshal.json-ONLY walk that answered 'claude' for an absent file, an
# unreadable one, a malformed one and one carrying no ``runtime.target`` alike.
# The cases below therefore pin the TIER, not just the value — a reader that
# returned 'claude' for everything would satisfy a value-only assertion and
# would be the defect again.


@pytest.mark.parametrize(
    ('env_signal', 'expected_target', 'expected_source'),
    [
        ('ANTIGRAVITY_AGENT', 'antigravity', 'env'),
        ('OPENCODE', 'opencode', 'env'),
        ('OPENCODE_PID', 'opencode', 'env'),
        ('CLAUDE_CODE_SESSION_ID', 'claude', 'env'),
    ],
    ids=['antigravity-signal', 'opencode-signal', 'opencode-pid-signal', 'claude-signal'],
)
def test_env_tier_outranks_local_config(monkeypatch, tmp_path, env_signal, expected_target, expected_source):
    """A platform env signal decides the target even when local harness config disagrees.

    The env leg is the one the removed reader never had: it read config only, so
    a machine whose only deployment is OpenCode was told ``claude`` no matter
    what its runtime injected. Each row writes a CONTRADICTING local harness config
    so a reader that consulted config first would answer wrongly.
    """
    for name in ('ANTIGRAVITY_AGENT', 'OPENCODE', 'OPENCODE_PID', 'CLAUDE_CODE_SESSION_ID'):
        monkeypatch.delenv(name, raising=False)
    harness_dir = tmp_path / '.plan' / 'local' / 'harness'
    harness_dir.mkdir(parents=True)
    contra = 'claude' if expected_target != 'claude' else 'opencode'
    (harness_dir / f'{contra}.json').write_text(
        json.dumps({'schema_version': 1, 'harness': contra}),
        encoding='utf-8',
    )
    monkeypatch.setenv(env_signal, '1')

    resolved = target_context.resolve_target(cwd=tmp_path)

    assert resolved['target'] == expected_target
    assert resolved['target_source'] == expected_source


@pytest.mark.parametrize(
    ('config_body', 'expected_target', 'expected_source', 'expected_reason'),
    [
        ('{"target": "opencode"}', 'opencode', target_context.SOURCE_LOCAL_CONFIG, ''),
        (
            None,
            target_context.default_target(),
            target_context.SOURCE_FALLBACK,
            target_context.REASON_LOCAL_CONFIG_ABSENT,
        ),
        (
            '{not valid json',
            target_context.default_target(),
            target_context.SOURCE_FALLBACK,
            target_context.REASON_LOCAL_CONFIG_MALFORMED,
        ),
        (
            '{"other": {"target": "opencode"}}',
            target_context.default_target(),
            target_context.SOURCE_FALLBACK,
            target_context.REASON_TARGET_ABSENT,
        ),
        (
            '{"target": 42}',
            target_context.default_target(),
            target_context.SOURCE_FALLBACK,
            target_context.REASON_TARGET_ABSENT,
        ),
    ],
    ids=[
        'declared-target-is-returned-verbatim',
        'no-local-config-anywhere-up-the-tree',
        'local-config-is-not-valid-json',
        'no-target-key',
        'target-is-not-a-string',
    ],
)
def test_config_tier_reports_its_own_fall_through_reason(
    monkeypatch, outside_repo_dir, config_body, expected_target, expected_source, expected_reason
):
    """A declared target resolves; each unusable shape names its OWN condition.

    ``config_body`` of ``None`` writes no file at all, so the walk reaches the
    filesystem root without a hit. The first row is the matched positive control
    for the rest: a reader that always answered the fallback would fail on it
    rather than satisfy every defaulting row.

    The root is OUTSIDE the repo because pytest's basetemp is repo-local, and a
    ``tmp_path`` root would find the real ``.plan/local/harness`` above it — the
    absent-config row would then measure the developer's checkout.

    The scalar row's value is deliberately NOT the fallback: a reader that
    dropped the mapping check and returned the scalar verbatim would pass every
    value-only assertion in this file.
    """
    for name in ('ANTIGRAVITY_AGENT', 'OPENCODE', 'OPENCODE_PID', 'CLAUDE_CODE_SESSION_ID'):
        monkeypatch.delenv(name, raising=False)
    root = outside_repo_dir / 'project'
    root.mkdir()
    if config_body is not None:
        plan_dir = root / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'run-configuration.json').write_text(config_body, encoding='utf-8')

    resolved = target_context.resolve_target(cwd=root)

    assert resolved['target'] == expected_target
    assert resolved['target_source'] == expected_source
    assert resolved['reason'] == expected_reason


def test_the_generator_reads_its_target_from_the_shared_resolver():
    """The module binds the shared resolver, not a private marshal.json walk."""
    assert _gen.resolve_target is target_context.resolve_target
    assert _gen.resolve_context is target_context.resolve_context
    assert not hasattr(_gen, 'read_marshal_target')


# =============================================================================
# generate_target_aware_resolver_code — per-target resolver selection
# =============================================================================


def test_resolver_code_for_opencode_emits_opencode_walk():
    """The opencode target emits the 7-root dash-namespaced resolver body."""
    code = _gen.generate_target_aware_resolver_code('opencode')

    assert 'def _resolve_notation_by_target(' in code
    assert 'OpenCode target' in code
    assert '.opencode/skills' in code


def test_resolver_code_for_claude_emits_plugin_cache_glob():
    """The claude target emits the plugin-cache glob resolver body."""
    code = _gen.generate_target_aware_resolver_code('claude')

    assert 'def _resolve_notation_by_target(' in code
    assert 'Claude target' in code
    assert 'plugins' in code and 'cache' in code


def test_resolver_code_for_unknown_target_falls_back_to_claude():
    """An unrecognized target falls back to the Claude resolver."""
    unknown = _gen.generate_target_aware_resolver_code('borg')
    claude = _gen.generate_target_aware_resolver_code('claude')

    assert unknown == claude


# =============================================================================
# discover_local_scripts — .claude/skills/*/scripts/*.py discovery
# =============================================================================


def test_discover_local_scripts_finds_public_scripts(tmp_path):
    """A .claude/skills/<skill>/scripts/<script>.py maps to default-bundle:skill:script."""
    scripts = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'do_thing.py').write_text('# script', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert 'default-bundle:my-skill:do_thing' in mappings
    assert mappings['default-bundle:my-skill:do_thing'].endswith('do_thing.py')


def test_discover_local_scripts_skips_private_modules(tmp_path):
    """Underscore-prefixed modules are excluded from local discovery."""
    scripts = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / '_private.py').write_text('# private', encoding='utf-8')
    (scripts / 'public.py').write_text('# public', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert 'default-bundle:my-skill:public' in mappings
    assert 'default-bundle:my-skill:_private' not in mappings


def test_discover_local_scripts_empty_when_no_local_skills(tmp_path):
    """A project with no .claude/skills/ directory yields an empty mapping."""
    assert _gen.discover_local_scripts(cwd=tmp_path) == {}


def test_discover_local_scripts_skips_hidden_skill_dirs(tmp_path):
    """A dot-prefixed skill directory under .claude/skills is skipped."""
    local = tmp_path / '.claude' / 'skills'
    hidden_scripts = local / '.hidden' / 'scripts'
    hidden_scripts.mkdir(parents=True)
    (hidden_scripts / 'sneaky.py').write_text('# sneaky', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert mappings == {}


def test_discover_local_scripts_uses_the_active_targets_roots(monkeypatch, tmp_path):
    """A non-Claude skill root defined by the runtime is discovered; .claude is not.

    The discovery root is target-aware via ``marketplace_paths.
    get_project_skill_roots()`` (the ``layout skill-roots`` op), so a project
    whose active target resolves a different root must discover there instead
    of at the hardcoded ``.claude/skills`` literal this function used to probe.
    """
    monkeypatch.setattr(_gen, '_shared_get_project_skill_roots', lambda: ('.custom/skills',))
    local = tmp_path / '.custom' / 'skills' / 'my-skill' / 'scripts'
    local.mkdir(parents=True)
    (local / 'do_thing.py').write_text('# script', encoding='utf-8')
    claude = tmp_path / '.claude' / 'skills' / 'old-skill' / 'scripts'
    claude.mkdir(parents=True)
    (claude / 'old.py').write_text('# script', encoding='utf-8')

    mappings = _gen.discover_local_scripts(cwd=tmp_path)

    assert 'default-bundle:my-skill:do_thing' in mappings
    assert 'default-bundle:old-skill:old' not in mappings


def test_discover_local_scripts_empty_when_target_resolves_no_roots(monkeypatch, tmp_path):
    """An active target with no resolvable skill roots yields an empty mapping.

    The previous behaviour (probe a hardcoded root and return {} only when it
    does not exist) would silently fall through to ``.claude/skills`` even when
    the target declares none; the empty-roots case is the guard that keeps a
    non-Claude target's discovery honest.
    """
    monkeypatch.setattr(_gen, '_shared_get_project_skill_roots', lambda: ())
    local = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    local.mkdir(parents=True)
    (local / 'do_thing.py').write_text('# script', encoding='utf-8')

    assert _gen.discover_local_scripts(cwd=tmp_path) == {}


# The format marker is read from the generator's own constant rather than
# written as a literal: a hard-coded version turns this fixture into a
# permanent format skew the moment the real version is bumped, and the failure
# then reads as "generation broke" instead of "the fixture is stale".
#
# ``{{SHARED_MODULE_DIRS}}`` sits inside a collection literal for the same reason
# the real template puts it there: the generator emits that placeholder's lines
# INDENTED, so a fixture with the slot at column 0 only ever compiled because the
# substituted content was the ``# (none detected)`` comment, where indentation is
# free. Modelling the real shape is what lets this fixture carry real shared dirs.
_TEMPLATE_BODY = (
    f'# TEMPLATE_FORMAT_VERSION: {_gen._SUPPORTED_TEMPLATE_FORMAT_VERSION}\n'
    'SCRIPTS = {\n'
    '{{SCRIPT_MAPPINGS}}\n'
    '}\n'
    'SCRIPT_SURFACES = {\n'
    '{{SCRIPT_SURFACES}}\n'
    '}\n'
    'LOGGING_DIR = "{{LOGGING_DIR}}"\n'
    '_BOOTSTRAP_SKILL_DIRS = [\n'
    '{{SHARED_MODULE_DIRS}}\n'
    ']\n'
    'EXTRA = [{{EXTRA_SCRIPT_DIRS}}]\n'
    'PLAN_DIR_NAME = "{{PLAN_DIR_NAME}}"\n'
    'EXECUTOR_TARGET = "{{EXECUTOR_TARGET}}"\n'
    '{{TARGET_AWARE_RESOLVER}}\n'
)


def _build_synthetic_base(tmp_path: Path) -> Path:
    """Create a minimal marketplace tree carrying the executor template.

    ``generate_executor`` resolves the template via
    ``get_templates_dir(base)`` → ``<base>/plan-marshall/skills/
    tools-script-executor/templates/execute-script.py.template``.

    The tree ALSO carries the logging-module directory and the five shared-module
    directories the writer refuses to fabricate. Generation is fail-closed on
    both: a missing logging directory fails the run rather than emitting an
    executor that cannot import ``plan_logging``, and an empty shared-module set
    may only be emitted as ``# (none detected)`` when script-discovery coverage
    was established. A synthetic base carrying neither would therefore be refused
    for its own emptiness, and every writer test would measure that refusal
    instead of the substitution it is about. The negative cases for both guards
    live beside their own tests and stub these resolvers directly.
    """
    base = tmp_path / 'base'
    templates = base / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates'
    templates.mkdir(parents=True)
    (templates / 'execute-script.py.template').write_text(_TEMPLATE_BODY, encoding='utf-8')
    (base / 'plan-marshall' / 'skills' / 'manage-logging' / 'scripts').mkdir(parents=True)
    for shared in (
        'tools-file-ops',
        'tools-input-validation',
        'ref-toon-format',
        'script-shared',
        'manage-change-ledger',
    ):
        (base / 'plan-marshall' / 'skills' / shared / 'scripts').mkdir(parents=True)
    return base


def test_generate_executor_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    """dry_run=True prints the rendered preview and writes no executor file."""
    base = _build_synthetic_base(tmp_path)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=True, target='claude')

    assert result['status'] == 'success'
    out = capsys.readouterr().out
    assert '=== execute-script.py ===' in out
    assert not (plan_dir / 'execute-script.py').exists()


def test_generate_executor_writes_substituted_executor(tmp_path, monkeypatch):
    """A real write substitutes every token and lands at executor_path()."""
    base = _build_synthetic_base(tmp_path)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    # get_templates_dir() deliberately ignores base_path and resolves the REAL
    # script-relative production template. Monkeypatch it back to
    # the synthetic base's templates dir so the isolated _TEMPLATE_BODY fixture is
    # what gets read and asserted on, keeping the test's deterministic-content
    # intent rather than coupling the assertions to the real template's shape.
    synthetic_templates = base / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates'
    monkeypatch.setattr(_gen, 'get_templates_dir', lambda base_path: synthetic_templates)

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')

    assert result['status'] == 'success'
    written = (plan_dir / 'execute-script.py').read_text(encoding='utf-8')
    # Mapping line, target token, and resolver body are all substituted.
    assert '"a:b:c": "/p/c.py"' in written
    assert 'EXECUTOR_TARGET = "claude"' in written
    assert 'def _resolve_notation_by_target(' in written
    # No raw substitution tokens survive.
    assert '{{' not in written


def test_generate_executor_returns_error_when_template_missing(tmp_path, monkeypatch):
    """A templates dir with no template file makes the writer return status: error."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

    # get_templates_dir() ignores base_path and always resolves the
    # real script-relative template, so a base_path with no templates/ tree can no
    # longer reach the missing-template branch. Monkeypatch get_templates_dir to a
    # directory that carries no template file, so generate_executor() still
    # exercises the template-missing status: error early return.
    empty_templates = tmp_path / 'no-templates'
    empty_templates.mkdir()
    monkeypatch.setattr(_gen, 'get_templates_dir', lambda base_path: empty_templates)

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, tmp_path / 'empty-base', dry_run=False)

    assert result['status'] == 'error'


# =============================================================================
# Fail-open guard (D1) — a regeneration that emits ZERO surfaces where the
# previous executor carried some must fail loudly, and the surface-stats line
# must be emitted UNCONDITIONALLY (including the zero) so a consumer asserts on
# a value rather than inferring the outcome from an absent line.
# =============================================================================


def _stats(registered: int, derived: int, reused: int) -> dict:
    """Build a four-count surface-stats mapping with a consistent residual.

    ``surfaces_not_derivable`` is the residual (registered minus emitted), so the
    three buckets always sum to ``scripts_registered`` — the invariant the real
    :func:`derive_script_surfaces` maintains.
    """
    return {
        'scripts_registered': registered,
        'surfaces_derived': derived,
        'surfaces_reused': reused,
        'surfaces_not_derivable': registered - derived - reused,
    }


def _prep_synthetic(tmp_path: Path, monkeypatch) -> Path:
    """Synthetic base + a tmp PLAN_BASE_DIR + get_templates_dir pointed at it.

    Mirrors ``test_generate_executor_writes_substituted_executor``: the executor
    lands at ``<PLAN_BASE_DIR>/execute-script.py`` and ``get_templates_dir`` is
    redirected to the synthetic base's isolated ``_TEMPLATE_BODY`` template so
    the writer runs deterministically against it.
    """
    base = _build_synthetic_base(tmp_path)
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))
    synthetic_templates = base / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates'
    monkeypatch.setattr(_gen, 'get_templates_dir', lambda base_path: synthetic_templates)
    return base


def _surface_literal() -> dict:
    """One emitted surface entry in the shape the generator writes."""
    return {'digest': 'd', 'surface': {'root': {'flags': []}}}


def test_fail_open_guard_refuses_zero_surfaces_against_nonempty_previous(
    tmp_path, monkeypatch, previous_surfaces, derived_surfaces
):
    """Previous executor had surfaces, this generation emits ZERO → status: error.

    This is the adversarial core of D1: a positive-only test (a normal
    regeneration still succeeds) passes against the defect and proves nothing.
    Here the derivation is forced to yield nothing while the previous executor is
    made to report surfaces, so a generator lacking the guard would return
    ``status: success`` and write a surfaces-less executor — exactly the shipped
    failure. The guard must instead refuse and leave the previous executor
    unwritten.
    """
    base = _prep_synthetic(tmp_path, monkeypatch)
    plan_dir = tmp_path / '.plan'

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')

    assert result['status'] == 'error'
    assert 'fail-open' in result['error'].lower()
    # The counts ride along on the error result so the outcome is a VALUE.
    assert result['surface_stats'] == _stats(1, 0, 0)
    # Nothing written — the previous (still-validating) executor is left in place.
    assert not (plan_dir / 'execute-script.py').exists()


def test_fail_open_guard_allows_zero_surfaces_against_empty_previous(tmp_path, monkeypatch, derived_surfaces):
    """A fresh install (empty previous) deriving zero is NOT a regression → success.

    Negative control for the guard: it must fire only when surfaces were LOST,
    never merely because a generation produced none. A first build has no
    previous surfaces to lose, so a zero-surface result is written normally with
    an all-zero stats block.
    """
    base = _prep_synthetic(tmp_path, monkeypatch)
    plan_dir = tmp_path / '.plan'
    # ``absent`` — no executor file exists at all, which is a MEASUREMENT that it
    # carried no surfaces. The distinction is load-bearing here: the same empty
    # mapping under ``unreadable`` is the guard's refusal case, so a stub that
    # returned only the mapping would not pin which branch this control takes.
    monkeypatch.setattr(_gen, 'read_previous_surfaces', lambda executor: _gen.PreviousSurfaces({}, 'absent', ''))

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')

    assert result['status'] == 'success'
    assert result['surface_stats'] == _stats(1, 0, 0)
    assert (plan_dir / 'execute-script.py').exists()


#: The two ways an emission can be non-empty, as ``(derived, reused)`` counts.
#: The ids are stated rather than left to pytest: these rows are bare integers,
#: so the generated ids would be the coordinate pairs ``1-0`` and ``0-1`` — which
#: name the numbers rather than the emission each one stands for.
_NON_EMPTY_EMISSIONS = [(1, 0), (0, 1)]

_NON_EMPTY_EMISSION_IDS = [
    'one-freshly-derived-surface',
    'one-surface-reused-unchanged',
]


@pytest.mark.parametrize('derived,reused', _NON_EMPTY_EMISSIONS, ids=_NON_EMPTY_EMISSION_IDS)
def test_fail_open_guard_does_not_trip_when_surfaces_are_emitted(
    tmp_path, monkeypatch, derived, reused, previous_surfaces
):
    """Either a derived OR a reused surface is a non-empty emission → no false trip.

    The guard keys on emitting ZERO (neither derived nor reused). A regeneration
    that reuses every surface unchanged emits a non-zero count and must succeed —
    otherwise the guard would fail every no-op rebuild.
    """
    base = _prep_synthetic(tmp_path, monkeypatch)
    plan_dir = tmp_path / '.plan'
    monkeypatch.setattr(
        _gen, 'derive_script_surfaces', lambda *a, **k: ({'a:b:c': _surface_literal()}, _stats(1, derived, reused))
    )

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')

    assert result['status'] == 'success'
    assert (plan_dir / 'execute-script.py').exists()


def test_surface_stats_line_emitted_on_both_fail_open_and_success(
    tmp_path, monkeypatch, capsys, previous_surfaces, derived_surfaces
):
    """The surface-stats line is present in BOTH the zero and the non-zero case.

    This is the assertion that would fail if the line were emitted only when the
    derivation was non-empty: the zero case here is the fail-open REFUSAL (an
    error), and the line — carrying ``surfaces_derived=0`` — must still be on
    stdout. An absence nothing consumes is not a signal, so the count is emitted
    as a value even when it is zero.
    """
    base = _prep_synthetic(tmp_path, monkeypatch)

    # Zero case — fail-open refusal, yet the line is present with the zero value.
    result_zero = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')
    out_zero = capsys.readouterr().out
    assert result_zero['status'] == 'error'
    assert _gen._SURFACE_STATS_LINE_PREFIX in out_zero
    assert 'surfaces_derived=0' in out_zero

    # Non-zero case — success, the line carries the non-zero value.
    monkeypatch.setattr(_gen, 'read_previous_surfaces', lambda executor: _gen.PreviousSurfaces({}, 'absent', ''))
    monkeypatch.setattr(
        _gen, 'derive_script_surfaces', lambda *a, **k: ({'a:b:c': _surface_literal()}, _stats(1, 1, 0))
    )
    result_nonzero = _gen.generate_executor({'a:b:c': '/p/c.py'}, base, dry_run=False, target='claude')
    out_nonzero = capsys.readouterr().out
    assert result_nonzero['status'] == 'success'
    assert _gen._SURFACE_STATS_LINE_PREFIX in out_nonzero
    assert 'surfaces_derived=1' in out_nonzero


# =============================================================================
# CLI-level refusal triple — the observable a CALLER actually sees
# =============================================================================
#
# Every fail-open assertion above reads the guard off the RETURNED DICT, which
# no caller ever holds: callers invoke the generator as a subprocess and see
# only an exit code and stdout. ``main()`` ends ``print(serialize_toon(result));
# return 0`` with no branch on ``result['status']``, so the CLI observable of a
# refusal is a TRIPLE — exit ``0``, a ``status: error`` payload, and the
# unconditional ``surface-stats:`` line — and the three state ONE contract only
# when they are asserted together, on one real run, through the process
# boundary. Exit ``0`` on an expected error is the DECLARED output contract, not
# a defect, so it is pinned here: a "fix" that made the exit non-zero fails this
# test rather than silently changing what every caller reads.


_GENERATOR_PATH = (
    PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
)

#: A previously generated executor carrying exactly ONE surfaces entry. The
#: digest is deliberately stale, so no freshly computed digest can match it and
#: the entry is never reused — the previous set is non-empty (what the fail-open
#: guard compares against) while the emitted set is forced to zero.
_PREVIOUS_EXECUTOR_WITH_ONE_SURFACE = (
    '#!/usr/bin/env python3\n'
    'SCRIPTS = {\n'
    '}\n'
    'SCRIPT_SURFACES = {\n'
    '    "a:b:c": {"digest": "stale-digest", "surface": {"root": {"flags": []}}},\n'
    '}\n'
)


def _synthetic_marketplace_root(tmp_path: Path) -> Path:
    """Build a minimal ``<root>/marketplace/bundles`` tree for glob discovery.

    Carries no inventory scanner, so ``discover_scripts`` exits and
    ``cmd_generate`` falls back to the pure ``discover_scripts_fallback`` walk —
    which finds this one script and nothing else. Keeping the discovered set at
    one entry is what makes this a fast CLI test rather than a full real-tree
    regeneration; the template itself is unaffected, because
    ``get_templates_dir`` deliberately resolves the REAL script-relative
    template regardless of ``base_path``.
    """
    scripts = tmp_path / 'mkt' / 'marketplace' / 'bundles' / 'probe-bundle' / 'skills' / 'probe-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'probe_script.py').write_text('# probe\n', encoding='utf-8')
    return tmp_path / 'mkt'


def _run_generate_cli(tmp_path: Path, *, stage_previous: bool) -> tuple[subprocess.CompletedProcess, Path]:
    """Run the real generator CLI with derivation disabled, returning (result, executor).

    ``PM_SURFACE_BUDGET_SECONDS=0`` disables accept-set derivation outright, so
    the generation emits zero surfaces. Whether that is a refusal or a normal
    first build is decided ONLY by ``stage_previous`` — which is what makes the
    pair below discriminating.
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    executor = plan_dir / 'execute-script.py'
    if stage_previous:
        executor.write_text(_PREVIOUS_EXECUTOR_WITH_ONE_SURFACE, encoding='utf-8')

    env = dict(os.environ)
    env['PLAN_BASE_DIR'] = str(plan_dir)
    env['PM_SURFACE_BUDGET_SECONDS'] = '0'
    result = subprocess.run(
        [
            sys.executable,
            str(_GENERATOR_PATH),
            'generate',
            '--marketplace',
            '--marketplace-root',
            str(_synthetic_marketplace_root(tmp_path)),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    return result, executor


def test_cli_refusal_reports_exit_zero_with_error_payload_and_stats_line(tmp_path):
    """The fail-open refusal, observed the way a caller observes it.

    All three legs are asserted on ONE run: the exit code a shell would branch
    on, the payload token that carries the real verdict, and the surface-stats
    line whose zero value proves the derivation outcome rather than leaving it
    to be inferred from an absent line. A caller that read only the exit code
    would conclude this generation succeeded.
    """
    result, executor = _run_generate_cli(tmp_path, stage_previous=True)

    assert result.returncode == 0, (
        'the expected-error exit contract is 0 — main() prints the TOON and '
        f'returns 0. stdout={result.stdout!r} stderr={result.stderr!r}'
    )
    assert 'status: error' in result.stdout, result.stdout
    assert 'Fail-open regeneration refused' in result.stdout, result.stdout
    assert _gen._SURFACE_STATS_LINE_PREFIX in result.stdout, result.stdout
    assert 'surfaces_derived=0' in result.stdout, result.stdout
    # The refusal writes nothing: the still-validating previous executor is
    # byte-identical afterwards.
    assert executor.read_text(encoding='utf-8') == _PREVIOUS_EXECUTOR_WITH_ONE_SURFACE


def test_cli_zero_surfaces_without_a_previous_reports_success(tmp_path):
    """Discriminating half: a zero-surface generation is not by itself an error.

    Identical invocation, identical disabled budget — the ONLY difference is
    that no previous executor was staged. Without this case the test above would
    also pass on a generator that reported ``status: error`` for every
    zero-surface run, and the ``status: error`` assertion would be measuring the
    budget rather than the guard.
    """
    result, executor = _run_generate_cli(tmp_path, stage_previous=False)

    assert result.returncode == 0, result.stderr
    assert 'status: success' in result.stdout, result.stdout
    assert 'Fail-open regeneration refused' not in result.stdout
    assert _gen._SURFACE_STATS_LINE_PREFIX in result.stdout, result.stdout
    assert 'surfaces_derived=0' in result.stdout, result.stdout
    assert executor.exists(), 'a first build with no previous surfaces is written normally'


def test_format_surface_stats_line_names_every_count():
    """The rendered line carries a value for each of the four buckets."""
    line = _gen.format_surface_stats_line(_stats(5, 3, 1))

    assert line.startswith(_gen._SURFACE_STATS_LINE_PREFIX)
    assert 'scripts_registered=5' in line
    assert 'surfaces_derived=3' in line
    assert 'surfaces_reused=1' in line
    assert 'surfaces_not_derivable=1' in line


def test_cmd_generate_flattens_stats_into_fail_open_error(tmp_path, monkeypatch):
    """cmd_generate surfaces the counts to the TOON top level on the error path.

    The fail-open error result carries ``surface_stats``; cmd_generate must
    flatten those into the returned dict so the counts reach the serialized TOON
    output on the error path exactly as they do on success — the evidence a
    consumer reads to distinguish a stripped surface set from a healthy build.
    """
    monkeypatch.setattr(_gen, 'get_base_path', lambda **k: tmp_path)
    monkeypatch.setattr(_gen, 'discover_scripts', lambda base: {'a:b:c': '/p/c.py'})
    monkeypatch.setattr(_gen, 'discover_local_scripts', lambda: {})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _passing_coverage())
    monkeypatch.setattr(
        _gen,
        'generate_executor',
        lambda *a, **k: {
            'status': 'error',
            'error': 'Fail-open regeneration refused: ...',
            'surface_stats': _stats(3, 0, 0),
        },
    )
    args = types.SimpleNamespace(marketplace=False, marketplace_root=None, dry_run=False, target=None)

    result = _gen.cmd_generate(args)

    assert result['status'] == 'error'
    assert result['scripts_registered'] == 3
    assert result['surfaces_derived'] == 0
    assert result['surfaces_reused'] == 0
    assert result['surfaces_not_derivable'] == 3
    # The nested block is flattened away, not left as a sub-mapping.
    assert 'surface_stats' not in result


# =============================================================================
# Discovery coverage — the guard that stops a resolver failure being laundered
# into a fact about the world
# =============================================================================


def _passing_coverage(discovered: int = 1) -> dict:
    """A coverage verdict that established full coverage over ``discovered`` notations."""
    return {
        'coverage_ok': True,
        'scripts_enumerated': discovered,
        'scripts_expected': discovered,
        'scripts_discovered': discovered,
        'exclusions': dict.fromkeys(_gen.DISCOVERY_EXCLUSION_RULES, 0),
        'missing_notations': [],
    }


def _failing_coverage(enumerated: int, discovered: int, missing: list[str]) -> dict:
    """A coverage verdict for a scan short of the tree by ``enumerated - discovered``."""
    return {
        'coverage_ok': False,
        'scripts_enumerated': enumerated,
        'scripts_expected': enumerated,
        'scripts_discovered': discovered,
        'exclusions': dict.fromkeys(_gen.DISCOVERY_EXCLUSION_RULES, 0),
        'missing_notations': missing,
    }


def _stub_discovery(monkeypatch, base: Path, mappings: dict[str, str] | Exception):
    """Pin the base path and the discovery result ``cmd_generate`` will read.

    ``mappings`` may be an exception instance, which is how the ``SystemExit``
    the inventory raises on an unavailable scan is injected: it is a
    ``BaseException``, so a stub returning a mapping cannot stand in for it.
    """
    monkeypatch.setattr(_gen, 'get_base_path', lambda **k: base)
    monkeypatch.setattr(_gen, 'discover_scripts_fallback', lambda b: {})
    monkeypatch.setattr(_gen, 'discover_local_scripts', lambda: {})
    if isinstance(mappings, BaseException):
        monkeypatch.setattr(_gen, 'discover_scripts', lambda b: (_ for _ in ()).throw(mappings))
    else:
        monkeypatch.setattr(_gen, 'discover_scripts', lambda b: mappings)


def _generate_args() -> types.SimpleNamespace:
    """The argv namespace ``generate`` parses, as a verb's own call site supplies it."""
    return types.SimpleNamespace(marketplace=False, marketplace_root=None, dry_run=False, target=None)


def test_enumeration_excludes_named_categories_and_reports_their_counts(tmp_path):
    """The declared exclusions are named rules with counts, not an unstated tolerance.

    A tree of two public scripts, one private module and one ``__pycache__``
    artefact. The private module must appear under its NAMED category — a
    threshold that silently absorbed it would let a genuinely truncated scan pass
    with the same numbers a complete one produces.
    """
    scripts = tmp_path / 'demo' / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (tmp_path / 'demo' / '.claude-plugin').mkdir(parents=True)
    (tmp_path / 'demo' / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    (scripts / 'entry.py').write_text('# public', encoding='utf-8')
    (scripts / 'other.py').write_text('# public', encoding='utf-8')
    (scripts / '_internal.py').write_text('# private', encoding='utf-8')
    pycache = scripts / '__pycache__'
    pycache.mkdir()
    (pycache / 'entry.cpython-312.pyc').write_bytes(b'\x00')

    notations, excluded, counts = _gen.enumerate_script_notations(tmp_path)

    assert notations == {'demo:demo-skill:entry', 'demo:demo-skill:other'}
    assert counts == {'private_module': 1, 'unattributed_flat_skill': 0}
    assert len(excluded) == 1


def test_every_exclusion_rule_is_reachable_from_the_candidate_set(tmp_path):
    """A rule naming a condition the enumeration cannot reach is a rule excluding nothing.

    The candidate set is ``*.py``/``*.sh`` under a ``scripts/`` directory, so a
    ``__pycache__`` artefact is never a candidate and a rule naming it would
    document a condition that does not exist — indistinguishable from a rule that
    was forgotten. This row drives every declared category and requires it to
    fire, so adding an unreachable rule is a red test rather than a comment.
    """
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    scripts = bundle / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'entry.py').write_text('# public', encoding='utf-8')
    (scripts / '_private.py').write_text('# private', encoding='utf-8')
    # A flat skill directory with scripts but no recorded bundle identity.
    unattributed = tmp_path / 'skills' / 'foreign-tool' / 'scripts'
    unattributed.mkdir(parents=True)
    (unattributed / 'tool.py').write_text('# unattributable', encoding='utf-8')

    _notations, _excluded, counts = _gen.enumerate_script_notations(tmp_path)

    assert set(counts) == set(_gen.DISCOVERY_EXCLUSION_RULES)
    assert all(count > 0 for count in counts.values()), f'a declared rule never fired: {counts}'


def test_enumeration_ignores_scripts_outside_a_skills_tree(tmp_path):
    """A script file that is not under ``skills/**/scripts/**`` is not a notation.

    The predicate is the LAYOUT, not the file extension: a stray ``.py`` at a
    bundle root would otherwise inflate the expected count and fail every
    generation on a tree that carries one.
    """
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    (bundle / 'build.py').write_text('# stray', encoding='utf-8')
    (bundle / 'skills' / 'demo-skill').mkdir(parents=True)
    (bundle / 'skills' / 'demo-skill' / 'build.py').write_text('# beside scripts', encoding='utf-8')

    notations, _excluded, _counts = _gen.enumerate_script_notations(tmp_path)

    assert notations == set()


def test_enumeration_attributes_a_subdirectory_script_to_its_skill(tmp_path):
    """``scripts/build/x.py`` belongs to the skill that OWNS ``scripts/``.

    The inventory derives the skill name the same way, so a sub-directory script
    must land on the same notation here or the coverage guard would report every
    organised layout as a shortfall.
    """
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    sub = bundle / 'skills' / 'demo-skill' / 'scripts' / 'build'
    sub.mkdir(parents=True)
    (sub / 'shared.py').write_text('# organised', encoding='utf-8')

    notations, _excluded, _counts = _gen.enumerate_script_notations(tmp_path)

    assert notations == {'demo:demo-skill:shared'}


def test_enumeration_counts_each_notation_once_for_a_colliding_stem(tmp_path):
    """Two files sharing a stem are ONE expected notation, because the map is keyed by notation.

    ``foo.py`` and ``foo.sh`` in one skill both derive ``{bundle}:{skill}:foo``,
    and the discovered mapping holds a single entry for it. Counting FILES would
    report a shortfall of one against a tree that is in fact fully covered, and
    fail every generation on it.
    """
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    scripts = bundle / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'entry.py').write_text('# python', encoding='utf-8')
    (scripts / 'entry.sh').write_text('# shell', encoding='utf-8')

    notations, _excluded, _counts = _gen.enumerate_script_notations(tmp_path)

    assert notations == {'demo:demo-skill:entry'}


def test_assess_coverage_passes_when_nothing_is_missing(tmp_path):
    """A scan that reported everything the tree holds establishes coverage."""
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    scripts = bundle / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'entry.py').write_text('# public', encoding='utf-8')

    coverage = _gen.assess_discovery_coverage(tmp_path, {'demo:demo-skill:entry': '/p/entry.py'})

    assert coverage['coverage_ok'] is True
    assert coverage['missing_notations'] == []
    assert coverage['scripts_enumerated'] == coverage['scripts_discovered'] == 1


def test_assess_coverage_passes_on_a_genuinely_empty_tree(tmp_path):
    """An empty tree AND an empty scan is a measurement, not a shortfall.

    This is the third of ``drift``'s three outcomes, and it is only honest
    because the counts travel with it: the same two zeros appear when a scan
    silently found nothing, and only ``coverage_ok`` separates them.
    """
    coverage = _gen.assess_discovery_coverage(tmp_path, {})

    assert coverage['coverage_ok'] is True
    assert coverage['scripts_enumerated'] == 0
    assert coverage['scripts_discovered'] == 0


def test_assess_coverage_fails_and_names_the_shortfall(tmp_path):
    """A scan that dropped a notation fails, and the payload names what it dropped."""
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    scripts = bundle / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'kept.py').write_text('# kept', encoding='utf-8')
    (scripts / 'dropped.py').write_text('# dropped', encoding='utf-8')

    coverage = _gen.assess_discovery_coverage(tmp_path, {'demo:demo-skill:kept': '/p/kept.py'})

    assert coverage['coverage_ok'] is False
    assert coverage['missing_notations'] == ['demo:demo-skill:dropped']
    assert coverage['scripts_enumerated'] == 2
    assert coverage['scripts_discovered'] == 1


def test_assess_coverage_caps_the_missing_sample(tmp_path):
    """A wholly empty scan against a large tree cannot turn the payload into a second report."""
    bundle = tmp_path / 'demo'
    (bundle / '.claude-plugin').mkdir(parents=True)
    (bundle / '.claude-plugin' / 'plugin.json').write_text('{}', encoding='utf-8')
    scripts = bundle / 'skills' / 'demo-skill' / 'scripts'
    scripts.mkdir(parents=True)
    for index in range(_gen._MISSING_NOTATION_SAMPLE + 10):
        (scripts / f'script_{index:03d}.py').write_text('# many', encoding='utf-8')

    coverage = _gen.assess_discovery_coverage(tmp_path, {})

    assert coverage['coverage_ok'] is False
    assert len(coverage['missing_notations']) == _gen._MISSING_NOTATION_SAMPLE
    # The COUNTS are not capped — only the sample is, so the magnitude survives.
    assert coverage['scripts_enumerated'] == _gen._MISSING_NOTATION_SAMPLE + 10


def test_cmd_generate_refuses_an_under_covered_scan(tmp_path, monkeypatch):
    """A truncated scan fails generation, with the discrepancy in the payload.

    The generator is stubbed to prove the refusal happens BEFORE any write: a
    guard that ran after the write would still produce an executor, and the
    ``generate_executor`` stub would never be reached with a green result.
    """
    _stub_discovery(monkeypatch, tmp_path, {'a:b:c': '/p/c.py'})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _failing_coverage(5, 1, ['x:y:z']))
    monkeypatch.setattr(
        _gen,
        'generate_executor',
        lambda *a, **k: pytest.fail('generation must not run on an under-covered scan'),
    )

    result = _gen.cmd_generate(_generate_args())

    assert result['status'] == 'error'
    assert result['error'] == 'discovery_coverage_incomplete'
    assert result['scripts_enumerated'] == 5
    assert result['scripts_discovered'] == 1
    assert result['missing_notations'] == ['x:y:z']
    assert set(result['exclusion_rules']) == set(_gen.DISCOVERY_EXCLUSION_RULES)


def test_cmd_generate_refuses_an_empty_scan_against_a_non_empty_tree(tmp_path, monkeypatch):
    """An empty scan fails identically to a truncated one — they are one defect class."""
    _stub_discovery(monkeypatch, tmp_path, {})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _failing_coverage(9, 0, []))
    monkeypatch.setattr(
        _gen,
        'generate_executor',
        lambda *a, **k: pytest.fail('generation must not run on an empty scan'),
    )

    result = _gen.cmd_generate(_generate_args())

    assert result['status'] == 'error'
    assert result['error'] == 'discovery_coverage_incomplete'
    assert result['scripts_discovered'] == 0
    assert result['scripts_enumerated'] == 9


def test_cmd_generate_falls_back_then_fails_closed_on_the_fallback(tmp_path, monkeypatch):
    """The glob fallback is attempted, and its known-truncation is what fails.

    The fallback's globbing rules are narrower than the inventory's (``.py``
    only, top level only, tests dropped), so on any real tree it cannot reach
    full coverage. The point of this case is that the fallback is still TRIED —
    a tree where it happens to suffice must generate — and that a shortfall it
    does produce is refused rather than accepted.
    """
    _stub_discovery(monkeypatch, tmp_path, SystemExit(2))
    monkeypatch.setattr(_gen, 'discover_scripts_fallback', lambda b: {'a:b:c': '/p/c.py'})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _failing_coverage(4, 1, ['q:r:s']))
    monkeypatch.setattr(
        _gen,
        'generate_executor',
        lambda *a, **k: pytest.fail('generation must not run on a truncated fallback scan'),
    )

    result = _gen.cmd_generate(_generate_args())

    assert result['status'] == 'error'
    assert result['error'] == 'discovery_coverage_incomplete'
    assert result['scripts_discovered'] == 1


def test_cmd_generate_refuses_an_unusable_context(tmp_path, monkeypatch):
    """A ``--marketplace-root`` that is not a usable path is refused at the resolver.

    The refusal is reported as a structured error rather than raised out of the
    verb, so the TOON contract (``status:`` on every expected failure) holds for
    caller-input rejections too.
    """
    monkeypatch.setattr(_gen, 'get_base_path', lambda **k: pytest.fail('no base resolution may run'))
    args = types.SimpleNamespace(marketplace=False, marketplace_root=Path('..') / 'escape', dry_run=False, target=None)

    result = _gen.cmd_generate(args)

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_context'
    assert 'traversal' in result['detail']


def test_marketplace_root_for_base_names_the_containing_directory(tmp_path):
    """The anchor handed to a subprocess is the directory CONTAINING ``marketplace/``.

    ``find_marketplace_path`` joins ``marketplace/bundles`` onto whatever anchor
    it is given, so handing it ``.../marketplace`` would make it look for
    ``.../marketplace/marketplace/bundles`` and resolve nothing. A cache base
    has no marketplace anchor at all and must yield ``None`` rather than a guess.
    """
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True)

    assert _gen.marketplace_root_for_base(bundles) == tmp_path
    assert _gen.marketplace_root_for_base(Path('/Users/x/.claude/plugins/cache/plan-marshall/0.1.1')) is None


def test_cmd_drift_reports_a_resolver_failure_as_an_error(tmp_path, monkeypatch):
    """A discovery failure is an error, never a removal list.

    The pre-fix verb substituted ``{}`` for the current set, so
    ``removed = executor_set - set()`` reported EVERY executor mapping as removed
    under ``status: success``. This case pins the opposite: an error, naming the
    failure and the coverage it could still establish.
    """
    monkeypatch.setattr(_gen, 'get_executor_mappings', lambda: {'a:b:c': '/p/c.py', 'd:e:f': '/p/f.py'})
    _stub_discovery(monkeypatch, tmp_path, SystemExit(2))
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _failing_coverage(3, 0, []))

    result = _gen.cmd_drift(_generate_args())

    assert result['status'] == 'error'
    assert result['error'] == 'bundles_state_unresolvable'
    assert 'removed' not in result, 'a resolver failure must never be reported as a removal list'
    assert result['executor_scripts'] == 2
    assert result['scripts_enumerated'] == 3
    assert 'SystemExit' in result['detail']


def test_cmd_drift_reports_an_under_covered_scan_as_an_error(tmp_path, monkeypatch):
    """A scan that returned but is short of the tree is an error too.

    The distinct second refusal path: ``discover_scripts`` SUCCEEDED, so the
    ``SystemExit`` handler never fired, and only the coverage verdict can catch
    it. Without this case a verb that handled the exception but not the
    truncation would pass the row above.
    """
    monkeypatch.setattr(_gen, 'get_executor_mappings', lambda: {'a:b:c': '/p/c.py'})
    _stub_discovery(monkeypatch, tmp_path, {'x:y:z': '/p/z.py'})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _failing_coverage(7, 1, ['x:y:z']))

    result = _gen.cmd_drift(_generate_args())

    assert result['status'] == 'error'
    assert result['error'] == 'bundles_state_under_covered'
    assert 'removed' not in result
    assert result['missing_notations'] == ['x:y:z']


def test_cmd_drift_claims_an_empty_set_only_when_coverage_supports_it(tmp_path, monkeypatch):
    """A genuinely empty current set succeeds AND carries the counts that prove it.

    The third outcome. ``removed: 1`` here is the honest reading of a populated
    executor against a tree that carries nothing — what the two error paths used
    to produce by laundering a failure. What separates the three outcomes is
    ``status`` plus the enumerated count beside the zero, not ``drift_status``.
    """
    monkeypatch.setattr(_gen, 'get_executor_mappings', lambda: {'a:b:c': '/p/c.py'})
    _stub_discovery(monkeypatch, tmp_path, {})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _passing_coverage(0))
    monkeypatch.setattr(_gen, '_detect_notation_drift', lambda registered, base: [])

    result = _gen.cmd_drift(_generate_args())

    assert result['status'] == 'success'
    assert result['bundles_scripts'] == 0
    assert result['scripts_enumerated'] == 0
    assert result['scripts_discovered'] == 0
    # The counts are what a reader needs to tell this from a truncated scan: the
    # same two zeros, on a run that failed to establish coverage.
    assert 'error' not in result


def test_cmd_drift_reports_a_real_comparison_with_the_counts(tmp_path, monkeypatch):
    """The success path is unchanged apart from the counts it now carries."""
    monkeypatch.setattr(_gen, 'get_executor_mappings', lambda: {'a:b:c': '/old/c.py', 'gone:e:f': '/p/f.py'})
    _stub_discovery(monkeypatch, tmp_path, {'a:b:c': '/new/c.py'})
    monkeypatch.setattr(_gen, 'assess_discovery_coverage', lambda base, discovered: _passing_coverage(1))
    monkeypatch.setattr(_gen, '_detect_notation_drift', lambda registered, base: [])

    result = _gen.cmd_drift(_generate_args())

    assert result['status'] == 'success'
    assert result['changed'] == 1
    assert result['removed'] == 1
    assert result['scripts_enumerated'] == 1
    assert result['scripts_discovered'] == 1


def test_generate_executor_refuses_a_missing_logging_module_directory(tmp_path, monkeypatch):
    """A logging dir that does not exist fails generation instead of being substituted.

    The generated executor imports ``plan_logging`` from this path before it can
    log anything, so emitting one against a missing directory produces a file
    whose very first operation fails — with a green ``status: success``.
    """
    monkeypatch.setattr(_gen, 'get_logging_scripts_dir', lambda base: tmp_path / 'nowhere' / 'scripts')
    monkeypatch.setattr(_gen, 'get_shared_module_dirs', lambda base: [tmp_path])

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, tmp_path, dry_run=True, coverage=_passing_coverage(1))

    assert result['status'] == 'error'
    assert result['error'] == 'logging_module_dir_missing'
    assert 'nowhere' in result['logging_dir']


def test_generate_executor_refuses_the_none_detected_degradation_unless_coverage_holds(tmp_path, monkeypatch):
    """``# (none detected)`` is a claim about the world, so coverage must back it.

    With shared-module resolution empty AND no established coverage, the emitted
    comment would be indistinguishable from a genuine "this tree has no shared
    modules", so the generation is refused and the payload says coverage was not
    established.
    """
    monkeypatch.setattr(_gen, 'get_logging_scripts_dir', lambda base: tmp_path)
    monkeypatch.setattr(_gen, 'get_shared_module_dirs', lambda base: [])

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, tmp_path, dry_run=True, coverage=None)

    assert result['status'] == 'error'
    assert result['error'] == 'shared_module_dirs_unresolved'
    assert result['scripts_enumerated'] == 0
    assert result['scripts_discovered'] == 0


def test_generate_executor_refuses_the_degradation_on_a_failing_verdict(tmp_path, monkeypatch):
    """An ASSESSED-but-failing verdict refuses too, with the discrepancy attached."""
    monkeypatch.setattr(_gen, 'get_logging_scripts_dir', lambda base: tmp_path)
    monkeypatch.setattr(_gen, 'get_shared_module_dirs', lambda base: [])

    result = _gen.generate_executor(
        {'a:b:c': '/p/c.py'},
        tmp_path,
        dry_run=True,
        coverage=_failing_coverage(6, 1, ['x:y:z']),
    )

    assert result['status'] == 'error'
    assert result['error'] == 'shared_module_dirs_unresolved'
    assert result['scripts_enumerated'] == 6
    assert result['missing_notations'] == ['x:y:z']


def test_generate_executor_emits_the_degradation_when_coverage_holds(tmp_path, monkeypatch):
    """The matched positive control: with coverage established, the zero is a measurement.

    Without this row the three rows above would also pass on a generator that
    simply refused EVERY empty shared-module set — which would break generation
    on any tree that genuinely has none. The assertion is that the run gets PAST
    the guard: the guard's only output is an error dict, so a success verdict is
    the observable that it declined to fire.
    """
    monkeypatch.setattr(_gen, 'get_logging_scripts_dir', lambda base: tmp_path)
    monkeypatch.setattr(_gen, 'get_shared_module_dirs', lambda base: [])

    result = _gen.generate_executor({'a:b:c': '/p/c.py'}, tmp_path, dry_run=True, coverage=_passing_coverage(1))

    assert result['status'] == 'success', result
    assert result['dry_run'] is True


# =============================================================================
# update_state — marshall-state.toon generation metadata
# =============================================================================


def test_update_state_writes_generation_metadata(tmp_path, plan_base_dir_at_tmp):
    """update_state writes a marshall-state.toon carrying count + checksum."""

    _gen.update_state(script_count=7, checksum='deadbeef', logs_cleaned=3)

    content = (tmp_path / 'marshall-state.toon').read_text(encoding='utf-8')
    assert 'deadbeef' in content
    assert '\t7\t' in content
    assert content.rstrip().endswith('3')


# =============================================================================
# check_paths_exist — existing vs missing mapping classification
# =============================================================================


def test_check_paths_exist_partitions_existing_and_missing(tmp_path):
    """check_paths_exist returns existing notations and (notation, path) misses."""
    real = tmp_path / 'real.py'
    real.write_text('# real', encoding='utf-8')
    mappings = {
        'a:b:real': str(real),
        'a:b:ghost': str(tmp_path / 'ghost.py'),
    }

    existing, missing = _gen.check_paths_exist(mappings)

    assert existing == ['a:b:real']
    assert missing == [('a:b:ghost', str(tmp_path / 'ghost.py'))]


# =============================================================================
# verify_executor / get_executor_mappings — missing-executor branches
# =============================================================================


def test_verify_executor_returns_false_when_executor_absent(plan_base_dir_at_tmp):
    """verify_executor reports (False, 0) when no executor file exists."""

    valid, count = _gen.verify_executor()

    assert valid is False
    assert count == 0


def test_get_executor_mappings_empty_when_executor_absent(plan_base_dir_at_tmp):
    """get_executor_mappings swallows the load failure and returns {}."""

    assert _gen.get_executor_mappings() == {}


# =============================================================================
# Notation-drift detection helpers
# =============================================================================


def test_flip_notation_separators_swaps_hyphen_and_underscore():
    """Hyphens and underscores swap; other characters are unchanged."""
    assert _gen._flip_notation_separators('manage_status') == 'manage-status'
    assert _gen._flip_notation_separators('manage-status') == 'manage_status'
    assert _gen._flip_notation_separators('plainname') == 'plainname'


def test_collect_referenced_notations_scans_markdown(tmp_path):
    """References after an execute-script.py token are collected from docs."""
    (tmp_path / 'doc.md').write_text(
        'Run `python3 .plan/execute-script.py some-bundle:some-skill:some-script list`.\n',
        encoding='utf-8',
    )

    referenced = _gen._collect_referenced_notations(tmp_path)

    assert 'some-bundle:some-skill:some-script' in referenced


def test_collect_referenced_notations_empty_for_non_directory(tmp_path):
    """A non-directory base path yields an empty reference set."""
    assert _gen._collect_referenced_notations(tmp_path / 'nope') == set()


def test_detect_notation_drift_flags_separator_rename(tmp_path):
    """A caller referencing the underscore form when only the hyphen form is
    registered is flagged as drift (and vice versa)."""
    (tmp_path / 'caller.md').write_text('python3 .plan/execute-script.py b:s:manage_status read\n', encoding='utf-8')
    registered = {'b:s:manage-status': '/path/manage-status.py'}

    drift = _gen._detect_notation_drift(registered, tmp_path)

    assert ('b:s:manage_status', 'b:s:manage-status') in drift


def test_detect_notation_drift_empty_when_reference_registered(tmp_path):
    """A reference that IS registered produces no drift entry."""
    (tmp_path / 'caller.md').write_text('python3 .plan/execute-script.py b:s:manage-status read\n', encoding='utf-8')
    registered = {'b:s:manage-status': '/path/manage-status.py'}

    assert _gen._detect_notation_drift(registered, tmp_path) == []


def test_notation_drift_zero_against_clean_marketplace_source():
    """The clean marketplace SOURCE tree carries zero caller-notation drift.

    Regression pin for the drift-detector self-catalog fix: resolve the
    production ``--marketplace`` base (``get_base_path(use_marketplace=True)``
    forces the marketplace tree, ignoring the plugin-cache / auto-detected
    context), build the filename-derived registered mapping with the pure
    ``discover_scripts_fallback`` glob walk (no subprocess, deterministic), and
    assert ``_detect_notation_drift`` finds nothing over the real source.

    Any future underscore-form third-segment reference whose hyphen-form is
    registered (a half-done entrypoint rename that silently changes a public
    notation) re-fails this test, and the assertion message names the offending
    ``(referenced_notation, registered_notation)`` pairs so the drift is
    identified at failure time.
    """
    try:
        base = _gen.get_base_path(use_marketplace=True)
    except FileNotFoundError as exc:  # pragma: no cover - tracked source tree
        raise AssertionError(
            'marketplace source tree (marketplace/bundles) is not present in '
            'this checkout — caller-notation drift detection requires the '
            'marketplace source and cannot run against a deployed plugin cache'
        ) from exc
    registered = _gen.discover_scripts_fallback(base)

    drift = _gen._detect_notation_drift(registered, base)

    assert drift == [], (
        f'caller-notation drift detected in marketplace source — offending (referenced, registered) pairs: {drift}'
    )


# =============================================================================
# Command handlers + main() dispatch
# =============================================================================


def test_cmd_paths_error_when_no_mappings(plan_base_dir_at_tmp):
    """cmd_paths returns an error result when the executor mappings are empty."""

    result = _gen.cmd_paths(types.SimpleNamespace())

    assert result['status'] == 'error'
    assert 'Could not read executor mappings' in result['error']


def test_cmd_drift_error_when_no_mappings(plan_base_dir_at_tmp):
    """cmd_drift returns an error result when the executor mappings are empty."""

    result = _gen.cmd_drift(types.SimpleNamespace(marketplace=False, marketplace_root=None))

    assert result['status'] == 'error'
    assert 'Could not read executor mappings' in result['error']


def test_cmd_cleanup_reports_deleted_count(plan_base_dir_at_tmp):
    """cmd_cleanup returns the number of logs deleted (zero on an empty tree)."""

    result = _gen.cmd_cleanup(types.SimpleNamespace(max_age_days=7))

    assert result['status'] == 'success'
    assert result['deleted'] == 0


def test_main_cleanup_dispatch_returns_zero(monkeypatch, capsys, plan_base_dir_at_tmp):
    """main() routes the cleanup subcommand and emits a TOON success result."""
    monkeypatch.setattr(_gen.sys, 'argv', ['generate_executor.py', 'cleanup', '--max-age-days', '30'])

    rc = _gen.main()

    assert rc == 0
    out = capsys.readouterr().out
    assert 'success' in out


# =============================================================================
# Build-class dispatch boundary — tier-agnostic kind=build change-ledger stamp
# =============================================================================
#
# Regression coverage for the leaf-no-background-build / tier-agnostic freshness
# stamp invariant: a build-class notation dispatched through the
# generated executor writes exactly one kind=build change-ledger entry carrying a
# worktree_sha and exit_code — including the orchestrator/global-tier shape
# (plan_id: null) the detached await-long-running path produces. This proves the
# stamp is tier-agnostic and covers the detached path, so the pre-commit
# freshness gate sees a stamp regardless of which tier ran the build.


def _redirect_ledger(module, monkeypatch, ledger_path: Path, worktree_sha: str) -> None:
    """Point the boundary writer at ``ledger_path`` and pin ``worktree_sha``.

    ``_append_build_ledger_record`` calls ``append_entry(record)`` (no path arg
    → ``resolve_ledger_path()``) and ``compute_worktree_sha(os.getcwd())``, both
    resolved from the rendered template module's namespace. Redirect the append
    to the explicit tmp ``ledger_path`` (via ``append_entry``'s optional ``path``
    parameter) and pin the currency hash so the test is deterministic and needs
    no git working tree.
    """
    import _ledger_core

    real_append = _ledger_core.append_entry
    monkeypatch.setattr(module, 'append_entry', lambda record: real_append(record, path=ledger_path))
    monkeypatch.setattr(module, 'compute_worktree_sha', lambda root: worktree_sha)


def test_build_class_dispatch_writes_orchestrator_tier_kind_build_entry(tmp_path, monkeypatch):
    """A build-class dispatch with ``plan_id=None`` (the orchestrator/global-tier
    shape the detached ``await-long-running`` path produces) writes exactly one
    ``kind=build`` ledger entry carrying a ``worktree_sha`` and ``exit_code``.
    """
    module = _load_template_module()
    import _ledger_core

    ledger_path = tmp_path / 'change-ledger.jsonl'
    _redirect_ledger(module, monkeypatch, ledger_path, worktree_sha='feedfacecafe0001')

    module._append_build_ledger_record(
        notation='plan-marshall:build-pyproject:pyproject_build',
        plan_id=None,
        script_args=['run', '--command-args', 'compile plan-marshall'],
        exit_code=0,
        stdout='',
        log_file=str(tmp_path / 'build.log'),
    )

    entries = _ledger_core.read_entries(path=ledger_path)
    assert len(entries) == 1, 'exactly one kind=build entry must be written per dispatch'
    entry = entries[0]
    assert entry['kind'] == 'build'
    assert entry['plan_id'] is None, 'orchestrator/global-tier build stamps plan_id: null'
    assert entry['worktree_sha'] == 'feedfacecafe0001'
    assert entry['exit_code'] == 0
    assert entry['status'] == 'unknown', (
        'empty stdout + exit_code 0 derives status=unknown: exit 0 proves the process '
        'ended, not that a build ran and passed, and an empty payload carries no '
        'wrapper-claimable verdict to read. Deriving success here would mint the '
        'false-fresh row pre-commit-verify-freshness accepts as proof of a build.'
    )
    assert entry['notation'] == 'plan-marshall:build-pyproject:pyproject_build'


def test_build_class_dispatch_records_non_zero_exit_code(tmp_path, monkeypatch):
    """The stamp is written even when the build failed — the freshness gate
    filters on ``exit_code``, so a non-zero exit is recorded (plan-scoped shape).
    """
    module = _load_template_module()
    import _ledger_core

    ledger_path = tmp_path / 'change-ledger.jsonl'
    _redirect_ledger(module, monkeypatch, ledger_path, worktree_sha='feedfacecafe0002')

    module._append_build_ledger_record(
        notation='plan-marshall:build-maven:maven',
        plan_id='plan-x',
        script_args=['run', '--targets', 'verify'],
        exit_code=1,
        stdout='',
        log_file=str(tmp_path / 'build.log'),
    )

    entries = _ledger_core.read_entries(path=ledger_path)
    assert len(entries) == 1
    assert entries[0]['exit_code'] == 1
    assert entries[0]['plan_id'] == 'plan-x'
    assert entries[0]['worktree_sha'] == 'feedfacecafe0002'
    assert entries[0]['status'] == 'error', 'empty stdout + non-zero exit derives status=error'


def test_build_class_notation_gate_scopes_the_ledger_boundary():
    """The ``_is_build_class_notation`` gate admits every build-* skill dispatched
    with the build-executing subcommand, and nothing else — the predicate is
    scoped by the CONJUNCTION of notation and subcommand.

    The notation half is pinned here. The subcommand half, swept over the
    argparse-derived subcommand population of every build wrapper, lives in
    test_build_class_stamp_discriminator.py — as does the boundary's THIRD
    conjunct (no help flag anywhere in argv), which this predicate does not and
    cannot decide: it is never given the argv a help flag can hide in.
    """
    module = _load_template_module()

    assert module._is_build_class_notation('plan-marshall:build-pyproject:pyproject_build', 'run') is True
    assert module._is_build_class_notation('plan-marshall:build-maven:maven', 'run') is True
    assert module._is_build_class_notation('plan-marshall:build-gradle:gradle', 'run') is True
    assert module._is_build_class_notation('plan-marshall:build-npm:npm', 'run') is True
    assert module._is_build_class_notation('plan-marshall:manage-status:manage-status', 'run') is False
    assert module._is_build_class_notation('plan-marshall:manage-change-ledger:manage-change-ledger', 'run') is False


# =============================================================================
# D0 tree-first emission — marketplace tree wins over stale cache / user-global
# =============================================================================
#
# Regression coverage for the OpenCode-regen gap: with a stale deployed cache
# present, every emitted notation must resolve to tree code. Tree-first holds
# in two places — the emitted mappings (ordered tree-first, with stale cache
# paths rewritten to their live tree equivalent) and the OpenCode resolver
# (an executor-file-anchored tree probe ahead of the dash-namespaced root
# walk, user-global roots deprioritised behind the tree but kept as fallback).


def test_generate_mappings_code_orders_tree_dirs_first():
    """Tree paths emit before deployed-cache copies, each family alphabetical."""
    mappings = {
        'b:z:zeta': '/home/u/.config/opencode/skills/b-z/scripts/zeta.py',
        'a:m:alpha': '/repo/marketplace/bundles/a/skills/m/scripts/alpha.py',
        'a:a:aaa': '/repo/marketplace/bundles/a/skills/a/scripts/aaa.py',
    }

    code = _gen.generate_mappings_code(mappings)

    lines = code.splitlines()
    assert len(lines) == 3
    # Tree family first, alphabetical within the family ...
    assert '"a:a:aaa"' in lines[0]
    assert '"a:m:alpha"' in lines[1]
    # ... then the deployed copy.
    assert '"b:z:zeta"' in lines[2]


def test_rewrite_mappings_to_tree_prefers_live_tree(tmp_path):
    """A stale cache path rewrites to its live tree equivalent when it exists."""
    base_path = tmp_path / 'tree' / 'marketplace' / 'bundles'
    (base_path / 'plan-marshall' / 'skills').mkdir(parents=True)
    script = base_path / 'probe-bundle' / 'skills' / 'probe-skill' / 'scripts' / 'probe_script.py'
    script.parent.mkdir(parents=True)
    script.write_text('# tree', encoding='utf-8')

    stale = {
        'probe-bundle:probe-skill:probe_script': '/stale/cache/0.1.1/skills/probe-skill/scripts/probe_script.py',
        'default-bundle:my-skill:do_thing': '/proj/.opencode/skills/my-skill/scripts/do_thing.py',
    }

    rewritten = _gen._rewrite_mappings_to_tree(stale, base_path)

    assert rewritten['probe-bundle:probe-skill:probe_script'] == str(script.resolve().as_posix())
    # Project-local pseudo-bundle entries have no tree equivalent and are kept.
    assert rewritten['default-bundle:my-skill:do_thing'] == stale['default-bundle:my-skill:do_thing']


def test_rewrite_mappings_to_tree_without_tree_base_returns_input_unchanged(tmp_path, monkeypatch):
    """No resolvable tree base means no comparison — the input is kept verbatim."""

    def _no_tree(*args, **kwargs):
        raise FileNotFoundError('no marketplace tree')

    monkeypatch.setattr(_gen, '_shared_get_base_path', _no_tree)
    base_path = tmp_path / 'bundles'
    base_path.mkdir()
    mappings = {
        'plan-marshall:manage-status:manage-status': '/stale/cache/0.1.1/skills/manage-status/scripts/manage-status.py',
    }

    assert _gen._rewrite_mappings_to_tree(mappings, base_path) == mappings


def test_opencode_resolver_code_carries_tree_first_probe():
    """The emitted OpenCode resolver probes the tree before the root walk."""
    code = _gen.generate_target_aware_resolver_code('opencode')

    assert 'def _resolve_notation_by_target(' in code
    assert 'marketplace' in code and 'bundles' in code


def _exec_opencode_resolver_with_executor_file(fake_file):
    """Exec the OpenCode resolver with ``__file__`` pinned to a fake executor."""
    code = _gen.generate_target_aware_resolver_code('opencode')
    ns = types.ModuleType('opencode_resolver_tree_first')
    ns.__dict__['Path'] = Path
    ns.__dict__['os'] = os
    ns.__dict__['__file__'] = fake_file
    exec(compile(code, '<resolver>', 'exec'), ns.__dict__)
    return ns


def test_opencode_resolver_prefers_tree_over_user_global_stale_copy(tmp_path, monkeypatch):
    """Tree above the executor file beats a stale user-global copy of the same notation.

    The fake ``d0-bundle`` exists nowhere in the real source tree, so the only
    tree that can answer is the synthetic checkout — a stale user-global copy
    must not shadow it.
    """
    checkout = tmp_path / 'checkout'
    tree_script = (
        checkout / 'marketplace' / 'bundles' / 'd0-bundle' / 'skills' / 'd0-skill' / 'scripts' / 'd0_script.py'
    )
    tree_script.parent.mkdir(parents=True)
    tree_script.write_text('# tree', encoding='utf-8')

    home = tmp_path / 'home'
    stale = home / '.config' / 'opencode' / 'skills' / 'd0-bundle-d0-skill' / 'scripts' / 'd0_script.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('# stale user-global copy', encoding='utf-8')

    monkeypatch.setenv('HOME', str(home))
    monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

    ns = _exec_opencode_resolver_with_executor_file(str(checkout / '.plan' / 'execute-script.py'))

    assert ns._resolve_notation_by_target('d0-bundle:d0-skill:d0_script') == str(tree_script.resolve())


def test_opencode_resolver_user_global_still_serves_without_tree(tmp_path, monkeypatch):
    """User-global roots are deprioritised, not removed — no tree, still found."""
    home = tmp_path / 'home'
    stale = home / '.config' / 'opencode' / 'skills' / 'd0-bundle-d0-skill' / 'scripts' / 'd0_script.py'
    stale.parent.mkdir(parents=True)
    stale.write_text('# user-global fallback', encoding='utf-8')

    monkeypatch.setenv('HOME', str(home))
    monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

    ns = _exec_opencode_resolver_with_executor_file(str(tmp_path / 'elsewhere' / 'execute-script.py'))

    assert ns._resolve_notation_by_target('d0-bundle:d0-skill:d0_script') == str(stale.resolve())
