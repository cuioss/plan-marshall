#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for the ``script-call-drift`` plugin-doctor rule.

The analyzer parses argparse ``--help`` output for documented executor
invocations in skill markdown and emits drift findings when documented
verbs or flags are absent from the published interface.

Replaces the runtime SUBCOMMANDS pre-flight validator removed in plan
``fix-generate-executor-ast-subcommands``. Tests cover the parser
internals (no subprocess), then the end-to-end analyzer with a fake
executor that emits controlled ``--help`` output.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from conftest import load_script_module

# ---------------------------------------------------------------------------
# Module loader — spec-load the analyzer directly. Underscore-prefixed
# analyzers are not importable through the executor.
# ---------------------------------------------------------------------------


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ascd = _load_module('_analyze_script_call_drift', '_analyze_script_call_drift.py')

analyze_script_call_drift = _ascd.analyze_script_call_drift
_extract_invocations = _ascd._extract_invocations
_parse_subcommand_choices = _ascd._parse_subcommand_choices
_parse_flag_names = _ascd._parse_flag_names


# =============================================================================
# Invocation extractor
# =============================================================================


def test_extract_invocations_finds_simple_verb():
    """A single notation + verb invocation is extracted with the verb chain."""
    content = (
        'Run the following:\n'
        '\n'
        '```bash\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read --plan-id foo\n'
        '```\n'
    )
    invocations = _extract_invocations(content)

    assert len(invocations) == 1
    line, notation, verbs, flags = invocations[0]
    assert notation == 'plan-marshall:manage-status:manage-status'
    assert verbs == ['read']
    assert '--plan-id' in flags


def test_extract_invocations_skips_placeholder_verbs():
    """A verb that is a template placeholder (`{value}`) is not extracted."""
    content = (
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status {verb} --plan-id foo\n'
    )
    invocations = _extract_invocations(content)
    assert len(invocations) == 1
    _, _, verbs, flags = invocations[0]
    assert verbs == []
    assert '--plan-id' in flags


def test_extract_invocations_handles_no_verb():
    """A bare notation with no verb yields an empty verb chain."""
    content = 'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status --help\n'
    invocations = _extract_invocations(content)
    assert len(invocations) == 1
    _, notation, verbs, _ = invocations[0]
    assert notation == 'plan-marshall:manage-status:manage-status'
    assert verbs == []


def test_extract_invocations_multiple_in_one_file():
    """Multiple invocations in one file are all extracted with correct line numbers."""
    content = (
        '# Heading\n'
        '\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read --plan-id A\n'
        '\n'
        'python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create --plan-id B\n'
    )
    invocations = _extract_invocations(content)
    assert len(invocations) == 2
    assert invocations[0][2] == ['read']
    assert invocations[1][2] == ['create']
    # Line numbers are 1-based and monotonically increasing.
    assert invocations[0][0] < invocations[1][0]


def test_extract_invocations_collects_nested_verb_chain():
    """Nested subparser invocations capture every positional verb in order."""
    content = (
        'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings '
        'qgate list --plan-id foo --phase 5-execute\n'
    )
    invocations = _extract_invocations(content)
    assert len(invocations) == 1
    _, notation, verbs, flags = invocations[0]
    assert notation == 'plan-marshall:manage-findings:manage-findings'
    assert verbs == ['qgate', 'list']
    assert '--plan-id' in flags
    assert '--phase' in flags


# =============================================================================
# --help parsers
# =============================================================================


def test_parse_subcommand_choices_single_block():
    """Standard argparse choices block is parsed correctly."""
    help_text = textwrap.dedent(
        """\
        usage: manage-status.py [-h] {create,read,update,archive,list} ...

        positional arguments:
          {create,read,update,archive,list}

        options:
          -h, --help            show this help message and exit
        """
    )
    choices = _parse_subcommand_choices(help_text)
    assert choices == {'create', 'read', 'update', 'archive', 'list'}


def test_parse_subcommand_choices_empty_when_no_subparsers():
    """A help text without subparsers returns an empty set."""
    help_text = textwrap.dedent(
        """\
        usage: single-action.py [-h] [--foo FOO]

        options:
          -h, --help            show this help message and exit
          --foo FOO             do the thing
        """
    )
    choices = _parse_subcommand_choices(help_text)
    assert choices == set()


def test_parse_flag_names_extracts_long_form_flags():
    """All `--flag` tokens from the options block are captured."""
    help_text = textwrap.dedent(
        """\
        usage: manage-tasks.py [-h] --plan-id PLAN_ID [--include-context]

        options:
          -h, --help            show this help message and exit
          --plan-id PLAN_ID     The plan identifier
          --include-context     Include surrounding context
        """
    )
    flags = _parse_flag_names(help_text)
    assert '--help' in flags
    assert '--plan-id' in flags
    assert '--include-context' in flags


# =============================================================================
# End-to-end analyzer with a fake executor
# =============================================================================


def _make_fake_executor(tmp_path: Path) -> Path:
    """Create a fake .plan/execute-script.py that emits scripted --help output.

    The fake recognizes two notations:
      - ``pkg:skill:multi`` → subcommands {alpha, bravo}; alpha has --foo, --bar
      - ``pkg:skill:single`` → single-action script with --baz

    Any other notation produces empty help (the analyzer treats this as
    "no choices found" and skips verb checking).
    """
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    executor = plan_dir / 'execute-script.py'
    executor.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys

            args = sys.argv[1:]
            if not args:
                sys.exit(0)

            notation = args[0]
            rest = args[1:]
            is_help = '--help' in rest

            if not is_help:
                sys.exit(0)

            non_help = [a for a in rest if a != '--help']

            if notation == 'pkg:skill:multi':
                if not non_help:
                    print('usage: multi.py [-h] {alpha,bravo} ...')
                    print('positional arguments:')
                    print('  {alpha,bravo}')
                    print('options:')
                    print('  -h, --help    show this help message and exit')
                elif non_help[0] == 'alpha':
                    print('usage: multi.py alpha [-h] [--foo FOO] [--bar BAR]')
                    print('options:')
                    print('  -h, --help     show this help message and exit')
                    print('  --foo FOO      foo arg')
                    print('  --bar BAR      bar arg')
                elif non_help[0] == 'bravo':
                    print('usage: multi.py bravo [-h] [--qux QUX]')
                    print('options:')
                    print('  -h, --help     show this help message and exit')
                    print('  --qux QUX      qux arg')
            elif notation == 'pkg:skill:single':
                print('usage: single.py [-h] [--baz BAZ]')
                print('options:')
                print('  -h, --help     show this help message and exit')
                print('  --baz BAZ      baz arg')

            sys.exit(0)
            """
        )
    )
    return executor


def _make_marketplace_with_skill(tmp_path: Path, markdown_body: str) -> Path:
    """Build a minimal marketplace tree with one skill containing markdown_body."""
    bundles = tmp_path / 'marketplace' / 'bundles'
    skill_dir = bundles / 'fake-bundle' / 'skills' / 'fake-skill'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(markdown_body)
    return bundles


def test_known_verb_produces_no_finding(tmp_path):
    """A documented verb that matches --help output produces no finding."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:multi alpha --foo bar\n',
    )

    findings = analyze_script_call_drift(bundles)
    assert findings == []


def test_invented_verb_emits_verb_not_in_subcommand_list(tmp_path):
    """A verb missing from --help output emits a verb_not_in_subcommand_list finding."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:multi invented-verb\n',
    )

    findings = analyze_script_call_drift(bundles)
    assert len(findings) == 1
    finding = findings[0]
    assert finding['type'] == 'verb_not_in_subcommand_list'
    assert finding['notation'] == 'pkg:skill:multi'
    assert finding['invented_verb'] == 'invented-verb'
    assert sorted(finding['valid_choices']) == ['alpha', 'bravo']


def test_invented_flag_emits_flag_not_in_options(tmp_path):
    """A documented --flag missing from --help output emits flag_not_in_options."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:multi alpha --invented-flag value\n',
    )

    findings = analyze_script_call_drift(bundles)
    assert len(findings) == 1
    finding = findings[0]
    assert finding['type'] == 'flag_not_in_options'
    assert finding['notation'] == 'pkg:skill:multi'
    assert finding['verb'] == 'alpha'
    assert finding['invented_flag'] == '--invented-flag'


def test_single_action_script_skips_verb_check(tmp_path):
    """A single-action script (no subparsers) does not produce verb findings."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:single some-positional --baz value\n',
    )

    findings = analyze_script_call_drift(bundles)
    # No findings — single-action scripts skip verb checking, and --baz is valid.
    assert findings == []


def test_help_and_audit_plan_id_flags_exempt(tmp_path):
    """--help and --audit-plan-id are universal flags handled by the executor."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:multi alpha --help --audit-plan-id foo\n',
    )

    findings = analyze_script_call_drift(bundles)
    assert findings == []


def test_caching_one_help_call_per_unique_notation(tmp_path, monkeypatch):
    """The analyzer caches --help output to avoid N² subprocess overhead."""
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        (
            'python3 .plan/execute-script.py pkg:skill:multi alpha --foo x\n'
            'python3 .plan/execute-script.py pkg:skill:multi bravo --qux y\n'
            'python3 .plan/execute-script.py pkg:skill:multi alpha --bar z\n'
        ),
    )

    call_count = {'n': 0}
    original_run_help = _ascd._run_help

    def counting_run_help(executor, args):
        call_count['n'] += 1
        return original_run_help(executor, args)

    monkeypatch.setattr(_ascd, '_run_help', counting_run_help)

    findings = analyze_script_call_drift(bundles)

    # No findings expected (all verbs and flags are valid).
    assert findings == []
    # Expected calls: 1 for notation choices + 2 for (multi, alpha) and (multi, bravo) flags.
    # The two `alpha` invocations share the (notation, verb) cache entry.
    assert call_count['n'] == 3


def test_no_executor_returns_empty(tmp_path):
    """When the executor is missing, the rule no-ops silently."""
    bundles = _make_marketplace_with_skill(
        tmp_path,
        'python3 .plan/execute-script.py pkg:skill:multi invented-verb\n',
    )

    # No .plan/execute-script.py — the rule cannot probe, returns [].
    findings = analyze_script_call_drift(bundles)
    assert findings == []


# =============================================================================
# Detection literal RETAINED — documented executor-proxy form is the anchor
# =============================================================================


def test_documented_executor_proxy_form_remains_detection_anchor(tmp_path):
    """The ``python3 .plan/execute-script.py {notation}`` literal is RETAINED.

    The path-resolution consolidation (adoption of
    ``file_ops.get_executor_path()``) changed how production *code* locates the
    executor at runtime — it did NOT change the documented invocation
    convention. Skill markdown still uses the executor-proxy form, and this
    drift detector must continue to parse it: a documented invocation with an
    invalid verb is still flagged via the retained literal.
    """
    _make_fake_executor(tmp_path)
    bundles = _make_marketplace_with_skill(
        tmp_path,
        # The canonical documented form — still the detection anchor.
        'python3 .plan/execute-script.py pkg:skill:multi invented-verb\n',
    )

    findings = analyze_script_call_drift(bundles)
    assert len(findings) == 1
    assert findings[0]['type'] == 'verb_not_in_subcommand_list'
    assert findings[0]['invented_verb'] == 'invented-verb'
