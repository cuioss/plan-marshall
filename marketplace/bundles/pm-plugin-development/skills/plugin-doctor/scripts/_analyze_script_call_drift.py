#!/usr/bin/env python3
"""Script-call drift analyzer for the ``script-call-drift`` rule.

This module implements a deterministic ``--help``-based static analyzer that
detects drift between documented ``python3 .plan/execute-script.py {notation}
{verb} {args...}`` invocations in skill markdown and the published argparse
interface of the target script.

Replaces the runtime SUBCOMMANDS pre-flight validator (removed in plan
``fix-generate-executor-ast-subcommands``). The runtime executor is now a
dumb dispatcher; this rule catches the same drift class at dev time by
parsing argparse's ``--help`` output, which is argparse's published
interface. Lessons ``2026-04-29-23-002``, ``2026-05-25-21-001``, and
``2026-05-26-09-001`` document the recurring failure modes this rule
replaces (invented subcommands, stale SUBCOMMANDS allowlist, flattened
nested subparsers).

Detection algorithm
-------------------
1. Grep every ``*.md`` under ``marketplace/bundles/**/skills/**`` for
   ``python3 .plan/execute-script.py {notation} [verb] [args...]`` lines.
2. For each unique ``notation``, invoke ``python3 .plan/execute-script.py
   {notation} --help`` (subprocess) and parse the ``{choice1, choice2, ...}``
   subcommand choices block from argparse's usage line.
3. For each unique ``(notation, verb)`` pair, invoke ``python3 .plan/
   execute-script.py {notation} {verb} --help`` and parse the ``options:``
   block for declared ``--flag`` names.
4. Emit findings for:
   - ``verb_not_in_subcommand_list`` — verb cited in prose absent from
     ``--help`` choices.
   - ``flag_not_in_options`` — ``--flag`` in prose absent from ``--help``
     options.

Caching
-------
``--help`` text is cached per process to avoid N² subprocess overhead — one
subprocess per unique notation, one per unique ``(notation, verb)`` pair.

Public API
----------
- ``analyze_script_call_drift(marketplace_root)``: entry point — scans every
  ``*.md`` under ``marketplace_root/**/skills/`` and returns the findings list.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RULE_ID = 'script-call-drift'
RULE_NAME = 'analyze_script_call_drift'
FINDING_TYPE_VERB = 'verb_not_in_subcommand_list'
FINDING_TYPE_FLAG = 'flag_not_in_options'

# ---------------------------------------------------------------------------
# Invocation extraction
# ---------------------------------------------------------------------------

# Match: python3 .plan/execute-script.py {bundle:skill:script} [verb] [flags...]
# notation has the shape bundle:skill:script (3 colon-separated tokens).
# ``rest`` captures the remainder of the line only — no newline crossing.
_INVOCATION_RE = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+'
    r'(?P<notation>[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*:[a-z][a-z0-9_-]*)'
    r'(?P<rest>[^\n`]*)'
)

# Match a candidate verb (first positional after notation, before any flag).
# Skip --audit-plan-id and --plan-id and other flag-shaped tokens.
_VERB_TOKEN_RE = re.compile(r'^[a-z][a-z0-9_-]*$')

# Match documented --flag tokens. Strip values: --flag=value or --flag value.
_FLAG_RE = re.compile(r'--[a-z][a-z0-9-]+')


def _extract_invocations(content: str) -> list[tuple[int, str, list[str], list[str]]]:
    """Extract documented executor invocations from markdown content.

    Returns:
        List of (line_number, notation, verbs, flag_list) tuples. ``verbs`` is
        the list of positional subcommand/verb tokens following the notation,
        preserving order (empty when no positional verb follows). Capturing the
        full verb chain — rather than only the first verb — is required to
        resolve flags declared on nested subparsers (e.g., ``qgate list`` on
        ``manage-findings``); see PR #462 review.
    """
    invocations: list[tuple[int, str, list[str], list[str]]] = []
    for m in _INVOCATION_RE.finditer(content):
        # 1-based line number of the match's start position.
        line_no = content.count('\n', 0, m.start()) + 1
        notation = m.group('notation')
        rest = m.group('rest') or ''
        tokens = [t for t in rest.split() if t]

        verbs: list[str] = []
        # Collect every non-flag positional token before the first flag as the
        # verb chain. Stop on the first flag-shaped token; the chain ends there.
        for tok in tokens:
            if tok.startswith('--'):
                break
            # Skip placeholder tokens and template variables.
            if '{' in tok or '}' in tok:
                continue
            if _VERB_TOKEN_RE.match(tok):
                verbs.append(tok)

        flags = list(_FLAG_RE.findall(rest))
        invocations.append((line_no, notation, verbs, flags))
    return invocations


# ---------------------------------------------------------------------------
# --help parsing
# ---------------------------------------------------------------------------

# argparse's usage line lists subparser choices as `{a,b,c}` or `{a, b, c}`.
_CHOICES_RE = re.compile(r'\{([a-z][a-z0-9_, -]*)\}')

# Long-form flags in the options: block. argparse shows them like:
#   --plan-id PLAN_ID     Description
#   -h, --help            show this help message and exit
_HELP_FLAG_RE = re.compile(r'(?:^|\s)(--[a-z][a-z0-9-]+)')


def _parse_subcommand_choices(help_text: str) -> set[str]:
    """Extract subcommand choice tokens from argparse --help output.

    argparse emits the choices block in the usage line as ``{a,b,c}`` or as
    ``{a, b, c}``. Returns the empty set when no choices block is present
    (single-action scripts).
    """
    choices: set[str] = set()
    for m in _CHOICES_RE.finditer(help_text):
        block = m.group(1)
        # Split on commas, tolerate internal whitespace.
        for tok in block.split(','):
            tok = tok.strip()
            if tok and _VERB_TOKEN_RE.match(tok):
                choices.add(tok)
        # Only the first choices block matters — argparse repeats the usage
        # line in some configurations, but the subcommand surface is one set.
        if choices:
            break
    return choices


def _parse_flag_names(help_text: str) -> set[str]:
    """Extract long-form ``--flag`` tokens from argparse --help output."""
    return set(_HELP_FLAG_RE.findall(help_text))


# ---------------------------------------------------------------------------
# Subprocess helpers with caching
# ---------------------------------------------------------------------------


def _run_help(executor: Path, args: list[str]) -> str:
    """Run the executor with --help and return combined stdout/stderr.

    argparse may emit help to either stream depending on configuration; we
    concatenate both so the parser sees everything. Exit codes are
    intentionally ignored — the executor exits non-zero on some help paths
    (when the help is printed to stderr after parse_known_args).
    """
    try:
        result = subprocess.run(
            ['python3', str(executor), *args, '--help'],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return ''
    return (result.stdout or '') + '\n' + (result.stderr or '')


# ---------------------------------------------------------------------------
# Marketplace scanning
# ---------------------------------------------------------------------------


def _iter_skill_markdown_files(marketplace_root: Path) -> list[Path]:
    """List every markdown file under ``marketplace_root/**/skills/``."""
    if not marketplace_root.is_dir():
        return []
    return sorted(marketplace_root.glob('**/skills/**/*.md'))


def analyze_script_call_drift(marketplace_root: Path) -> list[dict]:
    """Scan skill markdown for documented executor invocations and emit
    drift findings against the live ``--help`` interface.

    Args:
        marketplace_root: Path to ``marketplace/bundles``.

    Returns:
        List of finding dicts. Empty list when no drift is detected or when
        the executor is unreachable.
    """
    # Resolve the executor binary. The executor lives at
    # ``{repo_root}/.plan/execute-script.py``; from
    # ``marketplace_root == repo_root/marketplace/bundles`` walk up two.
    executor = marketplace_root.parent.parent / '.plan' / 'execute-script.py'
    if not executor.is_file():
        # Without an executor we cannot probe --help; rule silently no-ops.
        return []

    findings: list[dict] = []

    # Per-process caches. The flag cache is keyed by the full verb chain
    # (tuple) so nested subparser flags are resolved against the correct help
    # page (e.g., ``manage-findings qgate list``).
    notation_choices_cache: dict[str, set[str]] = {}
    notation_verb_flags_cache: dict[tuple[str, tuple[str, ...]], set[str]] = {}

    for md_path in _iter_skill_markdown_files(marketplace_root):
        try:
            content = md_path.read_text(encoding='utf-8')
        except OSError:
            continue

        invocations = _extract_invocations(content)
        for line_no, notation, verbs, flags in invocations:
            # Resolve choices for this notation (cached).
            if notation not in notation_choices_cache:
                help_text = _run_help(executor, [notation])
                notation_choices_cache[notation] = _parse_subcommand_choices(help_text)
            choices = notation_choices_cache[notation]

            # When choices is empty, the script is single-action — skip verb
            # checking. argparse owns flag validation for single-action
            # scripts and the verb token in prose may legitimately be a
            # positional argument value rather than a subcommand.
            first_verb = verbs[0] if verbs else None
            if first_verb and choices and first_verb not in choices:
                findings.append(
                    {
                        'rule_id': RULE_ID,
                        'type': FINDING_TYPE_VERB,
                        'rule': RULE_NAME,
                        'file': str(md_path),
                        'line': line_no,
                        'severity': 'error',
                        'fixable': False,
                        'notation': notation,
                        'invented_verb': first_verb,
                        'valid_choices': sorted(choices),
                        'description': (
                            f'Documented verb {first_verb!r} for {notation!r} is not in the script\'s '
                            f'declared subcommand choices: {sorted(choices)!r}'
                        ),
                    }
                )

            # Per-verb flag check — run when either (a) the notation is
            # single-action (no choices) and we probe with no verbs, or
            # (b) the first verb is valid against the root choices, in which
            # case the full verb chain probes the nested subparser help.
            if flags and (not choices or (first_verb is not None and first_verb in choices)):
                cache_key = (notation, tuple(verbs))
                if cache_key not in notation_verb_flags_cache:
                    help_text = _run_help(executor, [notation, *verbs])
                    notation_verb_flags_cache[cache_key] = _parse_flag_names(help_text)
                valid_flags = notation_verb_flags_cache[cache_key]
                verb_label = ' '.join(verbs)
                for flag in flags:
                    if flag in ('--help', '--audit-plan-id'):
                        # Universal flags handled by the executor itself.
                        continue
                    if flag not in valid_flags:
                        findings.append(
                            {
                                'rule_id': RULE_ID,
                                'type': FINDING_TYPE_FLAG,
                                'rule': RULE_NAME,
                                'file': str(md_path),
                                'line': line_no,
                                'severity': 'error',
                                'fixable': False,
                                'notation': notation,
                                'verb': verb_label,
                                'invented_flag': flag,
                                'valid_flags': sorted(valid_flags),
                                'description': (
                                    f'Documented flag {flag!r} for {notation!r} {verb_label!r} is '
                                    f'not in the script\'s declared options: {sorted(valid_flags)!r}'
                                ),
                            }
                        )

    return findings
