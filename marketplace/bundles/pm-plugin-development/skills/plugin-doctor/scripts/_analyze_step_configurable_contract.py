#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Step-configurable-contract scanner for the ``step-configurable-contract`` rule.

This module implements a deterministic static analyzer that fires on a
finalize-step body doc whose ``configurable:`` frontmatter block is present but
*malformed* — a missing required sub-field (``key`` / ``default`` /
``description``), a wrong-typed sub-field, an empty description, a duplicate
key, or any other declaration that fails to parse via the D1 contract parser.
A body doc with no ``configurable:`` block at all is *ownerless* (a legitimate,
expected state for a built-in finalize step that owns no params) and is silently
skipped — only a present-but-ill-formed block is a finding.

Single source of truth
-----------------------
The declaration schema and the validation logic are NOT re-implemented here.
The analyzer imports the central contract parser
``marketplace/bundles/plan-marshall/skills/extension-api/scripts/configurable_contract.py``
(see ``configurable_contract.py`` for the authoritative declaration shape and
the per-case ``ValueError`` messages) and delegates every malformed-declaration
decision to it. The parser is the only place that knows what a valid
``configurable`` block looks like; this analyzer is a thin static-scan wrapper
that turns the parser's ``ValueError`` into a plugin-doctor finding.

The ownerless-vs-malformed distinction is the parser's
``resolve_step_defaults_optional`` semantics expressed directly: a doc whose
frontmatter declares no ``configurable:`` key returns ``None`` (ownerless,
skipped); a doc that declares the key is parsed via ``parse_configurable`` and a
``ValueError`` is surfaced as a finding.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_finalize_step_token.py``:

- pure static analysis (no subprocess execution)
- regex/parse-driven extraction from markdown source
- stdlib-only dependencies (plus the dynamically-imported contract parser)
- no mutation of any file

Scan roots
----------
Two roots are walked, identical to ``_analyze_finalize_step_token.py``'s
finalize-step scope but at the body-doc granularity the contract parser
resolves:

1. **Built-in finalize step docs** —
   ``marketplace_root/plan-marshall/skills/phase-6-finalize/{workflow,standards}/*.md``.
   These are the body docs that declare built-in (``default:``) finalize-step
   configurable blocks.

2. **Project-local finalize-step skills** —
   ``<repo>/.claude/skills/finalize-step-*/SKILL.md`` discovered by glob, the
   same project-local root the token analyzer walks. The expected declaration
   surface is the project-local step's ``SKILL.md`` frontmatter.

Detection
---------
For each in-scope body doc, the analyzer asks the contract parser whether a
``configurable:`` block is present (frontmatter exists AND declares the key).
When present, ``parse_configurable`` is invoked; a ``ValueError`` becomes a
single finding anchored at the ``configurable:`` line. A doc with no
``configurable:`` block is skipped (ownerless — no false positive).

Findings have the shape::

    {
        'rule_id': 'step-configurable-contract',
        'type': 'step_configurable_contract',
        'rule': 'scan_step_configurable_contract',
        'file': '<absolute body-doc path>',
        'line': <int, 1-based line of the ``configurable:`` key>,
        'severity': 'error',
        'fixable': False,
        'message': '<the ValueError message from the contract parser>',
        'details': {
            'parser_error': '<the ValueError message>',
        },
    }

Public API
----------
- ``scan_step_configurable_contract(marketplace_root)``: entry point — scans the
  two roots above and returns a list of finding dicts (empty for a clean tree).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'step-configurable-contract'
RULE_NAME = 'scan_step_configurable_contract'
FINDING_TYPE = 'step_configurable_contract'

# Matches the top-level ``configurable:`` key on its own frontmatter line.
_CONFIGURABLE_KEY_RE = re.compile(r'^configurable:\s*$|^configurable:\s+\S', re.MULTILINE)


# ---------------------------------------------------------------------------
# Contract-parser import (single source of truth for the declaration schema)
# ---------------------------------------------------------------------------


def _load_contract_parser(marketplace_root: Path) -> ModuleType | None:
    """Import the central ``configurable_contract`` module from extension-api.

    The parser lives at
    ``marketplace_root/plan-marshall/skills/extension-api/scripts/configurable_contract.py``.
    It imports ``marketplace_bundles`` and ``toon_parser`` at module top, both
    of which the executor places on ``sys.path`` for cross-skill imports.

    Returns ``None`` only when the module cannot be *located* by the import
    machinery — the parser file is absent (a synthetic ``tmp_path`` marketplace
    with no plan-marshall bundle) or ``spec_from_file_location`` yields no usable
    spec/loader. In those file-not-found cases the analyzer is legitimately a
    no-op for that tree.

    When the parser file IS present but ``exec_module`` raises (a syntax error,
    a broken import, or any other module-load failure), the exception is
    re-raised rather than swallowed. Returning ``None`` there would silently
    disable the ``step-configurable-contract`` rule and turn a broken parser
    into a quality-gate bypass; surfacing the load failure is the correct,
    fail-loud behaviour.
    """
    parser_path = (
        marketplace_root
        / 'plan-marshall'
        / 'skills'
        / 'extension-api'
        / 'scripts'
        / 'configurable_contract.py'
    )
    if not parser_path.is_file():
        return None
    # Ensure the extension-api scripts dir is importable for any sibling-by-bare-name
    # imports the parser performs (it imports marketplace_bundles / toon_parser,
    # which the executor PYTHONPATH already provides; the dir insert is defensive).
    scripts_dir = str(parser_path.parent)
    inserted = scripts_dir not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            'configurable_contract_for_doctor', parser_path
        )
        if spec is None or spec.loader is None:
            # Import machinery could not produce a usable spec/loader for the
            # file — treat as "not locatable" (no-op), same as a missing file.
            return None
        module = importlib.util.module_from_spec(spec)
        # The file IS present: do NOT swallow exec_module failures. A syntax
        # error or broken import here means the contract parser is broken, and
        # silently returning None would disable the rule (a quality-gate
        # bypass). Let the exception propagate to fail loud.
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            try:
                sys.path.remove(scripts_dir)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Frontmatter presence + line anchoring
# ---------------------------------------------------------------------------


def _configurable_block_present(parser: ModuleType, content: str) -> bool:
    """Return True when ``content``'s frontmatter declares a ``configurable:`` block.

    Delegates the frontmatter extraction and the ``configurable:`` detection to
    the contract parser's own helpers so the ownerless-vs-present decision uses
    the exact same logic the parser uses at resolve time. A doc with no
    frontmatter, or with frontmatter that omits the ``configurable:`` key, is
    ownerless (returns False).
    """
    fm_lines = parser._extract_frontmatter_lines(content)
    if fm_lines is None:
        return False
    return parser._parse_configurable_entries(fm_lines) is not None


def _configurable_line(content: str) -> int:
    """Return the 1-based line of the ``configurable:`` frontmatter key (or 1)."""
    match = _CONFIGURABLE_KEY_RE.search(content)
    if not match:
        return 1
    return content.count('\n', 0, match.start()) + 1


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_doc(parser: ModuleType, path: Path) -> list[dict]:
    """Scan one body doc; emit a finding when its ``configurable:`` block is malformed.

    Ownerless docs (no ``configurable:`` block) are skipped. Present-but-malformed
    blocks surface the contract parser's ``ValueError`` message verbatim.
    """
    try:
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    if not _configurable_block_present(parser, content):
        # Ownerless — no configurable block to validate.
        return []

    try:
        parser.parse_configurable(path)
    except ValueError as exc:
        return [
            Finding(
                type=FINDING_TYPE,
                file=str(path),
                line=_configurable_line(content),
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                details={
                    'parser_error': str(exc),
                },
                extra={
                    'rule': RULE_NAME,
                    'message': (
                        f'Malformed step `configurable:` declaration — {exc}. '
                        f'See rule-catalog.md and '
                        f'extension-api/scripts/configurable_contract.py for the '
                        f'declaration schema (each entry needs key, default, '
                        f'description).'
                    ),
                },
            ).to_dict()
        ]
    return []


# ---------------------------------------------------------------------------
# Target enumeration
# ---------------------------------------------------------------------------


def _builtin_step_docs(marketplace_root: Path) -> list[Path]:
    """Return the built-in finalize-step body docs that may declare configurable blocks.

    Scope: ``plan-marshall/skills/phase-6-finalize/{workflow,standards}/*.md`` —
    the body docs the contract parser resolves built-in (``default:``) steps to.
    """
    phase6 = (
        marketplace_root
        / 'plan-marshall'
        / 'skills'
        / 'phase-6-finalize'
    )
    if not phase6.is_dir():
        return []
    docs: list[Path] = []
    for subdir in ('workflow', 'standards'):
        sub = phase6 / subdir
        if not sub.is_dir():
            continue
        docs.extend(sorted(sub.glob('*.md')))
    return docs


def _claude_skills_root(marketplace_root: Path) -> Path:
    """Resolve the project-local ``.claude/skills`` tree from ``marketplace_root``.

    ``marketplace_root`` is ``<repo>/marketplace/bundles``; the project-local
    skills tree is ``<repo>/.claude/skills`` — two levels up, then
    ``.claude/skills``.
    """
    return marketplace_root.parent.parent / '.claude' / 'skills'


def _project_local_step_docs(marketplace_root: Path) -> list[Path]:
    """Return project-local ``finalize-step-*/SKILL.md`` body docs."""
    skills_root = _claude_skills_root(marketplace_root)
    if not skills_root.is_dir():
        return []
    docs: list[Path] = []
    try:
        for skill_dir in sorted(skills_root.glob('finalize-step-*')):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.is_file():
                docs.append(skill_md)
    except OSError:
        pass
    return docs


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan_step_configurable_contract(marketplace_root: Path) -> list[dict]:
    """Scan finalize-step body docs for malformed ``configurable:`` declarations.

    Walks the built-in phase-6-finalize body docs and the project-local
    ``finalize-step-*`` skill docs, and reports every present-but-malformed
    ``configurable:`` block by delegating validation to the central contract
    parser (``configurable_contract.parse_configurable``). Docs with no
    ``configurable:`` block (ownerless) are silently skipped.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree, or when the contract
        parser cannot be imported).
    """
    marketplace_root = Path(marketplace_root)
    parser = _load_contract_parser(marketplace_root)
    if parser is None:
        return []

    findings: list[dict] = []
    for doc in _builtin_step_docs(marketplace_root):
        findings.extend(_scan_doc(parser, doc))
    for doc in _project_local_step_docs(marketplace_root):
        findings.extend(_scan_doc(parser, doc))
    return findings
