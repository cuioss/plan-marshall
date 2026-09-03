#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the ``permission fix --operation protect-path`` operation.

It renders deny rules for a directory the caller names, writes them, and returns
counts only — no rendered rule crosses back. A deny rule is a security control,
so a path it cannot express faithfully is refused rather than approximated.
"""
from __future__ import annotations  # noqa: I001

import json
from pathlib import Path
from typing import Any

import claude_runtime
from runtime_base import PERMISSION_FIX_OPERATIONS
import pytest
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    return parse_toon(output)



class TestPermissionFixProtectPath:
    """``permission fix --operation protect-path`` writes deny rules, goal-based."""

    # A directory under the home has both a tilde and an absolute spelling, so
    # it yields the full 19-rule set (1 Read + 8 Bash vectors, each doubled,
    # plus the python3 -c vector) — the same shape the real credentials
    # directory produces.
    RULE_COUNT = 19

    def _protected(self, monkeypatch, tmp_path: Path) -> Path:
        """Return a protected dir under a patched home, so both spellings differ."""
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: tmp_path)
        return tmp_path / 'creds'

    def _pin_scope_path(self, monkeypatch, settings_path: Path) -> None:
        monkeypatch.setattr(
            claude_runtime, '_settings_path_for_scope', lambda scope: settings_path
        )

    def test_writes_the_rendered_rules_to_the_deny_list(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        protected = self._protected(monkeypatch, tmp_path)
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [str(protected)], False
            )
        )
        assert result['status'] == 'success'
        assert result['fix_operation'] == 'protect-path'
        assert result['paths_named'] == 1
        assert result['rules_total'] == self.RULE_COUNT
        assert result['changes_applied'] == self.RULE_COUNT

        written = json.loads(settings_path.read_text(encoding='utf-8'))
        deny = written['permissions']['deny']
        assert len(deny) == self.RULE_COUNT
        # Spot-check both spellings rather than re-deriving the whole list from
        # the renderer, which would agree with itself whatever it emitted.
        assert 'Read(~/creds/**)' in deny
        assert f'Read({protected}/**)' in deny
        assert 'Bash(base64 ~/creds/*)' in deny
        assert 'Bash(python3 -c *creds*)' in deny

    def test_no_rendered_rule_crosses_back_to_the_caller(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The response is counts only — a caller cannot learn the DSL from it."""
        protected = self._protected(monkeypatch, tmp_path)
        self._pin_scope_path(monkeypatch, tmp_path / 'settings.json')
        raw = claude_runtime.ClaudeRuntime().permission_fix(
            'global', 'protect-path', [str(protected)], False
        )
        # Assert the operation SUCCEEDED first: an error TOON also contains no
        # rule text, so without this the test passes against a broken op.
        assert _parse(raw)['status'] == 'success'
        assert 'Read(' not in raw
        assert 'Bash(' not in raw

    def test_is_idempotent(self, tmp_path: Path, monkeypatch) -> None:
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)
        runtime = claude_runtime.ClaudeRuntime()

        runtime.permission_fix('global', 'protect-path', [protected], False)
        second = _parse(runtime.permission_fix('global', 'protect-path', [protected], False))

        assert second['changes_applied'] == 0
        assert second['rules_total'] == self.RULE_COUNT
        written = json.loads(settings_path.read_text(encoding='utf-8'))
        assert len(written['permissions']['deny']) == self.RULE_COUNT

    def test_a_no_change_rerun_does_not_rewrite_the_file(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Adding nothing writes nothing.

        The file is re-serialized in a DIFFERENT formatting before the second
        call, which is what makes this a guard rather than a tautology: the
        runtime writes ``json.dumps(..., indent=2)``, so comparing the bytes of
        a file the runtime itself just wrote can never detect a rewrite — the
        two serializations are identical. Seeding a compact spelling of the same
        content makes any write visible.
        """
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)
        runtime = claude_runtime.ClaudeRuntime()

        runtime.permission_fix('global', 'protect-path', [protected], False)
        # Re-spell the same settings compactly. Content is taken from the file,
        # not from the renderer, so this fixture asserts nothing about which
        # rules were written — only that a second call leaves them alone.
        populated = json.loads(settings_path.read_text(encoding='utf-8'))
        settings_path.write_text(json.dumps(populated, separators=(',', ':')), encoding='utf-8')
        before = settings_path.read_bytes()

        result = _parse(runtime.permission_fix('global', 'protect-path', [protected], False))

        assert result['changes_applied'] == 0
        assert settings_path.read_bytes() == before, (
            'a no-change re-run re-serialized the file: an operator sees a '
            'modified settings file for no effect'
        )

    def test_preserves_unrelated_deny_entries(self, tmp_path: Path, monkeypatch) -> None:
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        settings_path.write_text(
            json.dumps({'permissions': {'allow': [], 'deny': ['Read(~/.ssh/**)'], 'ask': []}}),
            encoding='utf-8',
        )
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [protected], False
            )
        )
        written = json.loads(settings_path.read_text(encoding='utf-8'))
        assert written['permissions']['deny'][0] == 'Read(~/.ssh/**)'
        assert len(written['permissions']['deny']) == self.RULE_COUNT + 1
        # `rules_total` counts THIS protection's rules, not the settings file's
        # deny list. The pre-existing entry above is what makes the two
        # denominators differ — on an empty deny list they coincide, and a
        # confusion between them would be invisible.
        assert result['rules_total'] == self.RULE_COUNT
        assert result['changes_applied'] == self.RULE_COUNT

    def test_dry_run_writes_nothing_and_reports_a_count(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [protected], True
            )
        )
        assert result['proposed_count'] == self.RULE_COUNT
        assert result['changes_applied'] == 0
        assert 'proposed_additions' not in result
        assert not settings_path.exists()

    def test_dry_run_proposes_only_what_is_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`proposed_count` counts rules NOT already present, not rules rendered.

        Some of the protection's own rules are seeded first, which is what
        separates the two quantities: against an empty deny list they coincide,
        and a `proposed_count` that counted everything rendered would look
        correct.
        """
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)
        runtime = claude_runtime.ClaudeRuntime()

        # Populate, then drop five rules so exactly five are missing.
        runtime.permission_fix('global', 'protect-path', [protected], False)
        populated = json.loads(settings_path.read_text(encoding='utf-8'))
        populated['permissions']['deny'] = populated['permissions']['deny'][:-5]
        settings_path.write_text(json.dumps(populated), encoding='utf-8')

        result = _parse(runtime.permission_fix('global', 'protect-path', [protected], True))

        assert result['proposed_count'] == 5
        assert result['rules_total'] == self.RULE_COUNT

    def test_one_directory_named_twice_is_counted_once(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`rules_total` must not double-count a rule the caller receives once.

        The per-path renderer de-duplicates within a path; without the same
        across paths, naming a directory twice reports twice the rules and
        writes half of them — the exact over-count the de-duplication exists to
        remove, re-created one level up.
        """
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [protected, protected], False
            )
        )

        assert result['paths_named'] == 2
        assert result['rules_total'] == self.RULE_COUNT
        assert result['changes_applied'] == self.RULE_COUNT
        written = json.loads(settings_path.read_text(encoding='utf-8'))
        assert len(written['permissions']['deny']) == self.RULE_COUNT

    def test_two_distinct_directories_each_get_their_rules(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """De-duplication across paths must not collapse genuinely distinct sets."""
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: tmp_path)
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global',
                'protect-path',
                [str(tmp_path / 'creds'), str(tmp_path / 'other')],
                False,
            )
        )

        assert result['paths_named'] == 2
        assert result['rules_total'] == self.RULE_COUNT * 2
        written = json.loads(settings_path.read_text(encoding='utf-8'))
        assert 'Read(~/creds/**)' in written['permissions']['deny']
        assert 'Read(~/other/**)' in written['permissions']['deny']

    def test_rejects_an_empty_path_list(self, tmp_path: Path, monkeypatch) -> None:
        """Protecting nothing is a caller error, never a silent success."""
        self._pin_scope_path(monkeypatch, tmp_path / 'settings.json')
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix('global', 'protect-path', [], False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_operation'

    @pytest.mark.parametrize(
        ('path', 'why'),
        [
            ('', 'an empty argument renders Read(/**) and Bash(python3 -c **)'),
            ('   ', 'whitespace is empty by another spelling'),
            ('./creds', 'a relative path denies an unrelated location or nothing'),
            ('creds', 'likewise, with no leading dot'),
            ('/home/u/cre)ds', 'a ")" truncates the rule and frees the remainder'),
            ('/home/u/cre(ds', 'a "(" is the other delimiter'),
            ('/home/u/x*', 'a "*" widens the rule past what was asked for'),
            ('/home/u/a\nb', 'a newline splits one rule into two'),
            ('/home/u/a\x7fb', 'DEL is a control character above the 0x20 range'),
            ('/home/u/my creds', 'a space moves the argument boundary in a Bash rule'),
            ('/', 'the root renders Bash(python3 -c */*) — any inline script with a slash'),
            ('/home/u/../../etc', 'a ".." silently renames the directory the caller named'),
        ],
    )
    def test_refuses_a_path_it_cannot_render_faithfully(
        self, tmp_path: Path, monkeypatch, path: str, why: str
    ) -> None:
        """A deny rule is a security control: refuse rather than approximate.

        Each of these renders *something* — that is the danger. An empty
        argument produced a denial of every absolute read and every inline
        script; a `)` let the rest of the path become rule text of its own.
        """
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [path], False
            )
        )

        assert result['status'] == 'error', why
        assert result['error'] == 'invalid_operation'
        assert not settings_path.exists(), 'a refused path must not reach the settings file'

    def test_one_directory_spelled_two_ways_protects_it_once(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Both spellings normalize from one `Path`, so de-duplication sees them.

        Rendering the tilde arm through `Path` and the absolute arm from the raw
        string let `"/a//b"` and `"/a/b/"` produce one live rule and one keyed on
        a spelling nothing matches — and two spellings of one directory then
        survived de-duplication as separate protections.
        """
        protected = self._protected(monkeypatch, tmp_path)
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global',
                'protect-path',
                [str(protected), str(protected) + '/', str(protected).replace('/creds', '//creds')],
                False,
            )
        )

        assert result['paths_named'] == 3
        assert result['rules_total'] == self.RULE_COUNT
        written = json.loads(settings_path.read_text(encoding='utf-8'))
        assert len(written['permissions']['deny']) == self.RULE_COUNT
        assert not any('//' in rule for rule in written['permissions']['deny'])

    def test_a_failed_write_is_an_error_not_a_reported_success(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """⛔ The fail-open this closes: a security control claiming rules it never wrote.

        `_save_settings` returns False on OSError, and the return was discarded
        — so an unwritable settings file produced `status: success` with a
        non-zero `rules_added`, telling an operator their credentials were
        guarded by rules that had reached nothing.
        """
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        self._pin_scope_path(monkeypatch, settings_path)
        monkeypatch.setattr(claude_runtime, '_save_settings', lambda path, settings: False)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [protected], False
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'io_error'
        assert 'changes_applied' not in result

    def test_a_malformed_deny_value_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        """A `deny` of the wrong type is an error, not an uncaught AttributeError.

        `protect-path` is the only operation that indexes `["deny"]`, so it is
        the only one that can meet this state and the only one that guards it.
        """
        protected = str(self._protected(monkeypatch, tmp_path))
        settings_path = tmp_path / 'settings.json'
        settings_path.write_text(
            json.dumps({'permissions': {'allow': [], 'deny': {}, 'ask': []}}), encoding='utf-8'
        )
        self._pin_scope_path(monkeypatch, settings_path)
        before = settings_path.read_bytes()

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'protect-path', [protected], False
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_settings'
        assert settings_path.read_bytes() == before

    def test_opencode_declines_with_an_honest_noop(self) -> None:
        """A target with no permission backend declines — it does not error."""
        result = _parse(
            OpenCodeRuntime().permission_fix('global', 'protect-path', ['/tmp/creds'], False)
        )
        assert result['status'] == 'no-op'
        assert 'OpenCode' in result['reason']
        assert result['alternative']
        assert 'changes_applied' not in result

    def test_the_two_runtimes_accept_the_same_operation_set(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A value one runtime accepts and the other rejects is a silent gap.

        Both runtimes are driven, because the claim is a COMPARISON: OpenCode
        rejecting ``protect-path`` as ``invalid_operation`` would turn its
        honest no-op into an error the caller must special-case, and Claude
        rejecting one OpenCode accepts would be the same gap mirrored. The
        operation list is spelled out rather than read from either runtime's own
        ``valid_ops``, so a value dropped from both still fails here.

        Deriving it from ``PERMISSION_FIX_OPERATIONS`` instead would forfeit
        exactly that. This sweep's claim is *about the set*: that both runtimes
        accept the same operations. Derive the population from the set and a
        **removal** silently shrinks the claim — the sweep keeps passing while
        covering less — and an **addition** silently widens it to an operation
        nobody checked OpenCode handles. A non-vacuity guard catches only the
        empty case, a third failure the equality check already covers.

        So the literal stays as the independent oracle AND is asserted equal to
        the published tuple: divergence in either direction fails loudly, and
        "update both deliberately" is the intended cost.

        The sibling in ``test_opencode_runtime.py`` derives from the published
        set instead, with a non-vacuity guard, because it asserts a property of
        *whatever* the set contains rather than a property of the set. Both
        patterns are deliberate; which one fits depends on where the claim lives.
        """
        self._pin_scope_path(monkeypatch, tmp_path / 'settings.json')
        operations = ('normalize', 'add', 'remove', 'ensure', 'consolidate', 'protect-path')
        assert operations == PERMISSION_FIX_OPERATIONS, (
            'the published operation set and this sweep have diverged; update both deliberately'
        )

        for operation in operations:
            if operation == 'protect-path':
                args = [str(tmp_path / 'arg')]
            elif operation in ('add', 'remove', 'ensure'):
                args = [{'kind': 'path', 'tool': 'Read', 'path': str(tmp_path / 'arg')}]
            else:
                args = []
            claude = _parse(
                claude_runtime.ClaudeRuntime().permission_fix(
                    'global', operation, args, True
                )
            )
            assert claude['status'] == 'success', operation

            opencode = _parse(
                OpenCodeRuntime().permission_fix('global', operation, args, True)
            )
            assert opencode['status'] == 'no-op', operation


class TestEveryMutatingBranchReportsAFailedWrite:
    """`io_error` is not `protect-path`'s alone — every write path reports it.

    `protect-path` was the only branch that checked `_save_settings`; the five
    allow-list operations discarded it and returned `status: success` with a
    non-zero `changes_applied` after writing nothing. Splitting the population
    across a fixed and an unfixed half is how the next reader concludes the
    checked one is the exception.
    """

    def _pin_scope_path(self, monkeypatch, settings_path: Path) -> None:
        monkeypatch.setattr(
            claude_runtime, '_settings_path_for_scope', lambda scope: settings_path
        )

    @pytest.mark.parametrize(
        ('operation', 'permissions'),
        [
            ('normalize', []),
            ('add', [{'kind': 'path', 'tool': 'Read', 'path': '/tmp/x'}]),
            ('remove', [{'kind': 'path', 'tool': 'Read', 'path': '/tmp/seeded'}]),
            ('ensure', [{'kind': 'path', 'tool': 'Read', 'path': '/tmp/x'}]),
            ('consolidate', []),
        ],
    )
    def test_an_unwritable_settings_file_is_an_error(
        self, tmp_path: Path, monkeypatch, operation: str, permissions: list
    ) -> None:
        settings_path = tmp_path / 'settings.json'
        settings_path.write_text(
            json.dumps(
                {
                    'permissions': {
                        # Seeded so every operation has real work to do: an
                        # operation that changed nothing could report success
                        # honestly, and prove nothing here.
                        'allow': ['Read(/tmp/b)', 'Read(/tmp/a)', 'Read(/tmp/seeded)'],
                        'deny': [],
                        'ask': [],
                    }
                }
            ),
            encoding='utf-8',
        )
        self._pin_scope_path(monkeypatch, settings_path)
        monkeypatch.setattr(claude_runtime, '_save_settings', lambda _p, _s: False)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', operation, permissions, False
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'io_error'
        assert 'changes_applied' not in result

    def test_a_writable_file_still_succeeds(self, tmp_path: Path, monkeypatch) -> None:
        """The guard must not turn a working write into an error."""
        settings_path = tmp_path / 'settings.json'
        settings_path.write_text(
            json.dumps({'permissions': {'allow': ['Read(/tmp/b)'], 'deny': [], 'ask': []}}),
            encoding='utf-8',
        )
        self._pin_scope_path(monkeypatch, settings_path)

        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix(
                'global', 'add', [{'kind': 'path', 'tool': 'Read', 'path': '/tmp/x'}], False
            )
        )

        assert result['status'] == 'success'
        assert 'Read(/tmp/x)' in json.loads(settings_path.read_text())['permissions']['allow']
