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
heuristic-first / conservative-default contract. One exception: an explicit
negative build constraint in the raw request text (a fixed negation-phrase
table, e.g. ``"no build"`` / ``"docs only"``, matched case-insensitively
BEFORE tokenization) overrides the sub-threshold fallback — the classifier
then returns the higher-scored non-implementation candidate aspect with
``drops_build_steps: true`` and reports the matched phrase via
``negative_constraint_matched``.

Heuristic-first: this verb performs NO LLM call and NO plan-scoped read. The
bounded LLM fallback for genuinely ambiguous requests is the orchestrator's
responsibility (phase-1-init), keeping the LLM out of the script body.

No-plan-scoped-read is a deliberate contract, not an omission. aspect-classify
is the **compose-time narrative-only** signal: it runs at ``phase-1-init`` and
end-of-``phase-4-plan``, both BEFORE phase-5 Step 2.5 materialises the worktree,
so the live footprint is ALWAYS empty at classification time. A footprint read
inside this verb would therefore resolve ``[]`` and mis-drop every build step —
the empty-footprint trap. The classifier deliberately reads only the request
narrative and stays out of footprint territory.

Run-time footprint-consistency is delivered at the ONE point with footprint
fidelity: the ``manage-config build-decision`` consult wired into phase-5
execution (Step 11b Final Quality Sweep + the ``default:verify:{canonical}``
loop). That consult — a thin wrapper over ``extension_base.should_execute_build``
— is the authoritative run-time footprint backstop. The two signals are
complementary and non-contradictory: this narrative aspect-drop clears the
phase-5 verification list at compose for a confident ``analysis`` / ``planning``
request (nothing left to gate), while ``build-decision`` corrects an
``implementation``-classified plan whose live footprint turned out to be
pure-doc by returning ``not_necessary`` and skipping the whole-tree build. See
``manage-execution-manifest/scripts/_manifest_rules.py`` ``_apply_aspect_step_dropping``
for the compose-time half of this division of labour.
"""

from __future__ import annotations

import re
from typing import Any

from recipe_scoring import tokenize

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

# Explicit negative build constraints. Matched case-insensitively against the
# RAW ``--request-text`` BEFORE tokenization: ``recipe_scoring.tokenize``
# drops ``no`` (length > 2 filter) and ``build`` is itself an
# ``_IMPLEMENTATION_KEYWORDS`` member, so a token-set approach structurally
# cannot see the negation — the override keys on the phrase, not the tokens.
_NEGATION_PHRASES: tuple[str, ...] = (
    'no build',
    'no builds',
    'without build',
    'do not build',
    'no verify',
    'docs only',
    'docs-only',
    'documentation only',
    'documentation-only',
)


def _match_negation_phrase(request_text: str) -> str | None:
    """Return the matched negation phrase from the raw request text, if any.

    Case-insensitive word-boundary match (``\\b``-anchored regex) over the
    fixed ``_NEGATION_PHRASES`` table, longest phrase first so the most
    specific phrase is reported (e.g. ``'no builds'`` wins over its
    ``'no build'`` prefix). Word boundaries prevent substring false
    positives where a phrase appears inside a larger token — e.g.
    ``"mono build"`` contains ``"no build"`` as a substring but MUST NOT
    trigger the negation override.
    """
    lowered = request_text.lower()
    for phrase in sorted(_NEGATION_PHRASES, key=len, reverse=True):
        if re.search(r'\b' + re.escape(phrase) + r'\b', lowered):
            return phrase
    return None


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
    threshold: float = getattr(args, 'threshold', _DEFAULT_THRESHOLD)

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

    negation_phrase = _match_negation_phrase(request_text)

    if negation_phrase is not None:
        # Explicit negative build constraint: override the sub-threshold
        # implementation fallback — the request text itself rules out build
        # steps, so the higher-scored non-implementation candidate wins.
        aspect = candidate_aspect
        confidence = candidate_score
        drops_build_steps = True
    elif candidate_score >= threshold and candidate_score > implementation_score:
        aspect = candidate_aspect
        confidence = candidate_score
        drops_build_steps = True
    else:
        aspect = 'implementation'
        confidence = implementation_score
        drops_build_steps = False

    result: dict[str, Any] = {
        'status': 'success',
        'request_tokens': sorted(request_tokens),
        'threshold': threshold,
        'aspect': aspect,
        'confidence': confidence,
        'drops_build_steps': drops_build_steps,
        'scores': scores,
        'breakdown': breakdown,
    }
    if negation_phrase is not None:
        result['negative_constraint_matched'] = negation_phrase
    return result
