"""Tests for the OpenCode body transforms (Skill: rewrite + slash-command rewrite)."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketplace.targets.opencode.body_transforms import (
    SKILL_DIRECTIVE_RE,
    SKILL_REWRITTEN_RE,
    UnmappedIdiomError,
    assert_dispositions_known,
    build_slash_command_re,
    build_user_invocable_lookup,
    load_idiom_registry,
    make_body_transformer,
    rewrite_registered_idioms,
    rewrite_skill_directives,
    rewrite_slash_commands,
)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Transform 1 — Skill: directive rewrite
# ---------------------------------------------------------------------------


def test_rewrite_skill_directives_full_line_match():
    """Full-line directive is rewritten; the regex's trailing ``\\s*$`` consumes
    the line's terminating newline as part of the match."""
    body = 'Skill: foo:bar\n'
    result = rewrite_skill_directives(body)
    assert result == 'Call the `skill` tool with `{ name: "foo-bar" }` before continuing.'


def test_rewrite_skill_directives_full_line_with_extra_spacing():
    body = 'Skill:   plan-marshall:phase-5-execute\n'
    result = rewrite_skill_directives(body)
    assert (
        result
        == 'Call the `skill` tool with `{ name: "plan-marshall-phase-5-execute" }` before continuing.'
    )


def test_rewrite_skill_directives_inline_backtick_left_alone():
    """Inline backtick references must NOT be rewritten — they are prose."""
    body = 'Some text `Skill: foo:bar` more text\n'
    assert rewrite_skill_directives(body) == body


def test_rewrite_skill_directives_mid_line_left_alone():
    """A Skill: token in the middle of a sentence is not a full-line directive."""
    body = 'See the Skill: foo:bar reference for details\n'
    assert rewrite_skill_directives(body) == body


def test_rewrite_skill_directives_idempotent():
    """Running the transform on already-rewritten text is a no-op."""
    body = 'Skill: foo:bar\n'
    once = rewrite_skill_directives(body)
    twice = rewrite_skill_directives(once)
    assert once == twice


def test_rewrite_skill_directives_multiple_directives():
    body = (
        'Skill: alpha:one\n'
        'middle prose\n'
        'Skill: beta:two\n'
    )
    result = rewrite_skill_directives(body)
    assert 'Call the `skill` tool with `{ name: "alpha-one" }` before continuing.' in result
    assert 'Call the `skill` tool with `{ name: "beta-two" }` before continuing.' in result
    assert 'middle prose' in result


def test_rewrite_skill_directives_no_match_returns_unchanged():
    body = '# Heading\n\nSome prose without a directive.\n'
    assert rewrite_skill_directives(body) == body


def test_skill_directive_re_anchored_to_full_line():
    """The compiled regex MUST be anchored — guards against accidental relaxation."""
    pattern = SKILL_DIRECTIVE_RE.pattern
    assert pattern.startswith('^Skill:')
    assert pattern.endswith(r'\s*$')


def test_skill_rewritten_re_matches_canonical_replacement():
    line = 'Call the `skill` tool with `{ name: "foo-bar" }` before continuing.'
    assert SKILL_REWRITTEN_RE.search(line) is not None


# ---------------------------------------------------------------------------
# Transform 2 — Slash-command rewrite
# ---------------------------------------------------------------------------


def _basic_lookup() -> dict[str, str]:
    return {
        'plan-marshall': 'plan-marshall-plan-marshall',
        'sync-plugin-cache': 'plan-marshall-sync-plugin-cache',
    }


def test_rewrite_slash_commands_happy_path():
    body = 'Run /plan-marshall to start.\n'
    result = rewrite_slash_commands(body, _basic_lookup())
    assert result == 'Run /plan-marshall-plan-marshall to start.\n'


def test_rewrite_slash_commands_path_substring_left_alone():
    """A slash inside a filesystem path MUST NOT be rewritten."""
    body = 'See path/to/plan-marshall for details.\n'
    assert rewrite_slash_commands(body, _basic_lookup()) == body


def test_rewrite_slash_commands_with_action_arg():
    """Slash commands followed by `key=value` args are still rewritten."""
    body = 'Try /plan-marshall action=execute now.\n'
    result = rewrite_slash_commands(body, _basic_lookup())
    assert result == 'Try /plan-marshall-plan-marshall action=execute now.\n'


def test_rewrite_slash_commands_at_end_of_line():
    body = 'And finally /sync-plugin-cache\n'
    result = rewrite_slash_commands(body, _basic_lookup())
    assert result == 'And finally /plan-marshall-sync-plugin-cache\n'


def test_rewrite_slash_commands_already_namespaced_passthrough():
    """Already-namespaced names are not in the lookup keys, so they pass through."""
    body = 'Run /plan-marshall-plan-marshall to start.\n'
    result = rewrite_slash_commands(body, _basic_lookup())
    assert result == body


def test_rewrite_slash_commands_unknown_name_passthrough():
    body = 'Run /unknown-thing here.\n'
    result = rewrite_slash_commands(body, _basic_lookup())
    assert result == body


def test_rewrite_slash_commands_empty_lookup_returns_unchanged():
    body = 'Run /plan-marshall to start.\n'
    assert rewrite_slash_commands(body, {}) == body


def test_rewrite_slash_commands_idempotent():
    body = 'Run /plan-marshall to start.\n'
    once = rewrite_slash_commands(body, _basic_lookup())
    twice = rewrite_slash_commands(once, _basic_lookup())
    assert once == twice


def test_build_slash_command_re_empty_returns_none():
    assert build_slash_command_re([]) is None


def test_build_slash_command_re_sorts_longer_first():
    """When one name is a prefix of another, the longer name wins."""
    pattern = build_slash_command_re(['foo', 'foo-bar'])
    assert pattern is not None
    match = pattern.search('Run /foo-bar here\n')
    assert match is not None
    assert match.group('name') == 'foo-bar'


def test_build_slash_command_re_drops_empty_strings():
    pattern = build_slash_command_re(['foo', ''])
    assert pattern is not None
    match = pattern.search('Run /foo here\n')
    assert match is not None
    assert match.group('name') == 'foo'


# ---------------------------------------------------------------------------
# build_user_invocable_lookup
# ---------------------------------------------------------------------------


def _write_skill(marketplace: Path, bundle: str, skill: str, *, user_invocable: bool, description: str = 'desc') -> None:
    fm_lines = [
        '---',
        f'name: {skill}',
        f'description: {description}',
    ]
    if user_invocable:
        fm_lines.append('user-invocable: true')
    fm_lines.append('---')
    body = '\n'.join(fm_lines) + '\nbody\n'
    _write(marketplace / bundle / 'skills' / skill / 'SKILL.md', body)


def test_build_user_invocable_lookup_picks_user_invocable_only(tmp_path: Path):
    marketplace = tmp_path / 'bundles'
    _write_skill(marketplace, 'alpha', 'one', user_invocable=True)
    _write_skill(marketplace, 'alpha', 'two', user_invocable=False)
    _write_skill(marketplace, 'beta', 'three', user_invocable=True)

    lookup = build_user_invocable_lookup(marketplace)

    assert lookup == {
        'one': 'alpha-one',
        'three': 'beta-three',
    }


def test_build_user_invocable_lookup_skips_dot_dirs(tmp_path: Path):
    marketplace = tmp_path / 'bundles'
    _write_skill(marketplace, '.hidden', 'h', user_invocable=True)
    _write_skill(marketplace, 'visible', 'v', user_invocable=True)

    lookup = build_user_invocable_lookup(marketplace)

    assert 'h' not in lookup
    assert lookup.get('v') == 'visible-v'


def test_build_user_invocable_lookup_empty_for_missing_dir(tmp_path: Path):
    missing = tmp_path / 'does-not-exist'
    assert build_user_invocable_lookup(missing) == {}


def test_build_user_invocable_lookup_skips_user_invocable_false_string(tmp_path: Path):
    marketplace = tmp_path / 'bundles'
    skill_dir = marketplace / 'alpha' / 'skills' / 'one'
    body = '---\nname: one\ndescription: desc\nuser-invocable: false\n---\nbody\n'
    _write(skill_dir / 'SKILL.md', body)

    lookup = build_user_invocable_lookup(marketplace)

    assert lookup == {}


# ---------------------------------------------------------------------------
# make_body_transformer (composition)
# ---------------------------------------------------------------------------


def test_make_body_transformer_applies_transform_1():
    transform = make_body_transformer({})
    body = 'Skill: foo:bar\n'
    result = transform(body, 'demo', 'skill')
    assert 'Call the `skill` tool with `{ name: "foo-bar" }`' in result


def test_make_body_transformer_applies_transform_2():
    transform = make_body_transformer({'foo': 'demo-foo'})
    body = 'Run /foo now.\n'
    result = transform(body, 'demo', 'skill')
    assert result == 'Run /demo-foo now.\n'


def test_make_body_transformer_applies_both_in_one_pass():
    body = 'Skill: demo:foo\nThen run /foo to continue.\n'
    transform = make_body_transformer({'foo': 'demo-foo'})
    result = transform(body, 'demo', 'skill')
    assert 'Call the `skill` tool with `{ name: "demo-foo" }`' in result
    assert '/demo-foo' in result


def test_make_body_transformer_idempotent_on_already_transformed():
    body = 'Skill: demo:foo\nUse /foo here.\n'
    transform = make_body_transformer({'foo': 'demo-foo'})
    once = transform(body, 'demo', 'skill')
    twice = transform(once, 'demo', 'skill')
    assert once == twice


def test_make_body_transformer_kind_signature():
    """The transformer must accept (body, bundle, kind) — emitter contract."""
    transform = make_body_transformer({})
    # All three kinds must be accepted; bodies pass through identity when no patterns match
    for kind in ('skill', 'agent', 'command'):
        assert transform('plain text\n', 'demo', kind) == 'plain text\n'


# ---------------------------------------------------------------------------
# Integration — fixture skill body with both transforms
# ---------------------------------------------------------------------------


def test_integration_fixture_skill_body_both_transforms(tmp_path: Path):
    marketplace = tmp_path / 'bundles'
    _write_skill(marketplace, 'demo', 'helper', user_invocable=True)
    _write_skill(marketplace, 'demo', 'runner', user_invocable=True)

    lookup = build_user_invocable_lookup(marketplace)
    transform = make_body_transformer(lookup)

    body = (
        '# Skill body\n'
        '\n'
        'Skill: demo:helper\n'
        '\n'
        'Then invoke /runner action=go here.\n'
        '\n'
        'Inline `/runner` mention in code-fences should be left alone... '
        'but inline-prose `Skill: demo:helper` is also left alone.\n'
        '\n'
        'See path/to/runner for filesystem references.\n'
    )

    result = transform(body, 'demo', 'skill')

    # Transform 1: full-line directive rewritten
    assert 'Call the `skill` tool with `{ name: "demo-helper" }`' in result
    # Transform 2: standalone slash-command rewritten
    assert '/demo-runner action=go' in result
    # NOT transformed: inline backtick mention preserved verbatim
    assert '`Skill: demo:helper`' in result
    # NOT transformed: filesystem path preserved
    assert 'path/to/runner' in result


def test_integration_real_marketplace_lookup_namespacing():
    """The real marketplace lookup namespacing matches {bundle}-{skill} convention."""
    project_root = Path(__file__).resolve().parents[3].parent
    marketplace = project_root / 'marketplace' / 'bundles'
    if not marketplace.is_dir():
        pytest.skip('marketplace/bundles not available in this checkout')

    lookup = build_user_invocable_lookup(marketplace)

    # Every emitted target must have the form {bundle}-{skill}.
    for skill_name, target in lookup.items():
        assert target.endswith(f'-{skill_name}'), f'{target} should end with -{skill_name}'
        # bundle prefix is non-empty
        prefix = target[: -(len(skill_name) + 1)]
        assert prefix, f'lookup target {target} missing bundle prefix'


def test_integration_real_marketplace_pickup_at_least_one():
    """Sanity check: real marketplace has user-invocable skills."""
    project_root = Path(__file__).resolve().parents[3].parent
    marketplace = project_root / 'marketplace' / 'bundles'
    if not marketplace.is_dir():
        pytest.skip('marketplace/bundles not available in this checkout')

    lookup = build_user_invocable_lookup(marketplace)
    assert len(lookup) >= 1, 'expected at least one user-invocable skill in real marketplace'


# ---------------------------------------------------------------------------
# Transform 3 — registered-idiom rewrite (data-driven, fail-closed)
# ---------------------------------------------------------------------------


def _registry(**overrides) -> dict:
    """Build a registry dict for the three registered idioms with optional overrides."""
    base = {
        'AskUserQuestion': {'disposition': 'rewrite_inline_code', 'opencode_tool': 'question'},
        'Task:': {'disposition': 'preserve'},
        'Skill: <entry>': {'disposition': 'source_fix'},
    }
    base.update(overrides)
    return base


def test_rewrite_inline_code_rewrites_backtick_tool_reference():
    """`AskUserQuestion` (backtick-wrapped) rewrites to the OpenCode `question` tool."""
    body = 'Escalate via `AskUserQuestion` when ambiguous.\n'
    result = rewrite_registered_idioms(body, _registry())
    assert '`question`' in result
    assert '`AskUserQuestion`' not in result


def test_rewrite_inline_code_leaves_bare_prose_mention():
    """A bare (non-backtick) prose mention of the concept is left alone."""
    body = 'The AskUserQuestion escalation mechanism is target-neutral.\n'
    result = rewrite_registered_idioms(body, _registry())
    # No backtick reference → no rewrite; the prose concept name stays.
    assert 'AskUserQuestion escalation mechanism' in result


def test_rewrite_inline_code_idempotent():
    """Re-running the rewrite on already-transformed text is a no-op."""
    body = 'Escalate via `AskUserQuestion`.\n'
    once = rewrite_registered_idioms(body, _registry())
    twice = rewrite_registered_idioms(once, _registry())
    assert once == twice


def test_preserve_disposition_leaves_task_references():
    """`Task:` carries the preserve disposition — leaf-constraint prose is untouched."""
    body = 'This is a leaf — no `Task:` dispatch. Every plan-marshall `Task:` invocation...\n'
    result = rewrite_registered_idioms(body, _registry())
    assert result == body
    assert '`Task:`' in result
    assert '`task`' not in result


def test_source_fix_disposition_leaves_skill_entry_placeholder():
    """`Skill: <entry>` carries the source_fix disposition — no emit-time rewrite."""
    body = 'For each entry in skills[]: `Skill: <entry>`\n'
    result = rewrite_registered_idioms(body, _registry())
    assert result == body


def test_assert_dispositions_known_accepts_valid_registry():
    """A registry with only known dispositions passes the fail-closed guard."""
    assert_dispositions_known(_registry())  # does not raise


def test_assert_dispositions_known_fails_closed_on_unknown_disposition():
    """An unmapped/unknown disposition raises UnmappedIdiomError (fail-closed build)."""
    bad = _registry(NewClaudeIdiom={'disposition': 'do_something_unknown'})
    with pytest.raises(UnmappedIdiomError, match='NewClaudeIdiom'):
        assert_dispositions_known(bad)


def test_assert_dispositions_known_fails_closed_on_missing_disposition():
    """A registered idiom with no disposition field raises (fail-closed)."""
    bad = _registry(NoDisposition={'opencode_tool': 'whatever'})
    with pytest.raises(UnmappedIdiomError):
        assert_dispositions_known(bad)


def test_load_idiom_registry_reads_real_mapping_json():
    """The real mapping.json registry loads and validates fail-closed (no raise)."""
    registry = load_idiom_registry()
    # The three registered idioms are present with their documented dispositions.
    assert registry['AskUserQuestion']['disposition'] == 'rewrite_inline_code'
    assert registry['AskUserQuestion']['opencode_tool'] == 'question'
    assert registry['Task:']['disposition'] == 'preserve'
    assert registry['Skill: <entry>']['disposition'] == 'source_fix'


def test_load_idiom_registry_fails_closed_on_bad_mapping(tmp_path: Path):
    """A mapping.json with an unknown disposition raises at load time."""
    bad_mapping = tmp_path / 'mapping.json'
    _write(
        bad_mapping,
        '{"body_idiom_rewrites": {"Foo": {"disposition": "bogus"}}}',
    )
    with pytest.raises(UnmappedIdiomError):
        load_idiom_registry(bad_mapping)


def test_make_body_transformer_applies_transform_3_from_real_mapping():
    """make_body_transformer wires Transform 3 using the real mapping.json registry."""
    transform = make_body_transformer({})
    body = 'Escalate via `AskUserQuestion`.\n'
    result = transform(body, 'demo', 'skill')
    assert '`question`' in result
    assert '`AskUserQuestion`' not in result


def test_make_body_transformer_transform_3_preserves_task():
    """The composed transformer preserves `Task:` (leaf-aware disposition)."""
    transform = make_body_transformer({})
    body = 'no `Task:` dispatch here\n'
    result = transform(body, 'demo', 'skill')
    assert result == body
