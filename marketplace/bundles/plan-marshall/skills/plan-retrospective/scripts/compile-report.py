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

from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    add_session_id_arg,
    parse_args_with_toon_errors,
)
from retro_sections import SECTION_SPEC
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
    Each value is the per-file shape from analyze-logs.read_dispatch_boundaries_per_phase
    (``present``, ``rows``, ``unknown_count``, ``clean_exit_queue_empty_count``).
    The section emits when at least one phase has ``present: true``.
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
    return False


def render_dispatch_boundaries_body(fragment: Any) -> str:
    """Render the Phase Dispatch Boundaries section body.

    Emits a markdown table with one row per recorded phase, columns:
    ``phase | rows | unknown_count | clean_exit_queue_empty_count``. Falls
    back to a generic JSON dump after the table for the full fragment data.
    """
    import json

    if not isinstance(fragment, dict) or not fragment:
        return '_No dispatch-boundary artifacts present._\n'

    lines = [
        '| phase | rows | unknown_count | clean_exit_queue_empty_count |',
        '|-------|------|---------------|------------------------------|',
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
        lines.append(f'| {phase} | {row_count} | {unknown_count} | {clean_count} |')

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
    generated = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
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
) -> tuple[str, list[str], list[str]]:
    """Assemble the markdown document.

    Returns ``(content, sections_written, sections_omitted)``.
    """
    written: list[str] = []
    omitted: list[str] = []
    parts: list[str] = [build_header(plan_id, mode, plan_dir, session_id)]

    # Executive summary is synthesized from fragment data — if the caller
    # provided one under ``_executive-summary``, use it verbatim; otherwise
    # emit a placeholder.
    exec_fragment = fragments.get('_executive-summary')
    if isinstance(exec_fragment, dict) and exec_fragment.get('summary'):
        exec_text = str(exec_fragment['summary']).strip()
    elif isinstance(exec_fragment, str) and exec_fragment.strip():
        exec_text = exec_fragment.strip()
    else:
        exec_text = '_No executive summary provided._'

    for heading, fragment_key, trigger in SECTION_SPEC:
        if fragment_key == '_executive-summary':
            parts.append(f'## {heading}\n\n{exec_text}\n')
            written.append(heading)
            continue
        if not should_emit(fragment_key, trigger, fragments):
            omitted.append(heading)
            continue
        fragment = fragments.get(fragment_key)
        # Dispatch_boundaries uses a dedicated per-phase table renderer; every
        # other fragment falls back to the generic JSON+findings renderer.
        if fragment_key == 'dispatch_boundaries':
            body = render_dispatch_boundaries_body(fragment)
        else:
            body = render_section_body(fragment)
        parts.append(f'## {heading}\n\n{body}')
        written.append(heading)

    # Generic fallback render path (registered ⇒ rendered completeness guard).
    # collect-fragments accepts domain-contributed aspects (via
    # ``_registerable_aspect_keys`` = ``valid_aspect_keys()`` ∪
    # ``_domain_aspect_keys()``) that are NOT in the static SECTION_SPEC — e.g.
    # ``wrapper-tangle`` from pm-plugin-development. Without this fallback the
    # SECTION_SPEC loop above never looks them up and compile-report silently
    # drops their sections. Iterate the bundle for any genuine aspect key that
    # has no dedicated SECTION_SPEC row and is not a reserved/underscore-prefixed
    # meta key (``_meta``, ``_executive-summary``), and render each verbatim via
    # the existing render_section_body. The renderer stays judgment-free — a
    # domain aspect is surfaced rather than lost. Keys are sorted for a
    # deterministic section order.
    spec_keys = {fragment_key for _heading, fragment_key, _trigger in SECTION_SPEC}
    for aspect_key in sorted(fragments):
        if aspect_key.startswith('_'):
            continue
        if aspect_key in spec_keys:
            continue
        heading = _heading_from_aspect_key(aspect_key)
        body = render_section_body(fragments.get(aspect_key))
        parts.append(f'## {heading}\n\n{body}')
        written.append(heading)

    return '\n'.join(parts), written, omitted


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    if not plan_dir.exists():
        raise ValueError(f'Plan directory does not exist: {plan_dir}')

    fragments = load_fragments(Path(args.fragments_file))
    plan_id = args.plan_id or plan_dir.name

    content, written, omitted = build_document(plan_id, args.mode, plan_dir, args.session_id, fragments)

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

    return {
        'status': 'success',
        'plan_id': plan_id,
        'mode': args.mode,
        'output_path': str(output_path),
        'sections_written': written,
        'sections_omitted': omitted,
    }


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
