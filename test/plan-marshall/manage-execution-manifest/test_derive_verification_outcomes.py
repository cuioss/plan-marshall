#!/usr/bin/env python3
"""Property/outcome tests for the single deterministic deriver (Deliverable 10).

Where ``test_derive_verification.py`` (Deliverable 4) pins the deriver's
behaviour case-by-case, this suite asserts the two aggregate *properties* the
build_map plan promises about the derived build ladder:

1. **docs_only_build_check** — for documentation-only changed sets the deriver
   returns ZERO Python build commands (no ``compile`` / ``test-compile`` /
   ``module-tests`` / ``verify``). Only a docs-validate gate, if anything, is
   emitted. This is the structural guarantee that a docs-only deliverable never
   triggers a Python build mid-execute.

2. **build_pattern_analysis** — over a population of production-role artifacts:
   - every production changed set derives ``compile`` (~100% compile coverage);
   - a test changed set derives ``test-compile`` + ``module-tests``;
   - the deriver NEVER emits a per-task ``verify`` (the heavy full-pipeline run).
     Heavy runs are at most ONE per affected bundle, and that single run is the
     execute-exit holistic verify driven by the orchestrator — never by the
     per-task deriver. So from the deriver's vantage the per-task heavy-run count
     is exactly 0.

The deriver under test is ``cmd_derive_verification`` in ``_cmd_client.py``; it is
a pure, deterministic function of (changed artifacts, build_map, architecture).
The fixture seeds a marshal.json ``build_map`` plus per-module ``derived.json``
commands, mirroring the live shape, exactly as ``test_derive_verification.py``
does.
"""

import importlib.util
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    _REPO_ROOT
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
_cmd_client = _load_module('_cmd_client', '_cmd_client.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
cmd_derive_verification = _cmd_client.cmd_derive_verification


# =============================================================================
# Fixture helpers (mirror test_derive_verification.py)
# =============================================================================

# Two independent bundle modules so the "heavy runs <= 1 per bundle" property
# can be asserted over a multi-bundle population.
_BUILD_MAP = {
    'plan-marshall-plugin-dev': [
        {'glob': 'pm-a/scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'pm-b/scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        {'glob': 'test/pm-a/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'test/pm-a/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'test/pm-b/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'test/pm-b/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'marketplace/bundles/*/skills/*/SKILL.md', 'role': 'documentation', 'build_class': 'docs-validate'},
        {'glob': 'pm-a/skills/*/SKILL.md', 'role': 'documentation', 'build_class': 'docs-validate'},
        {'glob': 'pm-a/generated/*.py', 'role': 'production', 'build_class': 'none'},
    ],
}


def _module_derived(name: str, module_path: str) -> dict:
    return {
        'name': name,
        'build_systems': ['python'],
        'paths': {'module': module_path},
        'commands': {
            'compile': {
                'executable': (
                    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
                    f'run --command-args "compile {name}"'
                )
            },
            'test-compile': {
                'executable': (
                    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
                    f'run --command-args "test-compile {name}"'
                )
            },
            'module-tests': {
                'executable': (
                    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
                    f'run --command-args "module-tests {name}"'
                )
            },
            'verify': {
                'executable': (
                    'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
                    f'run --command-args "verify {name}"'
                )
            },
        },
    }


def _seed(project_dir: str) -> None:
    save_project_meta(
        {
            'name': 'derive-outcomes-test',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'pm-a': {}, 'pm-b': {}},
        },
        project_dir,
    )
    save_module_derived('pm-a', _module_derived('pm-a', 'pm-a'), project_dir)
    save_module_derived('pm-b', _module_derived('pm-b', 'pm-b'), project_dir)
    marshal = Path(project_dir) / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    # build_map is relocated under skill_domains (single source of truth).
    marshal.write_text(
        json.dumps({'skill_domains': {'build_map': _BUILD_MAP}}, indent=2), encoding='utf-8'
    )


def _derive(project_dir: str, changed: str) -> dict:
    return cmd_derive_verification(
        Namespace(changed_artifacts=changed, project_dir=project_dir)
    )


def _verbs(result: dict) -> list[str]:
    return [c['command'] for c in result['commands']]


def _executables(result: dict) -> list[str]:
    return [c['executable'] for c in result['commands']]


_PYTHON_BUILD_VERBS = frozenset({'compile', 'test-compile', 'module-tests', 'verify'})


# A representative population of documentation-only changed sets.
_DOCS_ONLY_SETS = (
    'marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md',
    'marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/SKILL.md',
    'pm-a/skills/foo/SKILL.md',
    (
        'marketplace/bundles/plan-marshall/skills/a/SKILL.md,'
        'marketplace/bundles/plan-marshall/skills/b/SKILL.md'
    ),
)

# A representative population of single-module production changed sets.
_PRODUCTION_SETS = (
    'pm-a/scripts/architecture.py',
    'pm-a/scripts/config.py',
    'pm-a/scripts/a.py,pm-a/scripts/b.py',
    'pm-b/scripts/derive.py',
    'pm-b/scripts/x.py,pm-b/scripts/y.py,pm-b/scripts/z.py',
)


# =============================================================================
# Suite 1: docs_only_build_check — docs-only derives ZERO Python builds
# =============================================================================


def test_every_docs_only_set_derives_zero_python_builds():
    """For every docs-only changed set, the deriver emits no Python build command."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        for changed in _DOCS_ONLY_SETS:
            result = _derive(str(project), changed)
            assert result['status'] == 'success', changed
            verbs = set(_verbs(result))
            python_builds = verbs & _PYTHON_BUILD_VERBS
            assert python_builds == set(), (
                f'docs-only changed set {changed!r} unexpectedly derived '
                f'Python build verbs: {sorted(python_builds)}'
            )


def test_docs_only_executables_never_invoke_python_build_command():
    """Belt-and-suspenders: no derived executable string runs a Python build verb."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        for changed in _DOCS_ONLY_SETS:
            result = _derive(str(project), changed)
            for executable in _executables(result):
                assert 'command-args "compile' not in executable, changed
                assert 'command-args "test-compile' not in executable, changed
                assert 'command-args "module-tests' not in executable, changed
                assert 'command-args "verify' not in executable, changed


# =============================================================================
# Suite 2: build_pattern_analysis — compile ~100% on prod, heavy runs == 0 per task
# =============================================================================


def test_every_production_set_derives_compile():
    """Over the production population, compile coverage is 100%."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        compile_hits = 0
        for changed in _PRODUCTION_SETS:
            result = _derive(str(project), changed)
            assert result['status'] == 'success', changed
            if 'compile' in _verbs(result):
                compile_hits += 1
        assert compile_hits == len(_PRODUCTION_SETS), (
            f'compile derived for only {compile_hits}/{len(_PRODUCTION_SETS)} '
            'production sets — expected ~100% coverage'
        )


def test_production_sets_never_derive_per_task_verify():
    """No production changed set derives the heavy full-pipeline `verify` per task."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        for changed in _PRODUCTION_SETS:
            result = _derive(str(project), changed)
            assert 'verify' not in _verbs(result), (
                f'production changed set {changed!r} derived a per-task heavy '
                "`verify` run — heavy runs belong to the execute-exit holistic "
                'verify only, never the per-task deriver'
            )


def test_test_set_derives_test_compile_and_module_tests_not_verify():
    """A test changed set derives test-compile + module-tests, never per-task verify."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = _derive(str(project), 'test/pm-a/test_foo.py')
        verbs = _verbs(result)
        assert 'test-compile' in verbs
        assert 'module-tests' in verbs
        assert 'compile' not in verbs
        assert 'verify' not in verbs


def test_no_changed_set_anywhere_derives_a_per_task_verify():
    """Heavy-run accounting: across docs + prod + test + mixed sets the deriver
    never emits `verify`. The heavy run is execute-exit-only (<= 1 per bundle),
    so the per-task deriver's heavy-run count is exactly 0 over the whole
    population."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        mixed = (
            'pm-a/scripts/architecture.py,'
            'test/pm-a/test_foo.py,'
            'marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md'
        )
        population = list(_DOCS_ONLY_SETS) + list(_PRODUCTION_SETS) + [
            'test/pm-a/test_foo.py',
            'test/pm-b/test_bar.py',
            mixed,
        ]

        heavy_runs = 0
        for changed in population:
            result = _derive(str(project), changed)
            heavy_runs += _verbs(result).count('verify')
        assert heavy_runs == 0, (
            f'deriver emitted {heavy_runs} per-task `verify` heavy runs across the '
            'population — expected exactly 0 (heavy verify is execute-exit-only)'
        )


def test_multi_file_production_set_derives_one_compile_per_bundle():
    """N production files within one bundle derive exactly ONE compile for that bundle."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = _derive(str(project), 'pm-a/scripts/a.py,pm-a/scripts/b.py,pm-a/scripts/c.py')
        compiles = [c for c in result['commands'] if c['command'] == 'compile']
        assert len(compiles) == 1


def test_two_bundle_production_set_derives_one_compile_each():
    """Production files spanning two bundles derive one compile per bundle (heavy
    full-pipeline runs stay <= 1 per bundle — here, 0 verify and 1 compile each)."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = _derive(str(project), 'pm-a/scripts/a.py,pm-b/scripts/x.py')
        compile_execs = sorted(
            c['executable'] for c in result['commands'] if c['command'] == 'compile'
        )
        assert len(compile_execs) == 2
        assert any('compile pm-a' in e for e in compile_execs)
        assert any('compile pm-b' in e for e in compile_execs)
        assert 'verify' not in _verbs(result)


def test_outcomes_deriver_is_deterministic():
    """Same inputs yield identical output — the property suite rests on purity."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        args = Namespace(
            changed_artifacts='pm-a/scripts/architecture.py,test/pm-a/test_foo.py',
            project_dir=str(project),
        )
        assert cmd_derive_verification(args) == cmd_derive_verification(args)
