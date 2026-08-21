#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the misplaced-router-flag argparse message (D6).

A top-level router flag (declared on the root parser, ahead of the subparsers)
is accepted by argparse only BEFORE the subcommand. Placed after the verb it is
rejected with ``unrecognized arguments: --flag`` — a message that names the flag
but reads as "this flag does not exist", sending the caller to search an argparse
table the flag is (correctly) absent from at that level. The augmented message
states the flag exists and belongs before the verb.
"""

import argparse

import pytest
from input_validation import (  # noqa: I001
    _augment_misplaced_router_flag,
    _root_router_option_strings,
    parse_args_with_toon_errors,
)


def _build_parser() -> argparse.ArgumentParser:
    """A parser shaped like manage-architecture: root router flags + subparsers."""
    parser = argparse.ArgumentParser(prog='architecture', allow_abbrev=False)
    parser.add_argument('--project-dir', default='.')
    parser.add_argument('--plan-id')
    subs = parser.add_subparsers(dest='command', required=True)
    find = subs.add_parser('find', allow_abbrev=False)
    find.add_argument('--pattern', required=True)
    return parser


# ---------------------------------------------------------------------------
# _root_router_option_strings — root flags only, not subparser flags or help.
# ---------------------------------------------------------------------------
def test_root_router_option_strings_collects_root_flags_only():
    flags = _root_router_option_strings(_build_parser())
    assert '--project-dir' in flags
    assert '--plan-id' in flags
    assert '--pattern' not in flags  # subparser flag, not a router flag
    assert '--help' not in flags and '-h' not in flags  # help is not a router flag


# ---------------------------------------------------------------------------
# _augment_misplaced_router_flag — names the fix; leaves other errors alone.
# ---------------------------------------------------------------------------
def test_augment_names_router_flag_belongs_before_verb():
    flags = _root_router_option_strings(_build_parser())
    augmented = _augment_misplaced_router_flag('unrecognized arguments: --project-dir .', flags, 'architecture')
    assert '--project-dir' in augmented
    assert 'belongs BEFORE the subcommand' in augmented
    assert 'The flag exists' in augmented


def test_augment_handles_equals_form():
    flags = _root_router_option_strings(_build_parser())
    augmented = _augment_misplaced_router_flag('unrecognized arguments: --project-dir=.', flags, 'architecture')
    assert 'belongs BEFORE the subcommand' in augmented


def test_augment_leaves_genuinely_unknown_flag_unchanged():
    flags = _root_router_option_strings(_build_parser())
    message = 'unrecognized arguments: --totally-bogus'
    assert _augment_misplaced_router_flag(message, flags, 'architecture') == message


def test_augment_leaves_non_unrecognized_error_unchanged():
    flags = _root_router_option_strings(_build_parser())
    message = 'the following arguments are required: --pattern'
    assert _augment_misplaced_router_flag(message, flags, 'architecture') == message


# ---------------------------------------------------------------------------
# End-to-end through parse_args_with_toon_errors.
# ---------------------------------------------------------------------------
def test_router_flag_after_verb_is_rejected_with_helpful_note(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['architecture', 'find', '--pattern', '*.py', '--project-dir', '.'])
    with pytest.raises(SystemExit) as excinfo:
        parse_args_with_toon_errors(_build_parser())
    assert excinfo.value.code == 2  # argparse's rejection exit code, preserved
    stderr = capsys.readouterr().err
    assert '--project-dir' in stderr
    assert 'belongs BEFORE the subcommand' in stderr


def test_router_flag_before_verb_parses_cleanly(monkeypatch):
    monkeypatch.setattr('sys.argv', ['architecture', '--project-dir', '.', 'find', '--pattern', '*.py'])
    namespace = parse_args_with_toon_errors(_build_parser())
    assert namespace.command == 'find'
    assert namespace.project_dir == '.'
    assert namespace.pattern == '*.py'


def test_genuinely_unknown_flag_after_verb_gets_no_router_note(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['architecture', 'find', '--pattern', '*.py', '--nope', 'x'])
    with pytest.raises(SystemExit) as excinfo:
        parse_args_with_toon_errors(_build_parser())
    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert 'belongs BEFORE the subcommand' not in stderr


# ---------------------------------------------------------------------------
# The worked example is built from the caller's own argv, through the
# repository's script-execution convention.
# ---------------------------------------------------------------------------
def test_example_renders_the_callers_real_verb_and_moves_the_flag(monkeypatch, capsys):
    """The note prints a runnable command, not a ``<subcommand>`` placeholder.

    The verb was in the failing argv all along, so a placeholder puts the reader
    back where argparse's raw message left them.
    """
    monkeypatch.setattr(
        'sys.argv', ['architecture', 'find', '--pattern', '*.py', '--project-dir', '/repo']
    )
    with pytest.raises(SystemExit):
        parse_args_with_toon_errors(
            _build_parser(), notation='plan-marshall:manage-architecture:architecture'
        )

    stderr = capsys.readouterr().err

    # ``'*.py'`` is QUOTED, and that is the point: the example is meant to be
    # copied and run, and a bare ``--pattern *.py`` would be glob-expanded by the
    # shell into matching filenames before the script ever saw it. The note's
    # whole claim is that it prints the caller's own command with the flag moved,
    # so a command that means something different when pasted breaks the claim.
    assert (
        'python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture '
        "--project-dir /repo find --pattern '*.py'" in stderr
    )
    assert '<subcommand>' not in stderr


def test_example_uses_the_executor_convention_not_a_bare_script_filename():
    """With a notation supplied, the example names no bare ``*.py`` script.

    ``parser.prog`` is the bare script filename for most marketplace scripts —
    an invocation the script-execution convention forbids and no caller may run.
    """
    flags = _root_router_option_strings(_build_parser())

    augmented = _augment_misplaced_router_flag(
        'unrecognized arguments: --plan-id p1',
        flags,
        'architecture.py',
        notation='plan-marshall:manage-architecture:architecture',
        argv=['find', '--pattern', '*.py', '--plan-id', 'p1'],
    )

    example = augmented.rsplit('e.g. `', 1)[1].rstrip('`.')
    assert example.startswith('python3 .plan/execute-script.py ')
    assert 'architecture.py' not in example
    # Quoted for the reason given in the sibling test above: an unquoted glob is
    # a different command once the shell has seen it.
    assert example.endswith("--plan-id p1 find --pattern '*.py'")


def test_example_falls_back_to_prog_when_no_notation_is_supplied():
    """The fallback is documented and still produces a note.

    Without a notation there is nothing better than ``prog`` to name; the point
    is that a caller CAN supply one, not that the fallback disappears.
    """
    flags = _root_router_option_strings(_build_parser())

    augmented = _augment_misplaced_router_flag(
        'unrecognized arguments: --plan-id p1',
        flags,
        'architecture',
        argv=['find', '--plan-id', 'p1'],
    )

    assert 'e.g. `architecture --plan-id p1 find`' in augmented


def test_equals_form_flag_moves_as_one_token():
    """``--flag=value`` is a single token and must not swallow a following one."""
    flags = _root_router_option_strings(_build_parser())

    augmented = _augment_misplaced_router_flag(
        'unrecognized arguments: --plan-id=p1',
        flags,
        'architecture',
        argv=['find', '--pattern', 'x', '--plan-id=p1'],
    )

    assert 'e.g. `architecture --plan-id=p1 find --pattern x`' in augmented


# ---------------------------------------------------------------------------
# The REAL CI parser — the surface the note previously could not reach.
# ---------------------------------------------------------------------------
def test_real_ci_parser_reports_a_router_flag_written_after_the_verb(monkeypatch, capsys):
    """Driven against ``ci_base.build_parser``, not a synthetic stand-in.

    ``ci.py`` consumes ``--plan-id`` / ``--project-dir`` with
    ``extract_routing_args`` BEFORE the provider parser is built, so the
    provider's root parser declares neither and ``_root_router_option_strings``
    returns an empty set — the note could never fire on the one surface these
    flags actually belong to. ``parse_ci_args`` names them explicitly.
    """
    import ci_base

    monkeypatch.setattr('sys.argv', ['ci', 'pr', 'view', '--pr-number', '7', '--plan-id', 'p1'])
    parser, *_ = ci_base.build_parser('CI operations')

    with pytest.raises(SystemExit) as excinfo:
        ci_base.parse_ci_args(parser)

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert '--plan-id' in stderr
    assert 'belongs BEFORE the subcommand' in stderr
    assert (
        'python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci '
        '--plan-id p1 pr view --pr-number 7' in stderr
    )


def test_real_ci_parser_without_the_router_flag_names_gets_no_note(monkeypatch, capsys):
    """The control: the note comes from the explicit names, not from the parser.

    Pins the mechanism the fix depends on — the CI root parser genuinely
    declares neither flag, so a run without ``extra_router_flags`` still gets
    argparse's bare rejection.
    """
    import ci_base
    from input_validation import parse_args_with_toon_errors as raw_parse

    monkeypatch.setattr('sys.argv', ['ci', 'pr', 'view', '--plan-id', 'p1'])
    parser, *_ = ci_base.build_parser('CI operations')
    assert _root_router_option_strings(parser) == set()

    with pytest.raises(SystemExit):
        raw_parse(parser)

    assert 'belongs BEFORE the subcommand' not in capsys.readouterr().err


def test_real_ci_parser_accepts_a_genuinely_unknown_flag_without_the_note(monkeypatch, capsys):
    """A flag that is not a router flag still gets argparse's plain rejection."""
    import ci_base

    monkeypatch.setattr('sys.argv', ['ci', 'pr', 'view', '--totally-bogus', 'x'])
    parser, *_ = ci_base.build_parser('CI operations')

    with pytest.raises(SystemExit):
        ci_base.parse_ci_args(parser)

    assert 'belongs BEFORE the subcommand' not in capsys.readouterr().err
