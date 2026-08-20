#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Incident-reference scanner for the ``no-incident-references`` rule.

This module implements a deterministic regex-based static analyzer that
detects references to specific past plan-marshall PRs/issues used as
*narration* inside marketplace bundle documents and scripts — under
``marketplace/bundles/*/{skills,agents,commands}/**/*.{md,py}``.

Such a reference reasons from an incident the reader **cannot see**: it costs
context on every load and teaches the reader to reason from a PR number
instead of from the mechanism in front of them. ``CLAUDE.md`` § Documentation
Standards already forbids this ("No version history", "No timestamps",
"Current state only"); this rule enforces it so the pattern cannot regress.

Pattern alignment
-----------------
The analyzer mirrors ``_analyze_historical_prose_in_skills.py`` — pure static
analysis, regex-driven, stdlib-only, no mutation, and the same structural
exemptions (allowlisted paths via the shipped suppression config, YAML
frontmatter, fenced code blocks, ``Source:`` provenance lines, inline-code
spans, and per-file ``plugin-doctor-disable`` frontmatter). It differs in two
ways: it scans ``*.py`` scripts in addition to ``*.md`` (an incident label in a
docstring is the same misleading signal as one in prose), and it detects a
single family — the incident-narration form.

Detection
---------
The family fires on any of these narration forms (outside the exempt contexts
above):

1. **Explicit plan-marshall ref** — ``plan-marshall#NNNN``.
2. **Observed-on citation** — a capitalized ``Observed on`` clause opener
   followed by a ``#NNNN`` reference. Case-sensitive on ``Observed`` so that a
   lowercase mid-sentence "…observed on #103" in a genuine observation record
   (a bot data-sheet citing where a field was confirmed) is NOT flagged.
3. **Temporal narration** — ``post-#NNNN`` / ``pre-#NNNN`` / ``since #NNNN``.
4. **Incident term-of-art** — a ``#NNNN`` (optionally ``PR #NNNN``) bound to an
   incident noun: ``failure mode`` / ``signature`` / ``shape`` / ``defect`` /
   ``incident`` / ``regression`` (an optional single hyphenated qualifier may
   sit between, e.g. ``#948 sibling-worktree shape``).
5. **Incident term-of-art, REVERSED** — the same noun set with the reference
   AFTER it ("the failure mode #NNNN"), same optional hyphenated qualifier.
   English prose reaches for this ordering at least as often as form 4's.
6. **Dated / version-pinned narration** — a temporal preposition (``as of`` /
   ``since`` / ``before`` / ``after``) followed by a ``YYYY``(``-MM``(``-DD``))
   date or an ``N.N.N`` version. The date is the incident marker: prose pinned
   to a moment states when something WAS true rather than what IS true.

Deliberately NOT flagged, because the reference is not incident narration the
reader cannot act without: a bare ``#NNNN`` in prose with no incident noun
(ordinary provenance / worked-example / external-tracker citation), a
back-ticked ``#NNNN`` (a code token, exempt as inline code — tested at the
reference's offset inside the match, so forms 2 and 5, whose matches begin
before the reference, are exempt on the same terms as the rest), a lowercase
"observed on #NNNN" in an observation record, and a version CONSTRAINT carrying
no temporal preposition ("requires Python 3.12", "Node 20.1.0 or newer",
">= 1.2.3"), which states a requirement holding NOW rather than a moment.

Exemption posture
-----------------
This rule ships **unconditional**: no path is registered under ``RULE_ID`` in
``config/default-suppression.yml``. The genuinely-referential contexts that do
exist (bot data-sheets, the rule provenance/catalog docs) fall outside the
narration family above, so none needs a permanent exemption. The shared
config-suppression capability remains available — a future maintainer may
register a prefix under ``RULE_ID`` — but is left carrying zero entries rather
than a token unused mechanism.

Findings have the shape::

    {
        'rule_id': 'no-incident-references',
        'type': 'incident_reference',
        'rule': 'analyze_incident_reference_in_docs',
        'file': '<absolute md/py path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'snippet': '<matched text excerpt>',
        'description': 'Incident reference — state the mechanism, not the PR number. See rule-catalog.md.',
        'pattern_family': 'incident_reference',
    }

Public API
----------
- ``analyze_incident_reference_in_docs(marketplace_root)``: entry point.
- ``incident_reference_targets(marketplace_root)``: the derived file
  population, published so a clean verdict over an empty set is distinguishable
  from a clean tree (asserted non-empty by the rule's tests).
"""

from __future__ import annotations

import re
from pathlib import Path

from _analyze_shared import (
    _config_layer_suppresses,
    load_default_suppression_config,
    read_frontmatter_disable_list,
)
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'no-incident-references'
RULE_NAME = 'analyze_incident_reference_in_docs'

# Suppressible content scanner (project config / per-file frontmatter).
RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='content',
    scope='file-local',
)
FINDING_TYPE = 'incident_reference'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

# 1. Explicit plan-marshall reference: ``plan-marshall#NNNN``.
_PLAN_MARSHALL_REF_RE = re.compile(r'plan-marshall#\d+', re.IGNORECASE)

# 2. Observed-on citation: a capitalized clause opener followed by a #ref.
# Case-SENSITIVE on "Observed" — a lowercase "…observed on #103" is an
# observation record (bot data-sheet), not incident narration.
_OBSERVED_ON_RE = re.compile(r'Observed on\b[^\n]{0,80}#\d+')

# 3. Temporal narration: ``post-#NNNN`` / ``pre-#NNNN`` / ``since #NNNN``.
_TEMPORAL_RE = re.compile(r'\b(?:post-#|pre-#|since #)\d+', re.IGNORECASE)

# 4. Incident term-of-art: a #ref bound to an incident noun, with an optional
# single hyphenated qualifier between (e.g. "#NNNN sibling-worktree shape").
_TERM_OF_ART_RE = re.compile(
    r'#\d{3,4}\s+(?:[A-Za-z]+-[A-Za-z]+\s+)?'
    r'(?:failure mode|signature|shape|defect|incident|regression)\b',
    re.IGNORECASE,
)

# 5. Incident term-of-art, REVERSED: the noun first, the reference after it
# ("the failure mode #NNNN"). The shipped form above requires the reference
# first, so this ordering — the one English prose reaches for at least as often
# — passed a rule whose own brief named it. Same noun set, same optional
# hyphenated qualifier, mirrored.
#
# The example above spells the reference as a LITERAL ``#NNNN`` placeholder, as
# every example in this module does: the population includes ``*.py``, so a
# comment carrying a real digit run would make the analyzer fire on itself.
_TERM_OF_ART_REVERSED_RE = re.compile(
    r'(?:failure mode|signature|shape|defect|incident|regression)\s+'
    r'(?:[A-Za-z]+-[A-Za-z]+\s+)?`?#\d{3,4}',
    re.IGNORECASE,
)

# 6. Dated / version-pinned narration: a temporal preposition followed by a
# YYYY(-MM(-DD)) date or an N.N.N version. The date or version is the incident
# marker here — prose anchored to a moment states when something WAS true rather
# than what IS true, which is the same provenance-as-normative-prose defect a
# #ref carries.
#
# The temporal preposition is REQUIRED, which is what keeps an ordinary version
# CONSTRAINT ("requires Python 3.12", "Node 20.1.0 or newer") out of scope: those
# state a requirement that holds now, not a moment prose is pinned to.
#
# No example here spells a real date or version after a preposition, for the
# self-trigger reason given above.
_DATED_NARRATION_RE = re.compile(
    r'\b(?:as of|since|before|after)\s+(?:20\d{2}(?:-\d{2}(?:-\d{2})?)?|\d+\.\d+\.\d+)\b',
    re.IGNORECASE,
)

# All narration forms as (name, compiled_regex) pairs. A single finding family
# ('incident_reference') is emitted regardless of which form matched.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('plan_marshall_ref', _PLAN_MARSHALL_REF_RE),
    ('observed_on', _OBSERVED_ON_RE),
    ('temporal_narration', _TEMPORAL_RE),
    ('incident_term_of_art', _TERM_OF_ART_RE),
    ('incident_term_of_art_reversed', _TERM_OF_ART_REVERSED_RE),
    ('dated_narration', _DATED_NARRATION_RE),
]

# Locates the ``#NNNN`` reference inside a matched narration span.
_REF_IN_MATCH_RE = re.compile(r'#\d+')

# Inline-code span detection (matches `...`).
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# Fenced-block boundaries.
_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

# Source: line — structured provenance citation marker.
_SOURCE_LINE_RE = re.compile(r'^\s*(?:[-*]\s*)?\*{0,2}Source:\*{0,2}', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def _is_allowlisted(rel_to_bundles: str, default_cfg: dict[str, list[str]]) -> bool:
    """Return True if the file path is exempt from this rule (Granularity-1).

    Delegates to the shared config-layer predicate: a file is exempt when its
    bundles-relative path starts with a prefix registered under ``RULE_ID`` in
    ``config/default-suppression.yml``. This rule ships with **no** registered
    prefixes (it is unconditional), so this returns False for every path today;
    the delegation keeps the exemption capability available without a private
    list in the analyzer.
    """
    return _config_layer_suppresses(RULE_ID, rel_to_bundles, default_cfg)


# ---------------------------------------------------------------------------
# Helpers (mirror _analyze_historical_prose_in_skills.py)
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string."""
    inside: dict[int, str] = {}
    in_fence = False
    info_string = ''
    for idx, line in enumerate(lines):
        if not in_fence:
            m = _FENCE_OPEN_RE.match(line)
            if m:
                in_fence = True
                info_string = m.group(1).lower()
        else:
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
                info_string = ''
            else:
                inside[idx] = info_string
    return inside


def _build_frontmatter_set(lines: list[str]) -> set[int]:
    """Return the 0-based indices of lines inside leading YAML frontmatter."""
    inside: set[int] = set()
    if not lines or lines[0].strip() != '---':
        return inside
    inside.add(0)
    for idx in range(1, len(lines)):
        inside.add(idx)
        if lines[idx].strip() == '---':
            return inside
    return set()


def _inline_code_spans(line: str) -> list[tuple[int, int]]:
    """Return (start, end) character offsets of inline-code spans on ``line``."""
    return [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(line)]


def _offset_in_inline_code(offset: int, spans: list[tuple[int, int]]) -> bool:
    """Return True if ``offset`` lies within any of the inline-code spans."""
    return any(start <= offset < end for start, end in spans)


def _exemption_offset(match: re.Match) -> int:
    """The offset the inline-code exemption is tested at, for any narration form.

    The exemption is about the REFERENCE being a code token, so it is tested at
    the ``#NNNN`` inside the match rather than at the match's first character.

    TWO families have a match that begins BEFORE the reference, and both are
    affected — not just the new one:

    * ``incident_term_of_art_reversed``, where the match begins at the noun; and
    * ``observed_on``, whose pattern begins at ``Observed`` and can carry up to
      80 characters before the reference. Under the match-start test a
      back-ticked reference there still fired, making ``observed_on`` the ONE
      family in which the project-wide "a back-ticked reference is a code token"
      convention did not hold. Testing at the reference offset makes it hold
      everywhere, which WIDENS that family's exemption.

    That widening is deliberate and is disclosed rather than silent: it aligns
    the family with the convention published across the rule catalogue, the
    provenance table, a named test, and a sibling rule. It is bounded — over the
    whole derived population, zero ``observed_on`` lines have a verdict the
    change flips — and pinned by
    ``test_observed_on_with_a_backticked_ref_is_exempt``.

    A match carrying no ``#NNNN`` at all (the dated-narration form) has no
    reference to exempt, so the match start is used.
    """
    ref = _REF_IN_MATCH_RE.search(match.group(0))
    return match.start() + ref.start() if ref else match.start()


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path, rel_to_bundles: str, default_cfg: dict[str, list[str]]) -> list[dict]:
    """Scan a single markdown or python file and return all findings."""
    if _is_allowlisted(rel_to_bundles, default_cfg):
        return []

    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                type='file_read_error',
                file=str(path),
                line=0,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=f'Could not read file: {exc}',
                extra={'rule': RULE_NAME, 'snippet': '', 'pattern_family': 'file_read_error'},
            ).to_dict()
        ]

    # Per-file frontmatter: skip the whole file when its ``plugin-doctor-disable``
    # list names this rule. (A ``*.py`` file has no YAML frontmatter, so this is
    # a harmless no-op there.)
    if RULE_ID in read_frontmatter_disable_list(text):
        return []

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    frontmatter = _build_frontmatter_set(lines)

    findings: list[Finding] = []

    for idx, line in enumerate(lines):
        # Skip lines inside YAML frontmatter or fenced code blocks.
        if idx in frontmatter:
            continue
        if idx in fence_map:
            continue
        # Skip Source: provenance lines.
        if _SOURCE_LINE_RE.match(line):
            continue

        # Quick pre-check: does any pattern fire on this line?
        if not any(pat.search(line) for _, pat in _PATTERNS):
            continue

        spans = _inline_code_spans(line)

        # Emit at most one finding per line, from the first narration match — of
        # any form — whose start is OUTSIDE an inline-code span. Iterate ALL
        # matches of each pattern (``finditer``, not just the first ``search``):
        # a back-ticked reference early on a line must not mask a bare reference
        # later on the SAME line (the concrete case is pinned by the rule's tests).
        emitted = False
        for family_name, pattern in _PATTERNS:
            for m in pattern.finditer(line):
                # Skip matches whose start offset is fully inside an inline-code
                # span — those are code-token references, not narration.
                if _offset_in_inline_code(_exemption_offset(m), spans):
                    continue
                findings.append(
                    Finding(
                        type=FINDING_TYPE,
                        file=str(path),
                        line=idx + 1,
                        severity='warning',
                        fixable=False,
                        rule_id=RULE_ID,
                        description=(
                            'Incident reference — state the mechanism the incident '
                            'named, not the PR number. See rule-catalog.md.'
                        ),
                        extra={'rule': RULE_NAME, 'snippet': m.group(0), 'pattern_family': family_name},
                    )
                )
                emitted = True
                break
            if emitted:
                break

    return [f.to_dict() for f in findings]


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def incident_reference_targets(marketplace_root: Path) -> list[tuple[Path, str]]:
    """Return ``(absolute_path, rel_to_bundles)`` for every in-scope file.

    The population this rule examines: every ``*.md`` and ``*.py`` under
    ``marketplace_root/*/{skills,agents,commands}/**``. Published (rather than
    kept private, like the sibling rule's target walk) so a clean verdict over
    an empty set is distinguishable from a clean tree — the rule's tests assert
    this population is non-empty over the real marketplace.
    """
    if not marketplace_root.is_dir():
        return []
    results: list[tuple[Path, str]] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        for sub in ('skills', 'agents', 'commands'):
            sub_dir = bundle_dir / sub
            if not sub_dir.is_dir():
                continue
            for pattern in ('*.md', '*.py'):
                for target in sorted(sub_dir.rglob(pattern)):
                    if target.is_file():
                        rel = str(target.relative_to(marketplace_root)).replace('\\', '/')
                        results.append((target, rel))
    return results


def analyze_incident_reference_in_docs(marketplace_root: Path) -> list[dict]:
    """Scan bundle docs and scripts for plan-marshall incident references.

    Walks ``marketplace_root/*/{skills,agents,commands}/**/*.{md,py}`` and
    reports every incident-narration occurrence outside the documented exempt
    contexts (allowlisted path, YAML frontmatter, fenced code block, ``Source:``
    provenance line, inline-code span, or a per-file
    ``plugin-doctor-disable: [no-incident-references]`` frontmatter key).

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace bundles root (the directory that contains the
        ``plan-marshall``, ``pm-plugin-development``, etc. bundle directories).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree). If the derived file
        population is empty, returns a single ``empty_population`` anti-vacuity
        finding instead, so a clean verdict over an unread population cannot be
        read as a clean tree.
    """
    default_cfg = load_default_suppression_config()
    targets = incident_reference_targets(marketplace_root)
    # Anti-vacuity: publish the examined population at runtime. A clean verdict
    # over an EMPTY population is vacuous — it must not read as a clean tree — so
    # an empty population is itself surfaced as a finding rather than a silent
    # pass (the failure archetype this epic is named for).
    if not targets:
        return [
            Finding(
                type=FINDING_TYPE,
                file=str(marketplace_root),
                line=0,
                severity='warning',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    'Incident-reference scan derived an EMPTY file population '
                    '(no *.md or *.py under */{skills,agents,commands}/**). A '
                    'clean result over an empty population is vacuous, not a '
                    'clean tree.'
                ),
                extra={
                    'rule': RULE_NAME,
                    'snippet': '',
                    'pattern_family': 'empty_population',
                    'population_size': 0,
                },
            ).to_dict()
        ]
    findings: list[dict] = []
    for target_path, rel in targets:
        findings.extend(_scan_file(target_path, rel, default_cfg))
    return findings
