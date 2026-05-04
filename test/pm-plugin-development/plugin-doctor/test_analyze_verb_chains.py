#!/usr/bin/env python3
"""Tests for the AST verb-chain scanner used by the
``prose-verb-chain-consistency`` rule.

The scanner statically analyses ``python3 .plan/execute-script.py
{bundle}:{skill}:{script} {verb} [{sub_verb}...]`` invocations in
``SKILL.md`` and ``standards/*.md``, resolves each referenced script,
AST-walks its argparse subparser registrations, and reports invocations
whose verb chain does not line up with the script's registered
subparsers. The driving lesson (2026-04-18-16) described the drift
class: prose claiming a ``request clarify`` sub-verb when only
``request read`` / ``request mark-clarified`` were registered.

Test layers:
  * Markdown parsing (``extract_invocations``): fence detection, ignore
    marker, non-bash fences, backslash continuations.
  * AST walker (``build_subparser_tree``): flat subparsers, nested
    subparsers (>=3 levels).
  * Chain matching (``match_chain``): happy path, unknown top-level,
    unknown nested.
  * End-to-end (``analyze_verb_chains``): scoped to ``SKILL.md`` +
    ``standards/*.md``, ignore marker, nested validation, scope
    exclusion of ``references/`` and ``templates/``.

Follows the ``_load_module`` convention from ``test_argparse_safety``
so the module under test can be imported directly (Tier 2) without
adding the plugin-doctor scripts directory to ``sys.path`` at
test-session scope.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Path to the plugin-doctor scripts directory (same pattern as
# test_argparse_safety.py).
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_avc = _load_module('_analyze_verb_chains', '_analyze_verb_chains.py')

analyze_verb_chains = _avc.analyze_verb_chains
extract_invocations = _avc.extract_invocations
build_subparser_tree = _avc.build_subparser_tree
match_chain = _avc.match_chain
RULE_ID = _avc.RULE_ID


# =============================================================================
# Fixture helpers — build a synthetic marketplace tree under tmp_path
# =============================================================================


def _make_marketplace(tmp_path: Path) -> Path:
    """Create a minimal ``marketplace/bundles/`` skeleton.

    Returns the bundles root path. Individual tests then add bundles,
    skills, and scripts as needed. The layout mirrors the real repo so
    ``_find_marketplace_root`` can locate the marketplace root by
    walking up from any skill directory under ``bundles/``.
    """
    bundles = tmp_path / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True)
    return bundles


def _make_skill(bundles_root: Path, bundle: str, skill: str) -> Path:
    """Create a skill directory with an empty ``SKILL.md`` placeholder."""
    skill_dir = bundles_root / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True)
    # Callers replace this body via Path.write_text().
    (skill_dir / 'SKILL.md').write_text('', encoding='utf-8')
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir()
    return skill_dir


def _write_script(skill_dir: Path, script_name: str, body: str) -> Path:
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(exist_ok=True)
    path = scripts_dir / f'{script_name}.py'
    path.write_text(body, encoding='utf-8')
    return path


def _flat_subparsers_script(verbs: list[str]) -> str:
    """Produce an argparse script source with a single level of subparsers."""
    lines = [
        'import argparse',
        'parser = argparse.ArgumentParser(allow_abbrev=False)',
        'subparsers = parser.add_subparsers()',
    ]
    for verb in verbs:
        safe_var = verb.replace('-', '_')
        lines.append(f'p_{safe_var} = subparsers.add_parser({verb!r}, allow_abbrev=False)')
    return '\n'.join(lines) + '\n'


def _request_clarify_script() -> str:
    """Replicates the driving lesson's script layout.

    Top-level ``request`` verb with nested ``read`` and ``mark-clarified``
    subparsers — no ``clarify`` child. Additionally registers a
    flat ``refresh`` verb at the top level so tests can also exercise a
    valid happy-path chain.
    """
    return (
        'import argparse\n'
        'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subparsers = parser.add_subparsers()\n'
        "p_request = subparsers.add_parser('request', allow_abbrev=False)\n"
        'request_subs = p_request.add_subparsers()\n'
        "p_request_read = request_subs.add_parser('read', allow_abbrev=False)\n"
        'p_request_mark = request_subs.add_parser('
        "'mark-clarified', allow_abbrev=False)\n"
        "p_refresh = subparsers.add_parser('refresh', allow_abbrev=False)\n"
    )


def _deep_subparsers_script() -> str:
    """Produce a script with three levels of nested subparsers.

    ``alpha`` > ``beta`` > ``gamma`` is the only full path; other
    verbs at each level exist as leaf nodes.
    """
    return (
        'import argparse\n'
        'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subparsers = parser.add_subparsers()\n'
        "p_alpha = subparsers.add_parser('alpha', allow_abbrev=False)\n"
        "p_leaf = subparsers.add_parser('leaf', allow_abbrev=False)\n"
        'alpha_subs = p_alpha.add_subparsers()\n'
        "p_beta = alpha_subs.add_parser('beta', allow_abbrev=False)\n"
        "p_alpha_sibling = alpha_subs.add_parser('sibling', allow_abbrev=False)\n"
        'beta_subs = p_beta.add_subparsers()\n'
        "p_gamma = beta_subs.add_parser('gamma', allow_abbrev=False)\n"
    )


def _bash_fence(body: str) -> str:
    """Wrap ``body`` in a fenced bash block."""
    return '```bash\n' + body.rstrip('\n') + '\n```\n'


# =============================================================================
# build_subparser_tree — unit tests
# =============================================================================


def test_build_subparser_tree_flat(tmp_path):
    """A flat verbs list yields a dict of empty-dict leaves."""
    # Arrange
    script = tmp_path / 'flat.py'
    script.write_text(_flat_subparsers_script(['add', 'remove', 'get']))

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {'add': {}, 'remove': {}, 'get': {}}


def test_build_subparser_tree_nested_three_levels(tmp_path):
    """Three-level nesting is enumerated in full."""
    # Arrange
    script = tmp_path / 'deep.py'
    script.write_text(_deep_subparsers_script())

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {
        'alpha': {
            'beta': {
                'gamma': {},
            },
            'sibling': {},
        },
        'leaf': {},
    }


def test_build_subparser_tree_registers_bare_add_parser_calls(tmp_path):
    """Bare ``subparsers.add_parser('verb', ...)`` calls must register a verb.

    Regression for lesson 2026-05-02-10-001: the analyzer historically
    only walked ``ast.Assign`` statements, so a bare-Expr ``add_parser``
    call (whose return value is discarded) was invisible to the verb-chain
    scanner. Mixed-form scripts must register every verb regardless of
    whether the call's result was bound to a variable.

    Fixture exercises both forms — assigned (``a``) and bare (``b``) —
    and asserts both verbs appear in the resulting tree.
    """
    # Arrange
    script = tmp_path / 'mixed.py'
    script.write_text(
        'import argparse\n'
        'parser = argparse.ArgumentParser(allow_abbrev=False)\n'
        'subparsers = parser.add_subparsers()\n'
        # Assigned form — historical happy path.
        "p_a = subparsers.add_parser('a', allow_abbrev=False)\n"
        # Bare form — driving lesson case. Result is discarded; the call
        # must still register verb 'b' under the owning parser.
        "subparsers.add_parser('b', allow_abbrev=False)\n",
    )

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {'a': {}, 'b': {}}


def test_build_subparser_tree_no_subparsers(tmp_path):
    """A script with only a bare ArgumentParser yields an empty tree."""
    # Arrange
    script = tmp_path / 'bare.py'
    script.write_text(
        "import argparse\nparser = argparse.ArgumentParser(allow_abbrev=False)\nparser.add_argument('--flag')\n",
    )

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {}


def test_build_subparser_tree_real_architecture_script_includes_bare_verbs():
    """End-to-end: real ``architecture.py`` exposes its bare-form verbs.

    ``marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/
    architecture.py`` registers ``derived`` and ``info`` via the bare
    ``subparsers.add_parser('verb', ...)`` shape (no assignment target).
    Per lesson 2026-05-02-10-001, both verbs must appear in the tree
    returned by ``build_subparser_tree`` — historically they were
    silently dropped.

    This test also acts as a guard against future refactors of
    ``architecture.py`` that might switch to the assigned form for
    these specific verbs and accidentally make the regression test
    above pass for the wrong reason.
    """
    # Arrange — locate the real script via the project layout. The test
    # file lives at test/pm-plugin-development/plugin-doctor/, so four
    # ``parent`` hops reach the project root (mirroring ``PROJECT_ROOT``
    # at module top).
    script_path = (
        PROJECT_ROOT
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'manage-architecture'
        / 'scripts'
        / 'architecture.py'
    )
    assert script_path.is_file(), f'Expected real architecture.py at {script_path}; project layout may have changed.'

    # Act
    tree = build_subparser_tree(script_path)

    # Assert — both bare-form verbs are registered as top-level keys.
    assert 'derived' in tree, (
        f'Bare \'subparsers.add_parser("derived", ...)\' was not registered. Top-level verbs found: {sorted(tree)}'
    )
    assert 'info' in tree, (
        f'Bare \'subparsers.add_parser("info", ...)\' was not registered. Top-level verbs found: {sorted(tree)}'
    )


def test_build_subparser_tree_syntax_error_returns_empty(tmp_path):
    """Unparseable source must not raise — empty tree is the contract."""
    # Arrange
    script = tmp_path / 'broken.py'
    script.write_text('def oops(\n')

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {}


def test_build_subparser_tree_missing_file_returns_empty(tmp_path):
    """Reading a non-existent file is tolerated and returns an empty tree."""
    # Arrange
    script = tmp_path / 'does_not_exist.py'

    # Act
    tree = build_subparser_tree(script)

    # Assert
    assert tree == {}


# =============================================================================
# match_chain — unit tests
# =============================================================================


def test_match_chain_happy_path():
    """A chain whose every segment is a registered verb matches fully."""
    # Arrange
    tree = {'request': {'read': {}, 'mark-clarified': {}}}

    # Act
    result = match_chain(tree, ['request', 'read'])

    # Assert
    assert result.matched is True
    assert result.matched_depth == 2
    assert result.first_unknown_segment is None


def test_match_chain_empty_chain_matches():
    """Empty chain is the trivial match regardless of tree contents."""
    # Arrange
    tree = {'add': {}}

    # Act
    result = match_chain(tree, [])

    # Assert
    assert result.matched is True
    assert result.matched_depth == 0
    assert result.first_unknown_segment is None


def test_match_chain_unknown_top_level():
    """First unknown segment is the top-level verb itself."""
    # Arrange
    tree = {'read': {}, 'write': {}}

    # Act
    result = match_chain(tree, ['bogusverb'])

    # Assert
    assert result.matched is False
    assert result.matched_depth == 0
    assert result.first_unknown_segment == 'bogusverb'


def test_match_chain_unknown_nested():
    """Driving-lesson case: ``request clarify`` when only read/mark-clarified exist."""
    # Arrange
    tree = {'request': {'read': {}, 'mark-clarified': {}}}

    # Act
    result = match_chain(tree, ['request', 'clarify'])

    # Assert
    assert result.matched is False
    assert result.matched_depth == 1
    assert result.first_unknown_segment == 'clarify'


def test_match_chain_too_deep():
    """Chain longer than the tree reports the first out-of-tree segment."""
    # Arrange
    tree = {'add': {}}

    # Act
    result = match_chain(tree, ['add', 'extra'])

    # Assert
    assert result.matched is False
    assert result.matched_depth == 1
    assert result.first_unknown_segment == 'extra'


def test_match_chain_empty_tree_with_chain():
    """Empty tree cannot match any non-empty chain."""
    # Arrange
    tree: dict = {}

    # Act
    result = match_chain(tree, ['something'])

    # Assert
    assert result.matched is False
    assert result.matched_depth == 0
    assert result.first_unknown_segment == 'something'


# =============================================================================
# extract_invocations — markdown parsing tests
# =============================================================================


def test_extract_invocations_basic(tmp_path):
    """A single invocation in a bash fence is extracted with verb chain."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(
        'Intro paragraph.\n\n'
        + _bash_fence(
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-plan-documents:manage-plan-documents '
            'request read --plan-id foo'
        )
    )

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert len(invocations) == 1
    inv = invocations[0]
    assert inv.bundle == 'plan-marshall'
    assert inv.skill == 'manage-plan-documents'
    assert inv.script == 'manage-plan-documents'
    assert inv.verb_chain == ('request', 'read')
    assert inv.script_notation == ('plan-marshall:manage-plan-documents:manage-plan-documents')


def test_extract_invocations_ignore_marker_suppresses(tmp_path):
    """The doctor-ignore marker on the preceding line suppresses the fence."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(
        'Doc text.\n'
        '<!-- doctor-ignore: verb-check -->\n' + _bash_fence('python3 .plan/execute-script.py a:b:c clarify --flag')
    )

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert invocations == []


def test_extract_invocations_ignore_marker_tolerates_blank_line(tmp_path):
    """Whitespace-only lines between marker and fence are permitted."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(
        '<!-- doctor-ignore: verb-check -->\n   \n\n' + _bash_fence('python3 .plan/execute-script.py a:b:c verb')
    )

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert invocations == []


def test_extract_invocations_skips_non_bash_fence(tmp_path):
    """Python-tagged fences are not scanned."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text('```python\npython3 .plan/execute-script.py a:b:c verb\n```\n')

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert invocations == []


def test_extract_invocations_skips_non_invocation_bash(tmp_path):
    """Bash fences without the executor invocation are safely ignored."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(_bash_fence('ls -la\necho hello\n'))

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert invocations == []


def test_extract_invocations_multiline_continuation(tmp_path):
    """Backslash continuations join into a single logical invocation."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(_bash_fence('python3 .plan/execute-script.py a:b:c verb sub-verb \\\n  --plan-id foo \\\n  --flag'))

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].verb_chain == ('verb', 'sub-verb')


def test_extract_invocations_stops_chain_at_flag(tmp_path):
    """A flag terminates verb-chain accumulation."""
    # Arrange
    md = tmp_path / 'SKILL.md'
    md.write_text(_bash_fence('python3 .plan/execute-script.py a:b:c read --plan-id foo'))

    # Act
    invocations = extract_invocations(md)

    # Assert
    assert len(invocations) == 1
    assert invocations[0].verb_chain == ('read',)


def test_extract_invocations_unreadable_file_returns_empty(tmp_path):
    """A missing markdown file is tolerated and yields no invocations."""
    # Arrange
    missing = tmp_path / 'nope.md'

    # Act
    invocations = extract_invocations(missing)

    # Assert
    assert invocations == []


# =============================================================================
# analyze_verb_chains — end-to-end tests
# =============================================================================


def test_analyze_happy_path_no_findings(tmp_path):
    """Valid verb chain against a registered subparser tree yields nothing."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-plan-documents')
    _write_script(target_skill, 'manage-plan-documents', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        '# Phase 3\n\n'
        + _bash_fence(
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-plan-documents:manage-plan-documents '
            'request read --plan-id foo'
        )
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


def test_analyze_unknown_top_level_verb(tmp_path):
    """An unregistered top-level verb is reported."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-status')
    _write_script(
        target_skill,
        'manage-status',
        _flat_subparsers_script(['get', 'set']),
    )

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence('python3 .plan/execute-script.py plan-marshall:manage-status:manage-status bogusverb --flag')
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['script_notation'] == ('plan-marshall:manage-status:manage-status')
    assert finding['verb_chain'] == ['bogusverb']
    assert finding['first_unknown_segment'] == 'bogusverb'
    assert finding['file'] == str(caller_skill / 'SKILL.md')


def test_analyze_unknown_nested_verb_driving_lesson(tmp_path):
    """Driving-lesson case: ``request clarify`` drift is detected.

    ``manage-plan-documents`` registers ``request read`` and
    ``request mark-clarified``; prose referencing ``request clarify``
    must be flagged with ``first_unknown_segment == 'clarify'``.
    """
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-plan-documents')
    _write_script(target_skill, 'manage-plan-documents', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        '## Step: Clarify\n\n'
        + _bash_fence(
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-plan-documents:manage-plan-documents '
            'request clarify --plan-id foo'
        )
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['rule_id'] == RULE_ID
    assert finding['verb_chain'] == ['request', 'clarify']
    assert finding['first_unknown_segment'] == 'clarify'


def test_analyze_honors_ignore_marker(tmp_path):
    """A drifted chain behind an ignore marker is suppressed."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-plan-documents')
    _write_script(target_skill, 'manage-plan-documents', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        '<!-- doctor-ignore: verb-check -->\n'
        + _bash_fence(
            'python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request clarify'
        )
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


def test_analyze_skips_non_bash_fence(tmp_path):
    """Non-bash fences are not scanned, even with a valid-looking invocation."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-plan-documents')
    _write_script(target_skill, 'manage-plan-documents', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        '```python\n'
        'python3 .plan/execute-script.py '
        'plan-marshall:manage-plan-documents:manage-plan-documents '
        'request clarify\n'
        '```\n'
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


def test_analyze_multiline_invocation_notation_on_head_line(tmp_path):
    """Backslash continuations after the notation are joined before chain parsing.

    This mirrors the supported authoring pattern (notation on the head
    line; flags continue on subsequent lines) and proves the trailing
    verb tokens on continuation lines are consumed into the chain.
    """
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'plan-marshall', 'manage-plan-documents')
    _write_script(target_skill, 'manage-plan-documents', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'plan-marshall', 'phase-3-outline')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence(
            'python3 .plan/execute-script.py '
            'plan-marshall:manage-plan-documents:manage-plan-documents \\\n'
            '  request clarify \\\n'
            '  --plan-id foo'
        )
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['verb_chain'] == ['request', 'clarify']
    assert finding['first_unknown_segment'] == 'clarify'


def test_analyze_nested_three_levels_happy_path(tmp_path):
    """Three-level chain ``alpha beta gamma`` matches a deep subparser tree."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'pm', 'deep-skill')
    _write_script(target_skill, 'deep-script', _deep_subparsers_script())

    caller_skill = _make_skill(bundles, 'pm', 'caller-skill')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence('python3 .plan/execute-script.py pm:deep-skill:deep-script alpha beta gamma --flag')
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


def test_analyze_nested_three_levels_unknown_leaf(tmp_path):
    """Unknown leaf segment in a 3-level chain is reported at the leaf."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'pm', 'deep-skill')
    _write_script(target_skill, 'deep-script', _deep_subparsers_script())

    caller_skill = _make_skill(bundles, 'pm', 'caller-skill')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence('python3 .plan/execute-script.py pm:deep-skill:deep-script alpha beta stale')
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    assert finding['verb_chain'] == ['alpha', 'beta', 'stale']
    assert finding['first_unknown_segment'] == 'stale'


def test_analyze_scans_skill_md_and_standards_only(tmp_path):
    """Only SKILL.md and standards/*.md are scanned; other dirs are ignored.

    Sets up four markdown files under the caller skill:
      * SKILL.md      — in scope, drifted chain → must be flagged
      * standards/s1.md — in scope, drifted chain → must be flagged
      * references/r.md — out of scope, drifted chain → must be ignored
      * templates/t.md — out of scope, drifted chain → must be ignored
      * standards/nested/deep.md — out of scope (only top-level
        standards/*.md, no recursion) → must be ignored
    """
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'pm', 'target-skill')
    _write_script(target_skill, 'target-script', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'pm', 'caller-skill')

    drifted_body = _bash_fence('python3 .plan/execute-script.py pm:target-skill:target-script request clarify')

    (caller_skill / 'SKILL.md').write_text(drifted_body)

    standards_dir = caller_skill / 'standards'
    standards_dir.mkdir()
    (standards_dir / 's1.md').write_text(drifted_body)

    nested_dir = standards_dir / 'nested'
    nested_dir.mkdir()
    (nested_dir / 'deep.md').write_text(drifted_body)

    references_dir = caller_skill / 'references'
    references_dir.mkdir()
    (references_dir / 'r.md').write_text(drifted_body)

    templates_dir = caller_skill / 'templates'
    templates_dir.mkdir()
    (templates_dir / 't.md').write_text(drifted_body)

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    flagged_files = {Path(f['file']).relative_to(caller_skill).as_posix() for f in findings}
    assert flagged_files == {'SKILL.md', 'standards/s1.md'}, (
        f'Expected only SKILL.md + standards/s1.md to be scanned, got {flagged_files}'
    )


def test_analyze_skips_unresolvable_notation(tmp_path):
    """Invocations pointing to a non-existent script are silently skipped."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    caller_skill = _make_skill(bundles, 'pm', 'caller-skill')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence('python3 .plan/execute-script.py ghost-bundle:ghost-skill:ghost-script request clarify')
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


def test_analyze_missing_marketplace_root_returns_empty(tmp_path):
    """A skill directory outside a marketplace/bundles/ ancestor yields []."""
    # Arrange
    orphan_skill = tmp_path / 'orphan'
    orphan_skill.mkdir()
    (orphan_skill / 'SKILL.md').write_text(_bash_fence('python3 .plan/execute-script.py a:b:c verb'))

    # Act
    findings = analyze_verb_chains(orphan_skill)

    # Assert
    assert findings == []


def test_analyze_no_markdown_targets(tmp_path):
    """A skill directory with no SKILL.md and no standards dir yields []."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    caller_skill = bundles / 'pm' / 'skills' / 'empty-skill'
    caller_skill.mkdir(parents=True)

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert findings == []


# =============================================================================
# Finding shape — contract enforcement
# =============================================================================


def test_finding_shape_contract(tmp_path):
    """Every finding must expose the documented keys and types."""
    # Arrange
    bundles = _make_marketplace(tmp_path)
    target_skill = _make_skill(bundles, 'pm', 'target-skill')
    _write_script(target_skill, 'target-script', _request_clarify_script())

    caller_skill = _make_skill(bundles, 'pm', 'caller-skill')
    (caller_skill / 'SKILL.md').write_text(
        _bash_fence('python3 .plan/execute-script.py pm:target-skill:target-script request clarify')
    )

    # Act
    findings = analyze_verb_chains(caller_skill)

    # Assert
    assert len(findings) == 1
    finding = findings[0]
    expected_keys = {
        'rule_id',
        'file',
        'line',
        'script_notation',
        'verb_chain',
        'first_unknown_segment',
    }
    assert set(finding.keys()) == expected_keys
    assert isinstance(finding['rule_id'], str)
    assert isinstance(finding['file'], str)
    assert isinstance(finding['line'], int)
    assert finding['line'] >= 1
    assert isinstance(finding['script_notation'], str)
    assert isinstance(finding['verb_chain'], list)
    assert all(isinstance(s, str) for s in finding['verb_chain'])
    assert isinstance(finding['first_unknown_segment'], str)


# =============================================================================
# Public API surface — ensures imports expected by the rule are present
# =============================================================================


def test_module_exposes_documented_api():
    """The module publishes the four symbols the scanner rule relies on."""
    # Arrange / Act — names resolved at import time above.
    # Assert
    assert callable(analyze_verb_chains)
    assert callable(extract_invocations)
    assert callable(build_subparser_tree)
    assert callable(match_chain)
    assert RULE_ID == 'prose-verb-chain-consistency'


# Sanity check: the fixture helpers themselves parse cleanly under AST
# so any silent breakage of the fixture generators is caught early.
@pytest.mark.parametrize(
    'source',
    [
        _flat_subparsers_script(['add', 'remove']),
        _request_clarify_script(),
        _deep_subparsers_script(),
    ],
)
def test_fixture_scripts_are_well_formed(tmp_path, source):
    # Arrange
    path = tmp_path / 'probe.py'
    path.write_text(source)

    # Act
    tree = build_subparser_tree(path)

    # Assert — a non-empty tree proves the fixture registers at least
    # one subparser. Specific shapes are asserted in dedicated tests.
    assert tree != {}
