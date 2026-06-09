#!/usr/bin/env python3
"""Notation-staleness analyzer for the ``notation-staleness`` rule.

This module implements a deterministic regex-based static analyzer that
detects three-part executor notations (``{bundle}:{skill}:{script}``) whose
third segment has no matching ``{script}.py`` file under the resolved
``{bundle}/skills/{skill}/scripts/`` directory.

Motivating failure
-------------------
``generate_executor`` derives a script's three-part executor notation from
its filename. When an entrypoint script is renamed (e.g.
``manage_status.py`` → ``manage-status.py``) without sweeping its callers,
the rename silently changes the script's public notation: callers that
still reference the old third segment resolve to ``Unknown notation``. This
analyzer catches that drift at lint time so a half-done rename can never
reach ``main`` again.

Scope
-----
The analyzer walks ``SKILL.md`` and every ``*.md`` under ``standards/``,
``references/``, ``workflow/``, and ``recipes/`` for a skill, plus every
``*.py`` under ``scripts/`` (sibling-script cross-call notation strings).
For each three-part executor notation found, it resolves the target
``scripts/`` directory relative to the marketplace root and verifies a
matching ``{script}.py`` file exists.

Two-rule coverage
-----------------
This module emits two rules over the same three-segment notation surface:

- ``notation-staleness`` — the third (script) segment has no matching
  ``{script}.py`` file under an otherwise-resolving
  ``bundles/{bundle}/skills/{skill}/scripts/`` directory.
- ``notation-bundle-skill-drift`` — the FIRST or SECOND segment does not
  resolve: the ``{bundle}`` directory or the ``{skill}`` directory is missing
  on disk. This drift is only evaluated for notations anchored to the executor
  invocation prefix (``python3 .plan/execute-script.py {notation}``), because a
  bare three-segment token whose bundle/skill is unknown is indistinguishable
  from an incidental colon-joined token (URL, timestamp, prose). Anchoring on
  the executor prefix removes that ambiguity — anything following
  ``execute-script.py`` is unambiguously an executor notation.

Canonical hint
--------------
When the third segment has no matching file but the hyphen/underscore-
flipped form does match a real file, the ``notation-staleness`` finding
carries a ``details.canonical_hint`` naming the corrected notation so the fix
can be applied mechanically. ``notation-bundle-skill-drift`` findings carry a
``details.canonical_hint`` naming which segment (bundle or skill) failed to
resolve.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_phase2_refine_contract.py`` and
``_analyze_manage_findings_invocation.py``:

- pure static analysis (no subprocess execution, no imports of target
  scripts);
- regex-driven extraction from markdown / script source;
- stdlib-only dependencies;
- no mutation of any file;
- findings carry ``rule_id``/``file``/``line``/``severity``/``fixable``/
  ``details`` with rule-specific fields under ``details``.

Activation
----------
The rule is unconditionally active — it is wired through
``_doctor_analysis.py`` not gated on ``active_rules``, mirroring the
``refine-contract-violation`` integration, because a non-resolving notation
is a hard breakage that must surface on every plugin-doctor run.

Public API
----------
- ``analyze_notation_staleness(paths, rules_filter=None)``: entry point —
  scans a skill directory (or set of files / directories) and returns
  findings.
- ``RULE_ID``: the canonical staleness rule key.
- ``DRIFT_RULE_ID``: the bundle/skill drift rule key.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

RULE_ID = 'notation-staleness'
DRIFT_RULE_ID = 'notation-bundle-skill-drift'

# Match a three-part executor notation following the canonical executor
# invocation prefix ``python3 .plan/execute-script.py`` OR appearing as a
# bare three-segment token (sibling-script cross-call string literals).
# The notation segments are alphanumeric plus hyphen / underscore.
_SEGMENT = r'[A-Za-z0-9][A-Za-z0-9_-]*'
_NOTATION_RE = re.compile(
    rf'(?P<bundle>{_SEGMENT}):(?P<skill>{_SEGMENT}):(?P<script>{_SEGMENT})'
)

# Anchored form: a three-part notation immediately following the executor
# invocation prefix. Anything matching here is unambiguously an executor
# notation, so a non-resolving bundle / skill segment is real drift rather than
# an incidental colon-joined token.
_EXECUTOR_NOTATION_RE = re.compile(
    rf'execute-script\.py\s+'
    rf'(?P<bundle>{_SEGMENT}):(?P<skill>{_SEGMENT}):(?P<script>{_SEGMENT})'
)

# Subdirectories whose markdown sub-documents are scanned for notations.
_SUBDOC_DIRS = ('standards', 'references', 'workflow', 'recipes')


def _flip_separators(segment: str) -> str:
    """Return ``segment`` with hyphens and underscores swapped.

    ``manage_status`` → ``manage-status`` and vice versa. Used to compute
    the canonical-hint candidate when the literal third segment has no
    matching file.
    """
    flipped = []
    for ch in segment:
        if ch == '-':
            flipped.append('_')
        elif ch == '_':
            flipped.append('-')
        else:
            flipped.append(ch)
    return ''.join(flipped)


def _marketplace_root(skill_dir: Path) -> Path | None:
    """Resolve the marketplace root from a skill directory.

    A skill directory has the shape
    ``.../marketplace/bundles/{bundle}/skills/{skill}``; the marketplace
    root is therefore four parents up. Returns ``None`` when the path does
    not match that shape.
    """
    parts = skill_dir.parts
    try:
        bundles_idx = len(parts) - 1 - list(reversed(parts)).index('bundles')
    except ValueError:
        return None
    # bundles/{bundle}/skills/{skill} → root is the parent of 'bundles'.
    if bundles_idx == 0:
        return None
    return Path(*parts[:bundles_idx])


@functools.cache
def _script_exists(root: Path, bundle: str, skill: str, script: str) -> bool:
    """Return True when ``{script}.py`` exists under the resolved scripts dir.

    Cached: the marketplace tree is static for the duration of an analysis
    run, so repeated lookups for the same notation avoid redundant
    filesystem ``is_file()`` calls across every scanned file.
    """
    scripts_dir = root / 'bundles' / bundle / 'skills' / skill / 'scripts'
    return (scripts_dir / f'{script}.py').is_file()


@functools.cache
def _bundle_dir_exists(root: Path, bundle: str) -> bool:
    """Return True when ``bundles/{bundle}/`` is a real bundle directory."""
    return (root / 'bundles' / bundle / '.claude-plugin' / 'plugin.json').is_file()


@functools.cache
def _skill_dir_exists(root: Path, bundle: str, skill: str) -> bool:
    """Return True when ``bundles/{bundle}/skills/{skill}/`` exists on disk."""
    return (root / 'bundles' / bundle / 'skills' / skill).is_dir()


def _scan_bundle_skill_drift(line: str, idx: int, path: Path, root: Path) -> list[dict]:
    """Detect bundle/skill-segment drift in executor-anchored notations.

    Only notations anchored to ``execute-script.py {notation}`` are evaluated —
    the anchor removes the bundle/skill ambiguity that the bare-token path must
    tolerate. Emits a ``notation-bundle-skill-drift`` finding when the
    ``{bundle}`` directory or the ``{skill}`` directory does not resolve.
    """
    findings: list[dict] = []
    for match in _EXECUTOR_NOTATION_RE.finditer(line):
        bundle = match.group('bundle')
        skill = match.group('skill')
        script = match.group('script')
        notation = f'{bundle}:{skill}:{script}'

        if not _bundle_dir_exists(root, bundle):
            findings.append(
                {
                    'rule_id': DRIFT_RULE_ID,
                    'type': DRIFT_RULE_ID,
                    'file': str(path),
                    'line': idx,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Executor notation `{notation}` names bundle '
                        f'`{bundle}`, but `bundles/{bundle}/` is not a real '
                        f'bundle directory — the notation does not resolve '
                        f'(notation-bundle-skill-drift)'
                    ),
                    'details': {
                        'notation': notation,
                        'bundle': bundle,
                        'skill': skill,
                        'script': script,
                        'reason': 'bundle_dir_missing',
                        'canonical_hint': (
                            f'No bundle `{bundle}` exists under `bundles/` — '
                            f'correct the first notation segment to a real '
                            f'bundle name'
                        ),
                    },
                }
            )
            continue

        if not _skill_dir_exists(root, bundle, skill):
            findings.append(
                {
                    'rule_id': DRIFT_RULE_ID,
                    'type': DRIFT_RULE_ID,
                    'file': str(path),
                    'line': idx,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Executor notation `{notation}` names skill '
                        f'`{skill}` in bundle `{bundle}`, but '
                        f'`bundles/{bundle}/skills/{skill}/` does not exist — '
                        f'the notation does not resolve '
                        f'(notation-bundle-skill-drift)'
                    ),
                    'details': {
                        'notation': notation,
                        'bundle': bundle,
                        'skill': skill,
                        'script': script,
                        'reason': 'skill_dir_missing',
                        'canonical_hint': (
                            f'No skill `{skill}` exists under '
                            f'`bundles/{bundle}/skills/` — correct the second '
                            f'notation segment to a real skill name'
                        ),
                    },
                }
            )
    return findings


def _scan_file(path: Path, root: Path) -> list[dict]:
    """Scan a single file and return all notation-staleness findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    findings: list[dict] = []
    seen: set[tuple[int, str]] = set()
    drift_seen: set[tuple[int, str]] = set()
    for idx, line in enumerate(text.splitlines(), start=1):
        # Bundle/skill drift is evaluated first, over executor-anchored
        # notations only (the anchor removes bundle/skill ambiguity).
        for drift in _scan_bundle_skill_drift(line, idx, path, root):
            drift_key = (idx, drift['details']['notation'])
            if drift_key in drift_seen:
                continue
            drift_seen.add(drift_key)
            findings.append(drift)

        for match in _NOTATION_RE.finditer(line):
            bundle = match.group('bundle')
            skill = match.group('skill')
            script = match.group('script')

            scripts_dir = root / 'bundles' / bundle / 'skills' / skill / 'scripts'
            # Only evaluate notations whose target scripts/ directory exists —
            # this filters out incidental colon-separated tokens that are not
            # executor notations (e.g. URLs, timestamps, prose).
            if not scripts_dir.is_dir():
                continue
            if _script_exists(root, bundle, skill, script):
                continue

            notation = f'{bundle}:{skill}:{script}'
            key = (idx, notation)
            if key in seen:
                continue
            seen.add(key)

            flipped = _flip_separators(script)
            canonical_hint = ''
            if flipped != script and _script_exists(root, bundle, skill, flipped):
                canonical_hint = (
                    f'Use the hyphen/underscore-flipped form: '
                    f'`{bundle}:{skill}:{flipped}`'
                )
            else:
                canonical_hint = (
                    f'No `{script}.py` exists under '
                    f'`bundles/{bundle}/skills/{skill}/scripts/` — verify the '
                    f'script filename and update the notation to match'
                )

            findings.append(
                {
                    'rule_id': RULE_ID,
                    'type': RULE_ID,
                    'file': str(path),
                    'line': idx,
                    'severity': 'error',
                    'fixable': False,
                    'description': (
                        f'Executor notation `{notation}` has no matching '
                        f'`{script}.py` under '
                        f'`bundles/{bundle}/skills/{skill}/scripts/` — the '
                        f'notation does not resolve (notation-staleness)'
                    ),
                    'details': {
                        'notation': notation,
                        'bundle': bundle,
                        'skill': skill,
                        'script': script,
                        'reason': 'script_file_missing',
                        'canonical_hint': canonical_hint,
                    },
                }
            )
    return findings


def _resolve_targets(skill_dir: Path) -> list[Path]:
    """Expand a skill directory into the concrete files this rule scans.

    Scans ``SKILL.md``, every ``*.md`` under the sub-document directories,
    and every ``*.py`` under ``scripts/``.
    """
    targets: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)
    for sub in _SUBDOC_DIRS:
        sub_dir = skill_dir / sub
        if sub_dir.is_dir():
            targets.extend(sorted(sub_dir.glob('*.md')))
    scripts_dir = skill_dir / 'scripts'
    if scripts_dir.is_dir():
        targets.extend(sorted(scripts_dir.rglob('*.py')))
    return targets


def analyze_notation_staleness(
    paths: list[Path],
    *,
    rules_filter: set[str] | None = None,
) -> list[dict]:
    """Scan ``paths`` for stale executor notations.

    Parameters
    ----------
    paths:
        List of skill directories and / or individual files to scan. A
        directory entry is treated as a skill directory and expanded via
        ``_resolve_targets``; a file entry is scanned directly (its
        marketplace root is resolved from the file's own path).
    rules_filter:
        Optional opt-in rule allow-list. When supplied and ``RULE_ID`` is
        not in the set, the analyzer returns no findings. When ``None``
        (the default), the rule is unconditionally active.

    Returns
    -------
    list[dict]
        A list of finding dicts (see module docstring for the shape).
    """
    if rules_filter is not None and RULE_ID not in rules_filter:
        return []

    findings: list[dict] = []
    for entry in paths:
        if entry.is_dir():
            root = _marketplace_root(entry)
            if root is None:
                continue
            for target in _resolve_targets(entry):
                findings.extend(_scan_file(target, root))
        elif entry.is_file():
            # Resolve marketplace root from the file's nearest skill ancestor.
            skill_ancestor = None
            for parent in entry.parents:
                if parent.parent.name == 'skills':
                    skill_ancestor = parent
                    break
            if skill_ancestor is None:
                continue
            root = _marketplace_root(skill_ancestor)
            if root is None:
                continue
            findings.extend(_scan_file(entry, root))
    return findings
