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

import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from conftest import _MARKETPLACE_SCRIPT_DIRS, PROJECT_ROOT, load_script_module


@pytest.fixture()
def derived_surfaces(monkeypatch):
    """Pin the surface-derivation result the generator consumes."""
    monkeypatch.setattr(_gen, 'derive_script_surfaces', lambda *a, **k: ({}, _stats(1, 0, 0)))

@pytest.fixture()
def previous_surfaces(monkeypatch):
    """Pin the previously-generated surface set the generator reads."""
    monkeypatch.setattr(_gen, 'read_previous_surfaces', lambda executor: {'a:b:c': _surface_literal()})

@pytest.fixture()
def plan_base_dir_at_tmp(tmp_path, monkeypatch):
    """Point PLAN_BASE_DIR at an isolated tmp_path and yield that root."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    return tmp_path

# Unique module_name so the in-process load is distinct from the existing
# test module's ``load_module()`` exec-based load (which traces as <string>
# and does NOT count for coverage).
_gen = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_behavior'
)

# The build-class change-ledger boundary lives in the executor TEMPLATE (the
# generated executor), not in generate_executor.py. Rendering the template into
# an importable module is the established pattern for unit-testing its dispatch
# boundary helpers (mirrors ``_load_template_module`` in test_generate_executor.py).
_TEMPLATE_PATH = (
    PROJECT_ROOT
    / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
)


def _load_template_module() -> types.ModuleType:
    """Render the executor template with inert placeholders and exec it as a module.

    Fills the ``{{...}}`` substitution tokens with inert stand-ins (empty
    mappings, no target-aware resolver body) and points ``{{LOGGING_DIR}}`` at
    the real manage-logging scripts so the module-level ``from plan_logging
    import ...`` succeeds. The template's ``_ledger_core`` / ``worktree_sha`` /
    ``toon_parser`` imports resolve without a bootstrap, because the root conftest
    already put the shared script dirs on ``sys.path``. ``main()`` is guarded by
    ``__name__ == '__main__'`` so exec does not dispatch anything.
    """
    source = _TEMPLATE_PATH.read_text(encoding='utf-8')
    logging_dir = str(
        PROJECT_ROOT
        / 'marketplace/bundles/plan-marshall/skills/manage-logging/scripts'
    )
    source = source.replace('{{SCRIPT_MAPPINGS}}', '')
    source = source.replace('{{SCRIPT_SURFACES}}', '').replace('{{SUBCOMMAND_MAPPINGS}}', '')
    source = source.replace('{{LOGGING_DIR}}', logging_dir)
    source = source.replace('{{SHARED_MODULE_DIRS}}', '# (none)')
    source = source.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    source = source.replace('{{PLAN_DIR_NAME}}', '.plan')
    source = source.replace('{{EXECUTOR_TARGET}}', 'claude')
    source = source.replace('{{GENERATED_VERSION}}', '')
    source = source.replace('{{MAPPINGS_FINGERPRINT}}', '')
    source = source.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )

    # No bootstrap: the root conftest already put every entry of
    # ``_MARKETPLACE_SCRIPT_DIRS`` on ``sys.path`` at its own import time, so the
    # exec'd template's transitive imports resolve.

    module = types.ModuleType('executor_template_ledger_boundary')
    module.__dict__['__file__'] = str(_TEMPLATE_PATH)
    exec(compile(source, str(_TEMPLATE_PATH), 'exec'), module.__dict__)
    return module


# =============================================================================
# read_marshal_target — walk-up resolution of runtime.target from marshal.json
# =============================================================================


@pytest.mark.parametrize(
    ('marshal_body', 'expected_target'),
    [
        ('{"runtime": {"target": "opencode"}}', 'opencode'),
        (None, 'claude'),
        ('{not valid json', 'claude'),
        ('{"other": {"target": "opencode"}}', 'claude'),
        ('{"runtime": "claude"}', 'claude'),
    ],
    ids=[
        'declared-target-is-returned-verbatim',
        'no-marshal-json-anywhere-up-the-tree',
        'marshal-json-is-not-valid-json',
        'no-runtime-key',
        'runtime-is-a-scalar-not-a-mapping',
    ],
)
def test_read_marshal_target(tmp_path, marshal_body, expected_target):
    """A declared runtime.target is returned; every unusable shape reads 'claude'.

    ``marshal_body`` of ``None`` writes no file at all, so the walk reaches the
    filesystem root without a hit. The remaining defaulting rows are the ways a
    file that DOES exist can fail to name a target: unparseable JSON, no
    ``runtime`` key, and a ``runtime`` that is a scalar rather than a mapping.
    The first row is their matched control — a reader that always answered
    'claude' would fail on it rather than satisfy every defaulting row.
    """
    if marshal_body is not None:
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        (plan_dir / 'marshal.json').write_text(marshal_body, encoding='utf-8')

    assert _gen.read_marshal_target(cwd=tmp_path) == expected_target


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
    monkeypatch.setattr(_gen, "_shared_get_project_skill_roots", lambda: (".custom/skills",))
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
    monkeypatch.setattr(_gen, "_shared_get_project_skill_roots", lambda: ())
    local = tmp_path / '.claude' / 'skills' / 'my-skill' / 'scripts'
    local.mkdir(parents=True)
    (local / 'do_thing.py').write_text('# script', encoding='utf-8')

    assert _gen.discover_local_scripts(cwd=tmp_path) == {}

# The format marker is read from the generator's own constant rather than
# written as a literal: a hard-coded version turns this fixture into a
# permanent format skew the moment the real version is bumped, and the failure
# then reads as "generation broke" instead of "the fixture is stale".
_TEMPLATE_BODY = (
    f'# TEMPLATE_FORMAT_VERSION: {_gen._SUPPORTED_TEMPLATE_FORMAT_VERSION}\n'
    'SCRIPTS = {\n'
    '{{SCRIPT_MAPPINGS}}\n'
    '}\n'
    'SCRIPT_SURFACES = {\n'
    '{{SCRIPT_SURFACES}}\n'
    '}\n'
    'LOGGING_DIR = "{{LOGGING_DIR}}"\n'
    '{{SHARED_MODULE_DIRS}}\n'
    'EXTRA = [{{EXTRA_SCRIPT_DIRS}}]\n'
    'PLAN_DIR_NAME = "{{PLAN_DIR_NAME}}"\n'
    'EXECUTOR_TARGET = "{{EXECUTOR_TARGET}}"\n'
    '{{TARGET_AWARE_RESOLVER}}\n'
)


def _build_synthetic_base(tmp_path: Path) -> Path:
    """Create a minimal marketplace tree carrying the executor template.

    ``generate_executor`` resolves the template via
    ``get_templates_dir(base)`` → ``<base>/plan-marshall/skills/
    tools-script-executor/templates/execute-script.py.template``. Only that file
    is required for the writer to run; the logging/shared dirs resolve to
    non-existent paths and degrade gracefully.
    """
    templates = (
        tmp_path / 'base' / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates'
    )
    templates.mkdir(parents=True)
    (templates / 'execute-script.py.template').write_text(_TEMPLATE_BODY, encoding='utf-8')
    return tmp_path / 'base'


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


def test_fail_open_guard_refuses_zero_surfaces_against_nonempty_previous(tmp_path, monkeypatch, previous_surfaces, derived_surfaces):
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
    monkeypatch.setattr(_gen, 'read_previous_surfaces', lambda executor: {})

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
def test_fail_open_guard_does_not_trip_when_surfaces_are_emitted(tmp_path, monkeypatch, derived, reused, previous_surfaces):
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


def test_surface_stats_line_emitted_on_both_fail_open_and_success(tmp_path, monkeypatch, capsys, previous_surfaces, derived_surfaces):
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
    monkeypatch.setattr(_gen, 'read_previous_surfaces', lambda executor: {})
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
    PROJECT_ROOT
    / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py'
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
    scripts = (
        tmp_path / 'mkt' / 'marketplace' / 'bundles' / 'probe-bundle'
        / 'skills' / 'probe-skill' / 'scripts'
    )
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
    monkeypatch.setattr(_gen, 'read_marshal_target', lambda: 'claude')
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
    (tmp_path / 'caller.md').write_text(
        'python3 .plan/execute-script.py b:s:manage_status read\n', encoding='utf-8'
    )
    registered = {'b:s:manage-status': '/path/manage-status.py'}

    drift = _gen._detect_notation_drift(registered, tmp_path)

    assert ('b:s:manage_status', 'b:s:manage-status') in drift


def test_detect_notation_drift_empty_when_reference_registered(tmp_path):
    """A reference that IS registered produces no drift entry."""
    (tmp_path / 'caller.md').write_text(
        'python3 .plan/execute-script.py b:s:manage-status read\n', encoding='utf-8'
    )
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
        'caller-notation drift detected in marketplace source — '
        f'offending (referenced, registered) pairs: {drift}'
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
    assert (
        module._is_build_class_notation('plan-marshall:manage-change-ledger:manage-change-ledger', 'run')
        is False
    )
