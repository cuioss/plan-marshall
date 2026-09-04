# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``compile report`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for ``compile-report.py``.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import retro_sections as _retro_sections

from conftest import MARKETPLACE_ROOT, load_script_module

# Absolute path to the committed stripped-archive fixture. The regression
# test copies this tree into a tmp dir and drives the full
# collect-fragments + compile-report pipeline end-to-end. The fixture lives
# under version control so regressions in fragment key naming, bundle
# mode-propagation, or section rendering are caught deterministically.
_STRIPPED_ARCHIVE_FIXTURE = Path(__file__).parent / 'fixtures' / 'archived-plan'


_COLLECT_FRAGMENTS_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'
)


# Mapping from committed fragment filename (``fragment-{slug}.toon``) to the
# ``--aspect`` key that ``compile-report`` expects in _SECTION_SPEC. The
# ``invariant-check-summary`` filename intentionally differs from the
# consumer key ``invariant-summary`` — producers and consumers agreed on a
# rename and the fixture records the producer-side filename verbatim.
_FRAGMENT_TO_ASPECT = {
    'fragment-artifact-consistency.toon': 'artifact-consistency',
    'fragment-invariant-check-summary.toon': 'invariant-summary',
    'fragment-lessons-proposal.toon': 'lessons-proposal',
    'fragment-llm-to-script-opportunities.toon': 'llm-to-script-opportunities',
    'fragment-log-analysis.toon': 'log-analysis',
    'fragment-logging-gap-analysis.toon': 'logging-gap-analysis',
    'fragment-permission-prompt-analysis.toon': 'permission-prompt-analysis',
    'fragment-plan-efficiency.toon': 'plan-efficiency',
    'fragment-request-result-alignment.toon': 'request-result-alignment',
    'fragment-script-failure-analysis.toon': 'script-failure-analysis',
}


SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'compile-report.py'


# ``compile-report.py`` has a hyphenated filename, so it is addressable only by
# file — which is what the shared loader resolves. The cleanup tests reach
# ``cmd_run`` and ``Path.unlink`` through the SAME namespace the script uses, so
# monkeypatching affects the production code.
_compile_report = load_script_module(
    'plan-marshall', 'plan-retrospective', 'compile-report.py', 'compile_report'
)


cmd_run = _compile_report.cmd_run


def _write_fragments(tmp_path: Path, with_failure_aspects: bool = False) -> Path:
    """Write a minimal TOON fragments bundle.

    The conditional aspects include at least one ``failures``/``prompts``
    item so ``should_emit`` recognizes them as non-empty.
    """
    # Top-level fragment keys are HYPHENATED to match the keys produced by
    # ``collect-fragments add --aspect <name>`` and consumed by
    # ``compile-report.py`` _SECTION_SPEC. Underscored variants would be
    # silently dropped by the consumer lookup.
    lines = [
        '_executive-summary:',
        '  summary: "All green. 2 warnings worth reviewing."',
        'request-result-alignment:',
        '  status: success',
        '  aspect: request_result_alignment',
        'artifact-consistency:',
        '  status: success',
        '  aspect: artifact_consistency',
        'log-analysis:',
        '  status: success',
        '  aspect: log_analysis',
        'invariant-summary:',
        '  status: success',
        '  aspect: invariant_summary',
        'plan-efficiency:',
        '  status: success',
        '  aspect: plan_efficiency',
        'llm-to-script-opportunities:',
        '  status: success',
        '  aspect: llm_to_script_opportunities',
        'logging-gap-analysis:',
        '  status: success',
        '  aspect: logging_gap_analysis',
        'lessons-proposal:',
        '  status: success',
        '  aspect: lessons_proposal',
    ]
    if with_failure_aspects:
        lines.extend(
            [
                'script-failure-analysis:',
                '  status: success',
                '  aspect: script_failure_analysis',
                '  failures[1]{notation,exit_code}:',
                '    plan-marshall:foo:bar,1',
                'permission-prompt-analysis:',
                '  status: success',
                '  aspect: permission_prompt_analysis',
                '  prompts[1]{tool,resource}:',
                '    Bash,some-command',
            ]
        )
    fragments_file = tmp_path / 'fragments.toon'
    fragments_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return fragments_file


def _run_args(
    mode: str,
    fragments_path: Path,
    plan_id: str | None = None,
    archived_plan_path: Path | None = None,
    session_id: str | None = None,
) -> Namespace:
    """Build the ``argparse.Namespace`` that ``cmd_run`` expects."""
    return Namespace(
        command='run',
        plan_id=plan_id,
        archived_plan_path=str(archived_plan_path) if archived_plan_path else None,
        mode=mode,
        fragments_file=str(fragments_path),
        session_id=session_id,
        func=cmd_run,
    )


# =============================================================================
# Phase Dispatch Boundaries section
# =============================================================================


def _write_fragments_with_dispatch_boundaries(
    tmp_path: Path,
    phases: dict[str, dict] | None,
) -> Path:
    """Write a fragments bundle that includes a ``dispatch_boundaries`` key.

    Args:
        tmp_path: pytest tmp_path fixture.
        phases: dict mapping phase name (e.g. ``"5-execute"``) to a per-phase
            dict (``present``, ``rows``, ``unknown_count``,
            ``clean_exit_queue_empty_count``). Pass ``None`` to omit the key
            entirely; pass ``{}`` to emit an empty dict.
    """
    import json

    # Start from the minimal fragments bundle.
    base_fragments = _write_fragments(tmp_path)
    content = base_fragments.read_text(encoding='utf-8')

    if phases is None:
        return base_fragments
    # Inline the dispatch_boundaries dict as a TOON nested block.
    lines = ['dispatch_boundaries:']
    if phases:
        for phase, data in phases.items():
            # TOON keys are unquoted bare identifiers; phase names like
            # ``4-plan`` are accepted verbatim by the parser.
            lines.append(f'  {phase}:')
            for k, v in data.items():
                if isinstance(v, list):
                    if not v:
                        lines.append(f'    {k}[0]:')
                    else:
                        lines.append(f'    {k}: {json.dumps(v)}')
                elif isinstance(v, bool):
                    lines.append(f'    {k}: {"true" if v else "false"}')
                else:
                    lines.append(f'    {k}: {v}')
    content = content + '\n'.join(lines) + '\n'
    fragments_file = tmp_path / 'fragments-dispatch-boundaries.toon'
    fragments_file.write_text(content, encoding='utf-8')
    return fragments_file


# =============================================================================
# Registry-consistency regression guard (deliverable 2)
# =============================================================================
#
# The class of defect this guard pins down: a producer aspect key drifting from
# the consumer's section map. ``retro_sections.SECTION_SPEC`` is the single
# shared registry both scripts consume — ``compile-report`` renders from it and
# ``collect-fragments add`` validates ``--aspect`` against the derived
# ``valid_aspect_keys()``. This guard asserts the full registry↔producer↔consumer
# round-trip so a future aspect-key add or rename that drifts the two apart fails
# at test time, distinct from D1's hand-picked local ``cmd_add`` unit cases.

# ``retro_sections`` is imported PLAINLY at the top of this module, from the same
# scripts/ directory the executor puts on PYTHONPATH (conftest mirrors that path
# setup). Importing the live registry — rather than restating the key list — is
# what makes this guard self-maintaining: a new SECTION_SPEC row is automatically
# covered.

_COLLECT_FRAGMENTS_SCRIPT_REGISTRY = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'
)


def _registry_render_fragment_lines(fragment_key: str, trigger: str | None) -> list[str]:
    """Return TOON lines for a single registry aspect that ``should_emit`` accepts.

    Conditional sections (``trigger is not None``) emit only when their fragment
    carries non-empty payload, so this synthesizes the minimal shape each
    ``should_emit`` branch recognizes:

    - ``dispatch_boundaries`` → a per-phase dict with one ``present: true`` phase.
    - ``manifest-decisions`` → ``manifest_present: true``.
    - every other conditional key → a one-item ``findings`` list.

    Unconditional sections (``trigger is None``) emit on a bare ``status: success``
    fragment.
    """
    if fragment_key == 'dispatch_boundaries':
        return [
            'dispatch_boundaries:',
            '  5-execute:',
            '    present: true',
            '    rows[0]:',
            '    unknown_count: 0',
            '    clean_exit_queue_empty_count: 0',
        ]
    # A `summary` line, not a bare envelope. `status` and `aspect` are envelope
    # metadata that `_fragment_has_payload` deliberately does not count, and the
    # written/omitted partition now delegates to that same discriminator — so an
    # envelope-only fragment is correctly omitted rather than rendered. A fixture
    # without payload would therefore assert that a section with no body renders,
    # which is the opposite of the invariant. Every real producer emits payload.
    lines = [f'{fragment_key}:', '  status: success', '  summary: "registry round-trip probe"']
    if trigger is None:
        return lines
    if fragment_key == 'manifest-decisions':
        lines.append('  manifest_present: true')
        return lines
    # Generic conditional section — a single findings entry satisfies should_emit.
    lines.extend(
        [
            '  findings[1]{severity,message}:',
            '    info,registry-consistency probe finding',
        ]
    )
    return lines


def _write_full_registry_fragments(tmp_path: Path) -> Path:
    """Write a fragments bundle carrying EVERY non-``_`` key in SECTION_SPEC.

    Each aspect's fragment is shaped so its (possibly conditional) section
    emits, so the rendered report must contain a section for every registry
    key — exercising the consumer-render side of the round-trip invariant.
    """
    lines = [
        '_executive-summary:',
        '  summary: "Registry-consistency round-trip probe."',
    ]
    for _heading, fragment_key, trigger in _retro_sections.SECTION_SPEC:
        if fragment_key.startswith('_'):
            continue
        lines.extend(_registry_render_fragment_lines(fragment_key, trigger))
    fragments_file = tmp_path / 'fragments-full-registry.toon'
    fragments_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return fragments_file


# =============================================================================
# Loud-drop partition of the non-emit path
# =============================================================================


def _write_fragments_with_extra(tmp_path: Path, extra_lines: list[str], name: str) -> Path:
    """Write the minimal bundle plus ``extra_lines`` appended verbatim.

    ``_write_fragments`` returns a path whose content is the baseline bundle;
    this helper re-reads it and emits a distinct file so a single test can pin
    a bespoke fragment shape without disturbing the shared baseline.
    """
    base = _write_fragments(tmp_path)
    content = base.read_text(encoding='utf-8') + '\n'.join(extra_lines) + '\n'
    fragments_file = tmp_path / name
    fragments_file.write_text(content, encoding='utf-8')
    return fragments_file
