# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``check routing decisions`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

In-process behavioral tests for ``check-routing-decisions.py``.

The aspect's headline defect was inferring a removal *cause* from a removal
*fact*: any prunable step absent from ``phase_6.steps`` was treated as proof its
``no_code_delta`` predicate had fired, so a step dropped by the posture cutoff
(or by any of the three other recorded non-predicate mechanisms) was reported as
a mis-prune whenever the realized footprint touched production code.

These tests pin the corrected contract: the recorded decision log is consulted
FIRST, and ``log_readable`` is the sole discriminator between a substantiated
``fail`` and an honest ``inconclusive``.
"""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from _decision_line_shapes import format_dropped_record
from toon_parser import serialize_toon

from conftest import load_script_module

_crd = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-routing-decisions.py', 'crd_behavior_mod'
)


# The recorded non-predicate removal mechanisms.
#
# The composer's subtraction-record lines are rendered by the WRITER'S OWN
# formatter, imported from production. Importing the writer (never the reader's
# regexes) is what makes these a real contract check: the reader is exercised
# against bytes the emitter actually produces, so a change to the shape breaks
# writer and reader together instead of leaving the reader matching a form
# nothing emits.
#
# These fixtures were previously hand-written from the standards document and had
# drifted from it: they encoded a retired aggregate shape (a Python-list step
# repr, `execution_profile=` before the verb, a `(tier above posture cutoff)`
# trailing clause) that the composer had long since replaced with one line per
# dropped step. The tests passed against a reader that could not match a single
# real emission — the hand-written fixture drifted in lock-step with the wrong
# copy, which is precisely what it could not catch.
#
# The three mechanisms below render their own line shapes rather than reporting
# through the shared formatter, so their fixtures stay literal, each transcribed
# from its own emitter.
_LANE_TARGET = ' from phase_6.steps (execution_profile=minimal)'


_TIER_REASON = 'effective tier full exceeds the minimal posture cutoff'


LANE_RESOLUTION_LINE = '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] ' + format_dropped_record(
    'lane_resolution', 'sonar-roundtrip', _TIER_REASON, target=_LANE_TARGET
)


LANE_RESOLUTION_SECOND_STEP_LINE = (
    '[2026-04-17T10:00:01Z] [INFO] [aaaaab] '
    + format_dropped_record(
        'lane_resolution', 'plan-retrospective', _TIER_REASON, target=_LANE_TARGET
    )
)


LANE_RESOLUTION_PREFIXED_LINE = '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] ' + format_dropped_record(
    'lane_resolution', 'default:sonar-roundtrip', _TIER_REASON, target=_LANE_TARGET
)


DECISION_MATRIX_LINE = '[2026-04-17T10:00:02Z] [INFO] [ffffff] ' + format_dropped_record(
    'decision_matrix',
    'sonar-roundtrip',
    "decide rule 'early_terminate_analysis' narrowed phase_6 to the analysis minimum",
)


UNRESOLVED_ASK_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [bbbbbb] '
    '(plan-marshall:manage-execution-manifest:compose) unresolved_ask_provider_drop — '
    'dropped default:sonar-roundtrip from phase_6.steps '
    '(unresolved lane:ask, provider absent)'
)


SIMPLIFY_INACTIVE_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [cccccc] '
    '(plan-marshall:manage-execution-manifest:compose) finalize-step-simplify omitted — '
    'change_type=analysis affected_files_count=0'
)


CEREMONY_DROPPED_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [dddddd] '
    '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
    'finalize.simplify=never, dropped finalize-step-simplify from phase_6.steps'
)


CEREMONY_ADDED_LINE = (
    '[2026-04-17T10:00:00Z] [INFO] [eeeeee] '
    '(plan-marshall:manage-execution-manifest:compose) ceremony_finalize selection — '
    'finalize.simplify=always, added finalize-step-simplify to phase_6.steps'
)


# A production path — non-bookkeeping, non-doc, non-test — so
# ``footprint_has_production`` is True and the predicate would be FALSE.
PRODUCTION_PATH = 'marketplace/bundles/plan-marshall/skills/demo/scripts/demo.py'


def _manifest_toon(steps: list[str]) -> str:
    """Render a minimal ``execution.toon`` carrying only ``phase_6.steps``.

    Serialized with the same ``serialize_toon`` the manifest writer uses, so the
    fixture round-trips through the production ``parse_toon`` reader exactly as a
    real manifest does.
    """
    return serialize_toon({'plan_id': 'demo', 'phase_6': {'steps': steps}}) + '\n'


def _build_plan(
    plan_dir: Path,
    *,
    steps: list[str],
    decision_lines: list[str] | None = None,
    write_decision_log: bool = True,
    metadata: dict | None = None,
) -> Path:
    """Materialize a plan directory the aspect can read.

    ``write_decision_log=False`` omits ``logs/decision.log`` entirely, which is
    the ``log_readable == False`` input state.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'execution.toon').write_text(_manifest_toon(steps), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps({'metadata': metadata if metadata is not None else {}}), encoding='utf-8'
    )
    if write_decision_log:
        logs = plan_dir / 'logs'
        logs.mkdir(exist_ok=True)
        (logs / 'decision.log').write_text('\n'.join(decision_lines or []) + '\n', encoding='utf-8')
    return plan_dir


def _diff_file(tmp_path: Path, paths: list[str], name: str = 'diff.txt') -> str:
    path = tmp_path / name
    path.write_text('\n'.join(paths) + '\n', encoding='utf-8')
    return str(path)


def _run_args(plan_dir: Path, diff_file: str | None) -> Namespace:
    return Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(plan_dir),
        mode='archived',
        diff_file=diff_file,
    )


def _check(checks: list[dict], name: str) -> dict | None:
    return next((c for c in checks if c.get('check') == name), None)


# All phase_6 steps EXCEPT sonar-roundtrip — so sonar-roundtrip is the absent
# prunable step under test while finalize-step-simplify stays present.
_STEPS_WITHOUT_SONAR = ['finalize-step-simplify', 'lessons-capture', 'archive-plan']


# All phase_6 steps EXCEPT finalize-step-simplify.
_STEPS_WITHOUT_SIMPLIFY = ['sonar-roundtrip', 'lessons-capture', 'archive-plan']


_STEPS_WITH_BOTH = ['sonar-roundtrip', 'finalize-step-simplify', 'lessons-capture', 'archive-plan']
