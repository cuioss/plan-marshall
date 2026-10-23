#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The resolver's exclusion read fails closed, narrows by bundle, and is scripted.

PLAN-LB-80 D1/D2/D3 from the persona-resolver side:

* D1 — an unreadable ``marshal.json`` is reported, never degraded to "no
  exclusions", and an unimportable shared reader is an error too.
* D2 — a qualified exclusion removes a cell's bare skill only when that skill
  belongs to the excluded bundle.
* D3 — the persona augmentation phase-4 runs is a script verb, not a prose
  instruction, and the phase-4 text names that verb.
"""

import os
from pathlib import Path

import pytest
from extension_base import ExtensionBase

from conftest import create_marshal_json, load_script_module

_mp = load_script_module(
    'plan-marshall',
    'manage-personas',
    'manage_personas.py',
    'manage_personas_resolver_lb80',
)

CORE = 'pm-dev-java:java-core'


# =============================================================================
# Helpers
# =============================================================================


def _write_marshal(config: dict) -> Path:
    """Write a real marshal.json where the project config reader resolves it."""
    return Path(create_marshal_json(Path(os.environ['PLAN_BASE_DIR']), config=config, nest_in_plan_dir=False))


def _write_malformed_marshal() -> Path:
    """Write a marshal.json that exists but cannot be parsed (execution context)."""
    base = Path(os.environ['PLAN_BASE_DIR'])
    base.mkdir(parents=True, exist_ok=True)
    path = base / 'marshal.json'
    path.write_text('{"skill_domains": ', encoding='utf-8')
    return path


def _write_persona(bundles_root: Path, key: str, composes: list[str]) -> Path:
    """Write a synthetic persona whose composition edges are ``composes``."""
    bundle, skill = key.split(':', 1)
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / 'SKILL.md'
    path.write_text(
        '---\nimplements: persona\nprofiles: []\ncomposes: [' + ', '.join(composes) + ']\n---\n',
        encoding='utf-8',
    )
    return path


class _BareCellExtension(ExtensionBase):
    """A domain whose cell carries a BARE skill, plus a qualified default."""

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {'key': 'java', 'name': 'Java'},
                'profiles': {
                    'core': {'defaults': [{'skill': CORE}], 'optionals': []},
                    'implementation': {'defaults': [], 'optionals': [{'skill': 'java-cdi'}]},
                },
            }
        ]

    def applies_to_module(self, module_data: dict, active_profiles: set[str] | None = None) -> dict:
        return self._build_applicable_result(
            'high', [], module_data=module_data, active_profiles=active_profiles, domain_key='java'
        )


def _architecture_optionals() -> list[str]:
    """The optionals the architecture path serves for the bare-cell extension."""
    module_data = {'name': 'sample-module', 'build_systems': ['maven'], 'dependencies': []}
    result = _BareCellExtension().applies_to_module(module_data)
    return [entry['skill'] for entry in result['skills_by_profile']['implementation']['optionals']]


# =============================================================================
# D1 — the exclusion read fails closed
# =============================================================================


def test_malformed_marshal_makes_the_resolver_report_the_error(tmp_path, monkeypatch):
    """`manage-personas resolve` reports the read failure instead of serving."""
    _write_persona(tmp_path, 'plan-marshall:persona-x', composes=['plan-marshall:ref-code-quality'])
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)
    _write_malformed_marshal()

    result = _mp.cmd_resolve(
        type('Args', (), {'persona_key': 'plan-marshall:persona-x', 'domains': 'java', 'module': ''})()
    )

    assert result['status'] == 'error'
    assert result['error'] == 'skill_exclusions_unreadable'


def test_absent_marshal_still_resolves_without_exclusions(tmp_path, monkeypatch):
    """Regression guard: no configuration means no exclusions, not an error."""
    _write_persona(tmp_path, 'plan-marshall:persona-x', composes=['plan-marshall:ref-code-quality'])
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)

    result = _mp.cmd_resolve(
        type('Args', (), {'persona_key': 'plan-marshall:persona-x', 'domains': 'java', 'module': ''})()
    )

    assert result['status'] == 'success'
    assert 'plan-marshall:ref-code-quality' in result['skills']


def test_unimportable_reader_is_not_silently_no_exclusions(monkeypatch):
    """A broken shared reader raises instead of answering "nothing excluded"."""
    import builtins

    real_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == 'extension_base':
            raise ImportError('simulated missing shared reader')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', failing_import)

    with pytest.raises(Exception) as excinfo:
        _mp._excluded_skills('java')

    assert 'skill_exclusions_unreadable' in str(excinfo.value)


# =============================================================================
# D2 — a qualified exclusion narrows to its bundle, bare cells included
# =============================================================================


def test_another_bundles_qualified_exclusion_keeps_a_bare_skill():
    """`other-bundle:java-cdi` does not remove the pm-dev-java cell's bare java-cdi."""
    _write_marshal({'skill_domains': {'java': {'bundle': 'pm-dev-java', 'excluded_skills': ['other-bundle:java-cdi']}}})

    assert 'java-cdi' in _architecture_optionals()


def test_own_bundles_qualified_exclusion_removes_a_bare_skill():
    """`pm-dev-java:java-cdi` does remove the pm-dev-java cell's bare java-cdi."""
    _write_marshal({'skill_domains': {'java': {'bundle': 'pm-dev-java', 'excluded_skills': ['pm-dev-java:java-cdi']}}})

    assert 'java-cdi' not in _architecture_optionals()


def test_bare_exclusion_still_removes_a_bare_skill():
    """Matched negative control: a bare exclusion stays bundle-agnostic."""
    _write_marshal({'skill_domains': {'java': {'bundle': 'pm-dev-java', 'excluded_skills': ['java-cdi']}}})

    assert 'java-cdi' not in _architecture_optionals()


# =============================================================================
# D3 — the phase-4 augmentation step is a script verb
# =============================================================================


def test_the_augmentation_verb_exists_and_derives_the_persona():
    """`resolve-task-skills` derives the persona from a profile and resolves it."""
    parser = _mp.build_parser()
    args = parser.parse_args(
        ['resolve-task-skills', '--profile', 'implementation', '--domains', 'java', '--module', 'sample-module']
    )

    result = _mp.cmd_resolve_task_skills(args)

    assert result['status'] == 'success'
    assert result['profile'] == 'implementation'
    assert result['persona_key'] == 'plan-marshall:persona-implementer'
    assert 'plan-marshall:ref-code-quality' in result['skills']


def test_phase4_documentation_names_the_scripted_step():
    """The phase-4 text names the script call instead of prescribing a manual scan."""
    text = (
        Path(__file__).resolve().parents[3] / 'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md'
    ).read_text(encoding='utf-8')

    assert 'resolve-task-skills' in text
    assert 'via a reverse-lookup over persona frontmatter' not in text
