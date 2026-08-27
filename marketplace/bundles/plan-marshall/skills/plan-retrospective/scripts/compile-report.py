#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Compile the quality-verification markdown document from aspect fragments.

The script is a pure assembler — it does NOT make judgement calls. It reads
a TOON bundle of aspect fragments, validates their shapes, and writes the
markdown document to the correct path per invocation mode (live vs
archived).

Filename rules (documented in ``references/report-structure.md``):
- Live modes: ``<plan_dir>/quality-verification-report.md`` — overwrites.
- Archived mode: ``<archived_plan_path>/quality-verification-report-audit-{YYYYMMDDTHHMMSSZ}.md`` — never overwrites.

Usage:
    python3 compile-report.py run --plan-id EXAMPLE-PLAN --mode live \
        --fragments-file /abs/path/to/fragments.toon

    python3 compile-report.py run --archived-plan-path /abs --mode archived \
        --fragments-file /abs/path/to/fragments.toon
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _display_time import render_timestamp
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    add_session_id_arg,
    parse_args_with_toon_errors,
)
from retro_sections import (
    AGGREGATE_PARTIAL_COVERAGE,
    AGGREGATE_UNMEASURABLE,
    COMPOSE_TIME_ARTIFACT,
    COMPOSE_TIME_DEGRADED_TOKEN,
    COMPOSE_TIME_PRODUCER,
    FOOTPRINT_AGGREGATE_KEY,
    FOOTPRINT_DEGRADED_TOKENS,
    PRODUCER_DEGRADED,
    PRODUCER_RESOLVED,
    PRODUCER_UNREAD,
    PROVENANCE_ASPECT_REGISTRY,
    PROVENANCE_COMPOSE_TIME,
    SECTION_SPEC,
    ZERO_ATTRIBUTION_FIELDS,
    ZERO_DECLARED_UNMEASURED_STATUSES,
    footprint_consuming_aspect_keys,
)
from toon_parser import parse_toon

# The canonical section→fragment-key registry lives in ``retro_sections`` so the
# producer (``collect-fragments``) and this consumer share one source of truth.
# See ``retro_sections.SECTION_SPEC`` for the row schema and section order.


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def resolve_output_path(mode: str, plan_dir: Path) -> Path:
    """Return the markdown output path given the invocation mode."""
    if mode == 'live':
        return plan_dir / 'quality-verification-report.md'
    # Archived mode uses UTC compact timestamp for collision-free filenames.
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    return plan_dir / f'quality-verification-report-audit-{stamp}.md'


def load_fragments(fragments_path: Path) -> dict[str, Any]:
    """Read the TOON fragments bundle.

    The bundle is expected to be a top-level dict whose keys are aspect
    names and whose values are the aspect fragment dicts.
    """
    if not fragments_path.exists():
        raise ValueError(f'Fragments file does not exist: {fragments_path}')
    try:
        parsed = parse_toon(fragments_path.read_text(encoding='utf-8'))
    except Exception as e:
        raise ValueError(f'Failed to parse fragments TOON: {e}') from e
    if not isinstance(parsed, dict):
        raise ValueError('Fragments TOON must be a top-level dict')
    return parsed


def _dispatch_boundaries_has_present_phase(fragment: Any) -> bool:
    """Return True when at least one phase entry reports ``present: true``.

    The dispatch_boundaries fragment is structurally a per-phase dict
    keyed by phase name (e.g. ``"4-plan"``, ``"5-execute"``, ``"6-finalize"``).
    Each value is the per-file shape from
    analyze-logs.read_dispatch_boundaries_per_phase (whose authoritative key set
    lives in ``_parse_dispatch_boundary_file``); this gate reads only the
    ``present`` flag. The section emits when at least one phase has
    ``present: true``.
    """
    if not isinstance(fragment, dict) or not fragment:
        return False
    for phase_data in fragment.values():
        if not isinstance(phase_data, dict):
            continue
        present = phase_data.get('present')
        # Accept both Python bool True and the string ``"true"`` (TOON parser
        # may keep boolean values as strings depending on the load path).
        if present is True or str(present).lower() == 'true':
            return True
    return False


def should_emit(section_key: str, trigger_key: str | None, fragments: dict[str, Any]) -> bool:
    """Conditional sections emit only when their fragment has non-empty data."""
    if trigger_key is None:
        return True
    fragment = fragments.get(trigger_key)
    # Dispatch_boundaries is a per-phase dict, NOT a status-wrapped fragment —
    # gate on at least one phase entry with ``present: true``.
    if trigger_key == 'dispatch_boundaries':
        return _dispatch_boundaries_has_present_phase(fragment)
    if not isinstance(fragment, dict):
        return False
    # Chat-history-analysis is gated BEFORE the status guard below, and that
    # position is load-bearing — do NOT "tidy" this branch down beside the
    # manifest-decisions / routing-decisions carve-outs. Those two gate
    # ``status: success`` fragments, so sitting after the guard is correct for
    # them. This aspect's Tier-2 graceful-skip fragment (specified by
    # ``references/chat-history-analysis.md``) carries ``status: skipped`` plus a
    # ``severity: warning`` finding the reference explicitly requires to be
    # visible in the compiled report — the status guard would drop it, making a
    # post-guard branch dead code for the only case it exists to serve. Keying on
    # this aspect's own trigger_key means no other section's gating changes.
    if trigger_key == 'chat-history-analysis':
        findings = fragment.get('findings')
        if isinstance(findings, list) and findings:
            return True
    # Accept only success-status fragments with meaningful content.
    status = fragment.get('status')
    if status not in (None, 'success'):
        return False
    # A fragment is "non-empty" if it contains at least one of the expected
    # payload fields: ``findings``, ``failures``, ``prompts``, ``candidates``.
    for key in ('findings', 'failures', 'prompts', 'candidates'):
        value = fragment.get(key)
        if isinstance(value, list) and value:
            return True
    # Manifest-decisions is a special case: a clean run has zero findings but
    # still carries the manifest body + decision-log entries that the report
    # needs to surface (manifest = WHAT, decision.log = WHY). Emit whenever
    # the fragment claims a present manifest, regardless of finding count.
    if trigger_key == 'manifest-decisions' and fragment.get('manifest_present') is True:
        return True
    # Routing-decisions is the same shape of special case: the aspect grades the
    # run's lane/recipe/posture routing and carries verdict/cost/prune facts
    # (``posture``, ``mis_prune_checks``, ``cost_preview``, and the LLM-synthesized
    # ``posture_verdict``) rather than a ``findings`` list, so a clean run — which
    # is the common case and the whole point of the lane feedback loop — has none
    # of the payload fields checked above. Emit whenever the fragment reports a
    # present routing-decision analysis (``manifest_present``, set by the
    # deterministic producer) or carries any of its content fields (the
    # LLM-synthesized fragment shape).
    if trigger_key == 'routing-decisions':
        if fragment.get('manifest_present') is True:
            return True
        for key in ('mis_prune_checks', 'cost_preview', 'posture_verdict', 'posture'):
            value = fragment.get(key)
            if value not in (None, '', [], {}):
                return True
    return False


def _fragment_has_payload(fragment: Any) -> bool:
    """Return True when a fragment carries content beyond its envelope keys.

    ``status`` and ``aspect`` are envelope metadata every fragment carries, so
    they never count as payload. Any other key whose value is not one of the
    empty sentinels (``None``, ``''``, ``[]``, ``{}``, ``False``) makes the
    fragment non-empty. This is the discriminator between a benign omission
    (the aspect genuinely produced nothing) and a loud drop (the aspect
    produced content that ``should_emit`` nonetheless refused).

    ``False`` is matched by identity, never by equality: ``False == 0`` and
    ``False == 0.0`` in Python, so an equality-based sentinel tuple would
    misclassify a fragment whose only real content is numeric zero (a count of
    ``0``, a ratio of ``0.0``) as carrying no payload — silently dropping the
    very content this discriminator exists to make loud.
    """
    if not isinstance(fragment, dict):
        return False
    for key, value in fragment.items():
        if key in ('status', 'aspect'):
            continue
        if value is False:
            continue
        if value not in (None, '', [], {}):
            return True
    return False


def _reports_zero(fragment: Any) -> bool:
    """Return True when a fragment makes an explicit *zero findings* claim.

    The claim is a ``findings`` key holding a PRESENT-BUT-EMPTY list. A fragment
    carrying no ``findings`` key at all makes no such claim (it reports some
    other shape entirely), and one carrying a non-empty list reports findings —
    neither is a zero.
    """
    if not isinstance(fragment, dict):
        return False
    findings = fragment.get('findings')
    return isinstance(findings, list) and not findings


def _names_checked_set(fragment: Any) -> bool:
    """Return True when a zero-reporting fragment says what it checked.

    Two ways to be unambiguous, and a fragment needs only one:

    1. It DECLARES that it could not look — a status in
       :data:`retro_sections.ZERO_DECLARED_UNMEASURED_STATUSES`. Such a fragment
       is not claiming an evaluated-clean result at all.
    2. It publishes the population it examined, under one of
       :data:`retro_sections.ZERO_ATTRIBUTION_FIELDS`.

    The empty-sentinel tuple below deliberately EXCLUDES ``False``, which is
    filtered by a separate identity check — the same split ``_fragment_has_payload``
    makes, for the same reason. ``False == 0`` in Python, so folding ``False`` into
    the sentinel tuple (the natural way to spell "falsy means empty") would make
    ``0 in sentinels`` true and swallow a published population of ``0`` — discarding
    precisely the honest "I looked at nothing, and here is that number" case.
    """
    if not isinstance(fragment, dict):
        return False
    if str(fragment.get('status')) in ZERO_DECLARED_UNMEASURED_STATUSES:
        return True
    # Top level, then ONE level of nesting. The nesting pass is not
    # defensiveness — it is where the real producers put these fields: only
    # ``counts`` is published at the top of a fragment, while
    # ``evaluated_population`` appears inside ``shape_violation`` /
    # ``dispatch_coverage`` (``check-dispatch-audit``) and ``population`` inside
    # ``script_cost_rollup`` (``analyze-logs``). A top-level-only probe would
    # therefore flag a fragment that DOES name the population it examined,
    # simply because it named it one level down — a false positive against
    # exactly the producers this vocabulary was derived from.
    #
    # One level, not arbitrary depth: the population belongs to a named fact
    # block, and an unbounded walk would let any incidental key deep in a
    # payload clear the flag.
    if _has_attribution_field(fragment):
        return True
    return any(_has_attribution_field(value) for value in fragment.values())


def _has_attribution_field(candidate: Any) -> bool:
    """Return True when ``candidate`` is a dict publishing a non-empty population.

    ``False`` is matched by identity for the reason spelled out in
    :func:`_names_checked_set` — a published population of ``0`` must survive.
    """
    if not isinstance(candidate, dict):
        return False
    for field in ZERO_ATTRIBUTION_FIELDS:
        value = candidate.get(field)
        if value is False:
            continue
        if value not in (None, '', [], {}):
            return True
    return False


def _heading_to_fragment_key(fragments: dict[str, Any]) -> dict[str, str]:
    """Return the heading→fragment-key map ``build_document`` renders under.

    Covers BOTH render paths, because ``build_document`` writes sections through
    both: the static ``SECTION_SPEC`` rows, and the generic fallback that emits a
    registered-but-unlisted aspect (a domain-contributed key such as
    ``wrapper-tangle``) under a heading synthesized from its key. A map built
    from ``SECTION_SPEC`` alone would silently exclude every fallback-rendered
    aspect from any probe over the written set — and those are the newest and
    least conventional producers, so excluding them omits exactly the population
    most likely to be non-conforming.

    A ``SECTION_SPEC`` heading wins over a fallback key that synthesizes the same
    heading, mirroring ``build_document``, whose fallback loop skips every key
    already carrying a static row.
    """
    mapping = {heading: fragment_key for heading, fragment_key, _trigger in SECTION_SPEC}
    spec_keys = set(mapping.values())
    for aspect_key in sorted(fragments):
        if aspect_key.startswith('_') or aspect_key in spec_keys:
            continue
        mapping.setdefault(_heading_from_aspect_key(aspect_key), aspect_key)
    return mapping


def unattributed_zero_sections(written: list[str], fragments: dict[str, Any]) -> list[str]:
    """Return the written sections whose zero cannot be told from *could not look*.

    A section that reports ``findings: []`` is making one of two very different
    statements — *I checked, and the signals held* or *I could not check* — and a
    reader cannot tell which without the checked set. This probe names the
    sections that leave that ambiguity standing.

    It is a REPORTED signal, not a gate: unlike ``sections_dropped`` (content the
    report lost) an unattributed zero loses nothing, so it does not raise the
    run's status. Conflating the two would blur a content-loss signal with an
    ambiguity signal, which is the class of defect this partition exists to
    surface.

    The population is every WRITTEN section — both render paths (see
    :func:`_heading_to_fragment_key`) — walked in document order, deduplicated.
    A section the document does not carry reported nothing, so it cannot leave a
    zero ambiguous.

    Args:
        written: Headings the document actually carries, in document order.
        fragments: The fragment bundle the document was built from.

    Returns:
        The subset of ``written`` whose fragment reports zero without naming
        what it checked.
    """
    mapping = _heading_to_fragment_key(fragments)
    result: list[str] = []
    for heading in written:
        if heading in result:
            continue
        fragment_key = mapping.get(heading)
        if fragment_key is None:
            continue
        fragment = fragments.get(fragment_key)
        if _reports_zero(fragment) and not _names_checked_set(fragment):
            result.append(heading)
    return result


def render_dispatch_boundaries_body(fragment: Any) -> str:
    """Render the Phase Dispatch Boundaries section body.

    Emits a markdown table with one row per recorded phase, columns:
    ``phase | rows | error_total_tokens (terminal-error) | retryable_total_tokens |
    returned_with_findings | unknown_count | clean_exit_queue_empty_count``.
    The ``error_total_tokens`` and ``retryable_total_tokens`` columns are the
    terminal-error-vs-retryable dispatch-spend split — a reported figure so a
    reader sees the terminal-error spend without reconstructing it from the rows
    — reported distinctly because the two need different remedies. The
    terminal-error figure is the strongest proxy for genuinely-wasted spend once
    productive loop-backs are stamped ``returned_with_findings``; the finding-yield
    proof is the corpus-gated D3 measurement, not this column. Falls back to a
    generic JSON dump after the table for the full fragment data.
    """
    import json

    if not isinstance(fragment, dict) or not fragment:
        return '_No dispatch-boundary artifacts present._\n'

    lines = [
        '| phase | rows | error_total_tokens (terminal-error) | retryable_total_tokens | '
        'returned_with_findings | unknown_count | clean_exit_queue_empty_count |',
        '|-------|------|------------------------------------|------------------------|'
        '------------------------|---------------|------------------------------|',
    ]
    for phase in sorted(fragment.keys()):
        phase_data = fragment[phase]
        if not isinstance(phase_data, dict):
            continue
        present = phase_data.get('present')
        if not (present is True or str(present).lower() == 'true'):
            continue
        rows = phase_data.get('rows', [])
        row_count = len(rows) if isinstance(rows, list) else 0
        unknown_count = phase_data.get('unknown_count', 0)
        clean_count = phase_data.get('clean_exit_queue_empty_count', 0)
        wasted = phase_data.get('error_total_tokens', 0)
        retryable = phase_data.get('retryable_total_tokens', 0)
        returned_with_findings = phase_data.get('returned_with_findings_count', 0)
        lines.append(
            f'| {phase} | {row_count} | {wasted} | {retryable} | '
            f'{returned_with_findings} | {unknown_count} | {clean_count} |'
        )

    table_block = '\n'.join(lines) + '\n\n'
    data_block = '```json\n' + json.dumps(fragment, indent=2, default=str) + '\n```\n'
    return table_block + data_block


def render_section_body(fragment: Any) -> str:
    """Render an aspect fragment dict as a markdown body block.

    The renderer is intentionally simple: it emits a fenced TOON block
    containing the fragment, followed by a short bullet list of findings
    (if any). This keeps the assembler self-contained — the LLM already
    produced human-readable prose inside the fragment's ``summary`` or
    ``message`` fields where appropriate.
    """
    import json

    if fragment is None:
        return '_No data provided._\n'
    if not isinstance(fragment, dict):
        return f'```\n{fragment!s}\n```\n'

    summary_text = ''
    summary = fragment.get('summary')
    if isinstance(summary, str) and summary.strip():
        summary_text = summary.strip() + '\n\n'

    # Render findings as a bullet list.
    findings = fragment.get('findings')
    findings_block = ''
    if isinstance(findings, list) and findings:
        lines = []
        for item in findings:
            if not isinstance(item, dict):
                continue
            severity = str(item.get('severity', 'info')).upper()
            message = str(item.get('message', ''))
            lines.append(f'- [{severity}] {message}')
        if lines:
            findings_block = '\n'.join(lines) + '\n\n'

    # Include the full fragment as a JSON code block for reference.
    data_block = '```json\n' + json.dumps(fragment, indent=2, default=str) + '\n```\n'

    return summary_text + findings_block + data_block


def _fragment_renders_empty(fragment: Any) -> bool:
    """Return True when ``fragment`` cannot produce a body with content in it.

    This is the predicate the *written implies non-empty* invariant turns on, and
    it asks about EMPTINESS rather than absence. Asking ``fragment is None``
    instead — the obvious spelling — closes only the absent-key case and leaves
    the invariant false on the path the real pipeline takes:
    ``toon_parser.parse_toon`` returns ``''`` for a valueless key, never ``None``
    (only the literal token ``null`` yields ``None``), and
    ``collect-fragments._read_fragment`` accepts any file that is not
    whitespace-only. A producer that writes prose instead of a fragment therefore
    registers successfully, reaches this renderer as ``''``, and — under an
    ``is None`` guard — is emitted as a heading over an empty fenced block and
    counted as written.

    ⛔ **A non-empty CONTAINER is not the same as a usable BODY**, and testing the
    container was one of several attempts that each closed a narrower case than
    the invariant needs — no count is given here, because a count of attempts
    goes stale on the next one. A dict such as
    ``{'summary': ''}`` or ``{'findings': []}`` — the literal shape an LLM aspect
    with nothing to report writes — is a non-empty dict that renders a JSON block
    stating nothing. So for a dict the question is delegated to
    :func:`_fragment_has_payload`, the discriminator this module ALREADY uses for
    the drop-versus-omit split: a fragment it says carries nothing beyond its
    envelope cannot simultaneously be a written section with a body. One
    discriminator, one answer, both halves of the partition.

    For a non-dict the payload discriminator does not apply (it reports ``False``
    for every non-dict, which would swallow a bare scalar's content), so
    emptiness is judged directly: a blank string or an empty container is empty;
    ``0`` and ``0.0`` are content, because they render a value a reader can act
    on. ``False`` is empty, matching the identity skip ``_fragment_has_payload``
    applies to a ``False`` *value* — the two are kept genuinely consistent rather
    than merely described as such.
    """
    if fragment is None:
        return True
    if isinstance(fragment, dict):
        return not _fragment_has_payload(fragment)
    if fragment is False:
        return True
    if isinstance(fragment, str):
        return not fragment.strip()
    if isinstance(fragment, (list, tuple, set, frozenset, bytes, bytearray)):
        return not fragment
    return False


def _heading_from_aspect_key(aspect_key: str) -> str:
    """Derive a human-readable section heading from an aspect key.

    Hyphenated (or underscored) aspect keys map to title-cased headings for
    the generic fallback render path — e.g. ``wrapper-tangle`` -> ``Wrapper
    Tangle``. Used only for registered aspects that have no dedicated
    ``SECTION_SPEC`` row, so the heading is synthesized rather than looked up.
    """
    return aspect_key.replace('-', ' ').replace('_', ' ').title()


def build_header(plan_id: str, mode: str, plan_path: Path, session_id: str | None) -> str:
    """Build the document header (title + metadata list)."""
    generated = render_timestamp(datetime.now(UTC), '%Y-%m-%dT%H:%M:%S', 'Z')
    session = session_id or 'not provided'
    lines = [
        f'# Plan Retrospective — {plan_id}',
        '',
        f'- mode: {mode}',
        f'- generated: {generated}',
        f'- plan_path: {plan_path}',
        f'- session_id: {session}',
        '',
    ]
    return '\n'.join(lines)


def build_document(
    plan_id: str,
    mode: str,
    plan_dir: Path,
    session_id: str | None,
    fragments: dict[str, Any],
) -> tuple[str, list[str], list[str], list[str]]:
    """Assemble the markdown document.

    Returns ``(content, sections_written, sections_omitted, sections_dropped)``.
    """
    written: list[str] = []
    omitted: list[str] = []
    dropped: list[str] = []
    parts: list[str] = [build_header(plan_id, mode, plan_dir, session_id)]

    # Executive summary is synthesized from fragment data — if the caller
    # provided one under ``_executive-summary``, use it verbatim. When it did
    # not, there is NO body to render, and the section takes the same non-emit
    # partition every other section takes (see below). It is never emitted as a
    # placeholder heading: ``references/report-structure.md`` § "Conditional
    # Rule" forbids an empty heading, and counting one as written would break
    # the partition invariant *written implies non-empty* — the loud half of
    # this partition exists to make content loss visible, so the headline
    # section must not ride the clean half on an empty body.
    exec_fragment = fragments.get('_executive-summary')
    if isinstance(exec_fragment, dict) and exec_fragment.get('summary'):
        exec_text = str(exec_fragment['summary']).strip()
    elif isinstance(exec_fragment, str) and exec_fragment.strip():
        exec_text = exec_fragment.strip()
    else:
        exec_text = ''

    for heading, fragment_key, trigger in SECTION_SPEC:
        if fragment_key == '_executive-summary':
            if not exec_text:
                # Same discriminator the conditional sections use: a fragment
                # that carried payload the renderer nonetheless could not turn
                # into a body is a DROP; an absent or empty one is a benign
                # omission.
                if _fragment_has_payload(exec_fragment):
                    dropped.append(heading)
                else:
                    omitted.append(heading)
                continue
            parts.append(f'## {heading}\n\n{exec_text}\n')
            written.append(heading)
            continue
        if not should_emit(fragment_key, trigger, fragments):
            # Partition the non-emit path: a section whose trigger fragment is
            # absent or genuinely empty is a benign omission; a section whose
            # trigger fragment carries real payload is a DROP — content the
            # aspect produced that the gate refused — and must be loud.
            trigger_fragment = fragments.get(trigger) if trigger is not None else None
            if _fragment_has_payload(trigger_fragment):
                dropped.append(heading)
            else:
                omitted.append(heading)
            continue
        fragment = fragments.get(fragment_key)
        if _fragment_renders_empty(fragment):
            # Nothing usable to render, in any of three ways: an ABSENT fragment
            # gets the literal ``_No data provided._`` placeholder; an EMPTY
            # container (``''`` from a valueless TOON key, ``{}``, ``[]``) gets a
            # heading over an empty fenced block; and a NON-EMPTY dict carrying
            # no payload beyond its envelope (``{'findings': []}`` — the shape an
            # LLM aspect with nothing to report writes) gets a heading over a
            # JSON block that states nothing. Counting any of them as written is
            # the invariant breach the Executive Summary branch above closes, and
            # it was never confined to one row: every
            # ``conditional_trigger = None`` row reaches here whenever its
            # producer wrote nothing usable.
            #
            # Nothing was lost (there was no content to lose), so this is the
            # benign half of the partition.
            omitted.append(heading)
            continue
        # Dispatch_boundaries uses a dedicated per-phase table renderer; every
        # other fragment falls back to the generic JSON+findings renderer.
        if fragment_key == 'dispatch_boundaries':
            body = render_dispatch_boundaries_body(fragment)
        else:
            body = render_section_body(fragment)
        parts.append(f'## {heading}\n\n{body}')
        written.append(heading)

    # Generic fallback render path (registered ⇒ rendered completeness guard).
    # Guarantee: an aspect key present in the bundle that has no dedicated
    # SECTION_SPEC row — e.g. a domain-contributed ``wrapper-tangle`` — is
    # rendered verbatim under a heading synthesized from its key, never lost.
    # Reserved underscore-prefixed meta keys (``_meta``, ``_executive-summary``)
    # are excluded; keys are sorted for a deterministic section order.
    spec_keys = {fragment_key for _heading, fragment_key, _trigger in SECTION_SPEC}
    for aspect_key in sorted(fragments):
        if aspect_key.startswith('_'):
            continue
        if aspect_key in spec_keys:
            continue
        # Same invariant as the static loop above, because the invariant is a
        # property of the PARTITION rather than of one render path.
        #
        # This check sits AFTER the ``spec_keys`` skip, and the order is
        # load-bearing: above it, a registry key whose value is empty was
        # recorded twice — once by the static loop under its real heading, and
        # again here under a heading SYNTHESIZED from the key, naming a section
        # that exists in no registry row.
        if _fragment_renders_empty(fragments.get(aspect_key)):
            omitted.append(_heading_from_aspect_key(aspect_key))
            continue
        heading = _heading_from_aspect_key(aspect_key)
        body = render_section_body(fragments.get(aspect_key))
        parts.append(f'## {heading}\n\n{body}')
        written.append(heading)

    return '\n'.join(parts), written, omitted, dropped


def _iter_string_values(value: Any):
    """Yield every string VALUE in a fragment tree — never a dict KEY.

    The key/value split is load-bearing for the free-text arm of the degradation
    probe below, not a stylistic preference. ``check-artifact-consistency``
    publishes a ``summary.inconclusive`` COUNTER on every run, so a walk that
    also matched keys would find the token ``inconclusive`` in a perfectly clean
    fragment (``inconclusive: 0``) and read it as degraded — firing the
    aggregate on precisely the runs it must stay silent for, which is the
    control case deliverable 5 pins. The verdict arm has its own, narrower walk
    (:func:`_iter_verdict_field_values`); this one stays as broad as a free-text
    token needs.
    """
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_string_values(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_string_values(item)


#: Fragment keys under which a producer publishes its own degradation VERDICT.
#: ``status`` is the per-check verdict the three ``check-*`` aspects emit;
#: ``comparison`` is the peer field ``check-outline-vs-shipped`` publishes.
_VERDICT_FIELD_KEYS: frozenset[str] = frozenset({'status', 'comparison'})

#: The degradation tokens matched by EQUALITY against a verdict field only,
#: rather than as a substring of any string value in the fragment. Membership
#: here is a property of how the token is EMITTED — see :func:`_declares_degraded`.
_VERDICT_SCOPED_TOKENS: frozenset[str] = frozenset({'inconclusive'})


def _iter_verdict_field_values(value: Any):
    """Yield every string stored under one of :data:`_VERDICT_FIELD_KEYS`.

    Narrower than :func:`_iter_string_values` on purpose: it yields a string
    only where the producer published it AS a verdict, so an incidental string
    field carrying the same characters is never read as one. Three of the four
    roster producers emit a ``plan_dir`` (and a ``plan_id``) in their result
    dict, and both embed the plan id — so an all-values scan makes a plan whose
    id contains the token match on a fully RESOLVED fragment.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _VERDICT_FIELD_KEYS and isinstance(item, str):
                yield item
            else:
                yield from _iter_verdict_field_values(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_verdict_field_values(item)


def _declares_degraded(fragment: Any, tokens: tuple[str, ...]) -> bool:
    """Return True when *fragment* carries one of its producers' degradation tokens.

    TWO ARMS, because the two tokens are EMITTED in two different shapes and
    each must be read the way its producer writes it:

    * **Verdict-field equality** (:data:`_VERDICT_SCOPED_TOKENS`) —
      ``inconclusive`` is an exact per-check ``status`` / ``comparison`` VALUE,
      so it is matched by equality and only under those keys. A substring scan
      over every string value would also match the ``plan_dir`` / ``plan_id``
      fields three of the four roster producers publish: a plan whose id
      contains the token would then read as degraded on a fully resolved
      fragment, and because the aggregate is suppressed unless EVERY member
      degraded, one such false positive across the whole roster fires
      ``AGGREGATE_UNMEASURABLE`` on a run where every producer resolved — the
      confidently-wrong plan-level claim this signal exists to remove.
    * **Free-text substring** (every other token) —
      ``ARTIFACT_COVERAGE_UNMEASURABLE`` is embedded in the TEXT of the warning
      finding ``analyze-logs`` raises, so it is matched as a substring of any
      string value. Narrowing THIS arm to equality would read that producer as
      resolved on exactly the run where it declared it could not measure,
      leaving the aggregate one member short of firing, forever.

    Neither arm is a relaxation of honest degradation reporting: a producer that
    genuinely declares itself unmeasurable is still read as degraded by both.
    """
    verdict_tokens = tuple(token for token in tokens if token in _VERDICT_SCOPED_TOKENS)
    free_text_tokens = tuple(token for token in tokens if token not in _VERDICT_SCOPED_TOKENS)

    if verdict_tokens:
        for text in _iter_verdict_field_values(fragment):
            if text in verdict_tokens:
                return True
    if free_text_tokens:
        for text in _iter_string_values(fragment):
            if any(token in text for token in free_text_tokens):
                return True
    return False


def _compose_time_producer_verdict(plan_dir: Path) -> str:
    """Return the compose-time producer's verdict, read from the plan's manifest.

    Unlike the fragment probe above this matches the artifact's raw text, keys
    included, because ``pre_push_quality_gate_inactive`` is a STATE NAME rather
    than a counter key — there is no clean-run shape that carries the name beside
    a zero, so the key/value distinction that protects the fragment probe has
    nothing to protect here.

    An absent or unreadable manifest is :data:`PRODUCER_UNREAD`, never
    ``resolved``: a plan composed before the manifest existed has no verdict to
    report, and reporting one as clean would let an aggregate claim rest on a
    member nothing was ever read from.
    """
    artifact = plan_dir / COMPOSE_TIME_ARTIFACT
    if not artifact.is_file():
        return PRODUCER_UNREAD
    try:
        text = artifact.read_text(encoding='utf-8')
    except OSError:
        return PRODUCER_UNREAD
    return PRODUCER_DEGRADED if COMPOSE_TIME_DEGRADED_TOKEN in text else PRODUCER_RESOLVED


def footprint_derivation_record(
    fragments: dict[str, Any], plan_dir: Path
) -> dict[str, Any] | None:
    """Return the ONE plan-level footprint-derivation record, or ``None``.

    Every producer keeps its own honest report unchanged; this says once, with
    the roster attached, that N independent consumers all went unmeasurable on
    the SAME missing derivation — the separate-what-you-could-not-evaluate shape
    applied one level up, carrying producer identity in the answer.

    The roster has two provenances and publishes them separately: the
    retrospective-time members are DERIVED from the aspect registry
    (:func:`retro_sections.footprint_consuming_aspect_keys`), and the single
    compose-time member is named explicitly because it has no registry entry.

    Returns ``None`` — no record, and therefore no section — unless every member
    that was READ degraded. Two live states remain:

    * :data:`AGGREGATE_UNMEASURABLE` — the roster was fully read and every member
      degraded. The verdict fires.
    * :data:`AGGREGATE_PARTIAL_COVERAGE` — every member that could be read
      degraded, but at least one could not be read at all. The verdict is
      SUPPRESSED and the coverage gap reported in its place: an aggregate
      computed over a roster that was not fully read is the vacuous-authority
      shape this signal exists to remove.

    A run in which any member resolved yields ``None``: the signal is that they
    all failed together, and a mixed roster is not that signal.
    """
    producers: list[dict[str, str]] = []
    for fragment_key in footprint_consuming_aspect_keys():
        if fragment_key not in fragments:
            verdict = PRODUCER_UNREAD
        elif _declares_degraded(fragments.get(fragment_key), FOOTPRINT_DEGRADED_TOKENS):
            verdict = PRODUCER_DEGRADED
        else:
            verdict = PRODUCER_RESOLVED
        producers.append(
            {
                'producer': fragment_key,
                'verdict': verdict,
                'provenance': PROVENANCE_ASPECT_REGISTRY,
            }
        )
    producers.append(
        {
            'producer': COMPOSE_TIME_PRODUCER,
            'verdict': _compose_time_producer_verdict(plan_dir),
            'provenance': PROVENANCE_COMPOSE_TIME,
        }
    )

    degraded = [p for p in producers if p['verdict'] == PRODUCER_DEGRADED]
    resolved = [p for p in producers if p['verdict'] == PRODUCER_RESOLVED]
    unread = [p for p in producers if p['verdict'] == PRODUCER_UNREAD]

    if resolved or not degraded:
        return None

    state = AGGREGATE_PARTIAL_COVERAGE if unread else AGGREGATE_UNMEASURABLE
    names = ', '.join(p['producer'] for p in degraded)
    if state == AGGREGATE_UNMEASURABLE:
        message = (
            f'All {len(producers)} footprint-consuming producers went unmeasurable on the '
            f'same missing derivation: {names}.'
        )
        severity = 'warning'
    else:
        message = (
            f'{len(degraded)} of {len(producers)} footprint-consuming producers went '
            f'unmeasurable ({names}), but {len(unread)} could not be read — the aggregate '
            f'verdict is suppressed rather than computed over a partially-read roster.'
        )
        severity = 'info'

    return {
        'status': 'success',
        'aspect': 'footprint-derivation',
        'state': state,
        'roster_source': f'{PROVENANCE_ASPECT_REGISTRY}+{PROVENANCE_COMPOSE_TIME}',
        'producers': producers,
        'producer_count': len(producers),
        'degraded_count': len(degraded),
        'resolved_count': len(resolved),
        'unread_count': len(unread),
        'findings': [{'severity': severity, 'message': message}],
    }


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    if not plan_dir.exists():
        raise ValueError(f'Plan directory does not exist: {plan_dir}')

    fragments = load_fragments(Path(args.fragments_file))
    plan_id = args.plan_id or plan_dir.name

    # Derived here — every fragment is still on disk and the bundle cleanup below
    # has not run. The ordering is load-bearing rather than incidental: this
    # script DELETES the fragment bundle on success, so an aggregate computed
    # after that point could not read its own roster, and acting on its warning
    # would mean rebuilding every fragment first.
    derivation_record = footprint_derivation_record(fragments, plan_dir)
    if derivation_record is not None:
        fragments[FOOTPRINT_AGGREGATE_KEY] = derivation_record

    content, written, omitted, dropped = build_document(
        plan_id, args.mode, plan_dir, args.session_id, fragments
    )

    output_path = resolve_output_path(args.mode, plan_dir)
    output_path.write_text(content, encoding='utf-8')

    # Auto-cleanup: delete the fragments bundle after a successful report
    # write. Any error BEFORE this point retains the bundle for debugging
    # (we never reach this cleanup). A missing bundle is a silent no-op;
    # other OSError conditions log a warning to stderr but do NOT abort.
    fragments_path = Path(args.fragments_file)
    try:
        fragments_path.unlink()
    except FileNotFoundError:
        # Already gone — treat as successful cleanup.
        pass
    except OSError as exc:
        print(
            f'WARN: failed to delete fragments bundle {fragments_path}: {exc}',
            file=sys.stderr,
        )

    # A dropped section is content the aspect produced and the report lost —
    # ride the signal on the TOON status so the caller cannot mistake it for a
    # clean run. The process exit code stays 0: the document was written.
    result: dict[str, Any] = {
        'status': 'warning' if dropped else 'success',
        'plan_id': plan_id,
        'mode': args.mode,
        'output_path': str(output_path),
        'sections_written': written,
        'sections_omitted': omitted,
        'sections_dropped': dropped,
        # Reported, never gating: a written section whose "zero findings" cannot
        # be told apart from "could not look". See ``unattributed_zero_sections``.
        'sections_unattributed_zero': unattributed_zero_sections(written, fragments),
        # The plan-level footprint-derivation aggregate's state, or ``None`` when
        # no record was derived. Published so a caller can branch on the signal
        # without re-parsing the rendered document.
        'footprint_derivation_state': (
            derivation_record['state'] if derivation_record is not None else None
        ),
    }
    if dropped:
        result['message'] = (
            'Dropped non-empty sections from the compiled report: ' + ', '.join(dropped)
        )
    return result


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compile retrospective markdown document from aspect fragments',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser('run', help='Compile document', allow_abbrev=False)
    add_plan_id_arg(run_parser, required=False)
    run_parser.add_argument(
        '--archived-plan-path',
        help='Absolute path to archived plan directory (archived mode)',
    )
    run_parser.add_argument(
        '--mode',
        choices=['live', 'archived'],
        required=True,
        help='Resolution mode',
    )
    run_parser.add_argument(
        '--fragments-file',
        required=True,
        help='Path to TOON bundle of aspect fragments',
    )
    add_session_id_arg(run_parser, required=False)
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
