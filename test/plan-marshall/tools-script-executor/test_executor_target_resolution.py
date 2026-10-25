#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Target resolution for the executor — the cascade, and ONE resolver body.

Two contracts live here:

* the ``--target`` cascade every target-resolving verb shares (unchanged by the
  harness-independent executor: a verb still resolves which install to PREFER),
  and
* the resolver body, which no longer varies by target. The per-target bodies
  (Claude plugin-cache glob, OpenCode 7-root walk, Antigravity root walk) were
  what made two harnesses emit two different executors from one checkout; the
  replacement walks one order for every harness — tree, then the runtime
  harness's own install, then the others.
"""

import json  # noqa: I001
import os
import types
from pathlib import Path

import pytest
import target_context
from conftest import MARKETPLACE_ROOT, _MARKETPLACE_SCRIPT_DIRS, get_scripts_dir
from target_context import SOURCE_ENV, SOURCE_FALLBACK, SOURCE_LOCAL_CONFIG

SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'tools-script-executor')
GENERATE_SCRIPT = SCRIPTS_DIR / 'generate_executor.py'

#: The verbs that resolve a target. Restated here so the parametrised matrix has
#: a roster to iterate, and compared against the module's own parser by
#: ``test_roster_matches_the_parser`` — so a verb that gains or loses
#: ``--target`` fails that comparison instead of silently escaping the matrix.
TARGET_RESOLVING_VERBS = ('generate', 'verify', 'bootstrap', 'recover', 'drift', 'preflight', 'paths')

#: Every platform env signal the cascade reads. Cleared before each tier case so
#: the developer's own runtime cannot decide the outcome.
PLATFORM_ENV_SIGNALS = tuple(name for name, _target in target_context.TARGET_ENV_SIGNALS)

#: The (signal, target) matrix, derived from the registry so a new signal is
#: exercised here instead of silently escaping the sweep.
SIGNAL_CASES = list(target_context.TARGET_ENV_SIGNALS)
assert SIGNAL_CASES, 'the ambient-signal registry must not be empty'


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


def _resolver_namespace(
    roots: tuple[tuple[str, str], ...],
    runtime: str | None,
    executor_file: str | None = None,
    scripts: dict[str, str] | None = None,
) -> types.ModuleType:
    """Exec the production resolver body with the maps a generated executor carries."""
    module = _load_generate_executor()
    code = module.generate_target_aware_resolver_code('claude')
    ns = types.ModuleType('resolver_under_test')
    ns.__dict__['Path'] = Path
    ns.__dict__['os'] = os
    ns.__dict__['SCRIPTS'] = dict(scripts or {})
    ns.__dict__['_INSTALLED_ROOTS'] = roots
    ns.__dict__['_runtime_harness'] = lambda: runtime
    if executor_file is not None:
        ns.__dict__['__file__'] = executor_file
    exec(compile(code, '<resolver>', 'exec'), ns.__dict__)
    return ns


class TestTargetFlagIsRegisteredOnEveryVerb:
    """``--target`` is registered on all six verbs, from ONE shared definition.

    The accept-set is read back out of the production parser rather than
    restated, and the restated roster is compared against it by
    ``test_roster_matches_the_parser``. So a verb that dropped the flag, or a
    list that drifted from its siblings', fails here instead of in a user's
    terminal.
    """

    def test_roster_matches_the_parser(self):
        """The hardcoded roster still equals the one the production parser builds."""
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

    def test_local_config_tier_reaches_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """With a declared machine-local harness and no env signal, all six answer it."""
        module = _load_generate_executor()
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan' / 'local' / 'harness').mkdir(parents=True)
        (tmp_path / '.plan' / 'local' / 'harness' / 'antigravity.json').write_text(
            json.dumps({'schema_version': 1, 'harness': 'antigravity'}), encoding='utf-8'
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
        SIGNAL_CASES,
        ids=[name for name, _target in SIGNAL_CASES],
    )
    def test_every_env_signal_reaches_every_verb(self, no_platform_signal, monkeypatch, env_signal, expected):
        """The tier is not one signal's privilege — all three reach all six verbs."""
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

    def test_tier_is_reported_identically_for_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """The reported ``target_source`` agrees across verbs too, not only the value."""
        module = _load_generate_executor()
        parser = module.build_parser()
        monkeypatch.setenv('OPENCODE', '1')

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_ENV}

    def test_fallback_tier_is_reported_not_silently_assumed(self, no_platform_signal, monkeypatch, outside_repo_dir):
        """With no signal anywhere, every verb reports the FALLBACK tier."""
        module = _load_generate_executor()
        parser = module.build_parser()
        bare = outside_repo_dir / 'bare'
        bare.mkdir()
        monkeypatch.chdir(bare)

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_FALLBACK}

    def test_local_config_tier_is_reported_by_every_verb(self, no_platform_signal, monkeypatch, tmp_path):
        """A declared machine-local harness is reported as the ``local_config`` tier everywhere."""
        module = _load_generate_executor()
        parser = module.build_parser()
        monkeypatch.chdir(tmp_path)
        (tmp_path / '.plan' / 'local' / 'harness').mkdir(parents=True, exist_ok=True)
        (tmp_path / '.plan' / 'local' / 'harness' / 'opencode.json').write_text(
            json.dumps({'schema_version': 1, 'harness': 'opencode'}), encoding='utf-8'
        )

        sources = {
            module.resolve_verb_context(parser.parse_args([verb]))['target_source'] for verb in TARGET_RESOLVING_VERBS
        }

        assert sources == {SOURCE_LOCAL_CONFIG}


class TestSharedResolverIsTheOnlyReader:
    """The config-only reader is gone and nothing re-introduces one."""

    def test_generate_executor_exposes_no_private_target_reader(self):
        """``read_marshal_target`` is absent, not wrapped."""
        module = _load_generate_executor()

        assert not hasattr(module, 'read_marshal_target')
        assert not [name for name in dir(module) if 'marshal_target' in name]

    def test_generate_executor_routes_its_fallback_through_the_shared_resolver(self):
        """Every target read the module binds IS the shared resolver's function."""
        module = _load_generate_executor()

        assert module.resolve_target is target_context.resolve_target
        assert module.resolve_context is target_context.resolve_context

    @pytest.mark.parametrize('verb', TARGET_RESOLVING_VERBS, ids=TARGET_RESOLVING_VERBS)
    def test_each_verb_context_goes_through_the_shared_resolver(self, verb, no_platform_signal, monkeypatch):
        """A verb's own resolution reaches ``resolve_context`` and reports its source."""
        module = _load_generate_executor()
        monkeypatch.setenv('OPENCODE', '1')
        args = module.build_parser().parse_args([verb, '--target', 'opencode'])

        ctx = module.resolve_verb_context(args)

        assert ctx['target'] == 'opencode'
        assert ctx['target_source'] == target_context.SOURCE_EXPLICIT

    def test_a_verb_that_registers_no_marketplace_root_flag_still_resolves(self, no_platform_signal, monkeypatch):
        """``paths`` registers only ``--target``, and still produces a full context."""
        module = _load_generate_executor()
        args = module.build_parser().parse_args(['paths'])

        assert not hasattr(args, 'marketplace_root')
        assert module.resolve_verb_context(args)['marketplace_root'] is None


class TestTheResolverIsHarnessIndependent:
    """ONE body, one order: tree, own install, the other installs."""

    def test_every_target_renders_the_same_body(self):
        module = _load_generate_executor()
        bodies = {target: module.generate_target_aware_resolver_code(target) for target in ('claude', 'opencode')}

        assert bodies['claude'] == bodies['opencode']
        assert 'def _resolve_notation_by_target(' in bodies['claude']

    def test_the_body_is_valid_python(self):
        module = _load_generate_executor()

        compile(module.generate_target_aware_resolver_code('antigravity'), '<resolver>', 'exec')

    def test_the_tree_wins_over_a_deployed_copy(self, tmp_path):
        """A live checkout above the executor file outranks every installed root."""
        checkout = tmp_path / 'checkout'
        tree_script = checkout / 'marketplace' / 'bundles' / 'b' / 'skills' / 's' / 'scripts' / 'tool.py'
        tree_script.parent.mkdir(parents=True)
        tree_script.write_text('# tree', encoding='utf-8')
        installed = tmp_path / 'install'
        deployed = installed / 'b-s' / 'scripts' / 'tool.py'
        deployed.parent.mkdir(parents=True)
        deployed.write_text('# installed', encoding='utf-8')

        ns = _resolver_namespace(
            (('opencode', str(installed)),),
            'opencode',
            executor_file=str(checkout / '.plan' / 'execute-script.py'),
        )

        assert ns._resolve_notation_by_target('b:s:tool') == str(tree_script.resolve())

    def test_the_runtime_harness_install_is_searched_first(self, tmp_path):
        """With no tree, the runtime harness's own copy beats another harness's."""
        claude_root = tmp_path / 'claude-install'
        opencode_root = tmp_path / 'opencode-install'
        claude_script = claude_root / 'b' / '0.1.1' / 'skills' / 's' / 'scripts' / 'tool.py'
        opencode_script = opencode_root / 'b-s' / 'scripts' / 'tool.py'
        for path in (claude_script, opencode_script):
            path.parent.mkdir(parents=True)
            path.write_text('# copy', encoding='utf-8')

        roots = (('claude', str(claude_root)), ('opencode', str(opencode_root)))

        opencode_ns = _resolver_namespace(roots, 'opencode', executor_file=str(tmp_path / 'nope' / 'execute-script.py'))
        claude_ns = _resolver_namespace(roots, 'claude', executor_file=str(tmp_path / 'nope' / 'execute-script.py'))

        assert opencode_ns._resolve_notation_by_target('b:s:tool') == str(opencode_script.resolve())
        assert claude_ns._resolve_notation_by_target('b:s:tool') == str(claude_script.resolve())

    def test_the_newest_version_dir_wins_within_an_install(self, tmp_path):
        """A stale version dir carrying the script cannot shadow the newest one."""
        root = tmp_path / 'claude-install'
        for version in ('0.1.9', '0.1.100', '0.1.200'):
            script = root / 'b' / version / 'skills' / 's' / 'scripts' / 'tool.py'
            script.parent.mkdir(parents=True)
            script.write_text(f'# {version}', encoding='utf-8')
        newest = root / 'b' / '0.1.200' / 'skills' / 's' / 'scripts' / 'tool.py'

        ns = _resolver_namespace(
            (('claude', str(root)),), 'claude', executor_file=str(tmp_path / 'nope' / 'execute-script.py')
        )

        assert ns._resolve_notation_by_target('b:s:tool') == str(newest.resolve())

    def test_a_nested_script_is_found_by_its_embedded_suffix(self, tmp_path):
        """The four sub-directory entries resolve: the mapping's suffix, not ``{script}.py``."""
        root = tmp_path / 'install'
        nested = root / 'b' / '0.1.1' / 'skills' / 's' / 'scripts' / 'workflow' / 'tool.py'
        nested.parent.mkdir(parents=True)
        nested.write_text('# nested', encoding='utf-8')

        ns = _resolver_namespace(
            (('opencode', str(root)),),
            'opencode',
            executor_file=str(tmp_path / 'nope' / 'execute-script.py'),
            scripts={'b:s:tool': str(root / 'b' / '0.1.1' / 'skills' / 's' / 'scripts' / 'workflow' / 'tool.py')},
        )

        assert ns._resolve_notation_by_target('b:s:tool') == str(nested.resolve())

    def test_an_unknown_notation_resolves_to_nothing(self, tmp_path):
        ns = _resolver_namespace(
            (('claude', str(tmp_path / 'install')),), 'claude', executor_file=str(tmp_path / 'nope' / 'x.py')
        )

        assert ns._resolve_notation_by_target('two:parts') is None
        assert ns._resolve_notation_by_target('too:many:parts:here') is None
        assert ns._resolve_notation_by_target('') is None


class TestCwdWalkResolver:
    """Tests for the cwd-walk-to-marketplace fallback branch."""

    def _extract_cwd_walk_resolver(self) -> types.ModuleType:
        """Extract ``_resolve_notation_by_cwd_walk`` from the literal template.

        The cwd-walk fallback lives in the literal template (not in the generated
        resolver body), so it is parsed out of the template and executed in an
        isolated namespace. The suffix helper it calls is supplied from the same
        template, so the extraction measures the shipped pair.
        """
        import ast as _ast

        template = (
            MARKETPLACE_ROOT
            / 'plan-marshall'
            / 'skills'
            / 'tools-script-executor'
            / 'templates'
            / 'execute-script.py.template'
        ).read_text(encoding='utf-8')
        tree = _ast.parse(template)
        wanted = {'_resolve_notation_by_cwd_walk'}
        sources: list[str] = []
        for node in tree.body:
            if isinstance(node, _ast.FunctionDef) and node.name in wanted:
                segment = _ast.get_source_segment(template, node)
                assert segment is not None, 'the cwd-walk source segment could not be extracted'
                sources.append(segment)
        assert sources, '_resolve_notation_by_cwd_walk not found in template'

        ns = types.ModuleType('cwd_walk_under_test')
        ns.__dict__['Path'] = Path
        ns.__dict__['os'] = os
        ns.__dict__['_relative_script_path'] = lambda notation: f'{notation.split(":")[2]}.py'
        exec(compile(sources[0], '<cwd-walk>', 'exec'), ns.__dict__)
        return ns

    def _make_marketplace_script(self, root: Path) -> Path:
        """Create marketplace/bundles/b/skills/s/scripts/sc.py under ``root``."""
        scripts_dir = root / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-status' / 'scripts'
        scripts_dir.mkdir(parents=True)
        script_file = scripts_dir / 'manage-status.py'
        script_file.write_text('# stub', encoding='utf-8')
        return script_file

    def test_finds_script_by_walking_up_from_cwd(self, tmp_path, monkeypatch):
        """Discovers a live marketplace tree by walking up from cwd."""
        ns = self._extract_cwd_walk_resolver()

        checkout = tmp_path / 'checkout'
        script = self._make_marketplace_script(checkout)

        deep = checkout / 'a' / 'b' / 'c'
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)

        result = ns._resolve_notation_by_cwd_walk('plan-marshall:manage-status:manage-status')
        assert result is not None, 'Expected the cwd-walk to locate the marketplace script'
        assert os.path.isabs(result)
        assert result == str(script.resolve())

    def test_returns_none_when_no_marketplace_tree(self, outside_repo_dir, monkeypatch):
        """Returns None when no marketplace/bundles tree is found above cwd."""
        ns = self._extract_cwd_walk_resolver()

        empty = outside_repo_dir / 'empty'
        empty.mkdir()
        monkeypatch.chdir(empty)

        assert ns._resolve_notation_by_cwd_walk('plan-marshall:manage-status:manage-status') is None

    def test_invalid_notation_returns_none(self, tmp_path, monkeypatch):
        """A notation with other than 3 parts returns None."""
        ns = self._extract_cwd_walk_resolver()
        monkeypatch.chdir(tmp_path)

        assert ns._resolve_notation_by_cwd_walk('two:parts') is None
        assert ns._resolve_notation_by_cwd_walk('too:many:parts:here') is None
        assert ns._resolve_notation_by_cwd_walk('') is None


class TestCmdGenerateTargetFlag:
    """Tests for the --target flag on the generate subcommand."""

    def test_help_mentions_target_flag(self):
        """generate --help lists the --target flag."""
        import subprocess
        import sys

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
        """cmd_generate reports the target it resolved, as a hint for that run only."""
        module = _load_generate_executor()

        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir()
        monkeypatch.setenv('PLAN_BASE_DIR', str(plan_dir))

        class FakeArgs:
            marketplace = True
            marketplace_root = MARKETPLACE_ROOT.parent.parent
            dry_run = False
            force = False
            target = 'opencode'

        result = module.cmd_generate(FakeArgs())

        assert result.get('status') == 'success', f'Expected success, got {result}'
        assert result.get('executor_target') == 'opencode', f'Expected executor_target=opencode, got {result}'
