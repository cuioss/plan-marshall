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
