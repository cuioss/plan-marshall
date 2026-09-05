#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""manage-findings invocation analyzer — catches invalid invocation shapes.

This module implements the ``manage-findings-invocation-invalid`` rule used
by plugin-doctor to detect three canonical invalid spellings of the
``plan-marshall:manage-findings:manage-findings`` notation and its argparse
tree:

1. **Script-position underscore.** ``plan-marshall:manage-findings:manage_findings``
   — the script segment uses snake_case where the registered notation is
   kebab-case (``manage-findings``). The executor uses the third segment as
   a literal dict key, so the underscored form does not resolve.
2. **Invalid top-level subcommand.** The only registered top-level
   subcommands are ``add, list, get, resolve, promote, qgate, assessment``.
   Any other token in the subcommand position is invalid; the historically
   recurring invented form is ``list-qgate``.
3. **Invalid ``qgate`` sub-verb.** The only registered ``qgate`` sub-verbs
   are ``add, list, resolve, clear``. The historically recurring invented
   form is ``qgate query`` (the legacy verb — the canonical verb is ``list``).

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_argument_naming.py`` and the surrounding
``_analyze_*.py`` cluster:

- pure static analysis (no subprocess execution, no imports of the target
  script);
- regex-driven extraction of executor invocations from markdown sources;
- findings are dicts with ``rule_id``/``file``/``line``/``severity``/
  ``fixable``/``details``, matching the surrounding shape.

Findings carry a ``details.canonical_hint`` field with the closest correct
spelling so reviewers can apply the fix mechanically.

Activation
----------
The rule is registered under the ``manage-findings-invocation-invalid``
key and is wired through ``_doctor_analysis.py`` gated on ``active_rules``,
matching the ``verb_chain`` opt-in pattern.

Public API
----------
- ``analyze_manage_findings_invocation(content, file_path)``: entry point —
  scans a single markdown body and returns findings.
- ``RULE_ID``: the canonical rule key.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

# =============================================================================
# Rule ID
# =============================================================================

RULE_ID = 'manage-findings-invocation-invalid'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='structural',
    scope='corpus-relational',
)

# Registered argparse tree for plan-marshall:manage-findings:manage-findings.
# Source of truth: marketplace/bundles/plan-marshall/skills/manage-findings/
#                  scripts/manage-findings.py (top-level + qgate sub-parsers).
VALID_TOP_LEVEL_SUBCOMMANDS: frozenset[str] = frozenset(
    {'add', 'list', 'get', 'resolve', 'promote', 'qgate', 'assessment'}
)
VALID_QGATE_SUBVERBS: frozenset[str] = frozenset({'add', 'list', 'resolve', 'clear'})
VALID_ASSESSMENT_SUBVERBS: frozenset[str] = frozenset({'add', 'list', 'get', 'clear'})

# =============================================================================
# Regexes
# =============================================================================

# Match any executor invocation whose third notation segment is some
# spelling of manage-findings — either the canonical kebab-case form or
# the invalid snake_case ``manage_findings`` form. The pattern also
# captures the second segment so we can distinguish ``manage-findings``
# (canonical) from ``manage_findings`` (the snake_case skill spelling
# that also drifts in prose).
_NOTATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<bundle>[A-Za-z0-9_\-]+):'
    r'(?P<skill>manage[-_]findings):'
    r'(?P<script>manage[-_]findings)'
    r'(?P<rest>.*)$'
)

# Token splitter for the trailing portion of an invocation. Captures
# alphanumeric/hyphen tokens following whitespace, while ignoring flag
# tokens (those start with ``-``).
_NEXT_TOKEN_RE = re.compile(r'\s+(?P<tok>[A-Za-z][A-Za-z0-9_\-]*)')


# =============================================================================
# Helpers
# =============================================================================


def _extract_subcommand_tokens(rest: str) -> list[str]:
    """Extract the positional token sequence from the trailing portion.

    Stops at the first flag token (anything starting with ``-``) and at
    end-of-line. Returns up to two positional tokens — the top-level
    subcommand and (when applicable) the sub-verb under ``qgate`` /
    ``assessment``.
    """
    tokens: list[str] = []
    pos = 0
    while pos < len(rest):
        match = _NEXT_TOKEN_RE.match(rest, pos)
        if not match:
            # Any other character (flag, backslash continuation, end-of-line)
            # ends the positional run.
            break
        tokens.append(match.group('tok'))
        pos = match.end()
        if len(tokens) >= 2:
            break
        # Look ahead: the next non-whitespace must still be alphanumeric
        # to extend the run; a flag (``-``) terminates positionals.
        peek = rest[pos:].lstrip()
        if peek.startswith('-'):
            break
    return tokens


def _build_canonical_hint(
    notation_script: str,
    top_token: str | None,
    sub_token: str | None,
) -> str:
    """Render a canonical-form hint for an invalid invocation."""
    if notation_script == 'manage_findings':
        return (
            'Use kebab-case in the script position: '
            '`plan-marshall:manage-findings:manage-findings`'
        )
    if top_token == 'list-qgate':
        return (
            'Use `qgate list --plan-id {plan_id} --phase {phase}` '
            '(no `list-qgate` top-level subcommand is registered)'
        )
    if top_token == 'qgate' and sub_token == 'query':
        return (
            'Use `qgate list --plan-id {plan_id} --phase {phase}` '
            '(`query` is the legacy verb; the canonical sub-verb is `list`; '
            f'registered sub-verbs: {sorted(VALID_QGATE_SUBVERBS)})'
        )
    if top_token and top_token not in VALID_TOP_LEVEL_SUBCOMMANDS:
        return (
            f'Use a registered top-level subcommand: '
            f'{sorted(VALID_TOP_LEVEL_SUBCOMMANDS)}'
        )
    if top_token == 'qgate' and sub_token and sub_token not in VALID_QGATE_SUBVERBS:
        return (
            f'Use a registered qgate sub-verb: '
            f'{sorted(VALID_QGATE_SUBVERBS)}'
        )
    if top_token == 'assessment' and sub_token and sub_token not in VALID_ASSESSMENT_SUBVERBS:
        return (
            f'Use a registered assessment sub-verb: '
            f'{sorted(VALID_ASSESSMENT_SUBVERBS)}'
        )
    return 'Refer to `manage-findings --help` for the registered command tree'


# =============================================================================
# Public entry point
# =============================================================================


def analyze_manage_findings_invocation(content: str, file_path: str) -> list[dict]:
    """Scan a markdown body and emit findings for invalid manage-findings shapes.

    Three failure modes are detected per the rule contract documented in the
    module docstring. Findings include line number, file path, the offending
    notation/subcommand shape, and a canonical-form hint.

    The scan is line-anchored — every invocation that drifts on any of the
    three axes produces an independent finding. The function is total: when
    the content carries no manage-findings notation references, an empty list
    is returned.
    """
    findings: list[dict] = []
    for idx, raw in enumerate(content.splitlines(), start=1):
        match = _NOTATION_RE.search(raw)
        if not match:
            continue

        bundle = match.group('bundle')
        skill = match.group('skill')
        script = match.group('script')
        rest = match.group('rest') or ''

        # Failure 1: script-position underscore.
        if script == 'manage_findings':
            findings.append(
                Finding(
                    type=RULE_ID,
                    rule_id=RULE_ID,
                    file=file_path,
                    line=idx,
                    severity='error',
                    fixable=False,
                    description=(
                        'manage-findings notation uses snake_case in the script '
                        f'position (`{bundle}:{skill}:{script}`) — the executor '
                        'registry keys are kebab-case'
                    ),
                    details={
                        'notation': f'{bundle}:{skill}:{script}',
                        'reason': 'script_position_underscore',
                        'canonical_hint': _build_canonical_hint(script, None, None),
                    },
                ).to_dict()
            )
            # Stop further analysis on this line — the notation itself does
            # not resolve, so the subcommand tree is moot.
            continue

        # script is the canonical 'manage-findings'. Only the kebab-case
        # second segment carries the canonical argparse tree; the snake_case
        # spelling of the skill is its own drift signal but caught at the
        # notation-validity rule level (ARGUMENT_NAMING_NOTATION_INVALID).
        # We continue analysing only when the canonical pair is intact.
        if skill != 'manage-findings':
            continue

        # Extract the positional sequence following the notation.
        tokens = _extract_subcommand_tokens(rest)
        if not tokens:
            # No subcommand tokens to validate.
            continue

        top = tokens[0]
        sub = tokens[1] if len(tokens) >= 2 else None

        # Failure 2: invalid top-level subcommand.
        if top not in VALID_TOP_LEVEL_SUBCOMMANDS:
            findings.append(
                Finding(
                    type=RULE_ID,
                    rule_id=RULE_ID,
                    file=file_path,
                    line=idx,
                    severity='error',
                    fixable=False,
                    description=(
                        f'manage-findings invocation uses unregistered top-level '
                        f'subcommand `{top}` (registered: '
                        f'{sorted(VALID_TOP_LEVEL_SUBCOMMANDS)})'
                    ),
                    details={
                        'notation': f'{bundle}:{skill}:{script}',
                        'subcommand': top,
                        'reason': 'top_level_subcommand_unknown',
                        'canonical_hint': _build_canonical_hint(script, top, sub),
                        'known_subcommands': sorted(VALID_TOP_LEVEL_SUBCOMMANDS),
                    },
                ).to_dict()
            )
            continue

        # Failure 3a: invalid qgate sub-verb.
        if top == 'qgate' and sub is not None and sub not in VALID_QGATE_SUBVERBS:
            findings.append(
                Finding(
                    type=RULE_ID,
                    rule_id=RULE_ID,
                    file=file_path,
                    line=idx,
                    severity='error',
                    fixable=False,
                    description=(
                        f'manage-findings invocation uses unregistered qgate '
                        f'sub-verb `{sub}` (registered: '
                        f'{sorted(VALID_QGATE_SUBVERBS)})'
                    ),
                    details={
                        'notation': f'{bundle}:{skill}:{script}',
                        'subcommand': 'qgate',
                        'sub_verb': sub,
                        'reason': 'qgate_sub_verb_unknown',
                        'canonical_hint': _build_canonical_hint(script, top, sub),
                        'known_sub_verbs': sorted(VALID_QGATE_SUBVERBS),
                    },
                ).to_dict()
            )
            continue

        # Failure 3b: invalid assessment sub-verb (defence in depth).
        if (
            top == 'assessment'
            and sub is not None
            and sub not in VALID_ASSESSMENT_SUBVERBS
        ):
            findings.append(
                Finding(
                    type=RULE_ID,
                    rule_id=RULE_ID,
                    file=file_path,
                    line=idx,
                    severity='error',
                    fixable=False,
                    description=(
                        f'manage-findings invocation uses unregistered '
                        f'assessment sub-verb `{sub}` (registered: '
                        f'{sorted(VALID_ASSESSMENT_SUBVERBS)})'
                    ),
                    details={
                        'notation': f'{bundle}:{skill}:{script}',
                        'subcommand': 'assessment',
                        'sub_verb': sub,
                        'reason': 'assessment_sub_verb_unknown',
                        'canonical_hint': _build_canonical_hint(script, top, sub),
                        'known_sub_verbs': sorted(VALID_ASSESSMENT_SUBVERBS),
                    },
                ).to_dict()
            )
            continue

    return findings


def scan_manage_findings_invocation(marketplace_root: Path) -> list[dict]:
    """Walk a marketplace tree and run the analyzer over every markdown file.

    Mirrors the marketplace-wide entry points used by sibling analyzers
    (``analyze_argument_naming``, ``analyze_verb_chains``). Reads markdown
    bodies from ``marketplace_root/bundles/*/`` recursively. Returns a flat
    list of findings.
    """
    findings: list[dict] = []
    bundles_dir = marketplace_root / 'bundles'
    if not bundles_dir.is_dir():
        return findings
    for md_file in sorted(bundles_dir.rglob('*.md')):
        try:
            content = md_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(analyze_manage_findings_invocation(content, str(md_file)))
    return findings


def scan_skill_for_manage_findings_invocation(skill_dir: Path) -> list[dict]:
    """Per-skill scanner used by ``_doctor_analysis.analyze_component``.

    Scans ``SKILL.md`` and every ``*.md`` under ``standards/``,
    ``references/``, ``workflow/``, and ``recipes/``. Mirrors the scope of
    sibling per-skill analyzers (``analyze_verb_chains``). Returns a flat
    list of findings.
    """
    findings: list[dict] = []
    if not skill_dir.is_dir():
        return findings

    targets: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)
    for sub in ('standards', 'references', 'workflow', 'recipes'):
        sub_dir = skill_dir / sub
        if sub_dir.is_dir():
            targets.extend(sorted(sub_dir.glob('*.md')))

    for md_file in targets:
        try:
            content = md_file.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(analyze_manage_findings_invocation(content, str(md_file)))
    return findings
