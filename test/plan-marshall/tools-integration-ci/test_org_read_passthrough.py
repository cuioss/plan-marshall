#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Passthrough tests for the org-wide and foreign-repository read verbs.

The four verbs — ``org list-repos``, ``org search-code``, ``repo file read`` and
``repo label list`` — are registered in the SHARED ``ci_base.build_parser``, so
the properties under test belong to the abstraction:

a. **The shared parser accepts each verb** with its declared required flags, and
   ``org`` is a known router token so a pre-verb ``--plan-id`` is consumed as the
   routing flag.
b. **Dispatch reaches the GitHub handler** for each verb through the real
   ``github_ops.main`` handler map.
c. **The GitLab arm refuses each verb** with ``error: not_supported`` — never an
   empty success and never an unrecognised-subcommand parser error.

Modules are imported plainly (not through ``conftest.load_script_module``) for
the reason ``test_not_triggered_passthrough.py`` records: ``ci_base`` carries
process-global state every provider reads, and a second copy of it would be
inspected while the providers read the first. The autouse fixture restores that
state around every test.
"""

import argparse
import sys

import ci_base
import github_ops
import gitlab_ops
import pytest

#: Each verb's argv (after the provider script name) and its dispatch key.
_VERBS: dict[str, tuple[list[str], tuple[str, ...]]] = {
    'org list-repos': (['org', 'list-repos', '--org', 'cuioss'], ('org', 'list-repos')),
    'org search-code': (['org', 'search-code', '--org', 'cuioss', '--query', 'x'], ('org', 'search-code')),
    'repo file read': (['repo', 'file', 'read', '--repo', 'o/r', '--path', 'a.yml'], ('repo', 'file', 'read')),
    'repo label list': (['repo', 'label', 'list', '--repo', 'o/r'], ('repo', 'label', 'list')),
}

#: The GitHub handler function each verb dispatches to.
_GITHUB_HANDLER = {
    'org list-repos': 'cmd_org_list_repos',
    'org search-code': 'cmd_org_search_code',
    'repo file read': 'cmd_repo_file_read',
    'repo label list': 'cmd_repo_label_list',
}


@pytest.fixture(autouse=True)
def _restore_ci_base_globals():
    """Snapshot and restore ci_base's process-global subcommand cache and default cwd."""
    cached_tokens = ci_base._KNOWN_SUBCOMMANDS_CACHE
    cached_cwd = ci_base.get_default_cwd()
    yield
    ci_base._KNOWN_SUBCOMMANDS_CACHE = cached_tokens
    ci_base.set_default_cwd(cached_cwd)


def test_the_handler_table_covers_every_verb_under_test():
    """The two tables above describe the same verb population."""
    assert set(_VERBS) == set(_GITHUB_HANDLER)


@pytest.mark.parametrize('verb', sorted(_VERBS))
def test_the_shared_parser_accepts_the_verb(verb):
    """Each verb parses off the shared builder with its required flags."""
    parser, *_ = ci_base.build_parser('test')

    args = parser.parse_args(_VERBS[verb][0])

    assert args.command == _VERBS[verb][1][0]


@pytest.mark.parametrize(
    'argv',
    [
        ['org', 'list-repos'],
        ['org', 'search-code', '--org', 'cuioss'],
        ['repo', 'file', 'read', '--repo', 'o/r'],
        ['repo', 'file', 'read', '--path', 'a.yml'],
    ],
    ids=['list-repos-no-org', 'search-code-no-query', 'file-read-no-path', 'file-read-no-repo'],
)
def test_required_flags_are_enforced(argv):
    """Omitting a required flag is an argparse rejection, not a defaulted target."""
    parser, *_ = ci_base.build_parser('test')

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(argv)

    assert excinfo.value.code == 2


def test_org_is_a_known_router_token_so_a_pre_verb_plan_id_is_routing():
    """``org`` bootstraps into the known-subcommand set from the shared parser."""
    ci_base._KNOWN_SUBCOMMANDS_CACHE = None

    pre, post = ci_base._split_at_subcommand(['--plan-id', 'P', 'org', 'list-repos', '--org', 'x'])

    assert 'org' in ci_base.get_known_subcommands()
    assert pre == ['--plan-id', 'P']
    assert post[0] == 'org'


@pytest.mark.parametrize('verb', sorted(_VERBS))
def test_github_dispatch_reaches_the_verb_handler(monkeypatch, capsys, verb):
    """``github_ops.main`` routes each verb to its handler through the real handler map."""
    calls: list = []

    def _stub(args: argparse.Namespace) -> dict:
        calls.append(args)
        return {'status': 'success', 'operation': 'stubbed'}

    # main() binds the handler names at call time from its own module globals.
    monkeypatch.setattr(github_ops, _GITHUB_HANDLER[verb], _stub)
    monkeypatch.setattr(sys, 'argv', ['github_ops.py', *_VERBS[verb][0]])

    rc = github_ops.main()

    assert rc == 0
    assert len(calls) == 1
    assert 'operation: stubbed' in capsys.readouterr().out


@pytest.mark.parametrize('verb', sorted(_VERBS))
def test_gitlab_refuses_the_verb_as_not_supported(monkeypatch, capsys, verb):
    """GitLab answers each verb with ``error: not_supported`` — not a parser error or success."""
    monkeypatch.setattr(sys, 'argv', ['gitlab_ops.py', *_VERBS[verb][0]])

    rc = gitlab_ops.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert 'status: error' in out
    assert f'error: {ci_base.ERROR_NOT_SUPPORTED}' in out
    assert 'provider: gitlab' in out
    assert 'Unknown subcommand' not in out


def test_make_not_supported_is_never_a_success_envelope():
    """The shared refusal builder always yields ``status: error`` with the token."""
    result = ci_base.make_not_supported('org_list_repos', 'gitlab', 'why')

    assert result == {
        'status': 'error',
        'operation': 'org_list_repos',
        'error': 'not_supported',
        'provider': 'gitlab',
        'message': 'why',
    }
