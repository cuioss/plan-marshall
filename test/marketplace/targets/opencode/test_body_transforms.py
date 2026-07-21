# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared body-transform engine, exercised via OpenCode rule data.

The engine lives at ``marketplace/targets/body_transform_engine`` (target-shared);
these tests drive it with the OpenCode ``mapping.json`` templates and registry so
the OpenCode-facing behaviour (Transform 1 directive rewrite, Transform 2 slash
rewrite, Transform 3 registered-idiom rewrite) stays covered after the applier was
lifted out of the OpenCode target.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from marketplace.targets.body_transform_engine import (
    SKILL_DIRECTIVE_RE,
    TransformRules,
    UnmappedIdiomError,
    assert_dispositions_known,
    assert_source_vocabulary_mapped,
    build_slash_command_re,
    build_user_invocable_lookup,
    load_transform_rules,
    make_body_transformer,
    rewrite_registered_idioms,
    rewrite_skill_directives,
    rewrite_slash_commands,
)

# The OpenCode rewrite templates, mirrored from mapping.json for direct-applier
# tests. Integration/composition tests load them from the real mapping.json.
OPENCODE_DIRECTIVE_TEMPLATE = (
    'Call the `skill` tool with `{ name: "{bundle}-{skill}" }` before continuing.'
)
OPENCODE_SLASH_TEMPLATE = '/{name}'


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3].parent


def _opencode_mapping_path() -> Path:
    return _project_root() / 'marketplace' / 'targets' / 'opencode' / 'mapping.json'


def _opencode_rules() -> TransformRules:
    return load_transform_rules(_opencode_mapping_path())


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Transform 1 — Skill: directive rewrite (template-driven)
# ---------------------------------------------------------------------------


def test_rewrite_skill_directives_full_line_match():
    """Full-line directive is rewritten; the regex's trailing ``\\s*$`` consumes
    the line's terminating newline as part of the match."""
    body = 'Skill: foo:bar\n'
    result = rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE)
    assert result == 'Call the `skill` tool with `{ name: "foo-bar" }` before continuing.'


def test_rewrite_skill_directives_full_line_with_extra_spacing():
    body = 'Skill:   plan-marshall:phase-5-execute\n'
    result = rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE)
    assert (
        result
        == 'Call the `skill` tool with `{ name: "plan-marshall-phase-5-execute" }` before continuing.'
    )


def test_rewrite_skill_directives_inline_backtick_left_alone():
    """Inline backtick references must NOT be rewritten — they are prose."""
    body = 'Some text `Skill: foo:bar` more text\n'
    assert rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE) == body


def test_rewrite_skill_directives_mid_line_left_alone():
    """A Skill: token in the middle of a sentence is not a full-line directive."""
    body = 'See the Skill: foo:bar reference for details\n'
    assert rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE) == body


def test_rewrite_skill_directives_idempotent():
    """Running the transform on already-rewritten text is a no-op."""
    body = 'Skill: foo:bar\n'
    once = rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE)
    twice = rewrite_skill_directives(once, OPENCODE_DIRECTIVE_TEMPLATE)
    assert once == twice


def test_rewrite_skill_directives_multiple_directives():
    body = (
        'Skill: alpha:one\n'
        'middle prose\n'
        'Skill: beta:two\n'
    )
    result = rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE)
    assert 'Call the `skill` tool with `{ name: "alpha-one" }` before continuing.' in result
    assert 'Call the `skill` tool with `{ name: "beta-two" }` before continuing.' in result
    assert 'middle prose' in result


def test_rewrite_skill_directives_no_match_returns_unchanged():
    body = '# Heading\n\nSome prose without a directive.\n'
    assert rewrite_skill_directives(body, OPENCODE_DIRECTIVE_TEMPLATE) == body


def test_rewrite_skill_directives_honours_custom_template():
    """The template is data — a different target's template drives the rewrite."""
    body = 'Skill: foo:bar\n'
    result = rewrite_skill_directives(body, 'load skill {bundle}::{skill} now')
    assert result == 'load skill foo::bar now'


def test_skill_directive_re_anchored_to_full_line():
    """The compiled regex MUST be anchored — guards against accidental relaxation."""
    pattern = SKILL_DIRECTIVE_RE.pattern
    assert pattern.startswith('^Skill:')
    assert pattern.endswith(r'\s*$')


# ---------------------------------------------------------------------------
# Transform 2 — Slash-command rewrite (template-driven)
# ---------------------------------------------------------------------------


def _basic_lookup() -> dict[str, str]:
    return {
        'plan-marshall': 'plan-marshall-plan-marshall',
        'sync-plugin-cache': 'plan-marshall-sync-plugin-cache',
    }


def test_rewrite_slash_commands_happy_path():
    body = 'Run /plan-marshall to start.\n'
    result = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert result == 'Run /plan-marshall-plan-marshall to start.\n'


def test_rewrite_slash_commands_path_substring_left_alone():
    """A slash inside a filesystem path MUST NOT be rewritten."""
    body = 'See path/to/plan-marshall for details.\n'
    assert rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE) == body


def test_rewrite_slash_commands_with_action_arg():
    """Slash commands followed by `key=value` args are still rewritten."""
    body = 'Try /plan-marshall action=execute now.\n'
    result = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert result == 'Try /plan-marshall-plan-marshall action=execute now.\n'


def test_rewrite_slash_commands_at_end_of_line():
    body = 'And finally /sync-plugin-cache\n'
    result = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert result == 'And finally /plan-marshall-sync-plugin-cache\n'


def test_rewrite_slash_commands_already_namespaced_passthrough():
    """Already-namespaced names are not in the lookup keys, so they pass through."""
    body = 'Run /plan-marshall-plan-marshall to start.\n'
    result = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert result == body


def test_rewrite_slash_commands_unknown_name_passthrough():
    body = 'Run /unknown-thing here.\n'
    result = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert result == body


def test_rewrite_slash_commands_empty_lookup_returns_unchanged():
    body = 'Run /plan-marshall to start.\n'
    assert rewrite_slash_commands(body, {}, OPENCODE_SLASH_TEMPLATE) == body


def test_rewrite_slash_commands_idempotent():
    body = 'Run /plan-marshall to start.\n'
    once = rewrite_slash_commands(body, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    twice = rewrite_slash_commands(once, _basic_lookup(), OPENCODE_SLASH_TEMPLATE)
    assert once == twice


def test_rewrite_slash_commands_honours_custom_template():
    """The invocation form is data — a target using a different prefix drives it."""
    body = 'Run /plan-marshall now.\n'
    result = rewrite_slash_commands(body, _basic_lookup(), '#{name}')
    assert result == 'Run #plan-marshall-plan-marshall now.\n'


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
# make_body_transformer (composition over rule data)
# ---------------------------------------------------------------------------


def test_make_body_transformer_applies_transform_1():
    transform = make_body_transformer({}, _opencode_rules())
    body = 'Skill: foo:bar\n'
    result = transform(body, 'demo', 'skill')
    assert 'Call the `skill` tool with `{ name: "foo-bar" }`' in result


def test_make_body_transformer_applies_transform_2():
    transform = make_body_transformer({'foo': 'demo-foo'}, _opencode_rules())
    body = 'Run /foo now.\n'
    result = transform(body, 'demo', 'skill')
    assert result == 'Run /demo-foo now.\n'


def test_make_body_transformer_applies_both_in_one_pass():
    body = 'Skill: demo:foo\nThen run /foo to continue.\n'
    transform = make_body_transformer({'foo': 'demo-foo'}, _opencode_rules())
    result = transform(body, 'demo', 'skill')
    assert 'Call the `skill` tool with `{ name: "demo-foo" }`' in result
    assert '/demo-foo' in result


def test_make_body_transformer_idempotent_on_already_transformed():
    body = 'Skill: demo:foo\nUse /foo here.\n'
    transform = make_body_transformer({'foo': 'demo-foo'}, _opencode_rules())
    once = transform(body, 'demo', 'skill')
    twice = transform(once, 'demo', 'skill')
    assert once == twice


def test_make_body_transformer_kind_signature():
    """The transformer must accept (body, bundle, kind) — emitter contract."""
    transform = make_body_transformer({}, _opencode_rules())
    # All three kinds must be accepted; bodies pass through identity when no patterns match
    for kind in ('skill', 'agent', 'command'):
        assert transform('plain text\n', 'demo', kind) == 'plain text\n'


def test_make_body_transformer_verbatim_rules_are_identity():
    """A verbatim target (empty rules) emits bodies byte-identical to source."""
    transform = make_body_transformer(_basic_lookup(), TransformRules())
    body = 'Skill: foo:bar\nRun /plan-marshall and escalate via `AskUserQuestion`.\n'
    assert transform(body, 'demo', 'skill') == body


# ---------------------------------------------------------------------------
# Integration — fixture skill body with all transforms
# ---------------------------------------------------------------------------


def test_integration_fixture_skill_body_both_transforms(tmp_path: Path):
    marketplace = tmp_path / 'bundles'
    _write_skill(marketplace, 'demo', 'helper', user_invocable=True)
    _write_skill(marketplace, 'demo', 'runner', user_invocable=True)

    lookup = build_user_invocable_lookup(marketplace)
    transform = make_body_transformer(lookup, _opencode_rules())

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
    marketplace = _project_root() / 'marketplace' / 'bundles'
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
    marketplace = _project_root() / 'marketplace' / 'bundles'
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


def test_integration_source_fix_contract_no_skill_entry_placeholder_in_bundles():
    """The source_fix disposition's contract: the `Skill: <entry>` placeholder stays
    fixed in the source. Because the emitter never rewrites this idiom, a source
    regression would flow verbatim into every emitted agent/skill body."""
    project_root = _project_root()
    marketplace = project_root / 'marketplace' / 'bundles'
    if not marketplace.is_dir():
        pytest.skip('marketplace/bundles not available in this checkout')

    offenders = [
        path.relative_to(project_root).as_posix()
        for path in sorted(marketplace.rglob('*.md'))
        if 'Skill: <entry>' in path.read_text(encoding='utf-8')
    ]
    assert not offenders, (
        f'`Skill: <entry>` placeholder found in bundle sources {offenders}; '
        'the source_fix disposition requires target-neutral wording in the source '
        '(see the step-3 skill-load loop in agents/execution-context.md)'
    )


def test_monitor_registry_entry_accepted_by_fail_closed_load():
    """The real mapping.json's `Monitor` entry passes the fail-closed registry load.

    `source_fix` is already in the known-disposition set, so registering `Monitor`
    is pure data — it must not trip `UnmappedIdiomError` at load time.
    """
    rules = _opencode_rules()
    assert rules.body_idiom_rewrites['Monitor']['disposition'] == 'source_fix'


def test_source_fix_disposition_leaves_monitor_prose_untouched():
    """Under `source_fix` the emit-time engine leaves `Monitor` prose alone.

    Both shapes are covered: bare prose and a backtick-wrapped reference. The
    divergence is fixed in the source, never rewritten at emit time.
    """
    registry = _registry(Monitor={'disposition': 'source_fix'})
    body = 'A `Monitor` tool call, and a bare Monitor mention.\n'
    assert rewrite_registered_idioms(body, registry) == body


def test_make_body_transformer_leaves_monitor_untouched_from_real_mapping():
    """The composed transformer over the real mapping.json does not rewrite `Monitor`."""
    transform = make_body_transformer({}, _opencode_rules())
    body = 'Poll conditions belong in a `Monitor` tool call.\n'
    assert transform(body, 'demo', 'skill') == body


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


def test_make_body_transformer_applies_transform_3_from_real_mapping():
    """make_body_transformer wires Transform 3 using the real mapping.json registry."""
    transform = make_body_transformer({}, _opencode_rules())
    body = 'Escalate via `AskUserQuestion`.\n'
    result = transform(body, 'demo', 'skill')
    assert '`question`' in result
    assert '`AskUserQuestion`' not in result


def test_make_body_transformer_transform_3_preserves_task():
    """The composed transformer preserves `Task:` (leaf-aware disposition)."""
    transform = make_body_transformer({}, _opencode_rules())
    body = 'no `Task:` dispatch here\n'
    result = transform(body, 'demo', 'skill')
    assert result == body


# ---------------------------------------------------------------------------
# load_transform_rules + source-vocabulary fail-closed guard
# ---------------------------------------------------------------------------


def test_load_transform_rules_reads_real_mapping_json():
    """The real mapping.json loads all three categories and validates fail-closed."""
    rules = _opencode_rules()
    assert not rules.is_verbatim
    assert rules.directive_rewrites['skill_directive']['template']
    assert rules.slash_rewrites['slash_command']['template'] == '/{name}'
    assert rules.body_idiom_rewrites['AskUserQuestion']['disposition'] == 'rewrite_inline_code'
    assert rules.body_idiom_rewrites['AskUserQuestion']['opencode_tool'] == 'question'
    assert rules.body_idiom_rewrites['Task:']['disposition'] == 'preserve'
    assert rules.body_idiom_rewrites['Skill: <entry>']['disposition'] == 'source_fix'


def test_load_transform_rules_missing_file_is_verbatim(tmp_path: Path):
    """A target with no mapping.json is verbatim (all-empty rules)."""
    rules = load_transform_rules(tmp_path / 'does-not-exist.json')
    assert rules.is_verbatim
    assert rules.directive_rewrites == {}
    assert rules.slash_rewrites == {}
    assert rules.body_idiom_rewrites == {}


def test_load_transform_rules_fails_closed_on_bad_disposition(tmp_path: Path):
    """A mapping.json with an unknown Transform-3 disposition raises at load time."""
    mapping = tmp_path / 'mapping.json'
    _write(mapping, '{"body_idiom_rewrites": {"Foo": {"disposition": "bogus"}}}')
    with pytest.raises(UnmappedIdiomError):
        load_transform_rules(mapping)


def test_load_transform_rules_fails_closed_on_unmapped_structural_idiom(tmp_path: Path):
    """A non-verbatim target that omits a structural template fails closed at load.

    Declaring slash_rewrites (non-verbatim) but omitting directive_rewrites leaves
    the `skill_directive` source idiom unmapped — the build must fail."""
    mapping = tmp_path / 'mapping.json'
    _write(mapping, '{"slash_rewrites": {"slash_command": {"template": "/{name}"}}}')
    with pytest.raises(UnmappedIdiomError, match='skill_directive'):
        load_transform_rules(mapping)


def test_assert_source_vocabulary_mapped_exempts_verbatim_target():
    """A verbatim target (no rewrite category) is exempt from the vocabulary check."""
    assert_source_vocabulary_mapped(TransformRules())  # does not raise


def test_assert_source_vocabulary_mapped_requires_slash_when_directive_present():
    """A non-verbatim target missing the slash template fails closed."""
    rules = TransformRules(
        directive_rewrites={'skill_directive': {'template': 'x {bundle}-{skill}'}},
    )
    with pytest.raises(UnmappedIdiomError, match='slash_command'):
        assert_source_vocabulary_mapped(rules)


def test_assert_source_vocabulary_mapped_rejects_empty_template():
    """A present-but-empty template does not satisfy the vocabulary check."""
    rules = TransformRules(
        directive_rewrites={'skill_directive': {'template': ''}},
        slash_rewrites={'slash_command': {'template': '/{name}'}},
    )
    with pytest.raises(UnmappedIdiomError, match='skill_directive'):
        assert_source_vocabulary_mapped(rules)


def test_assert_source_vocabulary_mapped_accepts_full_opencode_rules():
    """The real OpenCode rules map every structural source idiom — no raise."""
    assert_source_vocabulary_mapped(_opencode_rules())
