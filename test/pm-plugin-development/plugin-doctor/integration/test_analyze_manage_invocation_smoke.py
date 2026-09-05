#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-tree integration smokes for the manage-invocation analyzer.

COLLECTED in the default ``module-tests`` run. These smokes derive a real
script's ``--help`` surface through a real executor, and the per-shape /
per-finding-type coverage lives in the sibling in-process unit suite
(``test_analyze_manage_invocation.py``) against synthetic argparse scripts
behind an in-process shim.

The executor they probe is BUILT BY :func:`built_executor` into a session
temporary directory — it is not the tracked ``.plan/execute-script.py``. That
file is gitignored, so keying these smokes to it made them skip on any checkout
that had not run the generator, which is most CI runners: the suite reported
green while three of the analyzer's only real-surface checks had not run.
Building one from the shipped generator removes the precondition instead of
guarding it.

Three smokes — each asserts ZERO ``manage-invocation-invalid`` false positives
against the real shipped bundle for a shape that broke the old AST extractor:
loop-registered subcommands with shared flags, a many-subcommand script, and
(added with the consolidation) a documented ``aliases=`` invocation.

``derive_script_tree`` is imported from the analyzer, which is now a thin
adapter over the shared ``plan-marshall:script-shared`` ``argparse_surface``
derivation — so these smokes exercise the CONSOLIDATED entry point, the same
one the executor generator reads.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT, load_script_module

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

#: The shipped generator these smokes build their executor from — the same one
#: ``/marshall-steward`` and the phase-5 move-in run.
_GENERATOR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-script-executor'
    / 'scripts'
    / 'generate_executor.py'
)


@pytest.fixture(scope='session')
def built_executor(tmp_path_factory) -> Path:
    """A real executor, generated into a session temporary directory.

    Built once per session because generation costs a subprocess and all three
    smokes probe the same surface. The executor is a genuine one produced by the
    shipped generator against the real ``marketplace/bundles`` tree, so the
    ``--help`` surfaces the smokes derive are the shipped scripts' own.

    ``PM_SURFACE_BUDGET_SECONDS=0`` disables the per-parser-node accept-set
    derivation, which the generator documents as safe against a fresh target that
    carries no previous surfaces — and this target is always fresh. It is what
    keeps the fixture cheap: the derivation's default allowance is 180 seconds,
    and these smokes need the executor only to DISPATCH, never to pre-spawn
    validate.

    ``PLAN_TRACKED_CONFIG_DIR`` pins where the executor is written, ahead of both
    the inherited ``PLAN_BASE_DIR`` and the generator's cwd walk, so the build
    cannot land on the tracked ``.plan/execute-script.py`` no matter what the
    ambient environment says.

    Raises through an assertion naming the generator's own output when the build
    fails: an unbuildable executor is a broken environment, not one these smokes
    do not apply to.
    """
    assert _GENERATOR.is_file(), f'Executor generator not found at {_GENERATOR}'

    root = tmp_path_factory.mktemp('built-executor')
    plan_dir = root / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{}', encoding='utf-8')

    env = os.environ.copy()
    env['PLAN_TRACKED_CONFIG_DIR'] = str(plan_dir)
    env['PLAN_BASE_DIR'] = str(plan_dir)
    env['PM_SURFACE_BUDGET_SECONDS'] = '0'

    result = subprocess.run(
        [
            'python3',
            str(_GENERATOR),
            'generate',
            '--marketplace',
            '--marketplace-root',
            str(PROJECT_ROOT),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )

    executor = plan_dir / 'execute-script.py'
    assert result.returncode == 0, (
        f'Executor generation failed (exit {result.returncode}).\n'
        f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
    assert executor.is_file(), (
        f'Executor generation reported success but wrote no file at {executor}.\n'
        f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    )
    assert executor != PROJECT_ROOT / '.plan' / 'execute-script.py', (
        'The fixture built the tracked executor instead of a temporary one'
    )
    return executor


class TestRealMarketplaceZeroFalsePositives:
    """The corrected analyzer must not flag correctly-authored canonical calls.

    The AST extractor produced 1323 false positives in plan-marshall alone
    (loop/helper-registered subcommands invisible, shared flags dropped).
    The ``--help`` derivation derives the real surface, so canonical calls in
    the shipped docs — the exact loop-registered subcommands and shared flags
    that broke the AST extractor — must produce ZERO ``manage-invocation-invalid``
    findings.

    The surface is derived per-notation (``derive_script_tree``) against the
    fixture-built executor rather than via a whole-marketplace
    ``build_script_index`` so the test cost stays bounded to the notations
    under test.
    """

    def test_loop_and_shared_flag_calls_not_flagged_in_real_bundle(self, built_executor: Path) -> None:
        # manage-logging registers work/decision via a loop; --plan-id/--level/
        # --message are shared across them — the exact shapes the AST extractor
        # mis-flagged.
        notation = 'plan-marshall:manage-logging:manage-logging'
        tree = derive_script_tree(notation, built_executor)
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

    def test_documented_alias_calls_not_flagged_in_real_bundle(self, built_executor: Path) -> None:
        """The three accepted read-verb aliases resolve against the real surface.

        The coverage the consolidation adds. The replaced AST walk never read
        ``aliases=``, so every one of these documented calls was an unknown
        subcommand to it — a false rejection of the project's own canonical
        forms.
        """
        alias_calls = {
            'plan-marshall:manage-tasks:manage-tasks': 'get --plan-id p --task-number 1',
            'plan-marshall:manage-status:manage-status': 'get --plan-id p',
            'plan-marshall:manage-lessons:manage-lessons': 'read --lesson-id L-1',
        }
        for notation, tail in alias_calls.items():
            tree = derive_script_tree(notation, built_executor)
            assert tree is not None, f'{notation} --help must be reachable'
            call = f'python3 .plan/execute-script.py {notation} {tail}'
            findings = analyze_manage_invocation_markdown(
                call + '\n', '/fake/SKILL.md', {notation: tree}
            )
            invalid = [
                f for f in findings
                if f['rule_id'] == RULE_MANAGE_INVOCATION_INVALID
                and f['details'].get('reason') == 'subcommand_unknown'
            ]
            assert invalid == [], (
                f'documented alias invocation flagged as unknown subcommand: '
                f'{call}\n{invalid}'
            )

    def test_many_subcommand_calls_not_flagged_in_real_bundle(self, built_executor: Path) -> None:
        notation = 'plan-marshall:manage-status:manage-status'
        tree = derive_script_tree(notation, built_executor)
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
