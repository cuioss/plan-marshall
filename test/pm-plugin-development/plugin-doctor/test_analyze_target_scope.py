# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``targets-scope-invalid`` rule analyzer.

A component may declare the build-time ``targets:`` frontmatter field naming
the build targets it ships to. The multi-target generator rejects an unknown
target name and an empty declaration; this analyzer surfaces both at authoring
time. An absent field means "every target" and is never flagged.

Test layers:
  * Absent / valid declarations → no finding (positive)
  * Unknown target name → one finding, ``reason == targets_unknown``
  * Empty declaration → one finding, ``reason == targets_empty``
  * Every component kind (agent, command, skill) is in scope
  * The registered set is DERIVED from the targets' own registrations
  * A tree without ``marketplace/targets/`` still runs the registry-free check
"""

from pathlib import Path

import pytest

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ats = _load_module('_analyze_target_scope', '_analyze_target_scope.py')

analyze_target_scope = _ats.analyze_target_scope
component_files = _ats.component_files
declared_targets = _ats.declared_targets
registered_target_names = _ats.registered_target_names
RULE_ID = _ats.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake marketplace tree.
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _marketplace(tmp_path: Path, *, targets: tuple[str, ...] = ('claude', 'opencode')) -> Path:
    """Return a bundles root whose sibling targets tree registers ``targets``."""
    root = tmp_path / 'marketplace'
    for name in targets:
        package = name.replace('-', '_')
        _write(
            root / 'targets' / package / '__init__.py',
            f"from marketplace.targets import register_target\n\nregister_target('{name}', object)\n",
        )
    (root / 'bundles').mkdir(parents=True, exist_ok=True)
    return root / 'bundles'


def _component(bundles: Path, rel: str, frontmatter: str = '') -> Path:
    path = bundles / 'demo' / rel
    extra = f'{frontmatter}\n' if frontmatter else ''
    _write(path, f'---\nname: demo\ndescription: d\n{extra}---\n\n# Body\n')
    return path


# ---------------------------------------------------------------------------
# Declaration parsing
# ---------------------------------------------------------------------------


def test_absent_field_is_not_a_declaration():
    """The common case — no field — is never flagged."""
    assert declared_targets('---\nname: a\ndescription: d\n---\n\n# Body\n') is None


def test_inline_and_block_forms_parse_to_the_same_tokens():
    """Both YAML list spellings yield the same token list."""
    inline = declared_targets('---\nname: a\ntargets: [claude, opencode]\n---\n')
    block = declared_targets('---\nname: a\ntargets:\n  - claude\n  - opencode\n---\n')

    assert inline is not None and block is not None
    assert inline[0] == ['claude', 'opencode']
    assert block[0] == ['claude', 'opencode']


def test_declaration_reports_its_file_line_number():
    """The finding anchors on the declaring line, not on line 1."""
    declaration = declared_targets('---\nname: a\ndescription: d\ntargets: [claude]\n---\n')

    assert declaration is not None
    assert declaration[1] == 4


def test_nested_targets_key_is_not_a_declaration():
    """Only a TOP-LEVEL key counts; an indented one is a different field."""
    assert declared_targets('---\nname: a\nmetadata:\n  targets: nonsense\n---\n') is None


def test_comments_do_not_turn_a_declaration_into_an_empty_one():
    """A commented list declares its targets; reporting it empty names a file that does not exist."""
    block = declared_targets('---\nname: a\ntargets:\n  # why\n  - claude  # here\n---\n')
    inline = declared_targets('---\nname: a\ntargets: [claude]  # here\n---\n')

    assert block is not None and block[0] == ['claude']
    assert inline is not None and inline[0] == ['claude']


def test_a_byte_order_mark_does_not_hide_the_declaration():
    """A BOM'd file must not read as having no frontmatter at all."""
    declaration = declared_targets('﻿---\nname: a\ntargets: [cluade]\n---\n')

    assert declaration is not None
    assert declaration[0] == ['cluade']


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('["#claude"]', ['#claude'], id='quoted-leading-hash'),
        pytest.param('[cla#ude]', ['cla#ude'], id='hash-inside-a-name'),
        pytest.param('[claude]#note', ['[claude]#note'], id='hash-with-no-preceding-space'),
    ],
)
def test_a_hash_that_opens_no_token_is_not_a_comment(value, expected):
    """The comment stripper must not eat a ``#`` that is part of a value.

    The analyzer's `_strip_comment` docstring claims it mirrors the
    generator's parser; this is what holds the two to the same answer.
    """
    declaration = declared_targets(f'---\nname: a\ntargets: {value}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


@pytest.mark.parametrize(
    ('block', 'expected'),
    [
        pytest.param('targets: [claude,\n  opencode]', ['claude', 'opencode'], id='across-lines'),
        pytest.param(
            'targets: [claude,  # and\n  opencode]', ['claude', 'opencode'], id='with-comment'
        ),
        pytest.param('targets: [\n  claude\n  ]', ['claude'], id='opened-on-its-own-line'),
    ],
)
def test_a_flow_sequence_spanning_lines_is_read_whole(block, expected):
    """Reading only the first physical line would report a target nobody wrote."""
    declaration = declared_targets(f'---\nname: a\n{block}\n---\n')

    assert declaration is not None
    assert declaration[0] == expected


# ---------------------------------------------------------------------------
# The derived registry
# ---------------------------------------------------------------------------


def test_registered_names_are_derived_from_the_targets_own_registrations(tmp_path):
    """Adding a target's registration widens the set with no edit to the rule."""
    bundles = _marketplace(tmp_path, targets=('claude', 'opencode', 'newcomer'))

    assert registered_target_names(bundles) == frozenset({'claude', 'opencode', 'newcomer'})


def test_registry_is_unavailable_without_a_targets_tree(tmp_path):
    """A consumer install carries no targets tree, so names cannot be checked."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True)

    assert registered_target_names(bundles) is None


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


def test_valid_declaration_produces_no_finding(tmp_path):
    """A registry-valid declaration is accepted."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/ok.md', 'targets: [claude]')

    assert analyze_target_scope(bundles) == []


def test_component_without_the_field_produces_no_finding(tmp_path):
    """The default — ship everywhere — is not a defect."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/plain.md')

    assert analyze_target_scope(bundles) == []


def test_unknown_target_name_is_flagged(tmp_path):
    """A typo is reported with the offending value and the registered set."""
    bundles = _marketplace(tmp_path)
    path = _component(bundles, 'commands/typo.md', 'targets: [cluade]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['file'] == str(path)
    assert finding['severity'] == 'error'
    assert finding['details']['reason'] == 'targets_unknown'
    assert finding['details']['unknown_targets'] == ['cluade']
    assert finding['details']['registered_targets'] == ['claude', 'opencode']
    assert 'cluade' in finding['description']


def test_one_valid_name_does_not_excuse_an_unknown_one(tmp_path):
    """A partially-valid list is still rejected."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/mixed.md', 'targets: [claude, nope]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['unknown_targets'] == ['nope']


def test_empty_declaration_is_flagged(tmp_path):
    """A component that ships nowhere is an authoring error."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'commands/empty.md', 'targets: []')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_empty'


def test_empty_declaration_is_flagged_without_a_targets_tree(tmp_path):
    """The registry-free check still runs where names cannot be validated."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    _component(bundles, 'commands/empty.md', 'targets: []')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 1
    assert findings[0]['details']['reason'] == 'targets_empty'


def test_unknown_name_is_not_flagged_without_a_targets_tree(tmp_path):
    """An absent registry is reported by silence, never by a fabricated verdict."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    _component(bundles, 'commands/typo.md', 'targets: [cluade]')

    assert analyze_target_scope(bundles) == []


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------


def test_every_component_kind_is_scanned(tmp_path):
    """Agents, commands, and skill manifests all carry the field."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'agents/a.md')
    _component(bundles, 'commands/c.md')
    _component(bundles, 'skills/s/SKILL.md')

    scanned = {path.relative_to(bundles / 'demo').as_posix() for path in component_files(bundles)}

    assert scanned == {'agents/a.md', 'commands/c.md', 'skills/s/SKILL.md'}


def test_every_component_kind_is_flagged(tmp_path):
    """A defect is reported wherever it lives, not only in commands."""
    bundles = _marketplace(tmp_path)
    _component(bundles, 'agents/a.md', 'targets: [cluade]')
    _component(bundles, 'commands/c.md', 'targets: [cluade]')
    _component(bundles, 'skills/s/SKILL.md', 'targets: [cluade]')

    findings = analyze_target_scope(bundles)

    assert len(findings) == 3
    assert {Path(f['file']).name for f in findings} == {'a.md', 'c.md', 'SKILL.md'}


def test_a_skill_directory_without_a_manifest_is_not_scanned(tmp_path):
    """A skill directory carrying no SKILL.md contributes no component."""
    bundles = _marketplace(tmp_path)
    _write(bundles / 'demo' / 'skills' / 'empty-skill' / 'notes.md', '# notes\n')

    assert component_files(bundles) == []
