#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic change-type classifier for phase-3-outline Step 4.

Scores the plan's clarified-request narrative against a small keyword
table and returns one of ``feature``, ``bug_fix``, ``tech_debt``,
``enhancement``, ``verification``, ``analysis`` — or ``ambiguous=true``
when no keyword fires, when two change types tie, or when the top
score's confidence falls below ``0.7``. The caller dispatches the
``plan-marshall:phase-3-outline/workflow/detect-change-type.md``
workflow via ``execution-context-{level}`` resolved from
``effort`` only when ``ambiguous=true``.

The change-type vocabulary, keyword indicators, compound-intent guard,
and bug-fix-vs-tech-debt object disambiguation mirror the rules in
``detect-change-type.md`` so the heuristic and the LLM fallback resolve
identical narratives identically when both are exercised.
"""

from __future__ import annotations

import argparse
import re
from typing import Any

from _plan_parsing import parse_document_sections
from _status_core import read_status, write_status
from file_ops import get_plan_dir
from plan_logging import log_entry

# Confidence floor: below this the heuristic refuses to commit and the
# caller MUST dispatch the LLM detect-change-type workflow instead.
_CONFIDENCE_FLOOR = 0.70

# Keyword tables — taken from detect-change-type.md § Change-Type Vocabulary.
# All keywords are lowercased; matching is case-insensitive word-boundary.
_KEYWORDS: dict[str, frozenset[str]] = {
    'analysis': frozenset({
        'analyze', 'analyse', 'investigate', 'understand', 'research',
        'examine', 'study', 'review',
    }),
    'feature': frozenset({
        'add', 'create', 'new', 'implement', 'build', 'introduce',
    }),
    'enhancement': frozenset({
        'improve', 'enhance', 'extend', 'update', 'upgrade',
    }),
    'bug_fix': frozenset({
        'bug', 'error', 'crash', 'exception', 'failure', 'broken',
        'incorrect', 'regression',
    }),
    'tech_debt': frozenset({
        'refactor', 'restructure', 'cleanup', 'migrate', 'deprecation',
        'deprecated', 'outdated', 'modernize', 'obsolete', 'warnings',
        'legacy',
    }),
    'verification': frozenset({
        'verify', 'validate', 'confirm', 'ensure', 'audit',
    }),
}

# Tech-debt object disambiguation for the ``fix`` verb.
# ``fix`` + bug objects → bug_fix; ``fix`` + tech_debt objects → tech_debt.
_TECH_DEBT_OBJECTS: frozenset[str] = frozenset({
    'deprecation', 'deprecations', 'deprecated', 'outdated',
    'warnings', 'warning', 'obsolete', 'legacy', 'cleanup',
})
_BUG_OBJECTS: frozenset[str] = frozenset({
    'bug', 'bugs', 'error', 'errors', 'crash', 'crashes', 'exception',
    'exceptions', 'failure', 'failures', 'broken', 'incorrect',
    'regression', 'regressions',
})

# Action verbs that flip ``analysis`` to its implementation cousin under
# the compound-intent guard (see detect-change-type.md § Step 4).
_COMPOUND_INTENT_VERBS: frozenset[str] = frozenset({
    'fix', 'implement', 'improve', 'update', 'create', 'refactor',
    'migrate', 'remove', 'restructure', 'add', 'extend', 'introduce',
})

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z_-]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase + word-tokenize. Preserves hyphenated identifiers."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def _load_request_narrative(plan_id: str) -> tuple[str, str | None]:
    """Read clarified_request (or original_input fallback) from request.md.

    Returns ``(narrative_text, source_section_or_None)``. The source is
    None when neither section can be located, in which case the script
    reports ``ambiguous=true`` so the LLM dispatch fires.
    """
    request_path = get_plan_dir(plan_id) / 'request.md'
    if not request_path.exists():
        return '', None
    try:
        content = request_path.read_text(encoding='utf-8')
    except OSError:
        return '', None

    sections = parse_document_sections(content)
    for candidate in ('clarified_request', 'original_input'):
        body = sections.get(candidate)
        if isinstance(body, str) and body.strip():
            return body, candidate
    return '', None


def _score_change_types(tokens: list[str]) -> dict[str, int]:
    """Return per-change-type keyword-overlap counts.

    ``bug_fix`` and ``tech_debt`` receive an extra +1 for the ``fix`` verb
    routed to whichever side the object class falls on; ``feature`` and
    ``enhancement`` see the same boost for ``add``/``improve``/etc.
    """
    token_set = set(tokens)
    scores = {key: len(token_set & kw) for key, kw in _KEYWORDS.items()}

    if 'fix' in token_set or 'resolve' in token_set:
        bug_hit = bool(token_set & _BUG_OBJECTS)
        tech_hit = bool(token_set & _TECH_DEBT_OBJECTS)
        if tech_hit and not bug_hit:
            scores['tech_debt'] += 1
        elif bug_hit:
            scores['bug_fix'] += 1
        else:
            # Bare "fix" with no object class — default to bug_fix per
            # detect-change-type.md's ELSE branch.
            scores['bug_fix'] += 1

    return scores


def _apply_compound_intent_guard(
    scores: dict[str, int],
    tokens: list[str],
) -> dict[str, int]:
    """Demote ``analysis`` when an implementation verb is also present.

    Returns the adjusted score dict. Mirrors the compound-intent rule in
    detect-change-type.md Step 4: "Analyze X and fix issues" should
    resolve to ``enhancement`` / ``tech_debt`` / ``bug_fix``, not
    ``analysis``.
    """
    if scores.get('analysis', 0) == 0:
        return scores
    if not (set(tokens) & _COMPOUND_INTENT_VERBS):
        return scores
    adjusted = dict(scores)
    adjusted['analysis'] = 0
    return adjusted


def _pick_winner(scores: dict[str, int]) -> tuple[str | None, float, bool]:
    """Return ``(change_type, confidence, ambiguous)`` from the scored map.

    Confidence is ``top / (top + second)`` per the standard winner-margin
    formulation. ``ambiguous`` flips when:
      - every score is zero (no keyword fired), OR
      - the top two scores tie (no clear winner), OR
      - confidence falls below ``_CONFIDENCE_FLOOR``.
    """
    if not scores or max(scores.values()) == 0:
        return None, 0.0, True

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_key, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if second_score == top_score:
        return top_key, 0.5, True

    total = top_score + second_score
    confidence = top_score / total if total else 0.0
    ambiguous = confidence < _CONFIDENCE_FLOOR
    return top_key, round(confidence, 3), ambiguous


def cmd_change_type_heuristic(args: argparse.Namespace) -> dict[str, Any]:
    """Run the deterministic change-type classifier for a plan.

    With ``--persist`` (default off), the resolved change type lands in
    ``status.metadata.change_type`` so phase-3-outline doesn't need a
    follow-up ``metadata --set`` call. Persistence is skipped when
    ``ambiguous=true`` so the LLM dispatch (which itself persists) is
    the single writer in that path.
    """
    plan_id: str = args.plan_id
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    narrative, source = _load_request_narrative(plan_id)
    if source is None:
        return {
            'status': 'success',
            'plan_id': plan_id,
            'change_type': None,
            'confidence': 0.0,
            'ambiguous': True,
            'source': None,
            'scores': dict.fromkeys(_KEYWORDS, 0),
            'persisted': False,
            'reason': 'request.md missing clarified_request and original_input',
        }

    tokens = _tokenize(narrative)
    scores = _score_change_types(tokens)
    scores = _apply_compound_intent_guard(scores, tokens)

    change_type, confidence, ambiguous = _pick_winner(scores)

    persisted = False
    if persist and change_type is not None and not ambiguous:
        try:
            status = read_status(plan_id)
        except FileNotFoundError:
            status = {}
        if 'metadata' not in status or not isinstance(status['metadata'], dict):
            status['metadata'] = {}
        status['metadata']['change_type'] = change_type
        write_status(plan_id, status)
        log_entry(
            'work',
            plan_id,
            'INFO',
            f'[MANAGE-STATUS] (change-type-heuristic) Detected change_type={change_type} (confidence={confidence}).',
        )
        persisted = True

    return {
        'status': 'success',
        'plan_id': plan_id,
        'change_type': change_type,
        'confidence': confidence,
        'ambiguous': ambiguous,
        'source': source,
        'scores': scores,
        'persisted': persisted,
    }
