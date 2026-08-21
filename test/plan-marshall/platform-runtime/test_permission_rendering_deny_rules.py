#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the deny rules that protect a directory from being read.

The permission DSL is a target wire format, so it is rendered inside
``claude_runtime`` and never crosses the runtime boundary. The exact strings it
renders are the observable contract: they land in an operator's settings file
and a permission that changes spelling stops matching what it guards.

Expectations here are literals rather than values derived from the renderer. An
expectation computed by the code under test agrees with it by construction and
holds against any rewrite, which is exactly what a byte-level pin must not do.
The one value that cannot be a literal is the home directory, which differs per
machine.

conftest.py sets up PYTHONPATH so the cross-skill imports resolve without manual
sys.path manipulation.
"""
from pathlib import Path

import claude_runtime

# =============================================================================
# The credential-protection deny rules
# =============================================================================


class TestProtectPathDenyRules:
    """``_protect_path_deny_rules`` renders one pinned rule set per protected path."""

    def test_rules_are_the_pinned_set_for_a_directory_under_home(self) -> None:
        home = claude_runtime.resolve_home()
        protected = home / '.plan-marshall' / 'credentials'
        vectors = ('cat', 'head', 'tail', 'less', 'more', 'cp', 'grep', 'base64')

        expected = [
            'Read(~/.plan-marshall/credentials/**)',
            f'Read({protected}/**)',
        ]
        for vector in vectors:
            expected.append(f'Bash({vector} ~/.plan-marshall/credentials/*)')
            expected.append(f'Bash({vector} {protected}/*)')
        expected.append('Bash(python3 -c *.plan-marshall/credentials*)')

        assert claude_runtime._protect_path_deny_rules(str(protected)) == expected

    def test_a_sibling_of_home_gets_no_tilde_spelling(self, monkeypatch, tmp_path: Path) -> None:
        """``relative_to``, not ``startswith`` — a sibling of home is not under it.

        With home ``/home/user``, a plain prefix test also matches
        ``/home/user2/...`` and would render the nonsensical ``~2/...``.
        ``relative_to`` raises instead, so the path keeps its absolute spelling
        — and because the tilde form is then the SAME string as the absolute
        one, the two collapse and the rule list is shorter. That collapse is a
        property of this implementation, not of the prefix-test alternative,
        which would have produced two distinct (and one nonsensical) rules.
        """
        fake_home = tmp_path / 'user'
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: fake_home)
        sibling = tmp_path / 'user2' / 'creds'

        rules = claude_runtime._protect_path_deny_rules(str(sibling))
        assert not any('~' in rule for rule in rules)
        assert rules[0] == f'Read({sibling}/**)'
        # One Read + eight Bash vectors + the python3 -c vector, each in a
        # single spelling because there is no tilde form to differ from.
        assert len(rules) == 10

    def test_rules_are_deduplicated(self, monkeypatch, tmp_path: Path) -> None:
        """A drafted duplicate must not be reported as a rule the caller gets."""
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: tmp_path / 'user')
        rules = claude_runtime._protect_path_deny_rules(str(tmp_path / 'outside' / 'creds'))
        assert len(rules) == len(set(rules))

    def test_protecting_the_home_directory_itself_emits_no_match_everything_rule(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """``~`` — not ``~/.`` — so the inline-script vector cannot become ``*.*``.

        The distinctive segment is the tail after ``~/``. Rendering home as
        ``~/.`` makes that tail ``.``, and ``Bash(python3 -c *.*)`` denies very
        nearly every inline script an operator could run — a permission rule far
        broader than the directory it was asked to protect. Any directory is a
        legal argument, so this input is reachable rather than theoretical.
        """
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: tmp_path)

        rules = claude_runtime._protect_path_deny_rules(str(tmp_path))

        assert 'Bash(python3 -c *.*)' not in rules
        assert 'Read(~/./**)' not in rules
        assert 'Read(~/**)' in rules
        # With no ``~/`` tail to take, the inline-script vector falls back to
        # the absolute spelling, which names the directory rather than anything.
        assert f'Bash(python3 -c *{tmp_path}*)' in rules

    def test_every_exfiltration_vector_is_covered_in_both_spellings(self) -> None:
        protected = claude_runtime.resolve_home() / '.plan-marshall' / 'credentials'
        rules = claude_runtime._protect_path_deny_rules(str(protected))
        for vector in claude_runtime._EXFILTRATION_BASH_VECTORS:
            matching = [r for r in rules if r.startswith(f'Bash({vector} ')]
            assert len(matching) == 2, f'{vector} must be guarded in tilde AND absolute form'
