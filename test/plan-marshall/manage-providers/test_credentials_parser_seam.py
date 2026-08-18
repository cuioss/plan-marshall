#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the published parser seam on the credential-management CLI.

``credentials.py`` owns the parser for every subcommand the private ``_cred_*``
and ``_list_providers`` command modules implement. ``build_parser`` publishes it
at module level, so a namespace for one of those handlers is produced by the real
parser — carrying the ``--scope`` and ``--target`` defaults a hand-written one
omits — without executing ``main`` to reach it. These pin that seam, and that
``main`` parses with the same parser rather than a second declaration beside it.
"""

import pytest

from conftest import load_script_module, parse_ns

BUNDLE = 'plan-marshall'
SKILL = 'manage-providers'
SCRIPT = 'credentials.py'

#: One invocation per handler the private command modules expose, with the
#: defaults the parser supplies for the flags left off the command line.
SUBCOMMAND_DEFAULTS = [
    (('list-providers',), {'command': 'list-providers'}),
    (('find-by-category', '--category', 'ci'), {'command': 'find-by-category', 'category': 'ci'}),
    (('discover-and-persist',), {'command': 'discover-and-persist', 'providers': None}),
    (('ensure-denied',), {'command': 'ensure-denied', 'target': 'project'}),
    (('edit', '--skill', 'sonarqube'), {'command': 'edit', 'skill': 'sonarqube', 'scope': 'global'}),
    (('list',), {'command': 'list', 'scope': 'all'}),
]


@pytest.mark.parametrize(
    ('argv', 'expected'), SUBCOMMAND_DEFAULTS, ids=[argv[0] for argv, _ in SUBCOMMAND_DEFAULTS]
)
def test_seam_parses_each_subcommand_with_its_defaults(argv, expected):
    """The published seam parses each subcommand and applies the parser's own defaults."""
    namespace = parse_ns(BUNDLE, SKILL, SCRIPT, *argv)

    assert {key: getattr(namespace, key) for key in expected} == expected


def test_main_parses_with_the_published_parser(monkeypatch):
    """``main`` parses with ``build_parser``'s result rather than a second declaration.

    The seam is only trustworthy while it is the same parser production uses; a
    ``main`` that rebuilt its own could accept flags the seam never publishes, and
    a namespace taken from the seam would then describe a CLI that does not exist.
    """
    credentials = load_script_module(BUNDLE, SKILL, SCRIPT)
    calls = []

    def _record():
        calls.append('build_parser')
        raise SystemExit(0)

    monkeypatch.setattr(credentials, 'build_parser', _record)

    with pytest.raises(SystemExit):
        credentials.main()

    assert calls == ['build_parser']
