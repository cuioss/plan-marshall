#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the authored ``mutating`` signal on ``resolve_command``.

Pins deliverable 4 of the architecture-resolution plan (lesson
2026-07-16-17-013 recommendation 3): a resolved canonical derived from an
operator-authored mutating profile carries ``mutating: true``; an unmarked
canonical omits the field entirely (authored-true vs unknown stays
distinguishable — no inferred ``mutating: false`` ever).

The signal is stamped by build-maven's ``_build_commands`` as a dict-form
command-map entry ``{'executable': ..., 'mutating': True}``; these tests seed
that persisted shape directly and assert ``resolve_command`` surfaces it on
both the module-level and root-cascade resolution paths.
"""

import importlib.util
import sys
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
_cmd_client_query = _load_module('_cmd_client_query', '_cmd_client_query.py')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
resolve_command = _cmd_client_query.resolve_command


# =============================================================================
# Fixture helpers
# =============================================================================

_MUTATING_GATE = {
    'executable': (
        'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "verify -Ppre-commit"'
    ),
    'mutating': True,
}

_PLAIN_VERIFY = 'python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "verify"'


def _seed(project_dir: str, root_commands: dict, leaf_commands: dict | None = None) -> None:
    """Seed _project.json plus a root module (path '.') and an optional leaf module."""
    modules: dict = {'root-mod': {}}
    if leaf_commands is not None:
        modules['leaf-mod'] = {}
    save_project_meta(
        {
            'name': 'resolve-mutating-test',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': modules,
        },
        project_dir,
    )
    save_module_derived(
        'root-mod',
        {'name': 'root-mod', 'build_systems': ['maven'], 'paths': {'module': '.'}, 'commands': root_commands},
        project_dir,
    )
    if leaf_commands is not None:
        save_module_derived(
            'leaf-mod',
            {'name': 'leaf-mod', 'build_systems': ['maven'], 'paths': {'module': 'leaf'}, 'commands': leaf_commands},
            project_dir,
        )


# =============================================================================
# Tests
# =============================================================================


def test_resolve_surfaces_mutating_true_on_authored_canonical(tmp_path):
    """Lesson 2026-07-16-17-013 rec. 3: a mutating canonical resolves with mutating: true."""
    _seed(str(tmp_path), {'quality-gate': _MUTATING_GATE, 'verify': _PLAIN_VERIFY})

    result = resolve_command('quality-gate', 'root-mod', str(tmp_path))

    assert result['mutating'] is True
    assert result['executable'] == _MUTATING_GATE['executable']
    assert result['resolution_level'] == 'module'


def test_resolve_omits_mutating_on_unmarked_canonical(tmp_path):
    """An unmarked canonical (string entry) omits the field — no inferred false."""
    _seed(str(tmp_path), {'quality-gate': _MUTATING_GATE, 'verify': _PLAIN_VERIFY})

    result = resolve_command('verify', 'root-mod', str(tmp_path))

    assert 'mutating' not in result
    assert result['executable'] == _PLAIN_VERIFY


def test_resolve_omits_mutating_on_unmarked_dict_entry(tmp_path):
    """A dict-form entry without the stamp also omits the field."""
    _seed(str(tmp_path), {'verify': {'executable': _PLAIN_VERIFY}})

    result = resolve_command('verify', 'root-mod', str(tmp_path))

    assert 'mutating' not in result
    assert result['executable'] == _PLAIN_VERIFY


def test_resolve_surfaces_mutating_through_root_cascade(tmp_path):
    """The root-cascade resolution path surfaces the field identically."""
    _seed(
        str(tmp_path),
        root_commands={'quality-gate': _MUTATING_GATE, 'verify': _PLAIN_VERIFY},
        leaf_commands={'verify': _PLAIN_VERIFY},
    )

    result = resolve_command('quality-gate', 'leaf-mod', str(tmp_path))

    assert result['resolution_level'] == 'root'
    assert result['module'] == 'root-mod'
    assert result['mutating'] is True
