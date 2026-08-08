#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Passthrough tests for ``checks pull-request-runs`` across the CI abstraction.

Filed under ``tools-integration-ci`` rather than beside the GitHub provider tests
because the surface under test is the ABSTRACTION's: the shared
``ci_base.build_parser`` registration, the provider dispatch maps that consume it,
and the cross-provider contract that a verb registered in the shared parser
resolves to a real answer on every provider — a computed one where the observable
exists, an explicit refusal where it does not.

Three properties, each a different way the passthrough could be broken:

a. **The shared parser accepts the verb.** ``checks pull-request-runs --pr-number
   N`` parses, and ``--pr-number`` is genuinely required.
b. **Both entry points reach ONE handler.** The ``ci checks pull-request-runs``
   dispatch and the ``github_pr pull_request_runs`` verb are asserted to call the
   same shared ``github_ops.pull_request_runs_result``. This is the property that
   keeps two entry points from drifting into two implementations of one question —
   asserted by spying on the shared function rather than by comparing two outputs,
   because two independent implementations can agree on a fixture while disagreeing
   in general.
c. **The GitLab arm refuses explicitly.** ``build_parser`` is shared, so
   registering the verb for GitHub exposes the token on GitLab too. Without a
   handler entry, dispatch would report an unrecognised subcommand — misattributing
   a provider-coverage gap as a parser defect. The refusal must name the gap.

Every module is imported PLAINLY rather than through
``conftest.load_script_module``. That is load-bearing here above all: ``ci_base``
is imported by every provider script, and ``load_script_module`` re-registers
``sys.modules['ci_base']`` with a FRESH object — so the providers would keep
reading the ORIGINAL module's process-global state (the default cwd, the known-
subcommand cache) while this suite inspected a second, empty copy. That mismatch
does not fail locally in this file; it surfaces as unrelated identity failures in
sibling suites.

Driving a provider ``main()`` also touches ci_base's process-global subcommand
cache, so the ``_restore_ci_base_globals`` fixture below snapshots and restores it
around every test in this module.
"""

import argparse
import sys

import ci_base
import github_ops
import github_pr
import gitlab_ops
import pytest

_VERB = 'pull-request-runs'
_SNAKE_VERB = 'pull_request_runs'


@pytest.fixture(autouse=True)
def _restore_ci_base_globals():
    """Snapshot and restore ci_base's process-global state around each test.

    ``get_known_subcommands`` caches a module-global frozenset and
    ``set_default_cwd`` installs a module-global cwd for every provider
    subprocess. Both are mutated by importing a provider script and by driving its
    ``main()``. Leaking either into a sibling test is how a suite that passes alone
    fails in a full run — the registry leak makes ``_split_at_subcommand`` treat an
    unregistered token as known, and the cwd leak points a provider's CLI calls at
    the wrong tree.
    """
    cached_tokens = ci_base._KNOWN_SUBCOMMANDS_CACHE
    cached_cwd = ci_base.get_default_cwd()
    yield
    ci_base._KNOWN_SUBCOMMANDS_CACHE = cached_tokens
    ci_base.set_default_cwd(cached_cwd)


# ---------------------------------------------------------------------------
# (a) The shared parser accepts the verb
# ---------------------------------------------------------------------------


def test_the_shared_checks_parser_accepts_the_verb():
    """``checks pull-request-runs --pr-number N`` parses off the SHARED builder.

    Parsed through ``ci_base.build_parser`` itself, not a provider's copy, because
    the registration lives there and is what exposes the verb to both providers.
    """
    parser, _pr_sub, _checks_sub, _issue_sub, _branch_sub = ci_base.build_parser('test')

    args = parser.parse_args(['checks', _VERB, '--pr-number', '42'])

    assert args.command == 'checks'
    assert args.checks_command == _VERB
    assert args.pr_number == 42


def test_the_verb_is_registered_under_the_checks_noun_not_a_new_top_level():
    """The verb sits under ``checks``, alongside its siblings — not a fifth noun.

    Derived from the live parser's registered choices rather than asserted as a
    literal, so the membership claim tracks the parser.
    """
    _parser, _pr_sub, checks_sub, _issue_sub, _branch_sub = ci_base.build_parser('test')

    assert _VERB in checks_sub.choices
    # Its kebab-case sibling is the naming precedent this verb follows.
    assert 'wait-for-status-flip' in checks_sub.choices


def test_pr_number_is_required_on_the_verb():
    """Omitting ``--pr-number`` is an argparse rejection, not a defaulted PR.

    A defaulted or optional PR selector would let the verb answer about some other
    PR — or about none — while still reporting a confident observable.
    """
    parser, _pr_sub, _checks_sub, _issue_sub, _branch_sub = ci_base.build_parser('test')

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(['checks', _VERB])

    assert excinfo.value.code == 2


def test_the_verb_reaches_the_known_subcommand_registry():
    """The ``checks`` noun is a known router token, so routing flags split correctly.

    ``get_known_subcommands`` bootstraps from ``build_parser``'s top-level choices,
    which is what lets ``extract_routing_args`` tell a router-level ``--plan-id``
    from a subcommand-level one. Asserted via the derivation rather than a literal
    set so a future noun inherits the check.
    """
    assert 'checks' in ci_base.get_known_subcommands()


# ---------------------------------------------------------------------------
# (b) Both entry points reach ONE shared handler
# ---------------------------------------------------------------------------


def _spy_on_shared_handler(monkeypatch):
    """Replace the shared handler with a recording stub; return the call log."""
    calls: list = []

    def _spy(pr_number):
        calls.append(pr_number)
        return {
            'status': 'success',
            'operation': _SNAKE_VERB,
            'provider': 'github',
            'pr_number': pr_number,
            'not_triggered': False,
        }

    monkeypatch.setattr(github_ops, _SNAKE_VERB + '_result', _spy)
    return calls


def test_the_ci_checks_dispatch_reaches_the_shared_handler(monkeypatch, capsys):
    """Entry point 1: ``ci checks pull-request-runs`` routes into the shared handler.

    Driven through ``github_ops.main`` so the real dispatch map is exercised — the
    map is built inside ``main``, so asserting it any other way would assert a copy
    of the routing rather than the routing itself.
    """
    calls = _spy_on_shared_handler(monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['github_ops.py', 'checks', _VERB, '--pr-number', '7'])

    rc = github_ops.main()

    assert rc == 0
    assert calls == [7]
    assert f'operation: {_SNAKE_VERB}' in capsys.readouterr().out


def test_the_github_pr_verb_reaches_the_same_shared_handler(monkeypatch, capsys):
    """Entry point 2: ``github_pr pull_request_runs`` routes into the SAME handler.

    Together with the case above this is the anti-drift property: one shared body
    answers the question, so the abstraction verb and the provider verb cannot
    diverge. The snake_case spelling here matches its siblings (``fetch_findings`` /
    ``post_responses`` / ``bot_completion``) exactly as the kebab-case spelling
    matches the ``checks`` siblings — two spellings, one implementation.
    """
    calls = _spy_on_shared_handler(monkeypatch)
    monkeypatch.setattr(sys, 'argv', ['github_pr.py', _SNAKE_VERB, '--pr-number', '7'])

    github_pr.main()

    assert calls == [7]
    assert f'operation: {_SNAKE_VERB}' in capsys.readouterr().out


def test_the_github_pr_verb_delegates_rather_than_reimplementing(monkeypatch):
    """The provider verb's body is a delegation, asserted by the spy alone answering.

    With the shared handler stubbed out, the verb produces the stub's payload and
    nothing else. A second implementation living in ``github_pr`` would still return
    a plausible envelope here while the spy recorded no call — which is precisely
    the drift this asserts against.
    """
    calls = _spy_on_shared_handler(monkeypatch)

    result = github_pr.cmd_pull_request_runs(argparse.Namespace(pr_number=99))

    assert calls == [99]
    assert result['pr_number'] == 99


def test_the_snake_case_verb_is_a_known_subcommand_token():
    """``pull_request_runs`` is registered so routing-flag splitting stays correct.

    ``github_pr.py`` registers its top-level tokens with the shared registry; an
    unregistered token would make ``extract_routing_args`` mis-locate the
    subcommand boundary and consume a subcommand-level flag as a router flag.
    """
    assert _SNAKE_VERB in ci_base.get_known_subcommands()


# ---------------------------------------------------------------------------
# (c) The GitLab arm refuses explicitly
# ---------------------------------------------------------------------------


def test_the_gitlab_arm_returns_an_explicit_unsupported_refusal(monkeypatch, capsys):
    """GitLab answers with a NAMED refusal, never a generic unknown-subcommand error.

    The shared parser exposes the token on GitLab whether or not GitLab implements
    it. An unregistered handler would surface as an unrecognised-subcommand error,
    which sends a reader hunting for a parser bug instead of telling them the
    provider does not implement the observable. The refusal is asserted to name both
    the operation and the reason.
    """
    monkeypatch.setattr(sys, 'argv', ['gitlab_ops.py', 'checks', _VERB, '--pr-number', '7'])

    rc = gitlab_ops.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert 'status: error' in out
    assert f'operation: {_SNAKE_VERB}' in out
    # The refusal names the gap rather than reporting a parser failure.
    assert 'unsupported on GitLab' in out
    assert 'unrecognized arguments' not in out
    assert 'invalid choice' not in out


def test_the_gitlab_refusal_never_reports_a_participation_verdict(monkeypatch):
    """The refusal carries no observable — an unimplemented arm claims nothing.

    A GitLab refusal that carried ``not_triggered`` in any form would let the
    unimplemented provider feed the participation classifier a fabricated PR-wide
    state.
    """
    result = gitlab_ops.cmd_checks_pull_request_runs(argparse.Namespace(pr_number=7))

    assert result['status'] == 'error'
    assert 'not_triggered' not in result
    assert 'has_pull_request_run' not in result


def test_both_providers_register_the_verb_so_neither_falls_through():
    """Both dispatch maps carry the key — the cross-provider completeness claim.

    Asserted by driving each provider's ``main`` above; this case pins the
    structural reason those pass, namely that the shared-parser token has a handler
    on BOTH sides. A provider that registered the parser entry without a handler is
    the exact asymmetry that produces a misleading parser error.
    """
    for module in (github_ops, gitlab_ops):
        assert hasattr(module, 'cmd_checks_pull_request_runs'), module.__name__
