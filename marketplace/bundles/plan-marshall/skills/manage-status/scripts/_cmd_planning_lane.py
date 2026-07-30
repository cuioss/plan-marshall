#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Deterministic planning-lane router for phase-1-init.

Computes ``planning_lane ∈ {light, deep}`` from cheap field reads + a
``request.md`` regex, with ZERO codebase discovery and ZERO LLM cognition.
The default is ``light``; any deep-precondition signal forces ``deep``;
escalation is one-way (light may ratchet to deep, never deep→light).

The signal set (DQ1 of the planning-lanes solution outline):

| # | Signal | Source (cheap read) | → deep when |
|---|--------|---------------------|-------------|
| S1 | ``plan_source`` | ``status.metadata.plan_source`` | free-form (absent/unset) **AND** S5 concreteness fails |
| S2 | ``scope_estimate`` | ``references.scope_estimate`` | ∈ {multi_module, broad, none, unset} |
| S3 | ``change_type`` | ``status.metadata.change_type`` | ∈ {feature, feature_breaking} **AND NOT** narrow-and-concrete |
| S4 | ``compatibility`` | ``marshal.json plan.phase-2-refine.compatibility`` | == breaking **AND NOT** narrow-and-concrete |
| S5 | request concreteness | regex over ``request.md`` body | NO file path AND NO concrete fix signal |
| S6 | explicit override | ``status.metadata.planning_lane_override`` | == deep forces deep (one-way) |
| S7 | author risk prose | regex over ``request.md`` body | body carries an explicit scale warning |

``deep`` IFF (S1 ∨ S2 ∨ S3 ∨ S4 ∨ S5 ∨ S6-deep ∨ S7); otherwise ``light``.

The narrow-and-concrete carve-out: when ``scope_estimate == surgical`` AND the
request is concrete, S3 (generative change_type) and S4 (breaking compatibility)
are suppressed so they cannot force ``deep`` *alone* for a positively-bounded,
well-specified request. The carve-out demands ACTUAL narrowness — ``single_module``
is the catch-all middle band, not a bounded verdict, so it does NOT earn the
carve-out. The carve-out relaxes ONLY this co-firing — S1/S2/S5 (the
unknown-to-deep defaults), S6 (explicit override) and S7 (author risk prose) still
bias ``deep`` unchanged, so the conservative unknown case is untouched.

``plan.phase-1-init.deep_lane`` is read BEFORE the signal set and
short-circuits the evaluation: ``always`` forces deep, ``never`` forces light
(the DQ3 hard-escalation ratchet still fires unless ``plan.phase-1-init.escalation``
is also ``never``), ``auto`` (the default) defers to the signals.

The router also projects a RECOMMENDED execution-profile posture
(``minimal`` / ``standard`` / ``full``) over the SAME signals via
``project_profile_pure``. The projection is a pure derivation that adds no
discovery and no cognition; it is independent of the ``deep_lane`` gate_mode gate
(``deep_lane=always`` governs planning depth, NOT the profile — see
``extension-api/standards/ext-point-lane-element.md`` for the lane contract). On
``--persist`` the route command writes the projected posture into
``status.metadata.execution_profile`` as the init-time default; the phase-1-init
posture dialogue may override it via ``manage-status metadata``.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from _cmd_classification_validate import run_classification_validation
from _status_core import read_status, write_status
from constants import FILE_MARSHAL
from file_ops import base_path, get_plan_dir, read_json, write_json
from plan_logging import log_entry

LIGHT = 'light'
DEEP = 'deep'

# Execution-profile postures (the lane lattice minimal ⊏ standard ⊏ full). The
# planning-lane router projects a RECOMMENDED posture over the same signals it
# already scores for the {light, deep} verdict; the projection is independent of
# the deep_lane gate_mode gate (deep_lane governs planning DEPTH, not the profile
# — see ext-point-lane-element.md and §4.2 of the lane-selection outline).
MINIMAL = 'minimal'
STANDARD = 'standard'
FULL = 'full'

# Scope bands that read as broad-surface for the profile projection (a superset
# trigger toward keeping full ceremony when combined with a generative change).
_BROAD_SCOPE_ESTIMATES = frozenset({'multi_module', 'broad'})
# The ONE scope band that reads as genuinely narrow/localized — the sole member,
# so the narrow-and-concrete carve-out requires actual boundedness. Shared
# verbatim by evaluate_signals_pure (the lane verdict) and project_profile_pure
# (the posture projection), so this frozenset governs BOTH by construction:
# widening it would re-suppress S3/S4 *and* re-collapse the posture to minimal.
_NARROW_SCOPE_ESTIMATES = frozenset({'surgical'})

# S2 — scope_estimate values that bias deep (broad-surface / unknown bands).
# surgical / single_module do not fire S2; of the two only surgical additionally
# earns the narrow-and-concrete carve-out over S3/S4.
_DEEP_SCOPE_ESTIMATES = frozenset({'multi_module', 'broad', 'none'})

# S3 — change_type values that bias deep (generative, broad-surface).
# bug_fix / tech_debt / enhancement / verification bias light.
_DEEP_CHANGE_TYPES = frozenset({'feature', 'feature_breaking'})

# S5 — request-concreteness regexes.
# A file-path anchor: a repo-relative path with a directory separator and an
# extension (e.g. ``marketplace/.../foo.py``, ``test/x/test_y.py``).
_PATH_RE = re.compile(r'[\w./-]+/[\w.-]+\.[A-Za-z0-9]+')
# A concrete fix signal: a fenced code block, a ``python3 .plan/execute-script.py``
# CLI invocation, or an inline ``manage-*`` notation.
_FENCE_RE = re.compile(r'```')
_CLI_RE = re.compile(r'python3\s+\.plan/execute-script\.py')
_NOTATION_RE = re.compile(r'\bmanage-[a-z-]+\b')

# S7 — the author's own written scale warning. When a request says in prose that
# the work is large, that statement outranks any cheap band this module can
# compute from path counts: the author knows things the sensor cannot see.
# Case-insensitive and word-boundary anchored, mirroring the S5 pattern exactly.
#
# ``epic`` carries ONE extra guard, for the same reason ``_GLOB_RE``'s ``**``
# alternatives are path-adjacent: an alternative that matches document CHROME
# instead of request CONTENT makes the whole signal fire vacuously. Every ingested
# orchestrator plan spec opens with an ``epic:`` metadata key, so a bare ``\bepic\b``
# would fire S7 for the entire orchestrated population and the signal would mean
# "is orchestrator-authored" rather than "the author warned about scale" — and no
# orchestrated request, however genuinely surgical, could ever route light again.
# The ``(?!\s*:)`` lookahead therefore excludes the metadata-key form while keeping
# every prose use (``… the truthful-signals epic.``, ``an epic-sized rename``).
_RISK_PROSE_RE = re.compile(
    r'\b(?:multi-PR|codebase-wide|largest|riskiest|expect a split|foundation|campaign)\b'
    r'|\bepic\b(?!\s*:)',
    re.IGNORECASE,
)


def _distinct_paths(body: str) -> set[str]:
    """Return the DISTINCT repo-relative file paths ``_PATH_RE`` extracts from ``body``.

    The single source of the distinct-path extraction shared by
    ``classify_scope_pure`` and ``cmd_scope_estimate_heuristic``.
    Callers guard the empty-``body`` case themselves and layer their own
    downstream ``sorted()`` / ``len()`` on the returned set.

    What this counter counts — settled, not incidental:

    - **Path strings, not work targets.** The scan is purely lexical and has no
      notion of whether a matched path is a *target of the work* or a *citation
      of a governing document*. Discriminating the two needs the very
      architecture discovery and cognition this module is defined to exclude,
      so the sensor DECLARES ITS INAPPLICABILITY for that discrimination rather
      than faking it. The residual is documented, bounded, and one-directional:
      citations inflate the count, and inflation only ever pushes the band UP the
      ``surgical`` → ``single_module`` → ``multi_module`` line — so the error mode
      is conservative (more planning ceremony), never a silent narrowing.
      Consumers MUST read the count as "distinct path-shaped strings in the
      request", never as "files this plan will change".
    - **A directory separator is REQUIRED, deliberately.** ``_PATH_RE`` matches
      only ``dir/name.ext``, so a bare filename (``_cmd_planning_lane.py``,
      ``agents.md``) is intentionally NOT counted. This is a decision, not an
      artefact of the pattern: a bare filename cannot be resolved to a repo
      location without the directory discovery this module excludes, and
      matching bare ``word.word`` tokens would sweep in ordinary prose
      (``e.g.``, version numbers, sentence-final abbreviations). Under-counting
      a bare filename biases toward the wider band, which is the same
      conservative direction as citation inflation.

    Both properties are unchanged by the whole-body read in
    ``_read_request_body``; that change alters WHICH TEXT is scanned, never how
    a match is judged.
    """
    return {m.group(0) for m in _PATH_RE.finditer(body)}


# --- Pre-route scope_estimate heuristic --------------------------------------
# Coarse scope bands the pre-route heuristic emits. The band line is scale-
# truthful in both directions: it can report a bounded change (surgical) AND a
# large one (multi_module), so "I cannot bound this" never reads as "it is
# small". This is still a pre-route GUESS from cheap request signals, never the
# authoritative scope — the deep-lane refine Step 9 module-mapping derivation
# overwrites it with the measured band when the deep lane runs.
SURGICAL = 'surgical'
SINGLE_MODULE = 'single_module'
MULTI_MODULE = 'multi_module'
# The declared-unknown band emitted when the request body is unscoreable (absent,
# unreadable, or empty). It is a member of _DEEP_SCOPE_ESTIMATES, so S2 reads it
# as a deep-biasing signal — an unscoreable request never yields a confident
# narrow band. Reusing 'none' keeps the field inside the closed
# none|surgical|single_module|multi_module|broad enum that
# `manage-solution-outline validate` checks; no new member is introduced.
UNKNOWN = 'none'
# At most this many distinct file-path references still reads as a surgical,
# tightly-bounded change.
_SURGICAL_MAX_PATHS = 3
# From this many distinct file-path references upward the request reads as
# multi-module. The floor is anchored on the smallest counted instance in the
# observed under-routed population that fired ZERO deep signals.
_MULTI_MODULE_MIN_PATHS = 8
# A glob / pattern fan-out marker (``/**``, ``**/``, ``/*``, ``*/``, ``*.ext``)
# bands multi_module even with few explicit paths — a pattern implies fan-out
# across an unbounded file set, and an unbounded set cannot be a bounded one.
# The ``**`` alternatives are deliberately PATH-ADJACENT (``/**`` or ``**/``):
# a bare ``**`` also matches markdown bold, and because the marker check
# short-circuits ahead of the path count, a bold-saturated request body would
# otherwise decide the band on its own and make the count unreachable.
_GLOB_RE = re.compile(r'/\*\*|\*\*/|/\*|\*/|\*\.[A-Za-z0-9]+')

# The host document's own top-level title line (``# Request: {title}``). It is
# the ONLY line removed from the scored body — it is ``request.md`` chrome, not
# part of the request narrative. An ingested spec's own ``# PLAN-NN: …`` title
# does not match and is deliberately retained.
_REQUEST_TITLE_RE = re.compile(r'^#\s+Request\b')


def _read_request_body(plan_id: str) -> str:
    """Return the WHOLE ``request.md`` narrative, minus the document's title line.

    The scored text is deliberately **heading-blind**: it is the entire file
    body with only the host document's own ``# Request`` title line removed. No
    section boundary is consulted and nothing else is stripped.

    Why the whole body. ``request.md`` embeds an ingested orchestrator plan spec
    verbatim, and that spec legitimately carries its OWN markdown headings. The
    previous section-scoped read (``parse_document_sections`` →
    ``clarified_request`` / ``original_input``) terminated the section at the
    ingested body's first nested ``## `` line, because the shared splitter
    starts a new section on any line beginning ``'## '`` with no nesting
    awareness. The router therefore scored a boilerplate fragment — typically
    the spec's title plus the plan-spec template blockquote, whose only
    path-shaped token is a citation of a governing document — instead of the
    request. Reading the whole body removes that failure BY CONSTRUCTION: there
    is no section boundary left to get wrong, whatever headings the ingested
    body carries.

    Returns the empty string ONLY when ``request.md`` is genuinely absent,
    unreadable, or empty once the title line is removed — never as a side effect
    of document structure. That empty result is a DECLARED UNKNOWN:
    ``scope_estimate_from_request_pure`` reports it as ``none`` (a deep-biasing
    band) and the S5 concreteness check reads it as "no anchors", so an
    unscoreable request biases deep instead of receiving a confident band.
    """
    request_path = get_plan_dir(plan_id) / 'request.md'
    if not request_path.exists():
        return ''
    try:
        content = request_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        # UnicodeDecodeError is a ValueError subtype, not an OSError: a
        # non-UTF-8 request.md is an unreadable body, so it routes to the same
        # declared-unknown path as a missing file.
        return ''
    lines = content.split('\n')
    # Strip the title ONLY when it is the document's own first line. Matching
    # anywhere would also drop an ingested spec's ``# Request …`` heading, which
    # is request narrative, not host chrome — and would contradict the
    # ONLY-line-removed contract stated above.
    if lines and _REQUEST_TITLE_RE.match(lines[0]):
        lines = lines[1:]
    return '\n'.join(lines).strip()


def _request_is_concrete(body: str) -> bool:
    """S5 — the request names an existing file path OR a concrete fix signal.

    Concrete (returns True) when the body contains a file-path anchor OR a
    fenced code block / CLI invocation / ``manage-*`` notation. A vague ask
    with no anchors returns False (→ deep).
    """
    if not body:
        return False
    if _PATH_RE.search(body):
        return True
    if _FENCE_RE.search(body):
        return True
    if _CLI_RE.search(body):
        return True
    if _NOTATION_RE.search(body):
        return True
    return False


def _request_has_risk_prose(body: str) -> bool:
    """S7 — the request body carries an explicit author scale warning.

    Mirrors ``_request_is_concrete``: a single module-level regex over the same
    whole body, so the two signals are corroborating readings of one document. An
    empty (unscoreable) body has no warning to report and returns False — the
    unknown case is already handled by S2 and S5, which both bias deep, so S7 adds
    no second opinion there.
    """
    if not body:
        return False
    return bool(_RISK_PROSE_RE.search(body))


def _read_scope_estimate(plan_id: str) -> str | None:
    """S2 — read ``scope_estimate`` from references.json (None when absent)."""
    try:
        references = read_json(get_plan_dir(plan_id) / 'references.json', default={})
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(references, dict):
        value = references.get('scope_estimate')
        if isinstance(value, str):
            return value
    return None


def _read_compatibility() -> str | None:
    """S4 — read ``plan.phase-2-refine.compatibility`` from marshal.json."""
    try:
        config = read_json(base_path(FILE_MARSHAL), default={})
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(config, dict):
        plan_block = config.get('plan', {})
        if isinstance(plan_block, dict):
            refine = plan_block.get('phase-2-refine', {})
            if isinstance(refine, dict):
                value = refine.get('compatibility')
                if isinstance(value, str):
                    return value
    return None


def _read_deep_lane_gate() -> str:
    """Read ``plan.phase-1-init.deep_lane`` (``auto`` when absent)."""
    try:
        config = read_json(base_path(FILE_MARSHAL), default={})
    except (OSError, json.JSONDecodeError):
        return 'auto'
    if isinstance(config, dict):
        plan_block = config.get('plan', {})
        if isinstance(plan_block, dict):
            init = plan_block.get('phase-1-init', {})
            if isinstance(init, dict):
                value = init.get('deep_lane')
                if value in ('auto', 'always', 'never'):
                    return str(value)
    return 'auto'


def classify_scope_pure(body: str | None) -> tuple[str, dict[str, Any]]:
    """Classify the coarse scope band AND explain it — pure, I/O-free.

    Returns ``(scope_estimate, scope_provenance)``, where the provenance block
    carries ``distinct_path_count``, ``fan_out_marker`` and ``band_rule`` — the
    two measurements the band table reads plus the identifier of the row that
    fired. The single source of the band decision: ``scope_estimate_from_request_pure``
    is a thin projection of the first element, so band and explanation can never
    drift apart.

    The band table, scored from the DISTINCT repo-relative file-path references
    ``_PATH_RE`` extracts plus the ``_GLOB_RE`` fan-out marker, with ZERO
    architecture queries (the same zero-discovery invariant the lane router
    itself preserves):

    | Band | Predicate | ``band_rule`` |
    |------|-----------|---------------|
    | ``none`` | body absent / unreadable / empty | ``unscoreable_body`` |
    | ``multi_module`` | a fan-out marker is present | ``fan_out_marker`` |
    | ``multi_module`` | ``>= _MULTI_MODULE_MIN_PATHS`` distinct paths | ``path_count_at_or_above_multi_module_floor`` |
    | ``single_module`` | more than ``_SURGICAL_MAX_PATHS`` distinct paths | ``path_count_middle_band`` |
    | ``surgical`` | 1..``_SURGICAL_MAX_PATHS`` distinct paths, no fan-out | ``path_count_at_or_below_surgical_max`` |
    | ``single_module`` | no path at all, non-empty body | ``pathless_non_empty_body`` |

    Two rows carry the scale-truthfulness the band line exists for:

    - ``none`` is a DECLARED UNKNOWN. The body is unscoreable, and a scorer that
      read zero bytes must not emit a band, so this reports "cannot tell" instead
      of guessing. ``none`` is in ``_DEEP_SCOPE_ESTIMATES``, so S2 reads the
      unknown as a deep-biasing signal.
    - A fan-out marker bands ``multi_module``, NOT a narrow band. A pattern is a
      declared inability to enumerate the file set, so it must widen the band; the
      inverse — reporting an unbounded fan-out as a bounded change — is the
      silent-narrowing failure this table rules out by construction.

    The band remains a cheap pre-route guess: the deep-lane refine Step 9
    module-mapping derivation overwrites it with the measured band when the deep
    lane runs. Under the whole-body read the fan-out marker and the path count
    both see the entire request, so neither can be hidden by a truncated
    fragment; that widening is one-directional and therefore conservative.
    """
    if not body:
        return UNKNOWN, {
            'distinct_path_count': 0,
            'fan_out_marker': False,
            'band_rule': 'unscoreable_body',
        }
    fan_out_marker = bool(_GLOB_RE.search(body))
    distinct_path_count = len(_distinct_paths(body))
    if fan_out_marker:
        band, band_rule = MULTI_MODULE, 'fan_out_marker'
    elif distinct_path_count >= _MULTI_MODULE_MIN_PATHS:
        band, band_rule = MULTI_MODULE, 'path_count_at_or_above_multi_module_floor'
    elif distinct_path_count > _SURGICAL_MAX_PATHS:
        band, band_rule = SINGLE_MODULE, 'path_count_middle_band'
    elif distinct_path_count >= 1:
        band, band_rule = SURGICAL, 'path_count_at_or_below_surgical_max'
    else:
        band, band_rule = SINGLE_MODULE, 'pathless_non_empty_body'
    return band, {
        'distinct_path_count': distinct_path_count,
        'fan_out_marker': fan_out_marker,
        'band_rule': band_rule,
    }


def scope_estimate_from_request_pure(body: str | None) -> str:
    """Return just the coarse ``scope_estimate`` band for ``body``.

    The band-only projection of ``classify_scope_pure`` — see that function for
    the band table and the provenance contract.
    """
    return classify_scope_pure(body)[0]


def project_profile_pure(
    scope_estimate: str | None,
    change_type: str | None,
    compatibility: str | None,
    request_concrete: bool,
) -> str:
    """Project the recommended execution-profile posture — pure, I/O-free.

    A deterministic function of the SAME signals the lane verdict scores (it
    adds no discovery and no cognition). It recommends a posture on the
    ``minimal ⊏ standard ⊏ full`` lattice:

    - ``minimal`` — a ``surgical`` AND concretely specified change: mechanical,
      well-anchored, low-stakes. This is the same narrow-and-concrete predicate
      the lane verdict's S3/S4 carve-out uses — the ONE shared
      ``_NARROW_SCOPE_ESTIMATES`` frozenset — so a bounded surgical fix stays
      ``minimal`` even when its ``change_type`` reads generative or its
      ``compatibility`` reads breaking; the narrow, concrete bound dominates.
      Because the frozenset is shared verbatim, ``single_module`` and
      ``multi_module`` cannot collapse the posture to ``minimal`` here without
      also suppressing S3/S4 in the lane verdict, and neither does.
    - ``full`` — a generative change (``change_type ∈ {feature,
      feature_breaking}``) that is also broad (``scope_estimate`` ∈ multi_module
      / broad) OR clean-slate breaking, and NOT narrow-and-concrete. These are
      the correctly-deep features where the adversarial ceremony earns its cost.
    - ``standard`` — everything else (the generic recommendation / default).

    The recommendation is exactly that — a default the operator overrides. It is
    independent of the ``deep_lane`` gate_mode gate (which governs planning depth,
    not the profile).
    """
    narrow_and_concrete = scope_estimate in _NARROW_SCOPE_ESTIMATES and request_concrete
    if narrow_and_concrete:
        return MINIMAL
    generative = change_type in _DEEP_CHANGE_TYPES
    broad = scope_estimate in _BROAD_SCOPE_ESTIMATES
    breaking = compatibility == 'breaking'
    if generative and (broad or breaking):
        return FULL
    return STANDARD


def evaluate_signals_pure(
    scope_estimate: str | None,
    change_type: str | None,
    compatibility: str | None,
    plan_source: str | None,
    request_concrete: bool,
    risk_prose: bool = False,
    override: str | None = None,
) -> dict[str, Any]:
    """Score the S1–S7 signal set into a lane verdict — pure, I/O-free.

    Takes the realized signal values directly (the reads happen in the caller)
    and returns the ``{lane, fired_signals, signals, profile}`` dict that drives
    the route dispatch. ``profile`` carries the recommended execution-profile
    posture (``project_profile_pure``) plus the candidate posture lattice — the
    init dialogue consumes it as the default recommendation. Importable by
    downstream consumers (e.g. the audit retrospective check) so the routing
    thresholds are never duplicated.

    ``risk_prose`` (S7) defaults to False so a consumer that scores only the
    band-and-metadata signals keeps working; the default is the ABSENCE of a
    warning, which is the neutral value — it can never manufacture a deep verdict
    a caller did not supply evidence for.
    """
    # Carve-out — the positively-bounded case. A request that is BOTH narrowly
    # scoped (scope_estimate ∈ _NARROW_SCOPE_ESTIMATES, i.e. surgical) AND
    # concretely specified is well-bounded enough that S3 (generative
    # change_type) and S4 (breaking compatibility) firing *alone* must not force
    # deep. single_module is the catch-all middle band, so it does NOT earn the
    # carve-out: large concrete work keeps its S3/S4 escalation. The carve-out
    # relaxes ONLY this co-firing: S1/S2/S5 (the unknown-to-deep defaults) and
    # S6 (explicit override) are unaffected, so the conservative unknown case
    # keeps biasing deep unchanged.
    narrow_and_concrete = scope_estimate in _NARROW_SCOPE_ESTIMATES and request_concrete
    # S5 — vague ask, no anchors → deep.
    s5_deep = not request_concrete
    # S1 — free-form source (absent/unset) AND S5 concreteness fails → deep.
    # lesson-id / recipe sources are pre-specified by construction → bias light.
    free_form_source = plan_source in (None, '', 'free_form', 'cli')
    s1_deep = bool(free_form_source and s5_deep)
    # S2 — broad / unknown scope bands → deep.
    s2_deep = scope_estimate in _DEEP_SCOPE_ESTIMATES or scope_estimate is None
    # S3 — generative change types → deep, EXCEPT in the narrow-and-concrete
    # carve-out where a bounded, well-specified generative change stays light.
    s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete
    # S4 — clean-slate breaking changes tend cross-cutting → deep, EXCEPT in the
    # narrow-and-concrete carve-out.
    s4_deep = compatibility == 'breaking' and not narrow_and_concrete
    # S6 — explicit user override to deep is one-way.
    s6_deep = override == DEEP
    # S7 — the author's own written scale warning. Deliberately OUTSIDE the
    # narrow-and-concrete carve-out: the carve-out exists to stop a cheap band
    # plus a generative change_type from forcing deep, but S7 is not a cheap
    # inference — it is the author stating the scale. An explicit warning
    # therefore outranks the band, even for a surgical, concretely-specified
    # request.
    s7_deep = risk_prose

    fired = []
    if s1_deep:
        fired.append('S1:plan_source')
    if s2_deep:
        fired.append('S2:scope_estimate')
    if s3_deep:
        fired.append('S3:change_type')
    if s4_deep:
        fired.append('S4:compatibility')
    if s5_deep:
        fired.append('S5:concreteness')
    if s6_deep:
        fired.append('S6:override')
    if s7_deep:
        fired.append('S7:risk_prose')

    lane = DEEP if fired else LIGHT
    recommended_posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility=compatibility,
        request_concrete=request_concrete,
    )
    return {
        'lane': lane,
        'fired_signals': fired,
        'signals': {
            'plan_source': plan_source,
            'scope_estimate': scope_estimate,
            'change_type': change_type,
            'compatibility': compatibility,
            'request_concrete': request_concrete,
            'risk_prose': risk_prose,
            'planning_lane_override': override,
        },
        'profile': {
            'recommended_posture': recommended_posture,
            'candidate_postures': [MINIMAL, STANDARD, FULL],
        },
    }


def _evaluate_signals(plan_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Read S1–S7 signals from disk and delegate scoring to the pure helper.

    Returns the dict produced by ``evaluate_signals_pure`` — ``lane`` (the
    aggregate ``{light|deep}`` verdict), ``fired_signals`` (the deep-bias signals
    that fired), ``signals`` (the resolved S1-S7 input values) and ``profile``
    (the projected posture) — plus one key this reader adds:

    - ``scope_provenance`` — the ``classify_scope_pure`` explanation of the band
      the request body scores to (``distinct_path_count``, ``fan_out_marker``,
      ``band_rule``). It explains the band THIS BODY would produce; the S2 signal
      value itself is read from ``references.json``, which a later phase's
      module-mapping derivation may have overwritten with a measured band.
    """
    plan_source = metadata.get('plan_source')
    change_type = metadata.get('change_type')
    override = metadata.get('planning_lane_override')

    scope_estimate = _read_scope_estimate(plan_id)
    compatibility = _read_compatibility()
    body = _read_request_body(plan_id)
    concrete = _request_is_concrete(body)
    risk_prose = _request_has_risk_prose(body)
    _, scope_provenance = classify_scope_pure(body)

    evaluation = evaluate_signals_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility=compatibility,
        plan_source=plan_source,
        request_concrete=concrete,
        risk_prose=risk_prose,
        override=override,
    )
    evaluation['scope_provenance'] = scope_provenance
    return evaluation


def cmd_planning_lane_route(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve ``{light|deep}`` from the DQ1 signal set and persist it.

    ``--lane-override {deep|light}`` seeds ``status.metadata.planning_lane_override``
    before the signal evaluation (a CLI-init convenience). ``--persist`` writes
    the resolved lane into ``status.metadata.planning_lane`` and emits one
    decision-log line naming every signal value and the winning predicate.

    The return and that decision-log line both carry ``scope_provenance``
    (``distinct_path_count``, ``fan_out_marker``, ``band_rule``) alongside BOTH
    verdicts — ``planning_lane`` and ``execution_profile`` — so an operator reading
    either surface sees not just the two decisions but the band rule that drove
    them. The pre-existing override seam (``--lane-override`` / S6) is the way to
    disagree with the verdict; the provenance block is observability, not a gate.
    """
    plan_id: str = args.plan_id
    lane_override: str | None = getattr(args, 'lane_override', None)
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        status = {}
    metadata = status.get('metadata')
    if not isinstance(metadata, dict):
        metadata = {}

    # A CLI --lane-override seeds the S6 signal source so the evaluation sees it.
    if lane_override in (DEEP, LIGHT):
        metadata = dict(metadata)
        metadata['planning_lane_override'] = lane_override

    # Pre-route validation pass (deterministic, flag-not-block): cross-check
    # change_type / scope_estimate against cheap request signals and emit a
    # Q-Gate finding on a mismatch. This NEVER gates the lane resolution — the
    # gate result is surfaced under ``classification_validation`` for
    # observability and the routing continues unconditionally.
    classification_validation = run_classification_validation(plan_id)

    ceremony = _read_deep_lane_gate()

    # The signal set is scored unconditionally so the execution-profile
    # projection is available regardless of the deep_lane gate_mode gate. The
    # gate short-circuits ONLY the {light, deep} planning-depth verdict; it must
    # NOT coerce the profile (deep_lane=always does not force `full` — §4.2).
    signal_evaluation = _evaluate_signals(plan_id, metadata)
    profile = signal_evaluation['profile']
    # Band provenance is a property of the request body, not of the deep_lane
    # gate, so it survives both short-circuit branches below unchanged.
    scope_provenance = signal_evaluation['scope_provenance']

    evaluation: dict[str, Any]
    if ceremony == 'always':
        lane = DEEP
        decision = 'plan.phase-1-init.deep_lane=always'
        evaluation = {
            'lane': lane,
            'fired_signals': ['deep_lane:always'],
            'signals': signal_evaluation['signals'],
            'profile': profile,
        }
    elif ceremony == 'never':
        lane = LIGHT
        decision = 'plan.phase-1-init.deep_lane=never'
        evaluation = {'lane': lane, 'fired_signals': [], 'signals': signal_evaluation['signals'], 'profile': profile}
    else:
        evaluation = signal_evaluation
        lane = evaluation['lane']
        decision = 'signal_set'

    recommended_posture = profile['recommended_posture']

    persisted = False
    if persist:
        if 'metadata' not in status or not isinstance(status['metadata'], dict):
            status['metadata'] = {}
        status['metadata']['planning_lane'] = lane
        # Persist the projected posture as the init-time default; the operator's
        # final choice (if it overrides the recommendation) is written by the
        # phase-1-init dialogue via `manage-status metadata`.
        if 'execution_profile' not in status['metadata']:
            status['metadata']['execution_profile'] = recommended_posture
        if lane_override in (DEEP, LIGHT):
            status['metadata']['planning_lane_override'] = lane_override
        write_status(plan_id, status)
        persisted = True

    fired = evaluation['fired_signals']
    log_entry(
        'decision',
        plan_id,
        'INFO',
        (
            f'(plan-marshall:manage-status:planning-lane) Routed planning_lane={lane} '
            f'(predicate={decision}, fired={fired or "none"}, '
            f'ceremony.deep_lane={ceremony}, execution_profile={recommended_posture}, '
            f'scope_provenance={scope_provenance}, '
            f'signals={evaluation["signals"]})'
        ),
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'planning_lane': lane,
        'ceremony_deep_lane': ceremony,
        'decision_predicate': decision,
        'fired_signals': fired,
        'signals': evaluation['signals'],
        'execution_profile': recommended_posture,
        'profile': profile,
        'scope_provenance': scope_provenance,
        'persisted': persisted,
        'classification_validation': {
            'mismatch_count': classification_validation.get('mismatch_count', 0),
            'mismatches': classification_validation.get('mismatches', []),
            'findings_emitted': classification_validation.get('findings_emitted', 0),
        },
    }


def cmd_scope_estimate_heuristic(args: argparse.Namespace) -> dict[str, Any]:
    """Classify a coarse ``scope_estimate`` from the request and persist it.

    Reads the WHOLE ``request.md`` narrative (see ``_read_request_body``),
    classifies it via ``classify_scope_pure`` (fan-out marker plus
    distinct-file-path count, ZERO architecture queries), and with
    ``--persist`` writes it to
    ``references.json``'s ``scope_estimate`` field — the same field
    ``_read_scope_estimate`` (the router's S2 signal source) reads. Run at
    phase-1-init BEFORE the planning-lane route so the router reads a real
    ``scope_estimate`` instead of ``None``. The deep-lane refine Step 9
    module-mapping derivation later overwrites the coarse guess when the deep
    lane runs, so no accuracy is lost.

    The return carries ``scope_resolved`` so callers can tell a CLASSIFIED band
    apart from the DECLARED UNKNOWN: ``scope_resolved: false`` means the body was
    unscoreable and ``scope_estimate`` is ``none`` (a "cannot tell" verdict),
    not a measured narrow band. Reading ``scope_estimate`` alone cannot make that
    distinction, which is exactly how a zero-byte read used to pass for a band.
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

    body = _read_request_body(plan_id)
    scope_estimate, scope_provenance = classify_scope_pure(body)
    scope_resolved = scope_estimate != UNKNOWN
    distinct_paths = sorted(_distinct_paths(body)) if body else []

    persisted = False
    if persist:
        references_path = get_plan_dir(plan_id) / 'references.json'
        references = read_json(references_path, default={})
        if not isinstance(references, dict):
            references = {}
        references['scope_estimate'] = scope_estimate
        write_json(references_path, references)
        persisted = True
        verdict = (
            f'Classified scope_estimate={scope_estimate}'
            if scope_resolved
            else f'Declared scope_estimate={scope_estimate} (unknown — unscoreable request body)'
        )
        log_entry(
            'decision',
            plan_id,
            'INFO',
            (
                f'(plan-marshall:manage-status:scope-estimate-heuristic) {verdict} '
                f'(distinct_paths={len(distinct_paths)}, '
                f'glob={scope_provenance["fan_out_marker"]}, '
                f'band_rule={scope_provenance["band_rule"]}, '
                f'scope_resolved={scope_resolved}) '
                f'— pre-route coarse guess over the whole request body, deep-lane Step 9 may overwrite'
            ),
        )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'scope_estimate': scope_estimate,
        'scope_resolved': scope_resolved,
        'distinct_path_count': len(distinct_paths),
        'distinct_paths': distinct_paths,
        'persisted': persisted,
    }


def cmd_planning_lane_escalate(args: argparse.Namespace) -> dict[str, Any]:
    """One-way ratchet: set ``planning_lane=deep`` + ``lane_escalated=true``.

    Monotonic light→deep. Refuses any attempt to set a lane back to ``light``
    once ``lane_escalated`` is true — there is no downgrade path. The trigger
    (``explosion`` / ``premise`` / ``cross_cutting``) is recorded in
    ``status.metadata.escalation_trigger``. ``--persist`` writes the mutation.
    """
    plan_id: str = args.plan_id
    trigger: str = args.trigger
    persist: bool = bool(getattr(args, 'persist', False))

    plan_dir = get_plan_dir(plan_id)
    if not plan_dir.exists():
        return {
            'status': 'error',
            'error': 'plan_dir_not_found',
            'message': f'Plan directory not found: {plan_dir}',
        }

    try:
        status = read_status(plan_id)
    except FileNotFoundError:
        status = {}
    if 'metadata' not in status or not isinstance(status['metadata'], dict):
        status['metadata'] = {}
    metadata = status['metadata']

    metadata['planning_lane'] = DEEP
    metadata['lane_escalated'] = True
    metadata['escalation_trigger'] = trigger

    persisted = False
    if persist:
        write_status(plan_id, status)
        persisted = True

    log_entry(
        'decision',
        plan_id,
        'INFO',
        (
            f'(plan-marshall:manage-status:planning-lane) Escalated planning_lane=deep '
            f'(trigger={trigger}, lane_escalated=true) — one-way ratchet, no downgrade'
        ),
    )

    return {
        'status': 'success',
        'plan_id': plan_id,
        'planning_lane': DEEP,
        'lane_escalated': True,
        'escalation_trigger': trigger,
        'persisted': persisted,
    }
