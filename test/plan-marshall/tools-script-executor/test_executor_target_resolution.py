#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for target-aware executor resolution in generate_executor.py.

Covers:
  - the six-verb propagation matrix: every target-resolving verb reaches the
    same answer under each of the three cascade tiers
  - generate_target_aware_resolver_code: emits correct resolver per target
  - Claude resolver (_resolve_notation_by_target): tree-first, then plugin-cache
  - OpenCode resolver (_resolve_notation_by_target): tree-first, then 7-root walk
  - Absolute-path conversion for both targets
  - Integration: resolver round-trip for a real notation on each target
"""

import json  # noqa: I001
import os
import re
import sys
import types
from pathlib import Path

import pytest
import target_context
from conftest import MARKETPLACE_ROOT, _MARKETPLACE_SCRIPT_DIRS, get_scripts_dir
from target_context import SOURCE_ENV, SOURCE_FALLBACK, SOURCE_MARSHAL_JSON

SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'tools-script-executor')
GENERATE_SCRIPT = SCRIPTS_DIR / 'generate_executor.py'

#: The six verbs that resolve a target. Derived from the module's own parser
#: rather than restated, so a verb that gains or loses ``--target`` shows up
#: here as a roster change instead of silently escaping the matrix.
TARGET_RESOLVING_VERBS = ('generate', 'verify', 'bootstrap', 'drift', 'preflight', 'paths')

#: Every platform env signal the cascade reads. Cleared before each tier case so
#: the developer's own runtime cannot decide the outcome.
PLATFORM_ENV_SIGNALS = ('ANTIGRAVITY_AGENT', 'OPENCODE', 'OPENCODE_PID', 'CLAUDE_CODE_SESSION_ID')


@pytest.fixture()
def no_platform_signal(monkeypatch):
    """Clear every platform env signal so the cascade tier under test is the only input."""
    for name in PLATFORM_ENV_SIGNALS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv(target_context.MARKETPLACE_ROOT_ENV, raising=False)


def _load_generate_executor() -> types.ModuleType:
    """Load generate_executor.py as an in-process module."""
    source = GENERATE_SCRIPT.read_text(encoding='utf-8')
    module = types.ModuleType('generate_executor')
    module.__dict__['__file__'] = str(GENERATE_SCRIPT)
    exec(compile(source, str(GENERATE_SCRIPT), 'exec'), module.__dict__)
    return module


def _exec_resolver(resolver_code: str) -> types.ModuleType:
    """Execute resolver_code inside a minimal module namespace.

    The resolver bodies reference ``Path`` and ``os``; we inject those.
    Returns the module-like namespace so tests can call
    ``ns._resolve_notation_by_target(notation)``.
    """
    ns = types.ModuleType('resolver_under_test')
    ns.__dict__['Path'] = Path
    ns.__dict__['os'] = os
    exec(compile(resolver_code, '<resolver>', 'exec'), ns.__dict__)
    return ns


class TestTargetFlagIsRegisteredOnEveryVerb:
    """``--target`` is registered on all six verbs, from ONE shared definition.

    The roster and the accept-set are read back out of the production parser
    rather than restated, so a verb that dropped the flag, or a list that
    drifted from its siblings', fails here instead of in a user's terminal.
    """

    def test_roster_matches_the_parser(self):
        """The constant above is the parser's own roster, not a copy of it."""
        module = _load_generate_executor()
        subparsers = module.build_parser()._subparsers._group_actions[0].choices
        verbs_with_target = [
            verb
            for verb in subparsers
            if '--target' in {opt for action in subparsers[verb]._actions for opt in action.option_strings}
        ]

        assert tuple(sorted(verbs_with_target)) == tuple(sorted(TARGET_RESOLVING_VERBS))

    @pytest.mark.parametrize('verb', TARGET_RESOLVING_VERBS, ids=TARGET_RESOLVING_VERBS)
    def test_each_verb_accepts_the_shared_choice_list(self, verb):
        """Every verb's ``--target`` carries the same accept-set object."""
        module = _load_generate_executor()
        parser = module.build_parser()
        subparser = parser._subparsers._group_actions[0].choices[verb]

        flag = next(action for action in subparser._actions if '--target' in action.option_strings)

        assert flag.choices == module.TARGET_CHOICES
        assert flag.choices == ['claude', 'opencode', 'antigravity']

    @pytest.mark.parametrize('verb', TARGET_RESOLVING_VERBS, ids=TARGET_RESOLVING_VERBS)
    def test_each_verb_documents_the_flag_identically(self, verb):
        """All six carry the SAME help text, so ``--help`` cannot disagree with itself."""
        module = _load_generate_executor()
        subparser = module.build_parser()._subparsers._group_actions[0].choices[verb]

        flag = next(action for action in subparser._actions if '--target' in action.option_strings)

        assert flag.help == module.TARGET_FLAG_HELP

    @pytest.mark.parametrize('verb', TARGET_RESOLVING_VERBS, ids=TARGET_RESOLVING_VERBS)
    def test_each_verb_parses_an_explicit_target(self, verb):
        """The flag is not merely registered — it binds the value the verb reads."""
        module = _load_generate_executor()

        args = module.build_parser().parse_args([verb, '--target', 'opencode'])

        assert args.target == 'opencode'
        assert module.resolve_verb_context(args)['target'] == 'opencode'

    def test_an_unregistered_target_is_refused_by_every_verb(self):
        """The shared accept-set rejects an unknown target on each verb alike."""
        module = _load_generate_executor()
        parser = module.build_parser()

        for verb in TARGET_RESOLVING_VERBS:
            with pytest.raises(SystemExit):
                parser.parse_args([verb, '--target', 'not-a-target'])


class TestVerbTargetPropagationMatrix:
    """The propagation matrix: six verbs × three cascade tiers.

    The requirement is not that each verb resolves correctly but that they
    resolve IDENTICALLY — a machine with an OpenCode-only deployment must not
    have one verb reading the env tier while another reads ``marshal.json``.
    Every case is driven through the production parser and the production
    ``resolve_verb_context`` a verb calls, so the row measures the shipped path
    rather than a re-implementation of it.
    """

    @staticmethod
    def _resolve_all(module, verb_flags: dict[str, str]) -> dict[str, str]:
        """Resolve the target for every verb with the given per-verb flags."""
        parser = module.build_parser()
        answers: dict[str, str] = {}
        for verb in TARGET_RESOLVING_VERBS:
            args = parser.parse_args([verb, *verb_flags.get(verb, ())])
            answers[verb] = module.resolve_verb_context(args)['target']
        return answers

    def test_env_tier_reaches_every_verb(self, no_platform_signal, monkeypatch):
        """With a platform env signal, all six verbs answer that target."""
        module = _load_generate_executor()
        monkeypatch.setenv('OPENCODE', '1')

        answers = self._resolve_all(module, {})

        assert set(answers.values()) == {'opencode'}, answers

    def test_marshal_json_tier_reaches_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """With a declared ``runtime.target`` and no env signal, all six answer it."""
        module = _load_generate_executor()
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text(
            json.dumps({'runtime': {'target': 'antigravity'}}), encoding='utf-8'
        )

        answers = self._resolve_all(module, {})

        assert set(answers.values()) == {'antigravity'}, answers

    def test_fallback_tier_reaches_every_verb(self, no_platform_signal, monkeypatch, outside_repo_dir):
        """With neither signal, all six answer the same reported fallback."""
        module = _load_generate_executor()
        bare = outside_repo_dir / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)

        answers = self._resolve_all(module, {})

        assert set(answers.values()) == {target_context.default_target()}, answers

    @pytest.mark.parametrize(
        ('env_signal', 'expected'),
        [
            ('ANTIGRAVITY_AGENT', 'antigravity'),
            ('OPENCODE', 'opencode'),
            ('OPENCODE_PID', 'opencode'),
            ('CLAUDE_CODE_SESSION_ID', 'claude'),
        ],
        ids=['antigravity-signal', 'opencode-signal', 'opencode-pid-signal', 'claude-signal'],
    )
    def test_every_env_signal_reaches_every_verb(self, no_platform_signal, monkeypatch, env_signal, expected):
        """The tier is not one signal's privilege — all four reach all six verbs.

        Without this row the matrix above would pass on a resolver that read only
        ``OPENCODE``, which is the exact config-only-plus-one-signal shape the
        shared resolver replaced.
        """
        module = _load_generate_executor()
        monkeypatch.setenv(env_signal, '1')

        answers = self._resolve_all(module, {})

        assert set(answers.values()) == {expected}, answers

    def test_explicit_flag_reaches_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """``--target`` outranks the cascade on every verb, not only on ``generate``."""
        module = _load_generate_executor()
        monkeypatch.setenv('OPENCODE', '1')
        flags = dict.fromkeys(TARGET_RESOLVING_VERBS, ('--target', 'antigravity'))

        answers = self._resolve_all(module, flags)

        assert set(answers.values()) == {'antigravity'}, answers

    def test_no_verb_reaches_a_different_answer_than_another(self, no_platform_signal, monkeypatch, tmp_path):
        """The pairwise guarantee, asserted as a set collapse over all three tiers.

        One row per tier would fail on a disagreement in that tier alone; this
        one asserts the invariant that makes all of them true — at every tier,
        the six answers are ONE answer.
        """
        module = _load_generate_executor()
        tiers = {}

        monkeypatch.setenv('CLAUDE_CODE_SESSION_ID', '1')
        tiers['env'] = set(self._resolve_all(module, {}).values())
        monkeypatch.delenv('CLAUDE_CODE_SESSION_ID')

        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir(exist_ok=True)
        (tmp_path / '.plan' / 'marshal.json').write_text(
            json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8'
        )
        tiers['marshal_json'] = set(self._resolve_all(module, {}).values())
        (tmp_path / '.plan' / 'marshal.json').unlink()
        tiers['fallback'] = set(self._resolve_all(module, {}).values())

        for tier, answers in tiers.items():
            assert len(answers) == 1, f'{tier} tier: verbs disagreed — {answers}'

    def test_tier_is_reported_identically_for_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """The reported ``target_source`` agrees across verbs too, not only the value.

        Two verbs can agree on the string and disagree on WHY: one read the env
        tier, the other fell back. That disagreement is invisible to a
        value-only assertion and is exactly what a consumer branching on
        ``target_source`` would act on.
        """
        module = _load_generate_executor()
        parser = module.build_parser()
        monkeypatch.setenv('OPENCODE', '1')

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_ENV}

    def test_fallback_tier_is_reported_not_silently_assumed(self, no_platform_signal, monkeypatch, outside_repo_dir):
        """With no signal anywhere, every verb reports the FALLBACK tier.

        The value alone cannot tell a fallback apart from a real ``claude``
        env-tier resolution; the reported source can, and a consumer branching
        on it needs all six verbs to report it.
        """
        module = _load_generate_executor()
        parser = module.build_parser()
        bare = outside_repo_dir / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_FALLBACK}

    def test_marshal_tier_is_reported_by_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """A declared ``runtime.target`` is reported as the ``marshal_json`` tier everywhere."""
        module = _load_generate_executor()
        parser = module.build_parser()
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text(
            json.dumps({'runtime': {'target': 'opencode'}}), encoding='utf-8'
        )

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_MARSHAL_JSON}


class TestSharedResolverIsTheOnlyReader:
    """The config-only reader is gone and nothing re-introduces one."""

    def test_generate_executor_exposes_no_private_target_reader(self):
        """``read_marshal_target`` is removed, not wrapped.

        Wrapping it would have left the config-only walk in the tree as the
        implementation the wrapper delegates to, which is the duplication the
        deliverable set out to remove.
        """
        module = _load_generate_executor()

        assert not hasattr(module, 'read_marshal_target')
        assert not [name for name in dir(module) if 'marshal_target' in name]

    def test_generate_executor_routes_its_fallback_through_the_shared_resolver(self):
        """Every target read the module binds IS the shared resolver's function.

        Identity, not equality: a locally re-defined copy with the same behaviour
        would pass an equality check and would be the duplication the deliverable
        set out to remove.
        """
        module = _load_generate_executor()

        assert module.resolve_target is target_context.resolve_target
        assert module.resolve_context is target_context.resolve_context

    @pytest.mark.parametrize('verb', TARGET_RESOLVING_VERBS, ids=TARGET_RESOLVING_VERBS)
    def test_each_verb_context_goes_through_the_shared_resolver(self, verb, no_platform_signal, monkeypatch):
        """A verb's own resolution reaches ``resolve_context`` and reports its source.

        Driven through the production parser, so the row covers the flags the
        verb actually registers — including the three (``verify``, ``drift``,
        ``paths``) that register ``--target`` but not ``--marketplace-root``, and
        must therefore still resolve rather than fail on a missing attribute.
        """
        module = _load_generate_executor()
        monkeypatch.setenv('OPENCODE', '1')
        args = module.build_parser().parse_args([verb, '--target', 'opencode'])

        ctx = module.resolve_verb_context(args)

        assert ctx['target'] == 'opencode'
        assert ctx['target_source'] == target_context.SOURCE_EXPLICIT

    def test_a_verb_that_registers_no_marketplace_root_flag_still_resolves(self, no_platform_signal, monkeypatch):
        """``paths`` registers only ``--target``, and still produces a full context.

        The three verbs without ``--marketplace-root`` reach the resolver through
        the same ``getattr``-with-default seam. A resolver that read the
        attribute unconditionally would raise ``AttributeError`` here, which is
        why this row names a verb rather than a generic namespace.
        """
        module = _load_generate_executor()
        args = module.build_parser().parse_args(['paths'])

        assert not hasattr(args, 'marketplace_root')
        assert module.resolve_verb_context(args)['marketplace_root'] is None


class TestGenerateTargetAwareResolverCode:
    """Tests for the resolver code generator."""

    def test_returns_string_for_claude_target(self):
        """Returns a non-empty Python source string for target='claude'."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        assert isinstance(code, str)
        assert len(code) > 0

    def test_returns_string_for_opencode_target(self):
        """Returns a non-empty Python source string for target='opencode'."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        assert isinstance(code, str)
        assert len(code) > 0

    def test_claude_and_opencode_resolvers_differ(self):
        """The Claude and OpenCode resolver bodies are different."""
        module = _load_generate_executor()
        claude_code = module.generate_target_aware_resolver_code('claude')
        opencode_code = module.generate_target_aware_resolver_code('opencode')
        assert claude_code != opencode_code

    def test_unknown_target_returns_claude_resolver(self):
        """An unknown target string falls back to the Claude resolver."""
        module = _load_generate_executor()
        claude_code = module.generate_target_aware_resolver_code('claude')
        unknown_code = module.generate_target_aware_resolver_code('unknown-platform')
        assert claude_code == unknown_code

    def test_resolver_code_defines_function(self):
        """Both resolvers define the ``_resolve_notation_by_target`` function."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            code = module.generate_target_aware_resolver_code(target)
            assert 'def _resolve_notation_by_target(' in code, f'Target {target!r} resolver missing function definition'

    def test_resolver_code_is_valid_python(self):
        """Both resolver code strings compile without syntax errors."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            code = module.generate_target_aware_resolver_code(target)
            try:
                compile(code, f'<resolver-{target}>', 'exec')
            except SyntaxError as exc:
                pytest.fail(f'Resolver for {target!r} has syntax error: {exc}')

    def test_claude_resolver_references_plugin_cache(self):
        """Claude resolver body mentions the plugin-cache path."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        assert 'plugins' in code and 'cache' in code, 'Claude resolver must reference the plugin cache path'

    def test_opencode_resolver_references_seven_roots(self):
        """OpenCode resolver body references the 7 skill discovery roots."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        # Check for a representative subset of the 7 roots
        assert '.opencode/skills' in code, 'OpenCode resolver must include .opencode/skills root'
        assert '.claude/skills' in code, 'OpenCode resolver must include .claude/skills root'
        assert '.config/opencode/skills' in code, 'OpenCode resolver must include ~/.config/opencode/skills root'
        assert 'OPENCODE_CONFIG_DIR' in code, 'OpenCode resolver must honour OPENCODE_CONFIG_DIR env var'

    def test_opencode_resolver_uses_dash_namespaced_layout(self):
        """OpenCode resolver uses ``{bundle}-{skill}`` directory naming."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        # The dash-namespaced pattern must be present
        assert "f'{bundle}-{skill}'" in code or 'bundle-skill' in code or 'dir_name' in code, (
            'OpenCode resolver must construct dash-namespaced directory name'
        )


class TestClaudeResolver:
    """Tests for the inline Claude resolver function."""

    @pytest.fixture()
    def home_at_tmp(self, tmp_path, monkeypatch):
        """Point HOME at an isolated tmp_path and return that root."""
        monkeypatch.setenv('HOME', str(tmp_path))
        return tmp_path

    def test_returns_none_when_cache_dir_absent(self, home_at_tmp):
        """Returns None when the plugin cache root does not exist."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Point HOME at tmp_path so ~/.claude/plugins/cache is absent

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is None

    def test_returns_none_for_unknown_notation(self, tmp_path, home_at_tmp):
        """Returns None when the skill/script combination is not in the cache."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Create minimal plugin cache structure without the target script
        cache_dir = tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '1.0.0' / 'skills'
        cache_dir.mkdir(parents=True)

        result = ns._resolve_notation_by_target('no-bundle:no-skill:no-script')
        assert result is None

    def test_finds_script_in_cache_and_returns_absolute_path(self, tmp_path, home_at_tmp):
        """Discovers a script in the plugin cache and returns its absolute path."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Set up a minimal cache tree with a real script file
        version_dir = tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '1.2.3'
        scripts_dir = version_dir / 'skills' / 'manage-status' / 'scripts'
        scripts_dir.mkdir(parents=True)
        script_file = scripts_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected to find the script in the fake cache'
        assert os.path.isabs(result), f'Returned path must be absolute, got {result!r}'
        assert result.endswith('manage-status.py'), f'Expected manage-status.py, got {result!r}'

    def test_skips_hidden_version_directories(self, tmp_path, home_at_tmp):
        """Hidden directories (starting with '.') inside the cache are skipped."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        # Create only a hidden version dir — should not be discovered
        hidden_version = tmp_path / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '.hidden-version'
        scripts_dir = hidden_version / 'skills' / 'some-skill' / 'scripts'
        scripts_dir.mkdir(parents=True)
        (scripts_dir / 'some_script.py').write_text('# hidden', encoding='utf-8')

        result = ns._resolve_notation_by_target('plan-marshall:some-skill:some_script')
        assert result is None, 'Hidden version directories must be skipped'

    def test_invalid_notation_returns_none(self, home_at_tmp):
        """A notation with fewer or more than 3 parts returns None."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('claude')
        ns = _exec_resolver(code)

        assert ns._resolve_notation_by_target('two:parts') is None
        assert ns._resolve_notation_by_target('too:many:parts:here') is None
        assert ns._resolve_notation_by_target('') is None


class TestOpenCodeResolver:
    """Tests for the inline OpenCode resolver function."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    @pytest.fixture()
    def no_opencode_config_dir(self, monkeypatch):
        """Clear OPENCODE_CONFIG_DIR so resolution falls through to its next source."""
        monkeypatch.delenv('OPENCODE_CONFIG_DIR', raising=False)

    @pytest.fixture()
    def home_at_tmp(self, tmp_path, monkeypatch):
        """Point HOME at an isolated tmp_path and return that root."""
        monkeypatch.setenv('HOME', str(tmp_path))
        return tmp_path

    def test_returns_none_when_no_roots_exist(self, home_at_tmp, no_opencode_config_dir):
        """Returns None when none of the 7 roots contain the script."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is None

    def test_finds_script_in_opencode_skills_dir(self, tmp_path, home_at_tmp, no_opencode_config_dir, in_tmp_cwd):
        """Discovers a script in the .opencode/skills root (project-local)."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        # Create the .opencode/skills/{bundle}-{skill}/scripts/{script}.py structure
        skill_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        script_file = skill_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        # Change cwd to tmp_path so relative .opencode/skills resolves correctly

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected to find the script in .opencode/skills'
        assert os.path.isabs(result), f'Returned path must be absolute, got {result!r}'
        assert result.endswith('manage-status.py'), f'Expected manage-status.py, got {result!r}'

    def test_finds_script_via_env_var_override(self, tmp_path, monkeypatch, home_at_tmp, in_tmp_cwd):
        """$OPENCODE_CONFIG_DIR/skills root has highest priority."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        # Set up OPENCODE_CONFIG_DIR root with the target script
        config_dir = tmp_path / 'opencode-config'
        skill_dir = config_dir / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        script_file = skill_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')

        # Also create a lower-priority root with a different file to verify priority
        fallback_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        fallback_dir.mkdir(parents=True)
        (fallback_dir / 'manage-status.py').write_text('# fallback', encoding='utf-8')

        monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(config_dir))

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result)
        # Must have resolved through the env-var root (first match)
        assert str(config_dir.resolve()) in result, (
            f'Expected resolution through OPENCODE_CONFIG_DIR={config_dir}, got {result}'
        )

    def test_finds_script_in_user_global_config_root(self, tmp_path, home_at_tmp, no_opencode_config_dir, in_tmp_cwd):
        """Discovers a script in ~/.config/opencode/skills (user-global root)."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        # Create the user-global root
        skill_dir = tmp_path / '.config' / 'opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'manage-status.py').write_text('# user-global', encoding='utf-8')

        # cwd has no local .opencode/skills root

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result)

    def test_uses_dash_namespaced_directory(self, tmp_path, home_at_tmp, no_opencode_config_dir, in_tmp_cwd):
        """Resolver constructs ``{bundle}-{skill}`` directory name, not ``{bundle}/{skill}``."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        # Create the WRONG (slash-namespaced) layout — must NOT be found
        wrong_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall' / 'manage-status' / 'scripts'
        wrong_dir.mkdir(parents=True)
        (wrong_dir / 'manage-status.py').write_text('# wrong layout', encoding='utf-8')

        result_wrong = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result_wrong is None, 'Slash-namespaced layout must not be found; resolver uses dash-namespaced dirs'

        # Create the CORRECT (dash-namespaced) layout — must be found
        correct_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        correct_dir.mkdir(parents=True)
        (correct_dir / 'manage-status.py').write_text('# correct layout', encoding='utf-8')

        result_correct = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result_correct is not None, 'Dash-namespaced layout must be found'
        assert os.path.isabs(result_correct)

    def test_returns_absolute_path(self, tmp_path, home_at_tmp, no_opencode_config_dir, in_tmp_cwd):
        """Matched path is always converted to absolute before return."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        # Create the dash-namespaced layout
        skill_dir = tmp_path / '.opencode' / 'skills' / 'plan-marshall-manage-status' / 'scripts'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'manage-status.py').write_text('# stub', encoding='utf-8')

        result = ns._resolve_notation_by_target('plan-marshall:manage-status:manage-status')
        assert result is not None
        assert os.path.isabs(result), f'Path must be absolute, got {result!r}'

    def test_invalid_notation_returns_none(self, home_at_tmp):
        """A notation with fewer or more than 3 parts returns None."""
        module = _load_generate_executor()
        code = module.generate_target_aware_resolver_code('opencode')
        ns = _exec_resolver(code)

        assert ns._resolve_notation_by_target('two:parts') is None
        assert ns._resolve_notation_by_target('too:many:parts:here') is None
        assert ns._resolve_notation_by_target('') is None


class TestGenerateExecutorInjectsResolver:
    """Verify that the generator correctly replaces {{TARGET_AWARE_RESOLVER}} and {{EXECUTOR_TARGET}}."""

    def _generate_to_tmp(
        self,
        tmp_path: Path,
        module,
        target: str,
        monkeypatch,
    ) -> Path:
        """Run generate_executor → target file and return its path."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Use the real marketplace for base_path
        base_path = module.get_base_path(use_marketplace=True)

        # Run with empty mappings (we only care about the resolver injection)
        ok = module.generate_executor({}, base_path, dry_run=False, target=target)
        assert ok, 'generate_executor returned False'

        generated = plan_dir / 'execute-script.py'
        assert generated.exists(), f'Expected executor at {generated}'
        return generated

    def test_claude_executor_contains_plugin_cache_reference(self, tmp_path, monkeypatch):
        """Generated Claude executor references the plugin-cache path."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'claude', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert 'plugins' in content and 'cache' in content, (
            'Claude executor must contain plugin-cache reference in resolver'
        )

    def test_opencode_executor_contains_opencode_roots(self, tmp_path, monkeypatch):
        """Generated OpenCode executor contains the 7-root walk references."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'opencode', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert '.opencode/skills' in content, 'OpenCode executor must reference .opencode/skills'
        assert 'OPENCODE_CONFIG_DIR' in content, 'OpenCode executor must honour OPENCODE_CONFIG_DIR'

    def test_executor_target_comment_injected(self, tmp_path, monkeypatch):
        """The {{EXECUTOR_TARGET}} placeholder is replaced with the actual target."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            generated = self._generate_to_tmp(tmp_path, module, target, monkeypatch)
            content = generated.read_text(encoding='utf-8')
            assert f'target: {target}' in content, (
                f'Expected "target: {target}" in executor header comment for {target!r}'
            )

    def test_no_unresolved_placeholders(self, tmp_path, monkeypatch):
        """The generated executor must not contain any {{...}} template tokens."""
        module = _load_generate_executor()
        for target in ('claude', 'opencode'):
            generated = self._generate_to_tmp(tmp_path, module, target, monkeypatch)
            content = generated.read_text(encoding='utf-8')
            unresolved = re.findall(r'\{\{[A-Z_]+\}\}', content)
            assert unresolved == [], f'Target {target!r}: unresolved template tokens in executor: {unresolved}'

    def test_resolve_notation_calls_target_resolver(self, tmp_path, monkeypatch):
        """The generated executor's resolve_notation calls _resolve_notation_by_target."""
        module = _load_generate_executor()
        generated = self._generate_to_tmp(tmp_path, module, 'claude', monkeypatch)
        content = generated.read_text(encoding='utf-8')
        assert '_resolve_notation_by_target(' in content, (
            'resolve_notation must delegate to _resolve_notation_by_target'
        )


EXECUTOR_TEMPLATE = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-script-executor' / 'templates' / 'execute-script.py.template'
)


def _extract_cwd_walk_resolver() -> types.ModuleType:
    """Extract ``_resolve_notation_by_cwd_walk`` from the literal template.

    The cwd-walk fallback lives in the literal template (not in the generated
    target-aware resolver string), so it is parsed out of the rendered template
    and executed in an isolated namespace with the names it references
    (``Path``, ``os``) injected. Returns the namespace so tests can call
    ``ns._resolve_notation_by_cwd_walk(notation)``.
    """
    import ast as _ast

    template = EXECUTOR_TEMPLATE.read_text(encoding='utf-8')
    tree = _ast.parse(template)
    fn_src: str | None = None
    for node in tree.body:
        if isinstance(node, _ast.FunctionDef) and node.name == '_resolve_notation_by_cwd_walk':
            fn_src = _ast.get_source_segment(template, node)
            break
    assert fn_src is not None, '_resolve_notation_by_cwd_walk not found in template'

    ns = types.ModuleType('cwd_walk_under_test')
    ns.__dict__['Path'] = Path
    ns.__dict__['os'] = os
    exec(compile(fn_src, '<cwd-walk>', 'exec'), ns.__dict__)
    return ns


class TestCwdWalkResolver:
    """Tests for the cwd-walk-to-marketplace fallback branch."""

    def _make_marketplace_script(self, root: Path) -> Path:
        """Create marketplace/bundles/b/skills/s/scripts/sc.py under ``root``."""
        scripts_dir = root / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-status' / 'scripts'
        scripts_dir.mkdir(parents=True)
        script_file = scripts_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')
        return script_file

    def test_finds_script_by_walking_up_from_cwd(self, tmp_path, monkeypatch):
        """Discovers a live marketplace tree by walking up from cwd."""
        ns = _extract_cwd_walk_resolver()

        checkout = tmp_path / 'checkout'
        script = self._make_marketplace_script(checkout)

        # cwd is a deep subdir of the checkout — the walk must climb to it.
        deep = checkout / 'a' / 'b' / 'c'
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)

        result = ns._resolve_notation_by_cwd_walk('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected the cwd-walk to locate the marketplace script'
        assert os.path.isabs(result), f'Returned path must be absolute, got {result!r}'
        assert result == str(script.resolve())

    def test_returns_none_when_no_marketplace_tree(self, outside_repo_dir, monkeypatch):
        """Returns None when no marketplace/bundles tree is found above cwd."""
        ns = _extract_cwd_walk_resolver()

        # cwd must be OUTSIDE the repo: pytest's tmp_path now roots under the
        # repo-local --basetemp, whose ancestry HAS a marketplace/bundles tree,
        # so the cwd-walk would resolve a real script instead of returning None.
        empty = outside_repo_dir / 'empty'
        empty.mkdir()
        monkeypatch.chdir(empty)

        result = ns._resolve_notation_by_cwd_walk('plan-marshall:manage-status:manage-status')
        assert result is None

    def test_invalid_notation_returns_none(self, tmp_path, monkeypatch):
        """A notation with other than 3 parts returns None."""
        ns = _extract_cwd_walk_resolver()
        monkeypatch.chdir(tmp_path)

        assert ns._resolve_notation_by_cwd_walk('two:parts') is None
        assert ns._resolve_notation_by_cwd_walk('too:many:parts:here') is None
        assert ns._resolve_notation_by_cwd_walk('') is None


class TestCmdGenerateTargetFlag:
    """Tests for the --target flag on the generate subcommand."""

    def test_help_mentions_target_flag(self):
        """generate --help lists the --target flag."""
        import subprocess

        env = os.environ.copy()
        pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
        env['PYTHONPATH'] = f'{pythonpath}{os.pathsep}{env["PYTHONPATH"]}' if 'PYTHONPATH' in env else pythonpath
        result = subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT), 'generate', '--help'],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0
        assert '--target' in result.stdout, '--target flag must appear in generate --help'

    def test_executor_target_in_toon_output(self, tmp_path, monkeypatch):
        """cmd_generate result dict contains executor_target key."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        # Build a minimal args namespace
        class FakeArgs:
            marketplace = True
            marketplace_root = MARKETPLACE_ROOT.parent.parent  # project root
            dry_run = False
            force = False
            target = 'opencode'

        result = module.cmd_generate(FakeArgs())

        assert result.get('status') == 'success', f'Expected success, got {result}'
        assert result.get('executor_target') == 'opencode', f'Expected executor_target=opencode, got {result}'
