#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Outline-vs-shipped aspect — outline assessments against the realized footprint.

Compares what ``phase-3-outline`` said it would touch (the per-file component
assessments recorded in ``artifacts/findings/assessments.jsonl``) against what the
landing actually touched (the realized footprint, resolved through the SHARED
resolver in :mod:`_footprint_resolver`).

⛔ **This aspect REPORTS; it never GATES.** Every finding is emitted at
informational severity and the returned ``status`` is never a failing one. An
outline assessment is a planning-time judgement recorded BEFORE the work happened;
grading a landing against it would convert an honest forecast into a gate. Nothing
in this module is evidence that outline's judgement was wrong — only that nothing
had ever checked whether the work matched it.

⛔ **Assessments have NO ``resolution`` lifecycle, and this aspect does not give
them one.** They are scope INPUTS consumed by the decision they informed, not
defects awaiting closure. The store is opened read-only, no record is written, and
no ``resolution`` field is read, required, or emitted. Counting a missing
``resolution`` as ``pending`` is a known false reading — an earlier consumer did
exactly that across 29 assessment records and reported "29 findings never
resolved", a claim that had to be retracted. The published
``assessment_lifecycle`` field states the absence rather than leaving it implicit.

**Three distinguishable outcomes, never one divergence count.** They mean different
things and only one of them is unambiguously bad, so they are named and counted
separately, each with its own denominator:

``include_unrealised``
    Assessed :data:`CERTAINTY_INCLUDE`, absent from the realized footprint. MAY be
    a silent descope — or a forecast that a later, better-informed decision
    correctly abandoned. Denominator: the ``CERTAIN_INCLUDE``-assessed paths.

``touched_but_unassessed``
    Present in the realized footprint, carrying no assessment of any certainty.
    This is ORDINARY DISCOVERY — the system working — not a defect. Denominator:
    the realized-footprint paths.

``exclude_violated``
    Assessed :data:`CERTAINTY_EXCLUDE`, present in the realized footprint anyway.
    The one unambiguously bad outcome: outline ruled the file out and the work
    touched it regardless. Denominator: the ``CERTAIN_EXCLUDE``-assessed paths.

Collapsing the three into a single "divergence" count would hide the only one that
matters behind the two that are routinely benign.

**An unresolvable footprint yields ``inconclusive``, never three confident zeros.**
The three ``counts`` blocks are OMITTED on that path — absent, not zero — because a
zero published by a run that compared nothing is indistinguishable from a
zero it measured. The single informational finding names the reason instead.

**Sizing.** This script states no threshold and no magnitude: it publishes counts
beside the population each was taken over and nothing else. The rule governing any
magnitude a reader or an LLM synthesis states from these facts — that it be derived
from a CROSS-PLAN distribution with its denominator published, and reported
``unmeasured`` below the declared floor — lives in
``references/outline-vs-shipped.md``. Scripts never judge; references never run
code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from _footprint_resolver import footprint_resolved, resolve_diff_file_path, resolve_footprint
from constants import CERTAINTY_EXCLUDE, CERTAINTY_INCLUDE, FILE_FINDINGS_DIR
from file_ops import base_path, output_toon, safe_main
from input_validation import (
    add_plan_id_arg,
    parse_args_with_toon_errors,
)

#: The aspect key. MUST equal the ``fragment_key`` of this aspect's
#: :data:`retro_sections.SECTION_SPEC` row and the ``--aspect`` value
#: ``collect-fragments add`` is called with — the three are one registry, and a
#: spelling that differs from the row silently empties the report section.
ASPECT = 'outline-vs-shipped'

#: The assessments store, relative to the plan directory. Mirrors the layout
#: ``manage-findings`` writes (``_findings_core.get_assessments_path`` →
#: ``artifacts/findings/assessments.jsonl``). Held as a path tuple rather than
#: resolved through that skill's helper because this script reads ARCHIVED plan
#: directories too, where the ``--plan-id``-keyed helper cannot reach.
ASSESSMENTS_RELPATH = ('artifacts', FILE_FINDINGS_DIR, 'assessments.jsonl')

#: ``comparison`` verdicts. ``measured`` — the footprint resolved and the three
#: classes were computed. ``inconclusive`` — the footprint could not be resolved,
#: so NOTHING was compared and the ``counts`` block is absent.
COMPARISON_MEASURED = 'measured'
COMPARISON_INCONCLUSIVE = 'inconclusive'

#: Published verbatim so the report states the reports-never-gates rule rather
#: than leaving a reader to infer it from the absence of a failing status.
GATING_REPORT_ONLY = 'report_only'

#: Published verbatim so the report states that assessments carry no resolution
#: lifecycle. See the module docstring for the retracted claim this prevents.
ASSESSMENT_LIFECYCLE_NONE = 'none'

#: The one severity this aspect ever emits.
SEVERITY_INFO = 'info'

#: The population label each class count is published beside. A count without the
#: population it was taken over is inadmissible, so every class carries one.
POPULATION_CERTAIN_INCLUDE = 'certain_include_assessed_paths'
POPULATION_FOOTPRINT = 'realized_footprint_paths'
POPULATION_CERTAIN_EXCLUDE = 'certain_exclude_assessed_paths'


def resolve_plan_dir(mode: str, plan_id: str | None, archived_plan_path: str | None) -> Path:
    """Resolve the plan directory for ``mode``. Mirrors the sibling check scripts."""
    if mode == 'live':
        if not plan_id:
            raise ValueError('--plan-id is required for live mode')
        return base_path('plans', plan_id)
    if mode == 'archived':
        if not archived_plan_path:
            raise ValueError('--archived-plan-path is required for archived mode')
        return Path(archived_plan_path)
    raise ValueError(f'Unknown mode: {mode!r}')


def normalize_path(raw: Any) -> str:
    """Normalize a recorded path to the form the realized footprint uses.

    Both sides are repo-relative, but a hand-authored outline path may carry a
    ``./`` prefix or surrounding whitespace that a git-derived footprint never
    does. Normalizing BOTH sides through this one function is what keeps a
    cosmetic difference from being reported as a real divergence — the class
    ``exclude_violated`` in particular must not be manufacturable by a stray
    prefix.
    """
    text = str(raw).strip()
    while text.startswith('./'):
        text = text[2:]
    return text


def load_assessments(plan_dir: Path) -> tuple[list[dict[str, Any]], bool]:
    """Return ``(records, store_present)`` for the plan's assessment store.

    ``store_present`` is ``True`` only when the file existed AND was read. It is
    the discriminator between "outline recorded no assessments" and "the store
    could not be opened" — collapsing the two would let an unreadable store report
    as a plan whose outline assessed nothing, which reads benign.

    A malformed line is skipped rather than fatal: the store is append-only JSONL
    written by a different skill, and one corrupt line must not cost the whole
    comparison. Every readable record is still counted, so ``assessments_read``
    reports what was actually parsed.
    """
    path = plan_dir.joinpath(*ASSESSMENTS_RELPATH)
    if not path.is_file():
        return [], False
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError:
        return [], False
    records: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records, True


def paths_by_certainty(records: list[dict[str, Any]]) -> tuple[set[str], set[str], set[str]]:
    """Return ``(assessed, certain_include, certain_exclude)`` normalized path sets.

    Grouped by PATH rather than by record, because the denominators are path
    counts: two assessments of the same file are one assessed path, and counting
    them twice would inflate a denominator without adding a member.

    ``assessed`` spans EVERY certainty, ``UNCERTAIN`` included. That
    is what keeps ``touched_but_unassessed`` honest: a path outline explicitly
    judged uncertain WAS assessed, so touching it is not undeclared discovery.

    A path carrying both certainties (a contradictory outline) lands in both sets
    and is reported under both classes. That is the honest report of a
    contradiction; silently picking one would hide it.
    """
    assessed: set[str] = set()
    include: set[str] = set()
    exclude: set[str] = set()
    for record in records:
        raw_path = record.get('file_path')
        if not raw_path:
            continue
        path = normalize_path(raw_path)
        if not path:
            continue
        assessed.add(path)
        certainty = str(record.get('certainty') or '').strip()
        if certainty == CERTAINTY_INCLUDE:
            include.add(path)
        elif certainty == CERTAINTY_EXCLUDE:
            exclude.add(path)
    return assessed, include, exclude


def _class_block(members: set[str], denominator: int, population: str) -> dict[str, Any]:
    """Build one outcome-class block: a count, its own denominator, its members."""
    return {
        'count': len(members),
        'denominator': denominator,
        'population': population,
        'members': sorted(members),
    }


def compare(
    footprint: set[str],
    assessed: set[str],
    include: set[str],
    exclude: set[str],
) -> dict[str, Any]:
    """Return the three outcome-class blocks. Pure over its inputs.

    Each class is derived from its OWN set expression, so no class can be produced
    by another's code path:

    * ``include_unrealised`` — ``include - footprint``
    * ``touched_but_unassessed`` — ``footprint - assessed``
    * ``exclude_violated`` — ``exclude & footprint``
    """
    return {
        'include_unrealised': _class_block(
            include - footprint, len(include), POPULATION_CERTAIN_INCLUDE
        ),
        'touched_but_unassessed': _class_block(
            footprint - assessed, len(footprint), POPULATION_FOOTPRINT
        ),
        'exclude_violated': _class_block(
            exclude & footprint, len(exclude), POPULATION_CERTAIN_EXCLUDE
        ),
    }


def build_findings(counts: dict[str, Any]) -> list[dict[str, str]]:
    """Return one informational finding per NON-EMPTY outcome class.

    Informational severity only, and one finding per class rather than one per
    member: the classes mean different things, and a reader must be able to tell
    the unambiguously-bad ``exclude_violated`` apart from the routinely-benign
    ``touched_but_unassessed`` at a glance. A class with a zero count contributes
    no finding — its zero is already published beside its denominator in
    ``counts``.
    """
    messages = {
        'include_unrealised': (
            'assessed CERTAIN_INCLUDE but absent from the realized footprint '
            '(may be a silent descope, or a forecast a later decision abandoned)'
        ),
        'touched_but_unassessed': (
            'present in the realized footprint carrying no assessment '
            '(ordinary discovery — the system working)'
        ),
        'exclude_violated': (
            'assessed CERTAIN_EXCLUDE and touched anyway '
            '(the one unambiguously bad outcome)'
        ),
    }
    findings: list[dict[str, str]] = []
    for name, message in messages.items():
        block = counts[name]
        if not block['count']:
            continue
        findings.append(
            {
                'severity': SEVERITY_INFO,
                'message': (
                    f'{name}: {block["count"]} of {block["denominator"]} '
                    f'{block["population"]} — {message}: {", ".join(block["members"])}'
                ),
            }
        )
    return findings


def load_diff_files(diff_file: str | None, plan_dir: Path) -> list[str] | None:
    """Return the realized footprint from a pre-saved diff file, or ``None`` if omitted.

    Omission is tested as ``diff_file is None`` so a SUPPLIED file naming nothing
    stays distinguishable from no ``--diff-file`` at all: the former is a resolved,
    genuinely-empty footprint and the latter sends the caller to the shared
    resolver. A supplied-but-unresolvable path RAISES
    (:func:`_footprint_resolver.resolve_diff_file_path`) rather than reporting an
    empty one — a could-not-look must not carry a nothing-to-look-at's token.

    Byte-for-byte the contract ``check-routing-decisions.load_diff_files``
    documents; the two aspects consume the same capture pattern.
    """
    if diff_file is None:
        return None
    path = resolve_diff_file_path(diff_file, plan_dir)
    try:
        return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    except OSError as e:
        raise ValueError(f'Diff file could not be read: {diff_file}: {e}') from e


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    plan_dir = resolve_plan_dir(args.mode, args.plan_id, args.archived_plan_path)
    plan_id = args.plan_id or plan_dir.name

    records, store_present = load_assessments(plan_dir)
    assessed, include, exclude = paths_by_certainty(records)

    supplied = load_diff_files(args.diff_file, plan_dir)
    if supplied is not None:
        # Supplied — including a file that legitimately names nothing. That is a
        # RESOLVED empty footprint, not an unresolvable one.
        footprint: set[str] | None = {normalize_path(p) for p in supplied}
        footprint_source = 'diff_file'
    else:
        resolved = resolve_footprint(plan_dir, args.plan_id if args.mode == 'live' else None)
        if footprint_resolved(resolved):
            footprint = {normalize_path(p) for p in resolved}
            footprint_source = 'resolved'
        else:
            footprint = None
            footprint_source = 'unresolved'

    result: dict[str, Any] = {
        'status': 'success',
        'aspect': ASPECT,
        'plan_id': plan_id,
        'plan_dir': str(plan_dir),
        # Stated, not inferred: this aspect reports and never gates, and it
        # assigns assessments no resolution lifecycle.
        'gating': GATING_REPORT_ONLY,
        'assessment_lifecycle': ASSESSMENT_LIFECYCLE_NONE,
        'assessments_store_present': store_present,
        'assessments_read': len(records),
        'assessed_path_count': len(assessed),
        'footprint_source': footprint_source,
    }

    if footprint is None:
        # ⛔ No `counts` block. The three classes are ABSENT, not zero: a zero
        # published by a run that compared nothing reads exactly like a zero it
        # measured, and that is the confident-clean-over-nothing shape this aspect
        # exists to avoid committing itself.
        result['comparison'] = COMPARISON_INCONCLUSIVE
        result['findings'] = [
            {
                'severity': SEVERITY_INFO,
                'message': (
                    'outline-vs-shipped is inconclusive: the realized footprint could '
                    'not be resolved by any tier, so no outcome class was computed. '
                    'The three class counts are absent rather than zero.'
                ),
            }
        ]
        result['llm_judgement_required'] = True
        return result

    counts = compare(footprint, assessed, include, exclude)
    result['comparison'] = COMPARISON_MEASURED
    result['footprint_path_count'] = len(footprint)
    result['counts'] = counts
    result['findings'] = build_findings(counts)
    # The interpretation of the three classes — which divergence is a real problem
    # on THIS plan and which is the system working — is an LLM judgment over these
    # facts, synthesized per references/outline-vs-shipped.md. Not computed here.
    result['llm_judgement_required'] = True
    return result


@safe_main
def main() -> int:
    parser = argparse.ArgumentParser(
        description='Outline-vs-shipped aspect — outline assessments against the realized footprint',
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    run_parser = subparsers.add_parser(
        'run',
        help='Compare outline assessments against the realized footprint',
        allow_abbrev=False,
    )
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
        '--diff-file',
        default=None,
        help=(
            'Pre-saved realized footprint (one path per line). A relative path is '
            'resolved against the plan directory first and the cwd second; a supplied '
            'path that resolves to nothing is an error, never an empty footprint. When '
            'ABSENT, the footprint is recovered through the shared resolver.'
        ),
    )
    run_parser.set_defaults(func=cmd_run)

    args = parse_args_with_toon_errors(parser)
    result = args.func(args)
    output_toon(result)
    return 0


if __name__ == '__main__':
    main()
