#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``derive-verification`` deriver in ``_cmd_client.py``.

Pins the single deterministic build_map consumer (Deliverable 4 of the
build-map plan):

- a production changed set derives ``compile``;
- a test changed set derives ``test-compile`` + ``module-tests``;
- a docs-only changed set derives ZERO builds (documentation has no build owner,
  so doc paths go unclaimed);
- a ``none``-only changed set derives no command;
- a mixed set derives the union;
- derived commands are de-duplicated by their resolved executable;
- the deriver is a pure, deterministic function of (changed artifacts,
  build_map, architecture).

The deriver reads the merged ``build_map`` directly from the top-level
``build.map`` block in ``{project_dir}/.plan/marshal.json`` and resolves each
path's module by longest ``paths.module`` prefix, so the fixtures seed both a
marshal.json build.map and per-module ``derived.json`` files carrying
``paths.module`` + ``commands``.
"""

import importlib.util
import json
import sys
import tempfile
from argparse import Namespace
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'


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
classify_changed_path = _architecture_core.classify_changed_path
load_merged_build_map = _architecture_core.load_merged_build_map
resolve_module_for_path = _architecture_core.resolve_module_for_path
cmd_derive_verification = _cmd_client.cmd_derive_verification


# =============================================================================
# Fixture helpers
# =============================================================================

# A build_map that mirrors the real {domain: [{glob, role, build_class}]} shape.
# Globs are full-path fnmatch patterns, as the live extensions emit.
_BUILD_MAP = {
    'plan-marshall-plugin-dev': [
        {'glob': 'pm-mod/scripts/*.py', 'role': 'production', 'build_class': 'compile'},
        # Both depth forms, exactly as the real domain extensions emit
        # (e.g. pm-dev-python carries both `test/**/*.py` and `test/*.py`):
        # fnmatch `**` does not span a missing directory level, so the shallow
        # `test/pm-mod/*.py` form is required to claim `test/pm-mod/test_foo.py`.
        {'glob': 'test/pm-mod/**/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'test/pm-mod/*.py', 'role': 'test', 'build_class': 'module-tests'},
        {'glob': 'pm-mod/generated/*.py', 'role': 'production', 'build_class': 'none'},
    ],
}


def _module_derived(name: str, module_path: str) -> dict:
    """A module derived payload carrying paths.module + resolvable commands."""
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


def _seed(project_dir: str, build_map: dict | None = _BUILD_MAP) -> None:
    """Seed _project.json, one module (paths.module=pm-mod), and marshal.json.

    The build_map is seeded under the top-level ``build.map`` block (relocated;
    single source of truth), which is where ``load_merged_build_map`` reads it.
    """
    save_project_meta(
        {
            'name': 'derive-verification-test',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'pm-mod': {}},
        },
        project_dir,
    )
    save_module_derived('pm-mod', _module_derived('pm-mod', 'pm-mod'), project_dir)
    marshal = Path(project_dir) / '.plan' / 'marshal.json'
    marshal.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {}
    if build_map is not None:
        payload['build'] = {'map': build_map}
    marshal.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _executables(result: dict) -> list[str]:
    return [c['executable'] for c in result['commands']]


def _commands_for_verb(result: dict, verb: str) -> list[dict]:
    return [c for c in result['commands'] if c.get('command') == verb]


# =============================================================================
# Pure classification (classify_changed_path)
# =============================================================================


def test_classify_changed_path_longest_glob_wins():
    """When two globs match, the longest glob wins."""
    merged = {
        'd': [
            {'glob': '*.py', 'role': 'production', 'build_class': 'compile'},
            {'glob': 'pm-mod/generated/*.py', 'role': 'production', 'build_class': 'none'},
        ]
    }
    # The longer, more specific glob (none) wins over the broad *.py (compile).
    assert classify_changed_path('pm-mod/generated/foo.py', merged) == 'none'


def test_classify_changed_path_unmatched_returns_none():
    """A path no glob matches classifies to None (unclaimed)."""
    assert classify_changed_path('unrelated/file.txt', _BUILD_MAP) is None


def test_classify_changed_path_nested_pom_matches_bare_basename_route():
    """A nested ``services/auth/pom.xml`` is claimed by a bare ``pom.xml`` route.

    The bare-basename regime of the shared matcher (``route_matches``) matches
    a route with no ``/`` against the path's basename anywhere in the tree —
    the semantics the aggregator has always used. The pre-fix deriver matched
    the full path with ``fnmatch.fnmatch``, so every nested descriptor on a
    multi-module reactor went unclaimed (``classified_count: 0`` — lesson
    2026-07-16-17-012, TokenSheriff).
    """
    merged = {
        'java': [
            {'glob': 'pom.xml', 'role': 'config', 'build_class': 'verify'},
        ]
    }
    assert classify_changed_path('services/auth/pom.xml', merged) == 'verify'


def test_classify_changed_path_bare_basename_no_false_positive():
    """A bare-basename route claims only exact-basename matches, not siblings."""
    merged = {
        'javascript': [
            {'glob': 'package.json', 'role': 'config', 'build_class': 'verify'},
        ]
    }
    assert classify_changed_path('ui/package-lock.json', merged) is None


# =============================================================================
# Module resolution (resolve_module_for_path)
# =============================================================================


def test_resolve_module_for_path_prefix_match():
    """A path under a module's paths.module prefix resolves to that module."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))
        assert resolve_module_for_path('pm-mod/scripts/architecture.py', str(project)) == 'pm-mod'


def test_resolve_module_for_path_newly_created_file_resolves():
    """A path not yet in the files inventory still resolves by prefix."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))
        # File does not exist on disk / inventory — prefix resolution still works.
        assert resolve_module_for_path('pm-mod/scripts/brand_new.py', str(project)) == 'pm-mod'


# =============================================================================
# Deriver outcomes (cmd_derive_verification)
# =============================================================================


def test_production_path_derives_compile_only():
    """A production changed set derives compile, not the test ladder."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(changed_artifacts='pm-mod/scripts/architecture.py', project_dir=str(project))
        )

        assert result['status'] == 'success'
        verbs = {c['command'] for c in result['commands']}
        assert verbs == {'compile'}
        assert 'module-tests' not in verbs
        assert 'test-compile' not in verbs


def test_test_path_derives_test_compile_and_module_tests():
    """A test changed set derives test-compile + module-tests."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(changed_artifacts='test/pm-mod/test_foo.py', project_dir=str(project))
        )

        assert result['status'] == 'success'
        verbs = [c['command'] for c in result['commands']]
        assert 'test-compile' in verbs
        assert 'module-tests' in verbs
        assert 'compile' not in verbs


def test_docs_only_set_derives_zero_builds():
    """A docs-only changed set derives ZERO builds — documentation has no build owner.

    With the docs-validate build_class retired, a doc path matches no build_map
    glob, so it is recorded under ``unclaimed`` and derives no command at all.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        doc_path = 'marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md'
        result = cmd_derive_verification(
            Namespace(changed_artifacts=doc_path, project_dir=str(project))
        )

        assert result['status'] == 'success'
        # Zero commands — no compile / module-tests / verify and no doc gate.
        assert result['command_count'] == 0
        assert result['commands'] == []
        # The doc path is unclaimed (no build_map glob matched it).
        assert result['unclaimed'] == [doc_path]


def test_non_marketplace_doc_is_unclaimed():
    """A non-marketplace doc matches no build_map glob and derives nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(changed_artifacts='pm-mod/skills/foo/SKILL.md', project_dir=str(project))
        )

        assert result['status'] == 'success'
        assert result['command_count'] == 0
        assert result['commands'] == []
        assert result['unclaimed'] == ['pm-mod/skills/foo/SKILL.md']


def test_none_only_set_derives_no_command():
    """A changed set whose only role yields `none` derives no command at all."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(changed_artifacts='pm-mod/generated/codegen.py', project_dir=str(project))
        )

        assert result['status'] == 'success'
        assert result['command_count'] == 0
        assert result['commands'] == []


def test_mixed_set_derives_union():
    """A mixed prod+test+docs set derives the union of the buildable command sets.

    The doc path has no build owner, so it goes unclaimed and contributes no
    command — only the production and test paths derive builds.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        doc_path = 'marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md'
        result = cmd_derive_verification(
            Namespace(
                changed_artifacts=(
                    'pm-mod/scripts/architecture.py,'
                    'test/pm-mod/test_foo.py,'
                    f'{doc_path}'
                ),
                project_dir=str(project),
            )
        )

        assert result['status'] == 'success'
        verbs = {c['command'] for c in result['commands']}
        assert 'compile' in verbs
        assert 'test-compile' in verbs
        assert 'module-tests' in verbs
        assert 'docs-validate' not in verbs
        # The doc path is unclaimed — no build owner for documentation.
        assert doc_path in result['unclaimed']


def test_duplicate_production_files_derive_one_compile():
    """N production files in one module derive ONE compile, not N (executable dedup)."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(
                changed_artifacts='pm-mod/scripts/a.py,pm-mod/scripts/b.py,pm-mod/scripts/c.py',
                project_dir=str(project),
            )
        )

        compiles = _commands_for_verb(result, 'compile')
        assert len(compiles) == 1


def test_unclaimed_path_recorded():
    """A path no glob matches is recorded under unclaimed and derives nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        result = cmd_derive_verification(
            Namespace(changed_artifacts='unrelated/file.txt', project_dir=str(project))
        )

        assert result['status'] == 'success'
        assert result['unclaimed'] == ['unrelated/file.txt']
        assert result['commands'] == []


def test_deriver_is_deterministic():
    """The deriver is a pure function — same inputs yield identical output."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project))

        args = Namespace(
            changed_artifacts='pm-mod/scripts/architecture.py,test/pm-mod/test_foo.py',
            project_dir=str(project),
        )
        first = cmd_derive_verification(args)
        second = cmd_derive_verification(args)
        assert first == second


def test_it_route_stamped_verify_derives_failsafe_gate():
    """A seeded IT route stamped build_class=verify derives the module's verify
    executable — not the Surefire test goal — for a changed *IT.java artifact
    (lesson 2026-07-16-16-001 issue 1).
    """
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        build_map = {
            'java': [
                {'glob': '*/src/test/*IT.java', 'role': 'test', 'build_class': 'verify'},
                {'glob': '*/src/test/*.java', 'role': 'test', 'build_class': 'module-tests'},
            ],
        }
        _seed(str(project), build_map=build_map)

        result = cmd_derive_verification(
            Namespace(
                changed_artifacts='pm-mod/src/test/java/com/example/RestApiGatewayIT.java',
                project_dir=str(project),
            )
        )

        assert result['status'] == 'success'
        verbs = {c['command'] for c in result['commands']}
        assert verbs == {'verify'}
        assert any('verify pm-mod' in e for e in _executables(result))


def test_plain_test_java_still_derives_module_tests_beside_it_route():
    """A plain FooTest.java under the same seeded map keeps the module-tests ladder."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        build_map = {
            'java': [
                {'glob': '*/src/test/*IT.java', 'role': 'test', 'build_class': 'verify'},
                {'glob': '*/src/test/*.java', 'role': 'test', 'build_class': 'module-tests'},
            ],
        }
        _seed(str(project), build_map=build_map)

        result = cmd_derive_verification(
            Namespace(
                changed_artifacts='pm-mod/src/test/java/com/example/FooTest.java',
                project_dir=str(project),
            )
        )

        assert result['status'] == 'success'
        verbs = {c['command'] for c in result['commands']}
        assert verbs == {'test-compile', 'module-tests'}


def test_nested_pom_against_bare_route_derives_verify():
    """A nested pom.xml against a seeded bare ``pom.xml`` route classifies
    non-zero and derives the module's ``verify`` executable (lesson
    2026-07-16-17-012 end-to-end).
    """
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        build_map = {
            'java': [
                {'glob': 'pom.xml', 'role': 'config', 'build_class': 'verify'},
            ],
        }
        _seed(str(project), build_map=build_map)

        result = cmd_derive_verification(
            Namespace(
                changed_artifacts='pm-mod/services/auth/pom.xml',
                project_dir=str(project),
            )
        )

        assert result['status'] == 'success'
        assert result['classified_count'] == 1
        assert result['unclaimed'] == []
        verbs = {c['command'] for c in result['commands']}
        assert verbs == {'verify'}
        assert any('verify pm-mod' in e for e in _executables(result))


def test_empty_build_map_yields_all_unclaimed():
    """With no build_map seeded, every path is unclaimed and nothing derives."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / 'project'
        project.mkdir()
        _seed(str(project), build_map=None)

        result = cmd_derive_verification(
            Namespace(changed_artifacts='pm-mod/scripts/architecture.py', project_dir=str(project))
        )

        assert result['status'] == 'success'
        assert result['unclaimed'] == ['pm-mod/scripts/architecture.py']
        assert result['commands'] == []
