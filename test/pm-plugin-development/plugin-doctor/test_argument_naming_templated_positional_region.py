#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""A usage string is not a call — and the skip is COUNTED, never silent.

``_INVOCATION_RE`` resolves the verb slot with ``[a-z][A-Za-z0-9_\\-]*``, so a
line whose positional region holds usage-template syntax names no verb and comes
back with ``subcommand=None``. Every flag on the line was then judged against the
ROOT scope, and a pure subcommand-dispatching script legitimately declares almost
nothing there — so each flag read as invented against a line that was never a
call. Three real corpus shapes hit this:

    manage-plan-documents {type} create --summary ... --went_well ...
    permission_doctor {command} {args}          (addressed by --scope in prose)
    profiles [--project-dir PROJECT_DIR | --plan-id PLAN_ID] list [--module M]

⛔ The cause is NOT an accept-set that came back empty for a script that declares
flags. ``permission_doctor`` and ``profiles`` were probed live: both genuinely
declare no root long flags beyond the two-state ``--project-dir`` / ``--plan-id``
pair, so the derived surface was CORRECT and the extractor was wrong.

Every test here is a matched pair, because a skip is indistinguishable from a
disabled rule unless the same-shaped concrete call is shown still firing. The
coverage half is the one that matters most: omitting a site the cluster cannot
rule on is only honest if the omission RAISES ``blind_spots``. A skip that left
the figure alone would shrink the judged corpus quietly — the exact defect class
this cluster exists to end.
"""

from __future__ import annotations

from pathlib import Path

from _plugin_doctor_dispatching_executor import write_dispatching_executor
from conftest import load_script_module

_aan = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_argument_naming.py',
    '_analyze_argument_naming_templated_region',
)
analyze_argument_naming_with_population = _aan.analyze_argument_naming_with_population

NOTATION = 'plan-marshall:manage-plan-documents:manage-plan-documents'

#: A concrete verb the fixture script declares, plus one flag it declares on it.
CONCRETE_VERB = 'create'
DECLARED_FLAG = 'plan-id'

#: A flag the fixture script declares NOWHERE — the finding both halves hinge on.
UNDECLARED_FLAG = 'summary'


def _fixture(tmp_path: Path, invocation: str, *, register: bool = True) -> Path:
    """Materialize a marketplace whose sole SKILL.md carries ``invocation``."""
    marketplace_root = tmp_path / 'marketplace'
    write_dispatching_executor(tmp_path / '.plan', [NOTATION] if register else ['b:s:other'])

    bundle, skill, script_name = NOTATION.split(':', 2)
    scripts_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / f'{script_name}.py').write_text(
        '#!/usr/bin/env python3\n'
        '"""Synthetic fixture script for templated-positional-region tests."""\n'
        'import argparse\n'
        '\n'
        'parser = argparse.ArgumentParser()\n'
        'subparsers = parser.add_subparsers(dest="command")\n'
        f'p = subparsers.add_parser("{CONCRETE_VERB}")\n'
        f'p.add_argument("--{DECLARED_FLAG}")\n'
        '\n'
        'if __name__ == "__main__":\n'
        '    parser.parse_args()\n',
        encoding='utf-8',
    )

    skill_dir = marketplace_root / 'bundles' / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(
        f'# Fixture\n\n```bash\npython3 .plan/execute-script.py {invocation}\n```\n',
        encoding='utf-8',
    )
    return marketplace_root


def _run(marketplace_root: Path) -> tuple[list[dict], int, int]:
    """``(findings, population_size, blind_spots)`` from the single derivation.

    Unpacked into annotated locals because ``_aan`` is spec-loaded at runtime, so
    mypy types every attribute of it as ``Any`` and returning the call's result
    directly trips ``no-any-return`` against this signature.
    """
    findings: list[dict]
    population: int
    blind_spots: int
    findings, population, blind_spots = analyze_argument_naming_with_population(
        marketplace_root
    )
    return findings, population, blind_spots


def _flag_findings(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f.get('rule_id') == 'ARGUMENT_NAMING_FLAG_UNKNOWN']


# ---------------------------------------------------------------------------
# Pair 1 — the skip, and its matched concrete control
# ---------------------------------------------------------------------------


def test_templated_verb_slot_yields_no_flag_finding(tmp_path):
    """``{type} create --summary X`` is a usage string; its flags are illustrative."""
    marketplace_root = _fixture(
        tmp_path, f'{NOTATION} {{type}} {CONCRETE_VERB} --{UNDECLARED_FLAG} X'
    )

    findings, _population, _blind = _run(marketplace_root)
    assert _flag_findings(findings) == [], (
        f'a usage string was judged as a call: {findings!r}'
    )


def test_the_same_flag_on_a_concrete_invocation_is_still_reported(tmp_path):
    """⛔ The matched negative — without it the skip and a dead rule look alike.

    Same script, same undeclared flag, same line shape. The ONLY difference is
    that the verb slot holds a real verb instead of a ``{type}`` placeholder, so
    the invocation resolves and the flag is judged.
    """
    marketplace_root = _fixture(
        tmp_path, f'{NOTATION} {CONCRETE_VERB} --{UNDECLARED_FLAG} X'
    )

    findings, _population, _blind = _run(marketplace_root)
    flag_findings = _flag_findings(findings)
    assert len(flag_findings) == 1, flag_findings
    assert flag_findings[0]['details']['flag'] == UNDECLARED_FLAG


def test_template_syntax_inside_a_flag_value_does_not_suppress_the_line(tmp_path):
    """The guard reads the POSITIONAL region only, never a flag's value.

    ``--plan-id {plan_id}`` is how nearly every canonical block in the tree is
    written. A guard that scanned the whole line would skip essentially the whole
    corpus and report a serene zero — the vacuous-pass failure mode in its purest
    form. The undeclared flag on this concrete call must still be reported.
    """
    marketplace_root = _fixture(
        tmp_path,
        f'{NOTATION} {CONCRETE_VERB} --{DECLARED_FLAG} {{plan_id}} --{UNDECLARED_FLAG} X',
    )

    findings, _population, _blind = _run(marketplace_root)
    flag_findings = _flag_findings(findings)
    assert len(flag_findings) == 1, flag_findings
    assert flag_findings[0]['details']['flag'] == UNDECLARED_FLAG


# ---------------------------------------------------------------------------
# Pair 2 — the omission is PUBLISHED
# ---------------------------------------------------------------------------


def test_a_skipped_usage_string_raises_blind_spots(tmp_path):
    """The coverage half: omitting must cost a blind spot, not a silent zero.

    Both fixtures carry exactly ONE invocation, so the population is 1 in each
    and the two runs differ only in whether that invocation was judgeable. The
    delta is therefore attributable: 1 blind spot for the usage string, 0 for the
    concrete call. Asserting the DELTA rather than an absolute keeps the test
    honest if the fixture ever grows a second invocation.
    """
    templated = _fixture(
        tmp_path / 'templated', f'{NOTATION} {{type}} {CONCRETE_VERB} --{UNDECLARED_FLAG} X'
    )
    concrete = _fixture(
        tmp_path / 'concrete', f'{NOTATION} {CONCRETE_VERB} --{UNDECLARED_FLAG} X'
    )

    _t_findings, t_population, t_blind = _run(templated)
    _c_findings, c_population, c_blind = _run(concrete)

    assert t_population == c_population == 1, (t_population, c_population)
    assert c_blind == 0, f'a judgeable concrete call was counted as a blind spot: {c_blind}'
    assert t_blind == 1, f'the skipped usage string was not published as a blind spot: {t_blind}'


def test_an_unregistered_notation_on_a_usage_string_is_decided_not_blind(tmp_path):
    """⛔ Ordering control: a reported verdict must never be filed as a gap.

    ``scan_notation`` is deliberately NOT template-guarded — a notation is a
    notation whatever follows it — so a templated line carrying an unregistered
    notation still gets a decision and is reported as NOTATION_INVALID. Counting
    it as a blind spot too would file the cluster's loudest verdict as a coverage
    hole, which is the exact error the registry branch of
    ``_invocation_is_blind_spot`` already guards against for concrete calls.

    This pins the ORDER of those two checks, which is invisible in every other
    test here: swap them and this test alone goes red.
    """
    marketplace_root = _fixture(
        tmp_path,
        f'{NOTATION} {{type}} {CONCRETE_VERB} --{UNDECLARED_FLAG} X',
        register=False,
    )

    findings, population, blind = _run(marketplace_root)
    notation_findings = [
        f for f in findings if f.get('rule_id') == 'ARGUMENT_NAMING_NOTATION_INVALID'
    ]
    assert len(notation_findings) == 1, findings
    assert population == 1, population
    assert blind == 0, (
        'a DECIDED notation on a templated line was also counted as a blind spot; '
        'the registry test must run before the template test'
    )
