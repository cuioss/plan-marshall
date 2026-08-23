#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The argument-naming cluster resolves flags against the layer that ACCEPTS them.

``ARGUMENT_NAMING_FLAG_UNKNOWN`` used to judge every documented flag against the
help-derived argparse table alone. That table is not the layer that accepts: some
flags are consumed by the EXECUTOR / router before the target script's argparse
ever sees argv, so they appear in no node's ``--help`` and yet every documented
call carrying them works. Judging those against the argparse table manufactured a
finding against a correct invocation — the over-rejection direction the module's
own asymmetric-error rule forbids.

The empirical basis, measured live rather than assumed. All eight scripts whose
prose documents ``--audit-plan-id`` were probed three ways — invoke WITH the flag,
invoke with an arbitrary unknown flag, read ``--help``:

===================================== ======== ============ ==========
Script                                accepts  rejects      declares
                                      the flag a bogus flag it in help
===================================== ======== ============ ==========
manage-config                         yes      yes          no
manage-architecture                   yes      yes          no
manage-findings                       yes      yes          no
manage-logging                        yes      yes          no
manage-references                     yes      yes          no
manage-solution-outline               yes      yes          no
manage-plan-documents                 yes      yes          no
scan-marketplace-inventory            yes      yes          no
===================================== ======== ============ ==========

8/8 accept, 8/8 still reject an arbitrary unknown flag, 0/8 declare it. So the
acceptance is real and it is NOT a blanket "anything goes" — which is exactly the
pair this module pins.

Two matched pairs, because the fix has two halves that can each fail alone:

1. **Acceptance** — a router-consumed flag must NOT be flagged, while a
   genuinely-unknown flag on the SAME invocation MUST be. Without the second
   half, "no finding for ``--audit-plan-id``" would be satisfied just as well by
   a cluster that stopped reporting anything.
2. **Placement** — the acceptance widening must not leak into
   ``ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED``. ``--audit-plan-id`` is
   position-independent (the executor strips it wherever it was written), but
   ``--plan-id`` / ``--project-dir`` are ordinary root ``add_argument``
   declarations on many scripts and argparse DOES reject them after the verb:

       architecture which-module --path P --plan-id X

   exits 2 with ``unrecognized arguments``. A blanket exemption of
   ``UNIVERSAL_FLAGS`` from the placement rule would have traded one false
   finding for a silenced true one.
"""

from __future__ import annotations

from pathlib import Path

from _plugin_doctor_dispatching_executor import write_dispatching_executor
from conftest import load_script_module

_aan = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_argument_naming.py',
    '_analyze_argument_naming_router_consumed',
)
analyze_argument_naming = _aan.analyze_argument_naming
scan_router_flag_placement = _aan.scan_router_flag_placement
_ScriptEntry = _aan._ScriptEntry

#: The router-consumed flag the corpus census attributed 68 of 129 findings to.
ROUTER_CONSUMED_FLAG = 'audit-plan-id'

#: A flag no script declares and no layer consumes — the matched negative half.
GENUINELY_UNKNOWN_FLAG = 'finding-type'

NOTATION = 'plan-marshall:manage-architecture:architecture'


def _write_script(marketplace_root: Path, notation: str, verb: str, flags: list[str]) -> None:
    """Write a synthetic argparse script declaring ONE verb and its flags."""
    bundle, skill, script_name = notation.split(':', 2)
    scripts_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    parts = [
        '#!/usr/bin/env python3',
        '"""Synthetic fixture script for router-consumed-flag tests."""',
        'import argparse',
        '',
        'parser = argparse.ArgumentParser()',
        'subparsers = parser.add_subparsers(dest="command")',
        f'p = subparsers.add_parser("{verb}")',
    ]
    parts.extend(f'p.add_argument("--{flag}")' for flag in flags)
    parts.extend(['', 'if __name__ == "__main__":', '    parser.parse_args()'])
    (scripts_dir / f'{script_name}.py').write_text('\n'.join(parts) + '\n', encoding='utf-8')


def _write_invocation(marketplace_root: Path, invocation: str) -> Path:
    """Write a SKILL.md carrying exactly one executor invocation line."""
    skill_dir = marketplace_root / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture'
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text(
        f'# Architecture\n\n```bash\npython3 .plan/execute-script.py {invocation}\n```\n',
        encoding='utf-8',
    )
    return skill_md


def _flag_findings(marketplace_root: Path) -> list[dict]:
    findings = analyze_argument_naming(marketplace_root)
    return [f for f in findings if f.get('rule_id') == 'ARGUMENT_NAMING_FLAG_UNKNOWN']


def _fixture(tmp_path: Path, invocation: str) -> Path:
    """Materialize the shared fixture tree and return the marketplace root."""
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', [NOTATION])
    _write_script(marketplace_root, NOTATION, 'resolve', ['command', 'module'])
    _write_invocation(marketplace_root, invocation)
    return marketplace_root


# ---------------------------------------------------------------------------
# Pair 1 — acceptance
# ---------------------------------------------------------------------------


def test_router_consumed_flag_is_not_reported_unknown(tmp_path):
    """The positive half: a flag the executor consumes must NOT be flagged.

    ``--audit-plan-id`` is stripped from argv by the executor before the target
    script's argparse runs, so it is declared by no node and accepted by every
    one. Reporting it is a finding against an invocation that demonstrably works.
    """
    marketplace_root = _fixture(
        tmp_path, f'{NOTATION} resolve --command compile --{ROUTER_CONSUMED_FLAG} X'
    )

    findings = _flag_findings(marketplace_root)
    assert findings == [], (
        f'router-consumed --{ROUTER_CONSUMED_FLAG} reported as an invented flag: {findings!r}'
    )


def test_genuinely_unknown_flag_on_the_same_invocation_is_still_reported(tmp_path):
    """The negative half: the widening must not disable the rule.

    Same script, same verb, same line shape — only the flag differs. Without this
    control, the assertion above is satisfied by a cluster that stopped reporting
    anything at all, which is the failure mode the fix is most at risk of.
    """
    marketplace_root = _fixture(
        tmp_path, f'{NOTATION} resolve --command compile --{GENUINELY_UNKNOWN_FLAG} X'
    )

    findings = _flag_findings(marketplace_root)
    assert len(findings) == 1, findings
    assert findings[0]['details']['flag'] == GENUINELY_UNKNOWN_FLAG


def test_both_flags_on_one_line_split_correctly(tmp_path):
    """The discrimination is per-flag, not per-line.

    A line carrying BOTH a router-consumed flag and an invented one must produce
    exactly one finding, naming the invented one. A rule that skipped the whole
    line once it saw an accepted flag, or that flagged both, passes the two tests
    above and fails here.
    """
    marketplace_root = _fixture(
        tmp_path,
        f'{NOTATION} resolve --command compile '
        f'--{ROUTER_CONSUMED_FLAG} X --{GENUINELY_UNKNOWN_FLAG} Y',
    )

    findings = _flag_findings(marketplace_root)
    assert len(findings) == 1, findings
    assert findings[0]['details']['flag'] == GENUINELY_UNKNOWN_FLAG


# ---------------------------------------------------------------------------
# Pair 2 — placement must not inherit the acceptance widening
# ---------------------------------------------------------------------------


def test_executor_consumed_flag_after_the_verb_is_not_a_placement_finding(tmp_path):
    """A flag no ``--help`` renders has no placement to get wrong.

    ``--audit-plan-id`` is absent from the derived ``root_flags`` because it is
    consumed ahead of argparse, so the placement rule's per-script membership
    test skips it — the same route by which the router-consumed ``--project-dir``
    on ``tools-integration-ci:ci`` is skipped. This is asserted rather than
    assumed, because it is the property that lets the placement rule stay correct
    with no global exemption list.
    """
    marketplace_root = tmp_path / 'marketplace'
    _write_invocation(
        marketplace_root, f'{NOTATION} resolve --command compile --{ROUTER_CONSUMED_FLAG} X'
    )
    index = {
        NOTATION: _ScriptEntry(
            subcommands={'resolve': {'command', 'module'}},
            root_flags={'config'},
            subcommand_own_flags={'resolve': {'command', 'module'}},
        )
    }

    assert scan_router_flag_placement(marketplace_root, index) == []


def test_root_declared_flag_after_the_verb_is_still_a_placement_finding(tmp_path):
    """⛔ The matched negative: ``--plan-id`` after the verb IS a real defect.

    Verified live — ``architecture which-module --path P --plan-id X`` exits 2
    with ``unrecognized arguments``, and the executor's own error names the fix
    ("--plan-id is a top-level flag and belongs BEFORE the subcommand"). So
    ``--plan-id`` is NOT position-independent the way ``--audit-plan-id`` is,
    even though both are members of the acceptance-side ``UNIVERSAL_FLAGS``.

    This control exists because exempting that whole set from the placement rule
    is the tempting simplification, and it would silence the verb-scoped and
    router-scoped ``--plan-id`` / ``--project-dir`` recurrence signatures the
    project documents. The discriminator is the DERIVED ``root_flags``: here
    ``--plan-id`` is in it, so the placement question is real and is answered.
    """
    marketplace_root = tmp_path / 'marketplace'
    _write_invocation(marketplace_root, f'{NOTATION} resolve --command compile --plan-id X')
    index = {
        NOTATION: _ScriptEntry(
            subcommands={'resolve': {'command', 'module', 'plan-id'}},
            root_flags={'plan-id'},
            subcommand_own_flags={'resolve': {'command', 'module'}},
        )
    }

    findings = scan_router_flag_placement(marketplace_root, index)
    assert len(findings) == 1, findings
    assert findings[0]['details']['flag'] == 'plan-id'
    assert findings[0]['details']['subcommand'] == 'resolve'
