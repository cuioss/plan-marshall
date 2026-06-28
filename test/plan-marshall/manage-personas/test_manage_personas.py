#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for the manage-personas ``resolve`` script.

These tests exercise ``manage_personas.py`` IN-PROCESS (via the loaded module)
so coverage.py attributes the executed lines to the source script. The suite has
three layers:

1. Pure-helper unit tests (frontmatter parsing, YAML-list parsing, path
   resolution) over hand-built inputs and a synthetic bundle tree.
2. ``cmd_resolve`` / ``_flatten`` DAG tests over a synthetic bundle tree, with
   ``resolve_bundles_root`` monkeypatched so the resolver reads the synthetic
   personas rather than the real marketplace tree. These cover the success path,
   dedup, profile×domain merging, and every error discriminator (cycle,
   not-a-persona, persona-not-found, composed-persona-not-found).
3. Real-tree integration tests that resolve the ACTUAL shipped personas
   (``persona-implementer``, ``persona-code-reviewer``, ``persona-module-tester``)
   and assert the concrete flattened ``skills[]`` the production composition
   produces.

A small number of CLI-plumbing checks run the script as a subprocess to confirm
exit codes; those do not contribute to coverage (separate process) and are kept
minimal — the behavioral coverage comes from the in-process ``main`` calls.
"""

import sys
import types
from pathlib import Path

import pytest

from conftest import get_script_path, load_script_module

# In-process module under test — coverage attributes executed lines here.
_mp = load_script_module(
    'plan-marshall', 'manage-personas', 'manage_personas.py', 'manage_personas_under_test'
)

# Subprocess path for the few CLI-plumbing exit-code checks.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-personas', 'manage_personas.py')

BASE_PERSONA = _mp.BASE_PERSONA


# =============================================================================
# Synthetic bundle-tree helpers
# =============================================================================


def _write_skill(
    bundles_root: Path,
    key: str,
    *,
    implements: str = 'persona',
    profiles: list[str] | None = None,
    composes: list[str] | None = None,
) -> Path:
    """Write a synthetic ``bundle:skill`` SKILL.md under ``bundles_root``.

    Mirrors the on-disk layout ``{bundles_root}/{bundle}/skills/{skill}/SKILL.md``
    that ``resolve_bundle_path`` resolves. Returns the written path.
    """
    bundle, skill = key.split(':', 1)
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)

    lines = ['---', f'implements: {implements}']
    if profiles is not None:
        lines.append('profiles: [' + ', '.join(profiles) + ']')
    if composes is not None:
        lines.append('composes: [' + ', '.join(composes) + ']')
    lines += ['---', '', f'# {skill}', '']
    path = skill_dir / 'SKILL.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path


def _resolve_ns(persona_key: str, domains: str = ''):
    """Build the argparse Namespace ``cmd_resolve`` consumes."""
    return types.SimpleNamespace(persona_key=persona_key, domains=domains)


# =============================================================================
# _leading_frontmatter
# =============================================================================


def test_leading_frontmatter_extracts_delimited_block():
    content = '---\nname: foo\nprofiles: [a]\n---\n# body\ntext'
    assert _mp._leading_frontmatter(content) == 'name: foo\nprofiles: [a]'


def test_leading_frontmatter_absent_when_no_leading_delimiter():
    assert _mp._leading_frontmatter('# heading\nno frontmatter') == ''


def test_leading_frontmatter_absent_when_unterminated():
    # Opening --- but no closing --- => not a valid block.
    assert _mp._leading_frontmatter('---\nname: foo\nstill going') == ''


def test_leading_frontmatter_empty_string():
    assert _mp._leading_frontmatter('') == ''


# =============================================================================
# _parse_yaml_list
# =============================================================================


def test_parse_yaml_list_inline_flow_form():
    assert _mp._parse_yaml_list('profiles: [a, b, c]', 'profiles') == ['a', 'b', 'c']


def test_parse_yaml_list_inline_empty_brackets():
    assert _mp._parse_yaml_list('profiles: []', 'profiles') == []


def test_parse_yaml_list_inline_strips_quotes():
    assert _mp._parse_yaml_list("composes: ['x:y', \"p:q\"]", 'composes') == ['x:y', 'p:q']


def test_parse_yaml_list_block_form():
    fm = 'composes:\n  - plan-marshall:ref-a\n  - plan-marshall:ref-b\n'
    assert _mp._parse_yaml_list(fm, 'composes') == ['plan-marshall:ref-a', 'plan-marshall:ref-b']


def test_parse_yaml_list_block_form_stops_at_next_key():
    fm = 'composes:\n  - one\n  - two\nname: foo\n'
    assert _mp._parse_yaml_list(fm, 'composes') == ['one', 'two']


def test_parse_yaml_list_block_form_skips_blank_lines():
    fm = 'composes:\n\n  - one\n\n  - two\n'
    assert _mp._parse_yaml_list(fm, 'composes') == ['one', 'two']


def test_parse_yaml_list_absent_field_returns_empty():
    assert _mp._parse_yaml_list('name: foo\n', 'profiles') == []


# =============================================================================
# _resolve_persona_path
# =============================================================================


def test_resolve_persona_path_without_colon_returns_none(tmp_path):
    assert _mp._resolve_persona_path(tmp_path, 'nocolon') is None


def test_resolve_persona_path_missing_file_returns_none(tmp_path):
    assert _mp._resolve_persona_path(tmp_path, 'plan-marshall:persona-absent') is None


def test_resolve_persona_path_existing_returns_path(tmp_path):
    written = _write_skill(tmp_path, 'plan-marshall:persona-x')
    resolved = _mp._resolve_persona_path(tmp_path, 'plan-marshall:persona-x')
    assert resolved == written
    assert resolved.is_file()


# =============================================================================
# _read_persona_frontmatter
# =============================================================================


def test_read_persona_frontmatter_absent_returns_none(tmp_path):
    assert _mp._read_persona_frontmatter(tmp_path, 'plan-marshall:persona-absent') is None


def test_read_persona_frontmatter_reads_lists_and_persona_flag(tmp_path):
    _write_skill(
        tmp_path,
        'plan-marshall:persona-x',
        profiles=['implementation', 'quality'],
        composes=['plan-marshall:ref-code-quality'],
    )
    fm = _mp._read_persona_frontmatter(tmp_path, 'plan-marshall:persona-x')
    assert fm == {
        'profiles': ['implementation', 'quality'],
        'composes': ['plan-marshall:ref-code-quality'],
        'is_persona': True,
    }


def test_read_persona_frontmatter_is_persona_false_for_ref(tmp_path):
    _write_skill(tmp_path, 'plan-marshall:ref-thing', implements='ref')
    fm = _mp._read_persona_frontmatter(tmp_path, 'plan-marshall:ref-thing')
    assert fm is not None
    assert fm['is_persona'] is False


def test_read_persona_frontmatter_oserror_on_read_returns_none(tmp_path, monkeypatch):
    # File resolves (is_file True) but the read itself fails — the TOCTOU /
    # permission guard must map the OSError to None rather than raising.
    _write_skill(tmp_path, 'plan-marshall:persona-x')

    def _raise(self, *args, **kwargs):
        raise OSError('simulated unreadable file')

    monkeypatch.setattr(Path, 'read_text', _raise)
    assert _mp._read_persona_frontmatter(tmp_path, 'plan-marshall:persona-x') is None


# =============================================================================
# _resolve_profile_domain_skills
# =============================================================================


def _install_fake_skill_resolution(monkeypatch, func):
    """Inject a fake ``_cmd_skill_resolution`` module exposing ``func``."""
    fake = types.ModuleType('_cmd_skill_resolution')
    fake.cmd_resolve_domain_skills = func
    monkeypatch.setitem(sys.modules, '_cmd_skill_resolution', fake)


def test_resolve_profile_domain_skills_import_error_returns_empty(monkeypatch):
    # sys.modules[name] = None forces ``import`` to raise ImportError.
    monkeypatch.setitem(sys.modules, '_cmd_skill_resolution', None)
    assert _mp._resolve_profile_domain_skills('implementation', 'java') == []


def test_resolve_profile_domain_skills_merges_defaults_dict_and_optionals_list(monkeypatch):
    def fake(ns):
        assert ns.profile == 'security'
        assert ns.domain == 'java'
        return {
            'status': 'success',
            'defaults': {'pm-dev-java:java-security': {}},
            'optionals': ['pm-dev-java:java-core'],
        }

    _install_fake_skill_resolution(monkeypatch, fake)
    result = _mp._resolve_profile_domain_skills('security', 'java')
    assert result == ['pm-dev-java:java-security', 'pm-dev-java:java-core']


def test_resolve_profile_domain_skills_merges_defaults_list_and_optionals_dict(monkeypatch):
    def fake(ns):
        return {
            'status': 'success',
            'defaults': ['pm-dev-python:python-core'],
            'optionals': {'pm-dev-python:pytest-testing': {}},
        }

    _install_fake_skill_resolution(monkeypatch, fake)
    result = _mp._resolve_profile_domain_skills('quality', 'python')
    assert result == ['pm-dev-python:python-core', 'pm-dev-python:pytest-testing']


def test_resolve_profile_domain_skills_non_success_returns_empty(monkeypatch):
    _install_fake_skill_resolution(monkeypatch, lambda ns: {'status': 'error'})
    assert _mp._resolve_profile_domain_skills('implementation', 'java') == []


def test_resolve_profile_domain_skills_non_dict_result_returns_empty(monkeypatch):
    _install_fake_skill_resolution(monkeypatch, lambda ns: ['not', 'a', 'dict'])
    assert _mp._resolve_profile_domain_skills('implementation', 'java') == []


def test_resolve_profile_domain_skills_exception_returns_empty(monkeypatch):
    def boom(ns):
        raise RuntimeError('resolution blew up')

    _install_fake_skill_resolution(monkeypatch, boom)
    assert _mp._resolve_profile_domain_skills('implementation', 'java') == []


# =============================================================================
# _flatten — direct DAG-walk behavior
# =============================================================================


def test_flatten_immediate_cycle_when_already_visiting(tmp_path):
    # persona_key already in `visiting` => cycle detected at entry.
    err = _mp._flatten(
        tmp_path,
        'plan-marshall:persona-a',
        [],
        [],
        set(),
        {'plan-marshall:persona-a'},
        include_self_composition=False,
    )
    assert err == 'composition_cycle'


# =============================================================================
# cmd_resolve — synthetic DAG (resolve_bundles_root monkeypatched)
# =============================================================================


@pytest.fixture
def synthetic_root(tmp_path, monkeypatch):
    """Point ``cmd_resolve`` at a synthetic bundle tree under tmp_path."""
    monkeypatch.setattr(_mp, 'resolve_bundles_root', lambda _script: tmp_path)
    return tmp_path


def test_cmd_resolve_persona_not_found(synthetic_root):
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-missing'))
    assert result == {
        'status': 'error',
        'error': 'persona_not_found',
        'persona_key': 'plan-marshall:persona-missing',
    }


def test_cmd_resolve_not_a_persona(synthetic_root):
    _write_skill(synthetic_root, 'plan-marshall:ref-thing', implements='ref')
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:ref-thing'))
    assert result['status'] == 'error'
    assert result['error'] == 'not_a_persona'
    assert result['persona_key'] == 'plan-marshall:ref-thing'


def test_cmd_resolve_simple_persona_emits_base_and_ref_edge(synthetic_root):
    # A ref composition edge is merged verbatim (not recursed); with no domains
    # the profile×domain loop contributes nothing.
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-x',
        profiles=['implementation'],
        composes=['plan-marshall:ref-code-quality'],
    )
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-x'))
    assert result['status'] == 'success'
    assert result['persona_key'] == 'plan-marshall:persona-x'
    assert result['skills'] == [BASE_PERSONA, 'plan-marshall:ref-code-quality']


def test_cmd_resolve_base_listed_first_and_exactly_once(synthetic_root):
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-x',
        composes=['plan-marshall:ref-a', 'plan-marshall:ref-b'],
    )
    skills = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-x'))['skills']
    assert skills[0] == BASE_PERSONA
    assert skills.count(BASE_PERSONA) == 1


def test_cmd_resolve_composed_personas_flattened_and_deduped(synthetic_root):
    # Reviewer composes two work personas; both share a ref edge that must
    # appear exactly once; each composed persona's identity skill is merged.
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-a',
        composes=['plan-marshall:ref-shared'],
    )
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-b',
        composes=['plan-marshall:ref-shared'],
    )
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-reviewer',
        composes=['plan-marshall:persona-a', 'plan-marshall:persona-b'],
    )
    skills = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-reviewer'))['skills']
    assert skills == [
        BASE_PERSONA,
        'plan-marshall:ref-shared',
        'plan-marshall:persona-a',
        'plan-marshall:persona-b',
    ]
    # The top-level persona is the dispatch target, never merged as a lens.
    assert 'plan-marshall:persona-reviewer' not in skills


def test_cmd_resolve_composition_cycle(synthetic_root):
    _write_skill(synthetic_root, 'plan-marshall:persona-a', composes=['plan-marshall:persona-b'])
    _write_skill(synthetic_root, 'plan-marshall:persona-b', composes=['plan-marshall:persona-a'])
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-a'))
    assert result['status'] == 'error'
    assert result['error'] == 'composition_cycle'
    assert result['persona_key'] == 'plan-marshall:persona-a'


def test_cmd_resolve_composed_persona_not_found(synthetic_root):
    _write_skill(
        synthetic_root,
        'plan-marshall:persona-a',
        composes=['plan-marshall:persona-ghost'],
    )
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-a'))
    assert result['status'] == 'error'
    assert result['error'] == 'composed_persona_not_found'


def test_cmd_resolve_merges_profile_domain_skills(synthetic_root, monkeypatch):
    _write_skill(synthetic_root, 'plan-marshall:persona-x', profiles=['security'])

    def fake(ns):
        return {'status': 'success', 'defaults': {'pm-dev-java:java-security': {}}, 'optionals': []}

    _install_fake_skill_resolution(monkeypatch, fake)
    skills = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-x', domains='java,python'))['skills']
    assert BASE_PERSONA in skills
    assert 'pm-dev-java:java-security' in skills
    # Domain skill deduped across the two domains.
    assert skills.count('pm-dev-java:java-security') == 1


def test_cmd_resolve_bundles_root_unresolved(synthetic_root, monkeypatch):
    def boom(_script):
        raise RuntimeError('no bundles root above script')

    monkeypatch.setattr(_mp, 'resolve_bundles_root', boom)
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-x'))
    assert result['status'] == 'error'
    assert result['error'] == 'bundles_root_unresolved'
    assert 'no bundles root' in result['detail']


# =============================================================================
# cmd_resolve / main — real shipped personas (integration)
# =============================================================================


def test_resolve_real_persona_implementer_exact_skills():
    # persona-implementer: composes ref-code-quality, profiles [implementation,
    # quality]; with no domains the resolved set is base + the ref edge only.
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-implementer'))
    assert result['status'] == 'success'
    assert result['skills'] == [BASE_PERSONA, 'plan-marshall:ref-code-quality']


def test_resolve_real_persona_module_tester_is_base_only():
    # persona-module-tester: profile [module_testing], no composes; with no
    # domains nothing beyond the base is merged.
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-module-tester'))
    assert result['status'] == 'success'
    assert result['skills'] == [BASE_PERSONA]


def test_resolve_real_persona_code_reviewer_flattens_lenses():
    # persona-code-reviewer composes five work personas as lenses; each composed
    # persona's identity skill is merged, plus implementer's ref-code-quality.
    result = _mp.cmd_resolve(_resolve_ns('plan-marshall:persona-code-reviewer'))
    assert result['status'] == 'success'
    skills = result['skills']
    assert skills[0] == BASE_PERSONA
    expected_lenses = {
        'plan-marshall:ref-code-quality',
        'plan-marshall:persona-implementer',
        'plan-marshall:persona-module-tester',
        'plan-marshall:persona-integration-tester',
        'plan-marshall:persona-documenter',
        'plan-marshall:persona-security-expert',
    }
    assert expected_lenses.issubset(set(skills))
    # The reviewer itself is the dispatch target, not a merged lens.
    assert 'plan-marshall:persona-code-reviewer' not in skills
    # No duplicates anywhere in the flattened list.
    assert len(skills) == len(set(skills))


# =============================================================================
# main — in-process entry point (covers print + return-code branches)
# =============================================================================


def test_main_resolve_success_returns_zero_and_prints_toon(capsys):
    rc = _mp.main(['resolve', '--persona-key', 'plan-marshall:persona-implementer'])
    assert rc == 0
    out = capsys.readouterr().out
    assert 'status: success' in out
    assert 'plan-marshall:ref-code-quality' in out


def test_main_resolve_error_returns_one(capsys):
    rc = _mp.main(['resolve', '--persona-key', 'plan-marshall:persona-does-not-exist'])
    assert rc == 1
    assert 'persona_not_found' in capsys.readouterr().out


def test_main_missing_subcommand_exits_two():
    with pytest.raises(SystemExit) as exc:
        _mp.main([])
    assert exc.value.code == 2


def test_main_resolve_missing_persona_key_exits_two():
    with pytest.raises(SystemExit) as exc:
        _mp.main(['resolve'])
    assert exc.value.code == 2


def test_build_parser_rejects_abbreviated_flags():
    # allow_abbrev=False => '--persona' must not be accepted as '--persona-key'.
    parser = _mp.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['resolve', '--persona', 'plan-marshall:persona-x'])


# =============================================================================
# CLI plumbing (subprocess) — exit-code smoke checks
# =============================================================================


def test_cli_resolve_real_persona_exit_zero():
    from conftest import run_script

    result = run_script(SCRIPT_PATH, 'resolve', '--persona-key', 'plan-marshall:persona-implementer')
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'success'


def test_cli_resolve_unknown_persona_exit_one():
    from conftest import run_script

    result = run_script(SCRIPT_PATH, 'resolve', '--persona-key', 'plan-marshall:persona-nope')
    assert result.returncode == 1


def test_cli_missing_subcommand_exit_two():
    from conftest import run_script

    result = run_script(SCRIPT_PATH)
    assert result.returncode == 2
