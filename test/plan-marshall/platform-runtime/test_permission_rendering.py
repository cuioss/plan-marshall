#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the permission grammar the Claude runtime renders.

The permission DSL is a target wire format, so it is rendered inside
``claude_runtime`` and never crosses the runtime boundary. Two callers used to
render it themselves — ``permission_fix.DEFAULT_PERMISSIONS`` and
``_cred_ensure_denied.DENY_RULES`` — and the strings those produced are the
observable contract a user's settings file already carries. These tests pin the
rendered output BYTE-FOR-BYTE against what those callers produced, so the
relocation cannot quietly change what lands in anyone's settings.

They are written as literals rather than derived from the renderer: an
expectation computed by the code under test agrees with it by construction and
would pass against any rewrite, which is precisely the defect a relocation pin
exists to catch. The one value that cannot be a literal is the home directory,
which differs per machine.

conftest.py sets up PYTHONPATH so the cross-skill imports resolve without manual
sys.path manipulation.
"""
from __future__ import annotations  # noqa: I001

import json
from pathlib import Path
from typing import Any

import claude_runtime
from opencode_runtime import OpenCodeRuntime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    return parse_toon(output)


# =============================================================================
# D1 — the default permission set
# =============================================================================


class TestDefaultPermissionRules:
    """``_default_permission_rules`` renders exactly the former DEFAULT_PERMISSIONS."""

    def test_rendered_rules_are_byte_identical_to_the_former_literals(self) -> None:
        rendered = [rule for _rule_id, rule in claude_runtime._default_permission_rules()]
        assert rendered == [
            'Edit(.plan/**)',
            'Write(.plan/**)',
            'Read(~/.claude/plugins/cache/**)',
        ]

    def test_semantic_ids_are_the_only_thing_a_caller_receives(self) -> None:
        """The ids name the goal, not the grammar — no id may contain DSL syntax."""
        ids = [rule_id for rule_id, _rule in claude_runtime._default_permission_rules()]
        assert ids == ['plan-dir-edit', 'plan-dir-write', 'bundle-cache-read']
        for rule_id in ids:
            assert '(' not in rule_id and ')' not in rule_id

    def test_layout_op_reads_the_resolved_home(self, monkeypatch, tmp_path) -> None:
        """``layout bundle-cache-root`` derives its root — move home, it moves."""
        fake_home = tmp_path / 'elsewhere'
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: fake_home)
        roots = _parse(claude_runtime.ClaudeRuntime().layout_bundle_cache_root())['roots']
        assert roots == [str(fake_home / '.claude' / 'plugins' / 'cache' / 'plan-marshall')]

    def test_bundle_cache_rule_tracks_the_layout_op(self, monkeypatch, tmp_path) -> None:
        """The permission and the layout op must name one cache location.

        The expectation is computed from the layout op's OWN output plus
        arithmetic done here — never from the renderer — so the two surfaces are
        checked against each other rather than against themselves. What this
        catches is drift: change the cache segments on one side and the other
        stops matching. It cannot, by itself, distinguish a derived string from
        a hardcoded one, because the tilde spelling is home-invariant.
        """
        fake_home = tmp_path / 'elsewhere'
        monkeypatch.setattr(claude_runtime, 'resolve_home', lambda: fake_home)

        cache_root = Path(
            _parse(claude_runtime.ClaudeRuntime().layout_bundle_cache_root())['roots'][0]
        )
        # The permission covers the cache root's PARENT — every bundle cache,
        # not just plan-marshall's — spelled relative to home.
        expected_dir = '~/' + str(cache_root.parent.relative_to(fake_home))

        rendered = dict(claude_runtime._default_permission_rules())
        assert rendered['bundle-cache-read'] == f'Read({expected_dir}/**)'


class TestEnsureDefaultPermissions:
    """The goal-based entry point merges the defaults and performs the write."""

    def _settings(self, allow: list[str]) -> dict[str, Any]:
        return {'permissions': {'allow': list(allow), 'deny': [], 'ask': []}}

    def test_writes_the_defaults_and_reports_semantic_ids(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings(['Bash(git:*)'])
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added'] == ['plan-dir-edit', 'plan-dir-write', 'bundle-cache-read']
        assert result['defaults_added_count'] == 3
        assert result['applied'] is True
        written = json.loads(path.read_text(encoding='utf-8'))
        assert written['permissions']['allow'] == sorted(
            [
                'Bash(git:*)',
                'Edit(.plan/**)',
                'Write(.plan/**)',
                'Read(~/.claude/plugins/cache/**)',
            ]
        )

    def test_is_idempotent_and_writes_nothing_when_already_present(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings(
            ['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)', 'Write(.plan/**)']
        )
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added'] == []
        assert result['defaults_added_count'] == 0
        assert result['applied'] is False
        assert not path.exists()

    def test_dry_run_merges_in_memory_and_writes_nothing(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings([])
        result = claude_runtime.ensure_default_permissions(settings, path, dry_run=True)

        assert result['defaults_added_count'] == 3
        assert result['applied'] is False
        assert not path.exists()
        assert 'Edit(.plan/**)' in settings['permissions']['allow']

    def test_seeds_the_permissions_block_when_absent(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings: dict[str, Any] = {}
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added_count'] == 3
        assert settings['permissions']['allow'] == sorted(
            ['Edit(.plan/**)', 'Write(.plan/**)', 'Read(~/.claude/plugins/cache/**)']
        )


# =============================================================================
# D2 — the settings read path
# =============================================================================


class TestProjectSettingsReadPath:
    """The read preference is the runtime's, and it mirrors the write preference."""

    def test_prefers_settings_local_json_when_it_exists(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.local.json'
        )

    def test_reads_settings_local_json_when_it_is_the_only_one(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.local.json'
        )

    def test_falls_back_to_settings_json_when_local_absent(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            claude_dir / 'settings.json'
        )

    def test_returns_settings_json_when_neither_exists(self, tmp_path: Path) -> None:
        """The pre-delegation behaviour: an absent pair reads as the shared file."""
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)) == (
            tmp_path / '.claude' / 'settings.json'
        )

    def test_read_and_write_preferences_are_opposites(self, tmp_path: Path) -> None:
        """Both files present: the read path takes local, the write path takes shared."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / 'settings.local.json').write_text('{}', encoding='utf-8')
        (claude_dir / 'settings.json').write_text('{}', encoding='utf-8')
        assert claude_runtime._claude_project_settings_read_path(str(tmp_path)).name == (
            'settings.local.json'
        )
        assert claude_runtime._claude_project_settings_path(str(tmp_path)).name == 'settings.json'


# =============================================================================
# D3 — the credential-protection deny rules
# =============================================================================


class TestProtectPathDenyRules:
    """``_protect_path_deny_rules`` renders exactly the former DENY_RULES."""

    def test_rules_are_byte_identical_to_the_former_builder(self) -> None:
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

    def test_every_exfiltration_vector_is_covered_in_both_spellings(self) -> None:
        protected = claude_runtime.resolve_home() / '.plan-marshall' / 'credentials'
        rules = claude_runtime._protect_path_deny_rules(str(protected))
        for vector in claude_runtime._EXFILTRATION_BASH_VECTORS:
            matching = [r for r in rules if r.startswith(f'Bash({vector} ')]
            assert len(matching) == 2, f'{vector} must be guarded in tilde AND absolute form'


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
        assert result['paths_protected'] == 1
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
        """Adding nothing writes nothing — the retired caller behaved this way too.

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

    def test_rejects_an_empty_path_list(self, tmp_path: Path, monkeypatch) -> None:
        """Protecting nothing is a caller error, never a silent success."""
        self._pin_scope_path(monkeypatch, tmp_path / 'settings.json')
        result = _parse(
            claude_runtime.ClaudeRuntime().permission_fix('global', 'protect-path', [], False)
        )
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_operation'

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
        """
        self._pin_scope_path(monkeypatch, tmp_path / 'settings.json')
        operations = ('normalize', 'add', 'remove', 'ensure', 'consolidate', 'protect-path')

        for operation in operations:
            claude = _parse(
                claude_runtime.ClaudeRuntime().permission_fix(
                    'global', operation, [str(tmp_path / 'arg')], True
                )
            )
            assert claude['status'] == 'success', operation

            opencode = _parse(
                OpenCodeRuntime().permission_fix('global', operation, [str(tmp_path / 'arg')], True)
            )
            assert opencode['status'] == 'no-op', operation
