# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``script failure analysis`` test modules.

Holds the module-level loads, constants and helpers the modules beside it
import. Below, verbatim, is the docstring of the module they were split from:

Tests for ``script-failure-analysis.py``.

The script classifies non-zero-exit script calls in
``script-execution.log`` by stderr signature (invented_subcommand,
missing_required_flag, invented_flag, script_internal_error) and emits a
deduped TOON fragment for the retrospective compile-report consumer.
"""


from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'script-failure-analysis.py'
)


# The PRODUCER of every work.log dispatch-failure line this module's parser
# consumes. The executor is generated from this template, so the template is the
# authoritative source of the emitted line shape.
EXECUTOR_TEMPLATE_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'tools-script-executor'
    / 'templates'
    / 'execute-script.py.template'
)


# Direct module load so unit tests can poke the pure helpers.
_spec = importlib.util.spec_from_file_location('script_failure_analysis', str(SCRIPT_PATH))


assert _spec is not None and _spec.loader is not None


_mod = importlib.util.module_from_spec(_spec)


_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# Fixture log builders
# ---------------------------------------------------------------------------

def _header(ts_suffix: str, notation: str, sub: str, level: str = 'INFO') -> str:
    """Produce a script-execution.log header line matching production shape.

    Per ``manage-logging/standards/log-format.md`` the header carries NO
    inline ``exit_code`` token — the exit code lives on a two-space-indented
    continuation line for error entries.
    """
    return f'[2026-05-26T10:00:{ts_suffix}Z] [{level}] [abc123] {notation} {sub} (0.12s)'


def _success(ts_suffix: str, notation: str, sub: str) -> str:
    """A successful (exit-zero) call: a bare header with no continuation block."""
    return _header(ts_suffix, notation, sub)


def _failure(ts_suffix: str, notation: str, sub: str, exit_code: int, stderr: str) -> str:
    """A failed call: header plus a two-space-indented continuation block.

    Matches the documented Error Entry shape (``exit_code: N`` colon + space,
    ``args:``, ``stderr:`` continuation fields).
    """
    return (
        f'{_header(ts_suffix, notation, sub, level="ERROR")}\n'
        f'  exit_code: {exit_code}\n'
        f'  args: {sub}\n'
        f'  stderr: {stderr}'
    )


def _write_log(plan_dir: Path, content: str) -> None:
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'script-execution.log').write_text(content, encoding='utf-8')


def _extract_emitted_message_format() -> str:
    """Recover the executor's dispatch-failure message format from its template.

    The executor builds the work.log failure line as an implicitly-concatenated
    f-string assigned to ``message`` inside ``emit_dispatch_failure_work_log``.
    Because every placeholder in it is a bare ``{name}``, concatenating the
    literal parts yields a ``str.format``-compatible template — so the test
    fixture can render a line the PRODUCER defines instead of re-typing one.

    This is the coupling the deliverable asks for: rename a field on the
    producer side and every fixture line built here changes with it, so the
    parser's tests fail rather than silently continuing to assert a shape the
    executor no longer writes. Rename the *variable* behind a placeholder and
    the ``str.format`` call raises ``KeyError`` — also a failure, never a
    silent pass.

    Fails loudly (``AssertionError``) when the template's shape can no longer
    be recovered. A fixture that fell back to a hard-coded literal here would
    reintroduce exactly the drift this extraction exists to prevent.
    """
    lines = EXECUTOR_TEMPLATE_PATH.read_text(encoding='utf-8').splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == 'message = (']
    assert len(starts) == 1, (
        f'expected exactly one "message = (" assignment in '
        f'{EXECUTOR_TEMPLATE_PATH.name}, found {len(starts)} — the '
        f'dispatch-failure emitter moved and this extraction needs updating'
    )
    parts: list[str] = []
    for line in lines[starts[0] + 1:]:
        stripped = line.strip()
        if stripped == ')':
            break
        match = re.fullmatch(r"f'(.*)'", stripped)
        assert match is not None, (
            f'unexpected line inside the executor dispatch-failure message '
            f'literal: {stripped!r}'
        )
        parts.append(match.group(1))
    assert parts, 'executor dispatch-failure message literal is empty'
    return ''.join(parts)


# The emitted line shape, derived from the producer at import time. Placeholders
# are whatever the executor names them — this module never re-types them.
EMITTED_MESSAGE_FORMAT = _extract_emitted_message_format()


def _work_failure(ts_suffix: str, notation: str, exit_code: int, failure_kind: str, detail: str) -> str:
    """Produce a work.log executor-failure line rendered from the PRODUCER's own format.

    The manage-logging header (``[ts] [LEVEL] [hash] ``) is prepended here
    because ``log_entry`` — not the emitter — writes it; everything after it is
    rendered from :data:`EMITTED_MESSAGE_FORMAT`, extracted from the executor
    template. No part of the failure line is re-typed in this file.
    """
    message = EMITTED_MESSAGE_FORMAT.format(
        notation=notation,
        exit_code=exit_code,
        failure_kind=failure_kind,
        detail=detail,
    )
    return f'[2026-05-26T11:00:{ts_suffix}Z] [ERROR] [wlog{ts_suffix}] {message}'


def _legacy_work_failure(ts_suffix: str, notation: str, exit_code: int, failure_kind: str) -> str:
    """A work.log failure line in the RETIRED ``stderr=`` tail shape.

    Deliberately hand-written: it pins a shape the producer no longer emits, so
    it is the one place a literal is correct. Used only to assert the parser
    reports an unrecognised line shape rather than a clean zero.
    """
    return (
        f'[2026-05-26T11:00:{ts_suffix}Z] [ERROR] [wlog{ts_suffix}] '
        f'[ERROR] (plan-marshall:execute-script:{exit_code}) script_failure '
        f'notation={notation} exit_code={exit_code} failure_kind={failure_kind} '
        f'stderr=some retired tail'
    )


def _prefix_drifted_work_failure(
    ts_suffix: str, notation: str, exit_code: int, failure_kind: str, detail: str
) -> str:
    """The producer's own failure line with ONLY its record prefix reshaped.

    Single-variable by construction: the tail is rendered from
    :data:`EMITTED_MESSAGE_FORMAT`, so the sole difference from a line the
    parser accepts is the leading ``(...:execute-script:N)`` construct. That
    construct is the one both patterns used to share, which is what made a
    drift in it defeat the parser and the recognition guard together.
    """
    line = _work_failure(ts_suffix, notation, exit_code, failure_kind, detail)
    drifted = re.sub(
        r'\([^()]*execute-script:\d+\)', '(plan-marshall:dispatcher)', line, count=1
    )
    assert drifted != line, (
        'the record prefix this fixture reshapes is no longer present in the '
        f'producer format: {EMITTED_MESSAGE_FORMAT!r}'
    )
    return drifted


def _unprefixed_work_failure(
    ts_suffix: str, notation: str, exit_code: int, failure_kind: str, detail: str
) -> str:
    """The producer's failure line with the record prefix removed entirely."""
    line = _work_failure(ts_suffix, notation, exit_code, failure_kind, detail)
    stripped = re.sub(r'\([^()]*execute-script:\d+\)\s*', '', line, count=1)
    assert stripped != line, 'the record prefix this fixture strips is no longer present'
    return stripped


def _work_status(ts_suffix: str, msg: str) -> str:
    """A non-failure work.log line (STATUS/ARTIFACT) — must never be parsed as a failure."""
    return f'[2026-05-26T11:00:{ts_suffix}Z] [INFO] [wlog{ts_suffix}] [STATUS] (plan-marshall:phase-5-execute) {msg}'


def _write_work_log(plan_dir: Path, content: str) -> None:
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'work.log').write_text(content, encoding='utf-8')
