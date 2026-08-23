#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Pins for the default permission set the Claude runtime renders.

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
import json
from pathlib import Path
from typing import Any

import claude_runtime
from toon_parser import parse_toon


def _parse(output: str) -> dict[str, Any]:
    return parse_toon(output)



# =============================================================================
# The default permission set
# =============================================================================


class TestDefaultPermissionRules:
    """``_default_permission_rules`` renders exactly these two rules."""

    def test_rendered_rules_are_the_pinned_literals(self) -> None:
        rendered = [rule for _rule_id, rule in claude_runtime._default_permission_rules()]
        assert rendered == [
            'Edit(.plan/**)',
            'Read(~/.claude/plugins/cache/**)',
        ]

    def test_no_write_rule_is_rendered(self) -> None:
        """A ``Write(...)`` default would be an unmatched rule, not a redundant one.

        Claude consults ``Edit(...)`` rules for file permission checks, so a
        ``Write(path)`` allow rule guards nothing and the host reports it as
        unmatched at startup. Pinned separately from the literal list above
        because the property — never render a ``Write`` default — is what must
        survive a future addition to the set.
        """
        rendered = [rule for _rule_id, rule in claude_runtime._default_permission_rules()]
        assert not any(rule.startswith('Write(') for rule in rendered)

    def test_semantic_ids_are_the_only_thing_a_caller_receives(self) -> None:
        """The ids name the goal, not the grammar — no id may contain DSL syntax."""
        ids = [rule_id for rule_id, _rule in claude_runtime._default_permission_rules()]
        assert ids == ['plan-dir-edit', 'bundle-cache-read']
        for rule_id in ids:
            assert '(' not in rule_id and ')' not in rule_id


class TestRetiredDefaultRules:
    """The rules the renderer prunes rather than emits."""

    def test_retired_rules_are_the_pinned_literals(self) -> None:
        assert claude_runtime._RETIRED_DEFAULT_RULES == (('plan-dir-write', 'Write(.plan/**)'),)

    def test_no_rule_is_both_live_and_retired(self) -> None:
        """Rendering and pruning the same rule would never converge."""
        live = {rule for _rule_id, rule in claude_runtime._default_permission_rules()}
        retired = {rule for _rule_id, rule in claude_runtime._RETIRED_DEFAULT_RULES}
        assert live.isdisjoint(retired)

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

        assert result['defaults_added'] == ['plan-dir-edit', 'bundle-cache-read']
        assert result['defaults_added_count'] == 2
        assert result['applied'] is True
        written = json.loads(path.read_text(encoding='utf-8'))
        assert written['permissions']['allow'] == sorted(
            [
                'Bash(git:*)',
                'Edit(.plan/**)',
                'Read(~/.claude/plugins/cache/**)',
            ]
        )

    def test_is_idempotent_and_writes_nothing_when_already_present(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings(['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)'])
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added'] == []
        assert result['defaults_added_count'] == 0
        assert result['defaults_removed'] == []
        assert result['applied'] is False
        assert not path.exists()

    def test_prunes_a_retired_rule_and_reports_its_semantic_id(self, tmp_path: Path) -> None:
        """A settings file written by an earlier version loses the dead rule.

        The seed is otherwise default-complete, so pruning is the ONLY work in
        the run — an implementation that merely stopped rendering the rule
        would report no change and write nothing here.
        """
        path = tmp_path / 'settings.json'
        settings = self._settings(
            ['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)', 'Write(.plan/**)']
        )
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added'] == []
        assert result['defaults_removed'] == ['plan-dir-write']
        assert result['defaults_removed_count'] == 1
        assert result['applied'] is True
        written = json.loads(path.read_text(encoding='utf-8'))
        assert written['permissions']['allow'] == sorted(
            ['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)']
        )

    def test_prunes_every_copy_of_a_duplicated_retired_rule(self, tmp_path: Path) -> None:
        """A hand-edited file can carry the rule twice; one left standing still warns."""
        path = tmp_path / 'settings.json'
        settings = self._settings(
            [
                'Edit(.plan/**)',
                'Read(~/.claude/plugins/cache/**)',
                'Write(.plan/**)',
                'Write(.plan/**)',
            ]
        )
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_removed'] == ['plan-dir-write']
        assert 'Write(.plan/**)' not in settings['permissions']['allow']

    def test_dry_run_prunes_in_memory_and_writes_nothing(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings(['Write(.plan/**)'])
        result = claude_runtime.ensure_default_permissions(settings, path, dry_run=True)

        assert result['defaults_removed_count'] == 1
        assert result['applied'] is False
        assert not path.exists()

    def test_dry_run_merges_in_memory_and_writes_nothing(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings = self._settings([])
        result = claude_runtime.ensure_default_permissions(settings, path, dry_run=True)

        assert result['defaults_added_count'] == 2
        assert result['applied'] is False
        assert not path.exists()
        assert 'Edit(.plan/**)' in settings['permissions']['allow']

    def test_seeds_the_permissions_block_when_absent(self, tmp_path: Path) -> None:
        path = tmp_path / 'settings.json'
        settings: dict[str, Any] = {}
        result = claude_runtime.ensure_default_permissions(settings, path)

        assert result['defaults_added_count'] == 2
        assert settings['permissions']['allow'] == sorted(
            ['Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)']
        )

    def test_a_failed_write_is_not_reported_as_applied(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`applied` must follow the write, not the intent to write.

        The protect-path sibling closes exactly this fail-open one function
        over. Here the cost of getting it wrong is downstream: ``cmd_apply_fixes``
        reads ``defaults['applied'] or save_settings(...)``, so a wrongly-True
        ``applied`` short-circuits the retry AND suppresses the error the caller
        would otherwise report.
        """
        path = tmp_path / 'settings.json'
        settings = self._settings([])
        monkeypatch.setattr(claude_runtime, '_save_settings', lambda _p, _s: False)

        result = claude_runtime.ensure_default_permissions(settings, path)

        # There WAS work to do — otherwise `applied is False` proves nothing.
        assert result['defaults_added_count'] == 2
        assert result['applied'] is False
