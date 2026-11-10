#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""OpenCode 2 permission-shape pins for the permission tooling (PLAN-LB-48 D3).

OpenCode 2 stores permissions as an ordered ``permissions`` list evaluated
last-match-wins; OpenCode 1 used a ``permission`` map. Writing a map beside a
list does not merely look wrong — the normalizer concatenates the map BEFORE
the list, so the specific rule an operator just added is overridden by the
list's catch-all. These tests run every reading and writing operation against a
list-shaped fixture and pin that the list is what is read and what is written.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from opencode_runtime import OPENCODE_DEFAULT_PERMISSIONS, OpenCodeRuntime, to_opencode_grant
from toon_parser import parse_toon

from conftest import PROJECT_ROOT

CATCH_ALL = {'action': 'shell', 'resource': '*', 'effect': 'ask'}


@pytest.fixture()
def runtime() -> OpenCodeRuntime:
    return OpenCodeRuntime()


@pytest.fixture()
def list_settings(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A project ``opencode.json`` in the OpenCode 2 shape, with a shell catch-all."""
    global_dir = tmp_path / 'global'
    global_dir.mkdir()
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(global_dir))
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(
        json.dumps({'$schema': 'https://opencode.ai/config.json', 'permissions': [dict(CATCH_ALL)]}, indent=2) + '\n',
        encoding='utf-8',
    )
    return config


def _load(path: pathlib.Path) -> dict:
    data: dict = json.loads(path.read_text(encoding='utf-8'))
    return data


def _exact_index(rules: list[dict], action: str, resource: str, effect: str) -> int | None:
    for index, rule in enumerate(rules):
        if rule.get('action') == action and rule.get('resource') == resource and rule.get('effect') == effect:
            return index
    return None


def _matches(pattern: str, resource: str) -> bool:
    import re

    return re.match('^' + re.escape(pattern).replace(r'\*', '.*') + '$', resource, re.S) is not None


def _effective_effect(rules: list[dict], action: str, resource: str) -> str | None:
    hits = [rule for rule in rules if rule.get('action') == action and _matches(rule.get('resource', ''), resource)]
    return hits[-1]['effect'] if hits else None


def _effective_effect_any_action(rules: list[dict], action: str, resource: str) -> str | None:
    """Evaluate the way OpenCode 2 does, including the ``*`` action wildcard."""
    hits = [
        rule for rule in rules if rule.get('action') in (action, '*') and _matches(rule.get('resource', ''), resource)
    ]
    return hits[-1]['effect'] if hits else None


def _assert_no_legacy_map(data: dict) -> None:
    assert 'permission' not in data, 'a `permission` map must never be added beside a `permissions` list'


# ---------------------------------------------------------------------------
# ensure-defaults / skeleton
# ---------------------------------------------------------------------------


def test_ensure_defaults_writes_the_executor_into_the_permissions_list(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path
):
    """Defaults land inside ``permissions``, after the catch-all, and no map appears."""
    settings = runtime.permission_load_settings(str(list_settings))
    result = runtime.permission_ensure_defaults(settings, str(list_settings), dry_run=False)

    assert result['defaults_added_count'] > 0
    data = _load(list_settings)
    _assert_no_legacy_map(data)
    rules = data['permissions']
    assert rules[0] == CATCH_ALL, 'the catch-all must stay first'

    executor = 'python3 .plan/execute-script.py *'
    index = _exact_index(rules, 'shell', executor, 'allow')
    assert index is not None, 'the executor allow must be inside the permissions list'
    assert index > 0, 'the executor allow must come after the catch-all'


def test_ensure_defaults_is_idempotent_in_the_list_shape(runtime: OpenCodeRuntime, list_settings: pathlib.Path):
    settings = runtime.permission_load_settings(str(list_settings))
    runtime.permission_ensure_defaults(settings, str(list_settings), dry_run=False)

    reloaded = runtime.permission_load_settings(str(list_settings))
    again = runtime.permission_ensure_defaults(reloaded, str(list_settings), dry_run=False)
    assert again['defaults_added_count'] == 0
    assert again['applied'] is False


def test_new_skeleton_is_opencode2_shaped(runtime: OpenCodeRuntime, tmp_path: pathlib.Path):
    """A freshly created settings file carries a list, not the OpenCode 1 map."""
    path = runtime.permission_settings_path('project', write=True, project_dir=str(tmp_path))
    data = _load(pathlib.Path(path))

    _assert_no_legacy_map(data)
    rules = data['permissions']
    assert isinstance(rules, list) and rules
    assert all(rule['action'] == 'shell' and rule['effect'] == 'allow' for rule in rules)


def test_a_new_skeleton_carries_no_shell_catch_all(runtime: OpenCodeRuntime, tmp_path: pathlib.Path):
    """No skeleton rule re-decides a command a global deny already decided.

    Project rules are appended after the global ones, so a skeleton catch-all
    there would decide every command the global list denied. The client answers
    ``ask`` when nothing matches, which is the default the catch-all restated.
    """
    path = runtime.permission_settings_path('project', write=True, project_dir=str(tmp_path))
    rules = _load(pathlib.Path(path))['permissions']

    assert not [rule for rule in rules if rule['resource'] == '*'], 'the skeleton must carry no catch-all'
    assert {rule['resource'] for rule in rules} == set(OPENCODE_DEFAULT_PERMISSIONS)


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def test_analyze_reports_the_root_configs_deny_rules(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch):
    """Analyze over a copy of the repository's root config reports its deny rules."""
    root_config = pathlib.Path(PROJECT_ROOT) / 'opencode.json'
    (tmp_path / 'opencode.json').write_text(root_config.read_text(encoding='utf-8'), encoding='utf-8')
    global_dir = tmp_path / 'global'
    global_dir.mkdir()
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(global_dir))
    monkeypatch.chdir(tmp_path)

    result = parse_toon(OpenCodeRuntime().permission_analyze('project', ['all'], None))
    analysis = result['analysis']['project']

    assert analysis['permission_shape'] == 'permissions'
    assert analysis['has_executor'] is True
    denies = analysis['deny_rules']
    assert {'action': 'shell', 'resource': 'gh *', 'effect': 'deny'} in denies
    assert {'action': 'shell', 'resource': 'git restore *', 'effect': 'deny'} in denies


# ---------------------------------------------------------------------------
# configure / fix / protect-path
# ---------------------------------------------------------------------------


def test_configure_adds_into_the_permissions_list(runtime: OpenCodeRuntime, list_settings: pathlib.Path):
    result = runtime.permission_configure('project', [{'rule': 'deny(git push *)'}])
    assert parse_toon(result)['grants_added'] == 1
    data = _load(list_settings)
    _assert_no_legacy_map(data)
    assert _exact_index(data['permissions'], 'shell', 'git push *', 'deny') is not None


def test_a_config_with_neither_shape_gains_the_list_not_the_map(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A config naming only its schema must not gain the OpenCode 1 map from a producer."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'$schema': 'https://opencode.ai/config.json'}), encoding='utf-8')

    runtime.permission_configure('project', [{'rule': 'read'}])

    data = _load(config)
    _assert_no_legacy_map(data)
    assert _exact_index(data['permissions'], 'read', '*', 'allow') is not None


def test_the_opencode1_task_alias_is_written_as_the_opencode2_tool(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path
):
    """A ``task`` grant is normalized to ``subagent`` on write, never written as a dead action."""
    runtime.permission_configure('project', [{'rule': 'task'}])
    data = _load(list_settings)
    actions = [rule['action'] for rule in data['permissions']]
    assert 'subagent' in actions
    assert 'task' not in actions


def test_fix_ensure_and_remove_use_the_permissions_list(runtime: OpenCodeRuntime, list_settings: pathlib.Path):
    runtime.permission_fix('project', 'ensure', ['ask(git fetch *)'], False)
    data = _load(list_settings)
    _assert_no_legacy_map(data)
    assert _exact_index(data['permissions'], 'shell', 'git fetch *', 'ask') is not None

    runtime.permission_fix('project', 'remove', ['ask(git fetch *)'], False)
    data = _load(list_settings)
    assert _exact_index(data['permissions'], 'shell', 'git fetch *', 'ask') is None


def test_a_requested_deny_outranks_a_broader_earlier_allow(runtime: OpenCodeRuntime, list_settings: pathlib.Path):
    """Under last-match-wins an inserted deny must actually decide the (action, resource)."""
    settings = _load(list_settings)
    settings['permissions'].append({'action': 'shell', 'resource': 'git *', 'effect': 'allow'})
    list_settings.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')

    result = runtime.permission_fix('project', 'ensure', ['deny(git push *)'], False)

    assert parse_toon(result)['added'] == 1
    rules = _load(list_settings)['permissions']
    assert _effective_effect(rules, 'shell', 'git push origin') == 'deny'
    assert _effective_effect(rules, 'shell', 'git status') == 'allow'


def test_fix_reports_io_error_when_the_list_write_fails(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A write that never reached disk must not be reported as a success."""
    monkeypatch.setattr(runtime, 'permission_save_settings', lambda *_args, **_kwargs: False)

    result = parse_toon(runtime.permission_fix('project', 'ensure', ['deny(git push *)'], False))

    assert result['status'] == 'error'
    assert result['error'] == 'io_error'


def test_fix_reports_io_error_when_the_map_write_fails(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """The legacy-map branch reports a failed write too, not a success with a count."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'bash': {}}}), encoding='utf-8')
    monkeypatch.setattr(runtime, 'permission_save_settings', lambda *_args, **_kwargs: False)

    result = parse_toon(runtime.permission_fix('project', 'ensure', ['deny(git push *)'], False))

    assert result['status'] == 'error'
    assert result['error'] == 'io_error'


def test_protect_path_writes_denies_into_the_permissions_list(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path, tmp_path: pathlib.Path
):
    protected = tmp_path / 'secrets'
    protected.mkdir()
    runtime.permission_fix('project', 'protect-path', [str(protected)], False)

    data = _load(list_settings)
    _assert_no_legacy_map(data)
    denies = [
        rule for rule in data['permissions'] if rule.get('effect') == 'deny' and rule.get('action') in {'shell', 'read'}
    ]
    assert denies, 'protect-path must write deny rules into the permissions list'
    assert any(rule['action'] == 'read' and '/**' in rule['resource'] for rule in denies)


# ---------------------------------------------------------------------------
# web permissions
# ---------------------------------------------------------------------------


def test_web_apply_and_analyze_use_the_permissions_list(runtime: OpenCodeRuntime, list_settings: pathlib.Path):
    runtime.permission_web_apply('project', add=['example.com'], remove=[], dry_run=False)

    data = _load(list_settings)
    _assert_no_legacy_map(data)
    assert _exact_index(data['permissions'], 'webfetch', '*', 'allow') is not None

    analyzed = parse_toon(runtime.permission_web_analyze('project'))
    assert analyzed['webfetch_permission'] == 'allow'


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------


def test_health_permissions_reads_the_permissions_list(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """The health check's executor probe sees a list-shaped allow."""
    settings = _load(list_settings)
    settings['permissions'].append(
        {'action': 'shell', 'resource': 'python3 .plan/execute-script.py *', 'effect': 'allow'}
    )
    list_settings.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')

    result = parse_toon(runtime.health_check('permissions'))
    permissions = next(check for check in result['results'] if check['check'] == 'permissions')
    assert permissions['healthy'] is True
    assert 'executor permission' in permissions['detail']


def test_default_permissions_constant_is_not_empty() -> None:
    """Vacuity guard: an empty default set would make the assertions above hollow."""
    assert OPENCODE_DEFAULT_PERMISSIONS


# ---------------------------------------------------------------------------
# rule writer: conflicts and the evaluated action wildcard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('requested', ['ask(git push *)', 'allow(git push *)'])
def test_ensure_refuses_to_override_a_more_specific_later_deny(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, requested: str
):
    """A requested rule is never moved past a later, more specific deny.

    The list grants broadly, denies ``git push --force *``, then ends with a
    broader ``git *`` ask. Making ``git push *`` ask or allow effective would
    have to cross that deny, changing an outcome the caller did not name, so the
    write is a named conflict and the file is left byte-identical.
    """
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(
        json.dumps(
            {
                'permissions': [
                    {'action': 'shell', 'resource': '*', 'effect': 'allow'},
                    {'action': 'shell', 'resource': 'git push --force *', 'effect': 'deny'},
                    {'action': 'shell', 'resource': 'git *', 'effect': 'ask'},
                ]
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    before = config.read_bytes()

    result = parse_toon(runtime.permission_fix('project', 'ensure', [requested], False))

    assert result['status'] == 'error'
    assert result['error'] == 'permission_conflict'
    assert config.read_bytes() == before, 'a conflicting write must leave the file untouched'


def test_the_bare_shell_tool_names_the_shell_catch_all():
    """``shell`` is OpenCode 2's shell tool, not the literal command ``shell``."""
    assert to_opencode_grant('deny(shell)') == ('bash', '*', 'deny')


def test_a_wildcard_action_rule_decides_the_requested_effect(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """The action wildcard is evaluated, so a new allow has to outrank it."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(
        json.dumps({'permissions': [{'action': '*', 'resource': '*', 'effect': 'deny'}]}, indent=2) + '\n',
        encoding='utf-8',
    )

    result = parse_toon(runtime.permission_fix('project', 'ensure', ['allow(read)'], False))

    assert result['status'] == 'success'
    rules = _load(config)['permissions']
    assert _effective_effect_any_action(rules, 'read', '/tmp/x') == 'allow'


def test_an_opencode1_map_write_maps_subagent_to_task(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """An OpenCode 1 map knows ``task``, so a ``subagent`` grant is written as ``task``."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'bash': {}}}), encoding='utf-8')

    result = parse_toon(runtime.permission_fix('project', 'ensure', ['subagent'], False))

    assert result['status'] == 'success'
    perm = _load(config)['permission']
    assert perm.get('task') == 'allow'
    assert 'subagent' not in perm


def test_configure_maps_subagent_to_the_map_task_key(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """``permission configure`` writes the same map key the fix verbs do."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'bash': {}}}), encoding='utf-8')

    parse_toon(runtime.permission_configure('project', [{'rule': 'subagent'}]))

    perm = _load(config)['permission']
    assert perm.get('task') == 'allow'
    assert 'subagent' not in perm


def test_fix_remove_maps_subagent_to_the_map_task_key(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """Removing a ``subagent`` grant deletes the ``task`` key it was written as."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'bash': {}, 'task': 'allow'}}), encoding='utf-8')

    result = parse_toon(runtime.permission_fix('project', 'remove', ['subagent'], False))

    assert result['removed'] == 1
    assert 'task' not in _load(config)['permission']


def test_fix_remove_drops_only_the_named_map_pattern(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A map's other rows survive a removal that names one pattern."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(
        json.dumps({'permission': {'read': {'old.md': 'allow', '/etc/shadow': 'deny'}}}), encoding='utf-8'
    )

    result = parse_toon(runtime.permission_fix('project', 'remove', ['Read(old.md)'], False))

    assert result['removed'] == 1
    assert _load(config)['permission']['read'] == {'/etc/shadow': 'deny'}


def test_fix_ensure_keeps_a_pattern_map(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A category catch-all becomes the map's own ``*`` row, never a replacement map."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'read': {'/etc/shadow': 'deny'}}}), encoding='utf-8')

    runtime.permission_fix('project', 'ensure', ['read'], False)

    assert _load(config)['permission']['read'] == {'/etc/shadow': 'deny', '*': 'allow'}


def test_a_bare_task_grant_on_a_map_file_writes_task(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A ``task`` grant is already the OpenCode 1 name and keeps it."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(json.dumps({'permission': {'bash': {}}}), encoding='utf-8')

    runtime.permission_fix('project', 'ensure', ['task'], False)

    assert _load(config)['permission'].get('task') == 'allow'


# ---------------------------------------------------------------------------
# unreadable input and failed writes are reported
# ---------------------------------------------------------------------------


def test_an_unparsable_config_is_reported_and_left_untouched(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A config that does not parse is never loaded as an error skeleton and written over."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text('not json', encoding='utf-8')

    result = parse_toon(runtime.permission_fix('project', 'ensure', ['deny(git push *)'], False))

    assert result['status'] == 'error'
    assert result['error'] == 'load_error'
    assert config.read_text(encoding='utf-8') == 'not json'


def test_a_non_utf8_config_returns_the_loader_error(runtime: OpenCodeRuntime, tmp_path: pathlib.Path):
    """Undecodable bytes are a failed read, not an empty settings object."""
    config = tmp_path / 'opencode.json'
    config.write_bytes(b'\xff\xfe{"permissions": []}')

    loaded = runtime.permission_load_settings(str(config))

    assert 'error' in loaded


def test_ensure_defaults_reports_a_failed_save(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A defaults write that never reached disk carries an error, not just ``applied: False``."""
    monkeypatch.setattr(runtime, 'permission_save_settings', lambda *_args, **_kwargs: False)
    settings = runtime.permission_load_settings(str(list_settings))

    result = runtime.permission_ensure_defaults(settings, str(list_settings), dry_run=False)

    assert result['applied'] is False
    assert 'error' in result


def test_project_initial_setup_reports_an_unparsable_config(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """Setup surfaces the permission write it used to discard."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text('not json', encoding='utf-8')

    result = parse_toon(runtime.project_initial_setup(str(tmp_path), 'opencode'))

    assert result['status'] == 'error'
    assert result['error'] == 'permission_write_failed'
    assert config.read_text(encoding='utf-8') == 'not json'


def test_ensure_wildcards_does_not_wrap_a_failed_result(
    runtime: OpenCodeRuntime, list_settings: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """A failed defaults write is an error envelope, never a success one."""
    monkeypatch.setattr(runtime, 'permission_save_settings', lambda *_args, **_kwargs: False)

    result = parse_toon(runtime.permission_ensure_wildcards('project', str(list_settings.parent), False))

    assert result['status'] == 'error'
    assert result['error'] == 'io_error'


# ---------------------------------------------------------------------------
# one deny reader
# ---------------------------------------------------------------------------


def test_both_deny_readers_report_the_same_hybrid_deny_set():
    """A file carrying both shapes reports its list denies and its map denies."""
    from opencode_runtime import _deny_rules, _deny_rules_from_config

    config = {
        'permissions': [{'action': 'shell', 'resource': '*', 'effect': 'allow'}],
        'permission': {'bash': {'rm *': 'deny'}},
    }

    from_list = {(rule['action'], rule['resource']) for rule in _deny_rules(config)}
    from_config = set(_deny_rules_from_config(config))

    assert from_list == from_config
    assert ('bash', 'rm *') in from_list


def test_both_deny_readers_report_an_agent_scoped_deny():
    """An ``agents.*.permissions`` deny is a deny at both entry points."""
    from opencode_runtime import _deny_rules, _deny_rules_from_config

    config = {
        'permissions': [],
        'agents': {'b': {'permissions': [{'action': 'shell', 'resource': 'gh *', 'effect': 'deny'}]}},
    }

    from_list = {(rule['action'], rule['resource']) for rule in _deny_rules(config)}
    from_config = set(_deny_rules_from_config(config))

    assert from_list == from_config
    assert ('shell', 'gh *') in from_list


# ---------------------------------------------------------------------------
# the action wildcard decides, and the writer reports what it cannot do
# ---------------------------------------------------------------------------


def test_the_action_wildcard_decides_the_effective_effect():
    """A rule whose ``action`` is ``*`` decides every action, so it must be matched."""
    from opencode_runtime import _effective_rule_effect

    rules = [{'action': '*', 'resource': '*', 'effect': 'deny'}]

    assert _effective_rule_effect(rules, 'read', '/tmp/x') == 'deny'
    assert _effective_rule_effect(rules, 'shell', 'git status') == 'deny'


def test_remove_reports_the_wildcard_action_rule_it_cannot_remove(
    runtime: OpenCodeRuntime, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
):
    """Removing the named grant would not remove the effect, so it is a named reason."""
    monkeypatch.chdir(tmp_path)
    config = tmp_path / 'opencode.json'
    config.write_text(
        json.dumps({'permissions': [{'action': '*', 'resource': '*', 'effect': 'deny'}]}), encoding='utf-8'
    )
    before = config.read_bytes()

    result = parse_toon(runtime.permission_fix('project', 'remove', ['deny(read)'], False))

    assert result['status'] == 'error'
    assert result['error'] == 'wildcard_action_rule'
    assert config.read_bytes() == before
