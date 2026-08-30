#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process ``main()`` dispatcher tests for ``manage-findings.py``.

The existing ``test_manage_findings.py`` exercises the ``cmd_*`` handlers
directly and drives the CLI plumbing through subprocess (``run_script``).
Subprocess runs do not contribute to coverage, so the entire ``main()``
argparse-builder + dispatch surface (every subparser, ``set_defaults(func=...)``
wiring, and ``output_toon`` emission) was uncovered.

These tests invoke the module's ``main()`` in-process with a patched
``sys.argv`` so coverage records the dispatcher. Each test asserts the
real CLI contract: routing to the correct handler, the TOON payload content,
the error discriminator, or the argparse exit code — never coverage-only
padding.
"""

from __future__ import annotations

import argparse
import sys
from argparse import Namespace

import pytest
from toon_parser import parse_toon

from conftest import load_script_module

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'mf-cli-add',
    'mf-cli-assess',
    'mf-cli-badtype',
    'mf-cli-ev',
    'mf-cli-get',
    'mf-cli-getmiss',
    'mf-cli-list',
    'mf-cli-promote',
    'mf-cli-qg',
    'mf-cli-qgclear',
    'mf-cli-qgres',
    'mf-cli-resolve',
)

# Distinct sys.modules name so this in-process load never clobbers the
# 'manage_findings' module the sibling test file registers.
_mod = load_script_module('plan-marshall', 'manage-findings', 'manage-findings.py', 'manage_findings_maincli')


def _run_main(monkeypatch, capsys, argv):
    """Drive ``main()`` with a patched argv and return (exit_code, stdout).

    ``main`` is wrapped by ``@safe_main`` which always calls ``sys.exit(...)``,
    so the call always raises ``SystemExit``; the wrapped return value is the
    exit code. argparse reads the process-global ``sys.argv``.
    """
    monkeypatch.setattr(sys, 'argv', ['manage-findings', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if exc.value.code is not None else 0
    captured = capsys.readouterr()
    return code, captured.out


# =============================================================================
# ``--any-checkout`` write-authority contract, DERIVED from the parser tree
# =============================================================================
#
# ``--any-checkout`` lets a read verb adopt the findings store of whichever
# checkout currently holds the plan directory. Its whole safety property is a
# SET: it is declared on five read verbs and on no write verb, so a caller in
# one checkout can never obtain WRITE authority over a plan living in another.
#
# That set was asserted nowhere. It was stated in the module docstring — a
# hand-maintained mirror of the argparse surface — and the docstring itself
# names the failure mode ("a roster has to be re-derived from the argparse
# surface on every verb added, and that is what drifts"). Nothing failed when a
# future verb picked up the flag.
#
# The population below is therefore DERIVED from the built parser tree, which is
# the authoritative source: the flag's presence set IS what argparse was told,
# not what a comment says it was told. The literal roster is the EXPECTATION
# side of the comparison only — it is never the population being measured.


#: The read verbs permitted to adopt another checkout's findings store.
_ANY_CHECKOUT_READ_VERBS = frozenset(
    {
        'list',
        'get',
        'qgate list',
        'assessment list',
        'assessment get',
    }
)


def _capture_built_parser(monkeypatch) -> argparse.ArgumentParser:
    """Return the fully-built root parser that ``main()`` constructs.

    ``main`` hands its parser to the module-level ``parse_args_with_toon_errors``
    seam, so substituting that ONE name yields the real, fully-populated tree
    with no production change and no reliance on a parser factory that does not
    exist. The substitute returns a namespace carrying no ``func``, which routes
    ``main`` down its own ``print_help`` branch instead of dispatching a verb —
    so nothing is executed and no store is touched.
    """
    captured: list[argparse.ArgumentParser] = []

    def _capture(parser: argparse.ArgumentParser) -> Namespace:
        captured.append(parser)
        return Namespace()

    monkeypatch.setattr(_mod, 'parse_args_with_toon_errors', _capture)
    monkeypatch.setattr(sys, 'argv', ['manage-findings'])
    with pytest.raises(SystemExit):
        _mod.main()

    assert len(captured) == 1, 'main() did not build exactly one root parser'
    return captured[0]


def _walk_verbs(parser, prefix=()):
    """Yield ``(verb_path, parser)`` for this node and every subparser beneath it.

    Intermediate group nodes (``qgate``, ``assessment``) are yielded too, not
    only leaves: a flag declared on a group parser would be inherited by nothing
    yet would still be a surface change, and the equality assertion should see it
    rather than walk past it.
    """
    yield ' '.join(prefix), parser
    for action in parser._actions:
        choices = getattr(action, 'choices', None)
        # A subparsers action's ``choices`` is the name -> parser map; an
        # ordinary ``choices=[...]`` argument's is a plain sequence of values.
        if not isinstance(choices, dict):
            continue
        for name, child in choices.items():
            if isinstance(child, argparse.ArgumentParser):
                yield from _walk_verbs(child, (*prefix, name))


def _declares_any_checkout(parser) -> bool:
    return any('--any-checkout' in action.option_strings for action in parser._actions)


def test_the_parser_walk_reaches_the_whole_verb_surface(monkeypatch):
    """Non-vacuity control for the derivation the next test asserts on.

    A set-guarding assertion computed over an empty or truncated population
    passes for the wrong reason: a walk that silently stopped at the root would
    observe no ``--any-checkout`` anywhere and would then be compared against a
    five-element expectation, failing loudly — but a walk that reached ONLY the
    five would compare equal while having examined nothing else. This pins that
    the walk descends both nested groups and reaches write verbs too, so the
    equality below is a statement about the whole surface.
    """
    paths = {path for path, _ in _walk_verbs(_capture_built_parser(monkeypatch))}

    assert 'add' in paths
    assert 'qgate add' in paths
    assert 'assessment add' in paths
    assert 'ingest' in paths
    assert len(paths) > len(_ANY_CHECKOUT_READ_VERBS)


def test_any_checkout_is_declared_on_exactly_the_five_read_verbs(monkeypatch):
    """The flag's presence set, read off argparse rather than off a comment.

    Equality — not containment — in both directions at once: a write verb that
    picked the flag up fails here, and a read verb that lost it fails here too.
    The second direction matters as much as the first, because a silently
    dropped ``--any-checkout`` turns a documented capability into an
    ``unrecognized arguments`` exit 2 at the call site.
    """
    parser = _capture_built_parser(monkeypatch)

    observed = {path for path, node in _walk_verbs(parser) if _declares_any_checkout(node)}

    assert observed == _ANY_CHECKOUT_READ_VERBS


def test_the_write_verbs_are_the_complement_and_the_complement_is_not_empty(monkeypatch):
    """The safety property, stated as the complement the module docstring claims.

    The docstring declines to keep a second roster of the write verbs, on the
    grounds that the guarantee is the COMPLEMENT of the five. That is only true
    if the complement is non-empty and contains the verbs that actually write —
    otherwise "no write verb has it" would hold vacuously over a surface with no
    write verbs on it.
    """
    parser = _capture_built_parser(monkeypatch)
    all_paths = {path for path, _ in _walk_verbs(parser)}

    complement = all_paths - _ANY_CHECKOUT_READ_VERBS

    assert complement, 'every walked verb declares --any-checkout; the complement claim is vacuous'
    assert {'add', 'resolve', 'promote', 'qgate add', 'assessment add'} <= complement


# =============================================================================
# Plan-scoped finding verbs
# =============================================================================


def test_main_add_emits_success_toon(plan_context, monkeypatch, capsys):
    """``add`` routes to cmd_add and emits a success TOON with a hash_id."""
    code, out = _run_main(
        monkeypatch,
        capsys,
        ['add', '--plan-id', 'mf-cli-add', '--type', 'bug', '--title', 'Boom', '--detail', 'stack trace'],
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['type'] == 'bug'
    assert 'hash_id' in data


def test_main_list_after_add_counts_findings(plan_context, monkeypatch, capsys):
    """``list`` routes to cmd_query and counts the findings just added."""
    _run_main(
        monkeypatch,
        capsys,
        ['add', '--plan-id', 'mf-cli-list', '--type', 'tip', '--title', 'T', '--detail', 'd'],
    )
    code, out = _run_main(monkeypatch, capsys, ['list', '--plan-id', 'mf-cli-list'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['total_count'] == 1


def test_main_get_existing_finding(plan_context, monkeypatch, capsys):
    """``get`` returns the seeded finding record by hash_id."""
    seed = _mod.cmd_add(
        Namespace(
            plan_id='mf-cli-get',
            type='bug',
            title='Findable',
            detail='d',
            file_path=None,
            line=None,
            component=None,
            module=None,
            rule=None,
            severity=None,
            author=None,
            kind=None,
            reviewed_commit_sha=None,
            bot_kind=None,
        )
    )
    hid = str(seed['hash_id'])

    code, out = _run_main(monkeypatch, capsys, ['get', '--plan-id', 'mf-cli-get', '--hash-id', hid])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    # Assert on the round-tripped title rather than the hash: parse_toon
    # int-coerces an all-digit hash, which would spuriously fail an equality
    # check. The successful lookup (status) already proves --hash-id routed.
    assert data['title'] == 'Findable'


def test_main_get_missing_finding_errors(plan_context, monkeypatch, capsys):
    """``get`` for an absent hash_id emits a not-found error TOON."""
    code, out = _run_main(monkeypatch, capsys, ['get', '--plan-id', 'mf-cli-getmiss', '--hash-id', 'abc123'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'error'
    assert 'not found' in data['message'].lower()


def test_main_resolve_finding(plan_context, monkeypatch, capsys):
    """``resolve`` routes to cmd_resolve and records the resolution."""
    seed = _mod.cmd_add(
        Namespace(
            plan_id='mf-cli-resolve',
            type='build-error',
            title='Compile',
            detail='d',
            file_path=None,
            line=None,
            component=None,
            module=None,
            rule=None,
            severity=None,
            author=None,
            kind=None,
            reviewed_commit_sha=None,
            bot_kind=None,
        )
    )
    hid = str(seed['hash_id'])

    code, out = _run_main(
        monkeypatch,
        capsys,
        ['resolve', '--plan-id', 'mf-cli-resolve', '--hash-id', hid, '--resolution', 'fixed', '--detail', 'patched'],
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['resolution'] == 'fixed'


def test_main_promote_finding(plan_context, monkeypatch, capsys):
    """``promote`` routes to cmd_promote and records the promotion target."""
    seed = _mod.cmd_add(
        Namespace(
            plan_id='mf-cli-promote',
            type='tip',
            title='Use DI',
            detail='d',
            file_path=None,
            line=None,
            component=None,
            module=None,
            rule=None,
            severity=None,
            author=None,
            kind=None,
            reviewed_commit_sha=None,
            bot_kind=None,
        )
    )
    hid = str(seed['hash_id'])

    code, out = _run_main(
        monkeypatch,
        capsys,
        ['promote', '--plan-id', 'mf-cli-promote', '--hash-id', hid, '--promoted-to', 'architecture'],
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['promoted_to'] == 'architecture'


# =============================================================================
# Q-Gate verbs
# =============================================================================


def test_main_qgate_add_and_list(plan_context, monkeypatch, capsys):
    """``qgate add`` then ``qgate list`` route to the nested action handlers."""
    add_code, _ = _run_main(
        monkeypatch,
        capsys,
        [
            'qgate', 'add', '--plan-id', 'mf-cli-qg', '--phase', '5-execute',
            '--source', 'qgate', '--type', 'triage', '--title', 'Gate finding', '--detail', 'd',
        ],
    )
    assert add_code == 0

    code, out = _run_main(monkeypatch, capsys, ['qgate', 'list', '--plan-id', 'mf-cli-qg', '--phase', '5-execute'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['phase'] == '5-execute'
    assert data['total_count'] == 1


def test_main_qgate_resolve(plan_context, monkeypatch, capsys):
    """``qgate resolve`` records the resolution for a seeded q-gate finding."""
    seed = _mod.cmd_qgate_add(
        Namespace(
            plan_id='mf-cli-qgres',
            phase='3-outline',
            source='qgate',
            type='triage',
            title='Coverage gap',
            detail='d',
            file_path=None,
            component=None,
            severity=None,
            iteration=None,
            rule=None,
            raw_input=None,
            raw_input_max_bytes=_mod.DEFAULT_RAW_INPUT_MAX_BYTES,
        )
    )
    hid = str(seed['hash_id'])

    code, out = _run_main(
        monkeypatch,
        capsys,
        [
            'qgate', 'resolve', '--plan-id', 'mf-cli-qgres', '--hash-id', hid,
            '--resolution', 'taken_into_account', '--phase', '3-outline',
        ],
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['resolution'] == 'taken_into_account'


def _seed_qgate_with_file(plan_id, phase, title, file_path):
    """Seed one q-gate finding carrying a file_path via the cmd handler."""
    return _mod.cmd_qgate_add(
        Namespace(
            plan_id=plan_id,
            phase=phase,
            source='qgate',
            type='bug',
            title=title,
            detail='d',
            file_path=file_path,
            component=None,
            severity=None,
            iteration=None,
            rule=None,
            raw_input=None,
            raw_input_max_bytes=_mod.DEFAULT_RAW_INPUT_MAX_BYTES,
        )
    )


def test_main_qgate_resolve_evidenced_changed_path_shape(plan_context, monkeypatch, capsys):
    """The verb's value proposition IS the repeatable ``--changed-path`` input
    shape — its first boundary test drives that exact shape through the CLI entry
    point. A file in the set is resolved `fixed`; one outside it stays `pending`."""
    _seed_qgate_with_file('mf-cli-ev', '6-finalize', 'defect at src/hit.py:1', 'src/hit.py')
    _seed_qgate_with_file('mf-cli-ev', '6-finalize', 'defect at src/miss.py:1', 'src/miss.py')

    code, out = _run_main(
        monkeypatch,
        capsys,
        [
            'qgate', 'resolve-evidenced', '--plan-id', 'mf-cli-ev', '--phase', '6-finalize',
            '--changed-path', 'src/hit.py', '--changed-path', 'src/other.py',
            '--evidence-sha', 'abc123',
        ],
    )
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    resolved_files = {e['file_path'] for e in data['resolved']}
    left_files = {e['file_path'] for e in data['left_pending']}
    assert resolved_files == {'src/hit.py'}
    assert left_files == {'src/miss.py'}


def test_main_qgate_clear(plan_context, monkeypatch, capsys):
    """``qgate clear`` removes every pending finding for the phase."""
    _run_main(
        monkeypatch,
        capsys,
        [
            'qgate', 'add', '--plan-id', 'mf-cli-qgclear', '--phase', '4-plan',
            '--source', 'qgate', '--type', 'triage', '--title', 'F1', '--detail', 'd',
        ],
    )
    code, out = _run_main(monkeypatch, capsys, ['qgate', 'clear', '--plan-id', 'mf-cli-qgclear', '--phase', '4-plan'])
    assert code == 0
    data = parse_toon(out)
    assert data['status'] == 'success'
    assert data['cleared'] == 1


# =============================================================================
# Assessment verbs
# =============================================================================


def test_main_assessment_add_list_get_clear(plan_context, monkeypatch, capsys):
    """The full assessment lifecycle routes through the nested action handlers."""
    pid = 'mf-cli-assess'

    # add via main() (exercises the assessment-add route)
    add_code, add_out = _run_main(
        monkeypatch,
        capsys,
        [
            'assessment', 'add', '--plan-id', pid, '--file-path', 'src/foo.py',
            '--certainty', 'CERTAIN_INCLUDE', '--confidence', '80', '--agent', 'analyzer',
        ],
    )
    assert add_code == 0
    assert parse_toon(add_out)['status'] == 'success'

    # list (filter by certainty) via main()
    list_code, list_out = _run_main(
        monkeypatch, capsys, ['assessment', 'list', '--plan-id', pid, '--certainty', 'CERTAIN_INCLUDE']
    )
    assert list_code == 0
    assert parse_toon(list_out)['status'] == 'success'

    # get via main(): seed a second assessment through the direct handler so the
    # hash_id is a reliable string (parse_toon int-coerces all-digit hashes).
    seed = _mod.cmd_assessment_add(
        Namespace(
            plan_id=pid,
            file_path='src/bar.py',
            certainty='UNCERTAIN',
            confidence=40,
            agent='analyzer',
            detail=None,
            evidence=None,
        )
    )
    hid = str(seed['hash_id'])
    get_code, get_out = _run_main(monkeypatch, capsys, ['assessment', 'get', '--plan-id', pid, '--hash-id', hid])
    assert get_code == 0
    assert parse_toon(get_out)['status'] == 'success'

    # clear via main()
    clear_code, clear_out = _run_main(monkeypatch, capsys, ['assessment', 'clear', '--plan-id', pid])
    assert clear_code == 0
    assert parse_toon(clear_out)['status'] == 'success'


# =============================================================================
# Argparse boundary / dispatcher error paths
# =============================================================================


def test_main_missing_subcommand_exits_2(plan_context, monkeypatch, capsys):
    """No subcommand → argparse required-subparser error exits with code 2."""
    code, _ = _run_main(monkeypatch, capsys, [])
    assert code == 2


def test_main_invalid_type_choice_exits_2(plan_context, monkeypatch, capsys):
    """``add --type <not-a-type>`` → argparse invalid-choice error exits 2."""
    code, _ = _run_main(
        monkeypatch,
        capsys,
        ['add', '--plan-id', 'mf-cli-badtype', '--type', 'not-a-type', '--title', 't', '--detail', 'd'],
    )
    assert code == 2


def test_main_qgate_missing_action_exits_2(plan_context, monkeypatch, capsys):
    """``qgate`` with no nested action → required-action error exits 2."""
    code, _ = _run_main(monkeypatch, capsys, ['qgate'])
    assert code == 2
