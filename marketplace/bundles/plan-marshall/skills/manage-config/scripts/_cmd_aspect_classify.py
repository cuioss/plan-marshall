# SPDX-License-Identifier: FSL-1.1-ALv2
"""aspect-classify command handler for manage-config.

Deterministic request-aspect classifier. Given free-form ``--request-text``,
it tokenizes the text via the shared ``recipe_scoring`` core and scores the
overlap of the request tokens against two fixed keyword tables — one for
analysis/planning intent, one for implementation intent — returning an
``aspect ∈ {analysis, planning, implementation}`` plus a confidence.

Threshold contract: the winning aspect is accepted only when its confidence
clears the ``>= 0.7`` threshold (overridable via ``--threshold``, default
``0.7``). Below the threshold the classifier returns ``aspect:
implementation`` — the safe fallback that keeps the build / quality-gate /
test gates in the composed manifest. This mirrors ``change-type-heuristic``'s
heuristic-first / conservative-default contract.

Heuristic-first: this verb performs NO LLM call and NO plan-scoped read. The
bounded LLM fallback for genuinely ambiguous requests is the orchestrator's
responsibility (phase-1-init), keeping the LLM out of the script body.
"""

from __future__ import annotations

from typing import Any

from recipe_scoring import tokenize  # type: ignore[import-not-found]

# Default acceptance threshold: a winning aspect score at or above this
# confidence is accepted; anything below falls back to ``implementation``.
_DEFAULT_THRESHOLD = 0.7

# Keyword tables for the two non-default aspects. The request is classified by
# the overlap of its tokens with these tables. Tokens are matched after
# ``recipe_scoring.tokenize`` (lower-cased, stop-word filtered, length > 2), so
# every entry below is in that canonical token form.
_ANALYSIS_KEYWORDS: frozenset[str] = frozenset({
    'analysis', 'analyze', 'analyse', 'analyzing', 'audit', 'auditing',
    'assess', 'assessment', 'evaluate', 'evaluation', 'review', 'reviewing',
    'investigate', 'investigation', 'examine', 'inspect', 'inspection',
    'survey', 'study', 'understand', 'understanding', 'explore', 'exploration',
    'diagnose', 'diagnosis', 'compare', 'comparison', 'measure', 'metrics',
    'report', 'reporting', 'summarize', 'summary', 'identify', 'find',
    'research', 'retrospective', 'inventory',
})

_PLANNING_KEYWORDS: frozenset[str] = frozenset({
    'plan', 'planning', 'design', 'designing', 'outline', 'proposal',
    'propose', 'roadmap', 'strategy', 'approach', 'architecture',
    'architect', 'scope', 'scoping', 'estimate', 'estimation', 'schedule',
    'prioritize', 'prioritization', 'breakdown', 'decompose', 'specification',
    'specify', 'blueprint', 'draft',
})

_IMPLEMENTATION_KEYWORDS: frozenset[str] = frozenset({
    'implement', 'implementation', 'build', 'create', 'add', 'write',
    'code', 'develop', 'fix', 'refactor', 'rename', 'remove', 'delete',
    'update', 'modify', 'change', 'replace', 'migrate', 'migration',
    'extend', 'introduce', 'wire', 'integrate', 'integration', 'patch',
    'rework', 'rewrite', 'test', 'tests', 'testing', 'feature',
    'bugfix', 'install', 'configure', 'deploy', 'release', 'commit',
})


def _overlap_score(request_tokens: set[str], keyword_table: frozenset[str]) -> tuple[float, list[str]]:
    """Return ``(score, matched)`` for the request tokens against a table.

    Score is the fraction of request tokens that appear in the keyword
    table — a request whose vocabulary is dominated by one aspect's keywords
    scores high for that aspect. Returns ``0.0`` for an empty request.
    """
    if not request_tokens:
        return 0.0, []
    matched = sorted(request_tokens & keyword_table)
    score = len(matched) / len(request_tokens)
    return round(score, 3), matched


def cmd_aspect_classify(args) -> dict[str, Any]:
    """Classify request text as analysis / planning / implementation.

    The caller (phase-1-init) consumes the return TOON and persists the
    resolved ``aspect``; the execution-manifest composer drops build /
    quality-gate / test steps when the aspect is ``analysis`` or
    ``planning``. Below the threshold the safe ``implementation`` fallback
    keeps every gate in place.
    """
    request_text: str = args.request_text
    threshold: float = float(getattr(args, 'threshold', _DEFAULT_THRESHOLD) or _DEFAULT_THRESHOLD)

    request_tokens = tokenize(request_text)

    analysis_score, analysis_matched = _overlap_score(request_tokens, _ANALYSIS_KEYWORDS)
    planning_score, planning_matched = _overlap_score(request_tokens, _PLANNING_KEYWORDS)
    implementation_score, implementation_matched = _overlap_score(request_tokens, _IMPLEMENTATION_KEYWORDS)

    scores = {
        'analysis': analysis_score,
        'planning': planning_score,
        'implementation': implementation_score,
    }
    breakdown = {
        'analysis': {'score': analysis_score, 'matched_keywords': analysis_matched},
        'planning': {'score': planning_score, 'matched_keywords': planning_matched},
        'implementation': {'score': implementation_score, 'matched_keywords': implementation_matched},
    }

    # Decide between the two non-default aspects: the higher of analysis /
    # planning is the candidate. Only when that candidate clears the threshold
    # AND beats the implementation overlap does the request earn a
    # non-implementation aspect; otherwise the safe implementation fallback
    # applies (keeping build / quality-gate / test gates).
    if planning_score > analysis_score:
        candidate_aspect, candidate_score = 'planning', planning_score
    else:
        candidate_aspect, candidate_score = 'analysis', analysis_score

    if candidate_score >= threshold and candidate_score > implementation_score:
        aspect = candidate_aspect
        confidence = candidate_score
        drops_build_steps = True
    else:
        aspect = 'implementation'
        confidence = implementation_score
        drops_build_steps = False

    return {
        'status': 'success',
        'request_tokens': sorted(request_tokens),
        'threshold': threshold,
        'aspect': aspect,
        'confidence': confidence,
        'drops_build_steps': drops_build_steps,
        'scores': scores,
        'breakdown': breakdown,
    }
