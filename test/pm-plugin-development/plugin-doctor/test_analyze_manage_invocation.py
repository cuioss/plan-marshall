#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for the ``_analyze_manage_invocation.py`` plugin-doctor analyzer.

The analyzer ships two rules over markdown invocations of the seven in-scope
``manage-*`` / ``workflow-integration-*`` script families:

  * ``manage-invocation-invalid`` (severity: error) — emitted for each of
    four mismatch modes against the script's canonical argparse tree:

      - unknown top-level subcommand
      - unknown sub-verb (under a subcommand declaring its own subparsers)
      - unknown long flag under the resolved leaf parser
      - missing required long flag declared by the leaf parser

  * ``missing-canonical-block`` (severity: warning) — emitted for an
    in-scope SKILL.md that lacks a ``## Canonical invocations`` section.

Tests are hermetic: they synthesise argparse-bearing Python scripts and
markdown fixtures under ``tmp_path`` so no real marketplace tree state is
required. The seven in-scope notations are exercised via parameterised
positive cases; each negative finding type has at least one dedicated
case; payload shape (rule_id, severity, line, file, canonical_hint) is
verified against the documented schema.
"""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loader — load the analyzer directly from the marketplace scripts dir.
# Underscore-prefixed analyzers are not importable through the executor, so we
# spec-load the module by file path the same way the doctor harness does.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ami = _load_module('_analyze_manage_invocation', '_analyze_manage_invocation.py')

analyze_manage_invocation_markdown = _ami.analyze_manage_invocation_markdown
scan_skill_for_manage_invocation = _ami.scan_skill_for_manage_invocation
scan_manage_invocation = _ami.scan_manage_invocation
check_missing_canonical_blocks = _ami.check_missing_canonical_blocks
build_script_tree = _ami.build_script_tree
build_script_index = _ami.build_script_index
RULE_MANAGE_INVOCATION_INVALID = _ami.RULE_MANAGE_INVOCATION_INVALID
RULE_MISSING_CANONICAL_BLOCK = _ami.RULE_MISSING_CANONICAL_BLOCK
IN_SCOPE_SCRIPTS = _ami.IN_SCOPE_SCRIPTS


# ---------------------------------------------------------------------------
# Synthetic script fixtures (hermetic argparse declarations).
# ---------------------------------------------------------------------------


# Synthetic notation used across the per-shape unit tests. Mirrors the shape
# of a manage-* notation triple so the regex extractor accepts it, but does
# not collide with any real notation in IN_SCOPE_SCRIPTS — the per-test
# script_index controls which notations are valid.
_SYN_NOTATION = 'plan-marshall:manage-syn:manage-syn'


def _flat_script_source() -> str:
    """Synthetic script with two flat subcommands and one root-level flag.

    - ``foo`` subcommand has ``--alpha`` (required) and ``--beta``.
    - ``bar`` subcommand has ``--gamma``.
    - Root parser has ``--debug``.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            parser.add_argument('--debug', action='store_true')
            subparsers = parser.add_subparsers(dest='cmd')

            foo = subparsers.add_parser('foo')
            foo.add_argument('--alpha', required=True)
            foo.add_argument('--beta')

            bar = subparsers.add_parser('bar')
            bar.add_argument('--gamma')

            return parser
    ''').lstrip()


def _nested_script_source() -> str:
    """Synthetic script with one flat and one nested subcommand.

    - ``qgate`` subcommand declares its own subparsers:
        * ``add`` with ``--plan-id`` (required) and ``--phase`` (required)
        * ``query`` with ``--plan-id`` (required) and ``--phase``
    - ``other`` is a flat subcommand with ``--flag``.
    """
    return textwrap.dedent('''
        import argparse

        def main():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest='cmd')

            qgate = subparsers.add_parser('qgate')
            qgate_subs = qgate.add_subparsers(dest='sub')

            add_p = qgate_subs.add_parser('add')
            add_p.add_argument('--plan-id', required=True)
            add_p.add_argument('--phase', required=True)

            query_p = qgate_subs.add_parser('query')
            query_p.add_argument('--plan-id', required=True)
            query_p.add_argument('--phase')

            other = subparsers.add_parser('other')
            other.add_argument('--flag')

            return parser
    ''').lstrip()


@pytest.fixture
def flat_script(tmp_path: Path) -> Path:
    script_path = tmp_path / 'syn_flat.py'
    script_path.write_text(_flat_script_source(), encoding='utf-8')
    return script_path


@pytest.fixture
def nested_script(tmp_path: Path) -> Path:
    script_path = tmp_path / 'syn_nested.py'
    script_path.write_text(_nested_script_source(), encoding='utf-8')
    return script_path


@pytest.fixture
def flat_index(flat_script: Path) -> dict:
    tree = build_script_tree(flat_script)
    assert tree is not None
    return {_SYN_NOTATION: tree}


@pytest.fixture
def nested_index(nested_script: Path) -> dict:
    tree = build_script_tree(nested_script)
    assert tree is not None
    return {_SYN_NOTATION: tree}


# ---------------------------------------------------------------------------
# Layer A — AST-based tree extraction.
# ---------------------------------------------------------------------------


class TestBuildScriptTree:
    """``build_script_tree`` faithfully reconstructs argparse declarations."""

    def test_flat_subcommands_extracted(self, flat_script: Path) -> None:
        tree = build_script_tree(flat_script)
        assert tree is not None
        assert tree.known_subcommands() == {'foo', 'bar'}

        foo_leaf = tree.get_leaf('foo', None)
        assert foo_leaf is not None
        assert foo_leaf.flags == {'alpha', 'beta'}
        assert foo_leaf.required_flags == {'alpha'}

        bar_leaf = tree.get_leaf('bar', None)
        assert bar_leaf is not None
        assert bar_leaf.flags == {'gamma'}
        assert bar_leaf.required_flags == set()

    def test_root_flags_extracted(self, flat_script: Path) -> None:
        tree = build_script_tree(flat_script)
        assert tree is not None
        # ``--debug`` is action='store_true' which has no name= arg; it is
        # still a declared long flag and should appear in the root's flag set.
        assert 'debug' in tree.root.flags

    def test_nested_subcommands_extracted(self, nested_script: Path) -> None:
        tree = build_script_tree(nested_script)
        assert tree is not None
        assert tree.known_subcommands() == {'qgate', 'other'}

        # ``qgate`` resolves only with a sub_verb.
        assert tree.get_leaf('qgate', None) is None
        add_leaf = tree.get_leaf('qgate', 'add')
        assert add_leaf is not None
        assert add_leaf.flags == {'plan-id', 'phase'}
        assert add_leaf.required_flags == {'plan-id', 'phase'}

        query_leaf = tree.get_leaf('qgate', 'query')
        assert query_leaf is not None
        assert query_leaf.flags == {'plan-id', 'phase'}
        assert query_leaf.required_flags == {'plan-id'}

        # ``other`` is flat.
        other_leaf = tree.get_leaf('other', None)
        assert other_leaf is not None
        assert other_leaf.flags == {'flag'}

    def test_missing_script_returns_none(self, tmp_path: Path) -> None:
        tree = build_script_tree(tmp_path / 'does-not-exist.py')
        assert tree is None

    def test_invalid_syntax_returns_none(self, tmp_path: Path) -> None:
        bad = tmp_path / 'bad.py'
        bad.write_text('def broken(:\n', encoding='utf-8')
        tree = build_script_tree(bad)
        assert tree is None


# ---------------------------------------------------------------------------
# Layer B — positive cases (canonical invocations produce no findings).
# ---------------------------------------------------------------------------


class TestPositiveCanonicalInvocations:
    """Each in-scope script accepts a canonical invocation cleanly."""

    def test_flat_subcommand_canonical_clean(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v1 --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_nested_subcommand_canonical_clean(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p1 --phase phase-5-execute\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert findings == []

    @pytest.mark.parametrize(
        'notation_third_segment',
        [desc.notation.split(':')[-1] for desc in IN_SCOPE_SCRIPTS],
    )
    def test_in_scope_notations_are_enumerated(self, notation_third_segment: str) -> None:
        """The 14 in-scope script families are represented in IN_SCOPE_SCRIPTS.

        The parametrize matrix is the structural assertion — pytest will
        fail if any expected family is missing or extra. The set matches
        the 15 SKILL.md files touched by D1 minus ``manage-findings``,
        which is covered by its own dedicated analyzer
        (``_analyze_manage_findings_invocation.py``).
        """
        all_third_segments = {desc.notation.split(':')[-1] for desc in IN_SCOPE_SCRIPTS}
        expected = {
            'manage_status',
            'manage-tasks',
            'manage-logging',
            'manage-references',
            'manage-config',
            'git_workflow',
            'github_ops',
            'architecture',
            'manage-execution-manifest',
            'manage-files',
            'manage-lessons',
            'manage_metrics',
            'manage-plan-documents',
            'manage-solution-outline',
        }
        assert all_third_segments == expected
        assert notation_third_segment in all_third_segments

    def test_unknown_notation_is_skipped(self, flat_index: dict) -> None:
        """Notations not in the script_index are silently passed over."""
        content = (
            'python3 .plan/execute-script.py some-bundle:some-skill:some-script anything --x y\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []


# ---------------------------------------------------------------------------
# Layer C — negative cases (one per finding type).
# ---------------------------------------------------------------------------


class TestUnknownSubcommand:
    """An unregistered top-level subcommand produces one finding."""

    def test_unknown_subcommand_is_flagged(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v1\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['details']['reason'] == 'subcommand_unknown'
        assert f['details']['subcommand'] == 'zzz'
        assert set(f['details']['known_subcommands']) == {'foo', 'bar'}
        assert 'canonical_hint' in f['details']

    def test_subcommand_finding_short_circuits_flag_validation(
        self, flat_index: dict
    ) -> None:
        """When subcommand is unknown, no flag findings are emitted on the same line."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --not-a-real-flag\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'subcommand_unknown'


class TestUnknownSubVerb:
    """An unregistered sub-verb under a nested subparser produces one finding."""

    def test_unknown_sub_verb_is_flagged(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate banana --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'sub_verb_unknown'
        assert f['details']['subcommand'] == 'qgate'
        assert f['details']['sub_verb'] == 'banana'
        assert set(f['details']['known_sub_verbs']) == {'add', 'query'}

    def test_missing_sub_verb_is_flagged(self, nested_index: dict) -> None:
        """``qgate`` without a sub-verb still produces a sub_verb_unknown finding."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'sub_verb_unknown'
        assert findings[0]['details']['sub_verb'] is None


class TestUnknownFlag:
    """An unregistered long flag under a resolved leaf parser is flagged."""

    def test_unknown_flag_on_flat_subcommand(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v --not-a-flag z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        # One finding for the unknown flag. No missing-required finding because
        # --alpha is satisfied.
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'flag_unknown'
        assert f['details']['flag'] == 'not-a-flag'
        assert set(f['details']['known_flags']) == {'alpha', 'beta'}

    def test_unknown_flag_on_nested_sub_verb(self, nested_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p --phase ph --bogus z\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        # Required flags are satisfied — only the unknown-flag finding fires.
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'bogus'


class TestMissingRequiredFlag:
    """A missing required flag produces one finding."""

    def test_missing_required_on_flat_subcommand(self, flat_index: dict) -> None:
        # ``foo`` requires --alpha; invocation omits it.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'required_flag_missing'
        assert f['details']['missing'] == ['alpha']
        assert set(f['details']['required_flags']) == {'alpha'}

    def test_missing_required_on_nested_sub_verb(self, nested_index: dict) -> None:
        # ``qgate add`` requires both --plan-id and --phase; omit one.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} qgate add --plan-id p\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', nested_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'required_flag_missing'
        assert f['details']['missing'] == ['phase']


# ---------------------------------------------------------------------------
# Layer D — missing-canonical-block rule (per in-scope SKILL.md).
# ---------------------------------------------------------------------------


def _build_synthetic_marketplace(
    tmp_path: Path,
    *,
    canonical_blocks: dict[str, bool],
) -> Path:
    """Create a synthetic marketplace tree with seven in-scope skill dirs.

    Each SKILL.md is created with or without a ``## Canonical invocations``
    section based on ``canonical_blocks`` (keyed by notation). The scripts
    are also written so build_script_index can resolve trees.
    """
    marketplace_root = tmp_path / 'mp'
    bundles_dir = marketplace_root / 'marketplace' / 'bundles'
    bundles_dir.mkdir(parents=True)

    for desc in IN_SCOPE_SCRIPTS:
        skill_dir = marketplace_root / 'marketplace' / desc.skill_dir_relpath
        skill_dir.mkdir(parents=True)
        (skill_dir / 'scripts').mkdir()

        # Minimal argparse script — single ``run`` subcommand.
        script_rel = desc.script_relpath.split('/')[-1]
        script_path = skill_dir / 'scripts' / script_rel
        script_path.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='cmd')
                    run = subparsers.add_parser('run')
                    run.add_argument('--flag')
                    return parser
            ''').lstrip(),
            encoding='utf-8',
        )

        skill_md = skill_dir / 'SKILL.md'
        body = '# Skill\n\nDescription.\n'
        if canonical_blocks.get(desc.notation, False):
            body += '\n## Canonical invocations\n\n### run\n\n```\nrun --flag x\n```\n'
        skill_md.write_text(body, encoding='utf-8')

    return marketplace_root


class TestMissingCanonicalBlock:
    """SKILL.md without ``## Canonical invocations`` produces a warning."""

    def test_missing_block_flagged_for_every_in_scope_skill(
        self, tmp_path: Path
    ) -> None:
        # No skill has the canonical block.
        marketplace_root = _build_synthetic_marketplace(
            tmp_path,
            canonical_blocks={desc.notation: False for desc in IN_SCOPE_SCRIPTS},
        )
        findings = check_missing_canonical_blocks(marketplace_root)

        # Dedup means one finding per unique skill_dir; the 14 notations
        # map to 14 distinct skill dirs, so 14 findings are expected.
        assert len(findings) == len(IN_SCOPE_SCRIPTS)
        for f in findings:
            assert f['rule_id'] == RULE_MISSING_CANONICAL_BLOCK
            assert f['severity'] == 'warning'
            assert f['details']['reason'] == 'missing_canonical_block'
            assert 'canonical_hint' in f['details']

    def test_present_block_is_not_flagged(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(
            tmp_path,
            canonical_blocks={desc.notation: True for desc in IN_SCOPE_SCRIPTS},
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings == []

    def test_mixed_state_only_missing_flagged(self, tmp_path: Path) -> None:
        # Exactly one skill has the block — every other in-scope skill flagged.
        first = IN_SCOPE_SCRIPTS[0].notation
        canonical_blocks = {desc.notation: False for desc in IN_SCOPE_SCRIPTS}
        canonical_blocks[first] = True
        marketplace_root = _build_synthetic_marketplace(
            tmp_path, canonical_blocks=canonical_blocks
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert len(findings) == len(IN_SCOPE_SCRIPTS) - 1
        flagged_notations = {f['details']['notation'] for f in findings}
        assert first not in flagged_notations

    def test_block_heading_is_case_insensitive(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(
            tmp_path,
            canonical_blocks={desc.notation: False for desc in IN_SCOPE_SCRIPTS},
        )
        # Pick one skill, overwrite its SKILL.md with a lower-case heading.
        first = IN_SCOPE_SCRIPTS[0]
        skill_md = marketplace_root / 'marketplace' / first.skill_dir_relpath / 'SKILL.md'
        skill_md.write_text(
            '# Skill\n\n## canonical INVOCATIONS\n\n### run\n',
            encoding='utf-8',
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        flagged_notations = {f['details']['notation'] for f in findings}
        assert first.notation not in flagged_notations


# ---------------------------------------------------------------------------
# Layer E — per-skill scanner end-to-end.
# ---------------------------------------------------------------------------


class TestSkillScanner:
    """``scan_skill_for_manage_invocation`` walks SKILL.md + standards/refs/etc."""

    def test_scanner_picks_up_skill_md_invocations(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(
            f'# Skill\npython3 .plan/execute-script.py {_SYN_NOTATION} zzz --x y\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'subcommand_unknown'
        assert findings[0]['file'].endswith('SKILL.md')

    def test_scanner_aggregates_subdoc_findings(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        (skill_dir / 'standards').mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text('# clean\n', encoding='utf-8')
        (skill_dir / 'standards' / 'rules.md').write_text(
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --bogus z\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        # ``foo`` is registered (no subcommand finding), --alpha is missing
        # (required_flag_missing), and --bogus is unknown (flag_unknown).
        reasons = {f['details']['reason'] for f in findings}
        assert reasons == {'flag_unknown', 'required_flag_missing'}

    def test_scanner_returns_empty_for_clean_skill(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text(
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_invocation(skill_dir, flat_index)
        assert findings == []

    def test_scanner_handles_missing_directory(
        self, tmp_path: Path, flat_index: dict
    ) -> None:
        findings = scan_skill_for_manage_invocation(
            tmp_path / 'nonexistent', flat_index
        )
        assert findings == []


# ---------------------------------------------------------------------------
# Layer F — Finding payload shape (schema contract).
# ---------------------------------------------------------------------------


class TestFindingPayloadShape:
    """All findings carry the documented schema fields."""

    def test_payload_contains_required_keys_invocation_rule(
        self, flat_index: dict
    ) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/path/to/SKILL.md', flat_index
        )
        assert findings
        f = findings[0]
        for key in (
            'rule_id',
            'type',
            'file',
            'line',
            'severity',
            'fixable',
            'description',
            'details',
        ):
            assert key in f, f'missing required key {key}'
        assert f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['type'] == RULE_MANAGE_INVOCATION_INVALID
        assert f['file'] == '/path/to/SKILL.md'
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False

    def test_payload_contains_required_keys_canonical_block_rule(
        self, tmp_path: Path
    ) -> None:
        marketplace_root = _build_synthetic_marketplace(
            tmp_path,
            canonical_blocks={desc.notation: False for desc in IN_SCOPE_SCRIPTS},
        )
        findings = check_missing_canonical_blocks(marketplace_root)
        assert findings
        f = findings[0]
        for key in (
            'rule_id',
            'type',
            'file',
            'line',
            'severity',
            'fixable',
            'description',
            'details',
        ):
            assert key in f, f'missing required key {key}'
        assert f['rule_id'] == RULE_MISSING_CANONICAL_BLOCK
        assert f['severity'] == 'warning'
        assert f['line'] == 1

    def test_canonical_hint_present_in_details(self, flat_index: dict) -> None:
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --bogus v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/fake/SKILL.md', flat_index
        )
        assert findings
        details = findings[0]['details']
        assert 'canonical_hint' in details
        assert _SYN_NOTATION in details['canonical_hint']

    def test_line_number_anchored(self, flat_index: dict) -> None:
        content = (
            '# Title\n'
            '\n'
            '\n'
            f'python3 .plan/execute-script.py {_SYN_NOTATION} zzz --alpha v\n'
        )
        findings = analyze_manage_invocation_markdown(
            content, '/fake/SKILL.md', flat_index
        )
        assert findings
        assert findings[0]['line'] == 4


# ---------------------------------------------------------------------------
# Layer G — Marketplace-wide aggregator + build_script_index resolution.
# ---------------------------------------------------------------------------


class TestMarketplaceAggregator:
    """``scan_manage_invocation`` combines markdown + canonical-block findings."""

    def test_index_includes_only_resolvable_scripts(self, tmp_path: Path) -> None:
        # Only the first in-scope script gets a real on-disk script;
        # the rest are absent from the synthetic tree.
        marketplace_root = tmp_path / 'mp'
        first = IN_SCOPE_SCRIPTS[0]
        skill_dir = marketplace_root / 'marketplace' / first.skill_dir_relpath
        skill_dir.mkdir(parents=True)
        (skill_dir / 'scripts').mkdir()
        script_path = (
            marketplace_root / 'marketplace' / first.script_relpath
        )
        script_path.write_text(_flat_script_source(), encoding='utf-8')

        index = build_script_index(marketplace_root)
        assert first.notation in index
        assert len(index) == 1

    def test_aggregator_runs_both_rules(self, tmp_path: Path) -> None:
        marketplace_root = _build_synthetic_marketplace(
            tmp_path,
            canonical_blocks={desc.notation: False for desc in IN_SCOPE_SCRIPTS},
        )
        bundles_dir = marketplace_root / 'marketplace' / 'bundles'
        bundles_dir.mkdir(parents=True, exist_ok=True)
        # Add one bundle markdown with a bad invocation against the first
        # in-scope notation (which the synthetic script declares ``run`` for).
        first = IN_SCOPE_SCRIPTS[0]
        consumer_md = (
            bundles_dir / 'consumer-bundle' / 'skills' / 'consumer-skill' / 'SKILL.md'
        )
        consumer_md.parent.mkdir(parents=True)
        consumer_md.write_text(
            f'python3 .plan/execute-script.py {first.notation} zzz --x y\n',
            encoding='utf-8',
        )

        findings = scan_manage_invocation(marketplace_root)
        # At least one of each rule.
        rule_ids = {f['rule_id'] for f in findings}
        assert RULE_MANAGE_INVOCATION_INVALID in rule_ids
        assert RULE_MISSING_CANONICAL_BLOCK in rule_ids


# ---------------------------------------------------------------------------
# Layer F — robustness fixes for gemini review feedback (PR #372).
# ---------------------------------------------------------------------------


class TestMultiLineBackslashContinuation:
    """Backslash-continued invocations are joined before flag validation."""

    def test_flags_on_continuation_lines_are_recognized(self, flat_index: dict) -> None:
        """Invocation spread across multiple lines with ``\\`` continuations.

        Before the fix, ``--alpha`` on the first physical line satisfied
        the required-flag check, but the rest of the invocation was
        discarded. After the fix, the joined logical line is what we
        validate against — the canonical multi-line form must produce
        zero findings.
        """
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo \\\n'
            f'  --alpha v1 \\\n'
            f'  --beta v2\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_continuation_does_not_swallow_unknown_flag(self, flat_index: dict) -> None:
        """An unknown flag on a continuation line is still surfaced."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo \\\n'
            f'  --alpha v1 \\\n'
            f'  --nope v3\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'flag_unknown'
        assert f['details']['flag'] == 'nope'

    def test_finding_line_anchored_to_logical_start(self, flat_index: dict) -> None:
        """Findings on a continuation line report the starting line number."""
        content = (
            '# heading\n'  # line 1
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo --alpha v \\\n'  # line 2
            '  --nope v\n'  # line 3 (physical-only)
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['line'] == 2
        assert findings[0]['details']['reason'] == 'flag_unknown'


class TestShellQuotingFalsePositives:
    """Flag-like text inside quoted argument values is not parsed as a flag."""

    def test_double_quoted_value_with_dashes_is_not_a_flag(self, flat_index: dict) -> None:
        """``--message "release: --not-a-flag"`` parses one flag (--message)."""
        # Add a known --message flag to the synthetic root parser for the
        # purposes of this test by re-using the alpha flag of foo. The fix
        # under test is independent of which flag is whitelisted — what
        # matters is that ``--not-a-flag`` inside the double-quoted value
        # does NOT produce a flag_unknown finding.
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha "release: --not-a-flag"\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_single_quoted_value_with_dashes_is_not_a_flag(self, flat_index: dict) -> None:
        """``--alpha '--not-a-flag'`` (single quotes) is also handled."""
        content = (
            f"python3 .plan/execute-script.py {_SYN_NOTATION} foo "
            f"--alpha '--not-a-flag'\n"
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert findings == []

    def test_unquoted_flag_still_validated(self, flat_index: dict) -> None:
        """Quoting suppresses only the quoted region — unquoted flags still parse."""
        content = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} foo '
            f'--alpha "in quotes --safe" --nope unsafe\n'
        )
        findings = analyze_manage_invocation_markdown(content, '/fake/SKILL.md', flat_index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'nope'


class TestFlatSubcommandWithPositionalArgs:
    """A flat subcommand that accepts positional args still gets flag validation."""

    def test_positional_after_flat_subcommand_does_not_block_flag_check(
        self, tmp_path: Path
    ) -> None:
        """Pre-fix bug: a second positional token under a flat subcommand
        caused ``get_leaf`` to return ``None`` and skip flag validation
        for commands like ``architecture path SOURCE TARGET --json``.
        """
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='command')
                    path = subparsers.add_parser('path')
                    path.add_argument('source')
                    path.add_argument('target')
                    path.add_argument('--json', action='store_true')
                    return parser
            ''').lstrip(),
            encoding='utf-8',
        )
        tree = build_script_tree(script)
        assert tree is not None

        index = {_SYN_NOTATION: tree}
        # Canonical invocation with positional args + known flag — clean.
        clean = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} path src dst --json\n'
        )
        findings = analyze_manage_invocation_markdown(clean, '/fake/SKILL.md', index)
        assert findings == []

        # Same shape with an unknown flag — exactly one finding (proves
        # flag validation actually runs after the positional tokens).
        bad = (
            f'python3 .plan/execute-script.py {_SYN_NOTATION} path src dst --nope\n'
        )
        findings = analyze_manage_invocation_markdown(bad, '/fake/SKILL.md', index)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'flag_unknown'
        assert findings[0]['details']['flag'] == 'nope'


class TestMutuallyExclusiveGroupSupport:
    """Flags declared on ``add_mutually_exclusive_group`` are honored."""

    def test_group_flags_attach_to_parent_leaf(self, tmp_path: Path) -> None:
        """``group = parser.add_mutually_exclusive_group()`` followed by
        ``group.add_argument('--a')`` registers ``--a`` on the parent
        parser. Pre-fix, the receiver ``group`` was not in
        ``parser_kind`` and the flag was silently dropped.
        """
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    group = parser.add_mutually_exclusive_group(required=True)
                    group.add_argument('--by-id')
                    group.add_argument('--by-name')
                    parser.add_argument('--debug', action='store_true')
                    return parser
            ''').lstrip(),
            encoding='utf-8',
        )
        tree = build_script_tree(script)
        assert tree is not None
        # Root leaf carries the three flags (group + non-group).
        assert tree.root.flags == {'by-id', 'by-name', 'debug'}

    def test_argument_group_flags_attach_to_parent_leaf(self, tmp_path: Path) -> None:
        """``parser.add_argument_group(...)`` is also aliased to the parent."""
        script = tmp_path / 'syn.py'
        script.write_text(
            textwrap.dedent('''
                import argparse

                def main():
                    parser = argparse.ArgumentParser()
                    subparsers = parser.add_subparsers(dest='command')
                    run = subparsers.add_parser('run')
                    grp = run.add_argument_group('output')
                    grp.add_argument('--json', action='store_true')
                    grp.add_argument('--quiet', action='store_true')
                    return parser
            ''').lstrip(),
            encoding='utf-8',
        )
        tree = build_script_tree(script)
        assert tree is not None
        leaf = tree.get_leaf('run', None)
        assert leaf is not None
        assert leaf.flags == {'json', 'quiet'}
