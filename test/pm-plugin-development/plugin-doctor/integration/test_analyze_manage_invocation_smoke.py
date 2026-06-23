#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Real-tree integration smokes for the manage-invocation analyzer.

EXCLUDED from the default ``module-tests`` run — registered in the root
``test/conftest.py`` ``collect_ignore`` list, mirroring the established
``test/plan-marshall/integration/`` segregation pattern. These are the only
manage-invocation tests that probe the REAL ``.plan/execute-script.py``
executor and derive a real script's ``--help`` surface; the per-shape /
per-finding-type coverage lives in the sibling in-process unit suite
(``test_analyze_manage_invocation.py``) against synthetic argparse scripts
behind an in-process shim.

Two smokes are retained — both assert ZERO ``manage-invocation-invalid``
false positives against the real shipped bundle for the loop-registered,
shared-flag, and many-subcommand shapes that broke the old AST extractor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import load_script_module

# ---------------------------------------------------------------------------
# Module loader — load the analyzer directly from the marketplace scripts dir.
# Underscore-prefixed analyzers are not importable through the executor, so we
# spec-load the module by file path the same way the doctor harness does.
# ---------------------------------------------------------------------------

_ami = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_manage_invocation.py',
    '_analyze_manage_invocation',
)

analyze_manage_invocation_markdown = _ami.analyze_manage_invocation_markdown
derive_script_tree = _ami.derive_script_tree
RULE_MANAGE_INVOCATION_INVALID = _ami.RULE_MANAGE_INVOCATION_INVALID

# Repository (worktree) root:
# test/pm-plugin-development/plugin-doctor/integration/ -> 4 up.
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _real_executor() -> Path | None:
    """Resolve the real ``.plan/execute-script.py`` for the live bundle.

    Returns ``None`` when the executor is not present (e.g. an unconfigured
    checkout) so the dependent tests skip rather than fail spuriously.
    """
    candidate = PROJECT_ROOT / '.plan' / 'execute-script.py'
    return candidate if candidate.is_file() else None


class TestRealMarketplaceZeroFalsePositives:
    """The corrected analyzer must not flag correctly-authored canonical calls.

    The AST extractor produced 1323 false positives in plan-marshall alone
    (loop/helper-registered subcommands invisible, shared flags dropped).
    The ``--help`` derivation derives the real surface, so canonical calls in
    the shipped docs — the exact loop-registered subcommands and shared flags
    that broke the AST extractor — must produce ZERO ``manage-invocation-invalid``
    findings.

    The surface is derived per-notation (``derive_script_tree``) against the
    live executor rather than via a whole-marketplace ``build_script_index``
    so the test cost stays bounded to the two notations under test.
    """

    def test_loop_and_shared_flag_calls_not_flagged_in_real_bundle(self) -> None:
        executor = _real_executor()
        if executor is None:
            pytest.skip('real executor not present in this checkout')
        # manage-logging registers work/decision via a loop; --plan-id/--level/
        # --message are shared across them — the exact shapes the AST extractor
        # mis-flagged.
        notation = 'plan-marshall:manage-logging:manage-logging'
        tree = derive_script_tree(notation, executor)
        assert tree is not None, 'manage-logging --help must be reachable'
        index = {notation: tree}
        canonical_calls = [
            f'python3 .plan/execute-script.py {notation} work '
            f'--plan-id p --level INFO --message "[STATUS] hi"',
            f'python3 .plan/execute-script.py {notation} decision '
            f'--plan-id p --level INFO --message "(skill) decided"',
            f'python3 .plan/execute-script.py {notation} separator --plan-id p',
        ]
        for call in canonical_calls:
            findings = analyze_manage_invocation_markdown(
                call + '\n', '/fake/SKILL.md', index
            )
            invalid = [
                f for f in findings
                if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
            ]
            assert invalid == [], f'false positive(s) for canonical call: {call}\n{invalid}'

    def test_many_subcommand_calls_not_flagged_in_real_bundle(self) -> None:
        executor = _real_executor()
        if executor is None:
            pytest.skip('real executor not present in this checkout')
        notation = 'plan-marshall:manage-status:manage-status'
        tree = derive_script_tree(notation, executor)
        assert tree is not None, 'manage-status --help must be reachable'
        index = {notation: tree}
        # Subcommands the AST extractor commonly dropped.
        canonical_calls = [
            f'python3 .plan/execute-script.py {notation} read --plan-id p',
            f'python3 .plan/execute-script.py {notation} get-worktree-path --plan-id p',
            f'python3 .plan/execute-script.py {notation} transition --plan-id p --completed 5-execute',
        ]
        for call in canonical_calls:
            findings = analyze_manage_invocation_markdown(
                call + '\n', '/fake/SKILL.md', index
            )
            invalid = [
                f for f in findings
                if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
            ]
            assert invalid == [], f'false positive(s) for canonical call: {call}\n{invalid}'
