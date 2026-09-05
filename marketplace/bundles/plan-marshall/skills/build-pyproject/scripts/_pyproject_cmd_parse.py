#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parse functionality for Pyproject (Python/pyprojectx) build output.

Uses the shared ParserRegistry for consistent detection and routing.
Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _pyproject_cmd_parse import parse_log
"""

import re
from collections.abc import Callable
from pathlib import Path

from _build_parse import (
    SEVERITY_ERROR,
    CategoryPatterns,
    Issue,
    UnitTestSummary,
    add_issue_deduped,
    categorize_issue,
    collect_stack_traces,
    read_log_text,
)
from _build_parse import (
    detect_build_status as _detect_build_status_base,
)
from _build_parser_registry import DetectionRule, ParserRegistry

# Pre-compiled patterns for tool-specific parsers
_MYPY_ERROR_PATTERN = re.compile(r'^(.+\.py):(\d+): error: (.+)$', re.MULTILINE)
_RUFF_ISSUE_PATTERN = re.compile(r'^(.+\.py):(\d+):\d+: ([A-Z]+\d+) (.+)$', re.MULTILINE)
_PYTEST_FAILED_PATTERN = re.compile(r'^FAILED (.+\.py)::(\S+)(?: - (.+))?$', re.MULTILINE)

# Collection- and setup-level ERRORS, reported under pytest's `E` report
# character (already present in this project's `-rsfE` addopts). A module-import
# failure — an assertion or an ImportError raised while pytest is COLLECTING a
# test module — and a fixture failure raised at setup/teardown are reported as
# `ERROR ...` short-summary lines, NEVER as FAILED lines. A parser that reads
# only FAILED lines therefore renders such a run as `failed=0` with an EMPTY
# `failures[]`: the build still goes red, so no gate is defeated, but a triage
# consumer reading `failures[]` to learn WHAT broke is told nothing.
#
# Two spellings share the one pattern: `ERROR path.py` (a collection error, which
# names no test) and `ERROR path.py::test_name` (a setup/teardown error, which
# does). The trailing ` - <message>` is pytest's exception repr and is optional.
_PYTEST_ERROR_PATTERN = re.compile(r'^ERROR (\S+\.py)(?:::(\S+))?(?: - (.+))?$', re.MULTILINE)

# Failure-detail capture (deliverable 9). pytest renders per-test tracebacks
# under a `=== FAILURES ===` banner, each test block headed by an
# underscore-ruled `____ test_name ____` line and terminated by the next such
# header or the next top-level `=== section ===` line (short-summary / counts).
_PYTEST_FAILURES_BANNER = re.compile(r'^=+ FAILURES =+\s*$')
# The ERRORS section has the identical block structure under its own banner, so
# the same scanner reads both; only the banner and the header-to-key mapping
# differ (see `_pytest_error_block_key`).
_PYTEST_ERRORS_BANNER = re.compile(r'^=+ ERRORS =+\s*$')
# pytest pads a block header out to the terminal width with `_`, so how MANY
# underscores appear is a function of how long the name inside them is, not of
# the header's kind. A short `test_alpha` gets a wide rule on both sides; a full
# `ERROR collecting test/some/deeply/nested/test_module.py` consumes the whole
# width and the padding collapses to exactly ONE underscore per side. Requiring
# three would therefore match every short name and silently miss every long one —
# which is precisely how the ERRORS blocks went unfound while the FAILURES blocks
# (short test names) were read fine, leaving a collection error with no line
# number and no assertion message.
_PYTEST_BLOCK_HEADER = re.compile(r'^_+\s+(.+?)\s+_+\s*$')
_PYTEST_SECTION_LINE = re.compile(r'^=+\s+\S.*\s+=+\s*$')
# The two ERRORS-section block-header spellings. Each must map back onto the same
# key its short-summary line yields: `ERROR collecting <path>` pairs with
# `ERROR <path>`, and `ERROR at setup of <test>` pairs with `ERROR <path>::<test>`.
_PYTEST_ERROR_HEADER_COLLECTING = re.compile(r'^ERROR collecting (\S+)$')
_PYTEST_ERROR_HEADER_PHASE = re.compile(r'^ERROR at (?:setup|teardown) of (\S+)$')
# The `E   ` gutter pytest prefixes onto the raised exception's own lines inside
# a traceback block. A collection error's short-summary line carries NO
# ` - <message>` tail, so this gutter is the only place its real message exists.
_PYTEST_EXCEPTION_LINE = re.compile(r'^E\s+(\S.*)$', re.MULTILINE)
# Deepest `path.py:NN:` line in a traceback block — the frame the failure
# originated at (identical across tests that share a root cause).
_PYTEST_FRAME_PATTERN = re.compile(r'(\S+\.py):(\d+):')
# Signature-normalization: collapse run-specific literals so failures sharing a
# root cause map to ONE signature (hex addresses, quoted values, digit runs).
_PYTEST_HEX_ADDR = re.compile(r'0x[0-9a-fA-F]+')
_PYTEST_QUOTED = re.compile(r'''(['"]).*?\1''')
_PYTEST_DIGIT_RUN = re.compile(r'\d+')
_PYTEST_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*')
# Upper bound on a single captured detail block; keeps a pathological log from
# bloating the finding store. Distinct from deliverable 10's `errors` emission
# cap (which limits the NUMBER of failures shown, not one block's length).
_MAX_DETAIL_LEN = 2000

# The two Issue categories the pytest parser assigns. BOTH start with `test_`, so
# `_build_shared._classify_issue_finding_type` routes both to the `test-failure`
# finding store: a test module that could not even be imported is a broken test,
# not a build error, and a triage consumer looks for it in the same place.
CATEGORY_TEST_FAILURE = 'test_failure'
CATEGORY_COLLECTION_ERROR = 'test_collection_error'

# Python-specific categorization patterns for use with shared categorize_issue().
# Patterns are checked case-insensitively; regex metacharacters trigger regex mode.
PYTHON_PATTERNS: CategoryPatterns = {
    'type_error': [
        r'\.py:\d+: error:',
        'incompatible type',
        'incompatible return value',
        'has no attribute',
        'missing positional argument',
    ],
    'lint_error': [
        r'\.py:\d+:\d+: [A-Z]+\d+',
        'ruff',
    ],
    'test_failure': [
        r'^FAILED ',
        'AssertionError',
        'assert ',
    ],
    'import_error': [
        'ModuleNotFoundError',
        'ImportError',
        'No module named',
    ],
}


# =============================================================================
# Tool-specific parsers
# =============================================================================


def _parse_mypy(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse mypy type-check output."""
    content = read_log_text(log_file)
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _MYPY_ERROR_PATTERN.finditer(content):
        file_path = match.group(1)
        line = int(match.group(2))
        message = match.group(3)
        category = categorize_issue(message, PYTHON_PATTERNS) or 'type_error'
        if category == 'other':
            category = 'type_error'

        add_issue_deduped(
            issues,
            seen,
            file=file_path,
            line=line,
            message=message,
            severity=SEVERITY_ERROR,
            category=category,
        )

    status = _detect_build_status_base(
        content,
        success_markers=['Success: no issues found'],
        failure_markers=['error:'],
        default='FAILURE' if issues else 'SUCCESS',
    )
    return issues, None, status


def _parse_ruff(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse ruff lint output."""
    content = read_log_text(log_file)
    issues: list[Issue] = []
    seen: set[str] = set()

    for match in _RUFF_ISSUE_PATTERN.finditer(content):
        file_path = match.group(1)
        line = int(match.group(2))
        message = f'{match.group(3)} {match.group(4)}'

        add_issue_deduped(
            issues,
            seen,
            file=file_path,
            line=line,
            message=message,
            severity=SEVERITY_ERROR,
            category='lint_error',
        )

    status = 'FAILURE' if issues else 'SUCCESS'
    return issues, None, status


def _parse_pytest(log_file: str) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse pytest test output.

    Extracts file locations from FAILED lines AND from collection/setup ERROR
    lines, and attempts to find line numbers from traceback context in the
    output. Both report characters are read because a run whose test modules
    failed to import produces only ERROR lines: reading FAILED alone would emit a
    red build with an empty `errors[]`, which tells triage nothing.
    """
    content = read_log_text(log_file)
    lines = content.split('\n')
    issues: list[Issue] = []
    seen: set[str] = set()

    # One record per FAILED line and per ERROR line, each carrying the
    # representative per-signature detail block (deduped so N failures sharing
    # one root cause share ONE block). The same record set backs the
    # `parse --failures-detail` slice verb.
    for record in _collect_pytest_records(content):
        if not add_issue_deduped(
            issues,
            seen,
            file=record['file'],
            line=record['line'],
            message=record['message'],
            severity=SEVERITY_ERROR,
            category=record['category'],
        ):
            continue
        # `detail` is the truncated presentation block; `signature` is the full,
        # un-truncated dedup identity (assertion type + normalized message +
        # failing frame). Keep them separate so failure dedup keys on the full
        # signature rather than the truncated detail (which could collapse
        # distinct root causes sharing a truncated prefix).
        issues[-1].detail = record['detail']
        issues[-1].signature = record['signature']

    # Attach stack traces to issues
    collect_stack_traces(lines, issues)

    test_summary = _extract_pytest_summary(content)

    status = _detect_build_status_base(
        content,
        success_markers=['passed'],
        failure_markers=['FAILED', 'error'],
        default='FAILURE' if issues else 'SUCCESS',
    )
    return issues, test_summary, status


def _find_pytest_line_number(block: str, file_path: str) -> int | None:
    """Extract a pytest failure's line number from its own traceback block.

    Scoped to the single resolved failure `block` (NOT the whole log): searching
    the entire log content would collapse every failure in one file onto the last
    `file.py:NN` occurrence, so multiple failures sharing a file all resolved to
    the same wrong line. Confining the search to the block that belongs to this
    FAILED line keeps each failure's line distinct. Looks for `file.py:NN:`
    frames and returns the last (deepest, closest to the failure point); falls
    back to None when the block carries no such frame.
    """
    # Pattern: file.py:NN: in test_name or file.py:NN: AssertionError
    escaped_file = re.escape(file_path)
    pattern = re.compile(rf'{escaped_file}:(\d+):')
    matches = list(pattern.finditer(block))
    if matches:
        # Return last match (closest to the actual failure point)
        return int(matches[-1].group(1))
    return None


def _extract_pytest_blocks(
    content: str,
    banner: re.Pattern[str],
    key_fn: Callable[[str], str],
) -> dict[str, list[str]]:
    """Map each block key to its ordered list of traceback blocks under `banner`.

    Scans the section opened by `banner`, splitting it into per-item blocks on
    the underscore-ruled `____ name ____` headers. A block runs until the next
    header or the next top-level `=== section ===` line (pytest's short test
    summary / final counts), which terminates the section. The FAILURES and
    ERRORS sections have identical structure, so both are read here; they differ
    only in their banner and in how a header maps onto a key (`key_fn`).

    The value is an ORDERED LIST, not a single block: when separate files or
    repeated pytest runs share a name, each occurrence produces its own block.
    Storing one block per key would overwrite the earlier occurrences and lose
    their distinct tracebacks/signatures. The record collectors consume one block
    per matching short-summary line, in order, to keep them distinct.

    Args:
        content: ANSI-stripped log content.
        banner: The section banner that opens the region to scan.
        key_fn: Maps a block header's name to the key its short-summary line
            resolves to.

    Returns:
        Dict mapping a normalized block key to the ordered list of stripped block
        texts for that key. Empty when the log carries no such section (e.g. a
        `--tb=no` or summary-only run) — callers then fall back to the terse
        short-summary message.
    """
    blocks: dict[str, list[str]] = {}
    in_section = False
    current_key: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_key is not None:
            blocks.setdefault(current_key, []).append('\n'.join(current_lines).strip())

    for raw in content.split('\n'):
        if banner.match(raw):
            in_section = True
            continue
        if not in_section:
            continue

        header = _PYTEST_BLOCK_HEADER.match(raw)
        if header:
            _flush()
            current_key = key_fn(header.group(1))
            current_lines = []
            continue

        if _PYTEST_SECTION_LINE.match(raw):
            # A new top-level `=== section ===` closes the section.
            _flush()
            current_key = None
            in_section = False
            continue

        if current_key is not None:
            current_lines.append(raw)

    _flush()

    return blocks


def _pytest_block_key(name: str) -> str:
    """Normalize a pytest test identifier to a block-lookup key.

    The FAILED line renders `file.py::TestClass::test_method`, while the
    FAILURES block header renders `TestClass.test_method`. Collapsing `::` to
    `.` aligns both spellings; parametrized `[param]` suffixes are preserved.
    """
    return name.replace('::', '.').strip()


def _pytest_error_block_key(name: str) -> str:
    """Normalize an ERRORS block header to the key its summary line resolves to.

    The ERRORS section headers and the `ERROR ...` short-summary lines name the
    same item differently, and the pairing has to hold in both spellings or the
    block is never found and the record degrades to its terse message:

    * `ERROR collecting test/foo.py` pairs with `ERROR test/foo.py` — the key is
      the file path, because a collection error names no test.
    * `ERROR at setup of test_x` pairs with `ERROR test/foo.py::test_x` — the key
      is the test id, normalized exactly as `_pytest_block_key` normalizes it.

    Any other header falls back to `_pytest_block_key` rather than being dropped.
    """
    collecting = _PYTEST_ERROR_HEADER_COLLECTING.match(name.strip())
    if collecting:
        return collecting.group(1)
    phase = _PYTEST_ERROR_HEADER_PHASE.match(name.strip())
    if phase:
        return _pytest_block_key(phase.group(1))
    return _pytest_block_key(name)


def _pytest_exception_message(block: str) -> str | None:
    """Return the raised exception's own first line from a traceback block.

    A FAILED short-summary line carries its message inline (`FAILED x - Boom`),
    but the collection-error spelling of an ERROR line — `ERROR <path>` — carries
    NO message tail at all. Reading the block's `E   ` gutter is what recovers it,
    and without it the record degrades to a restatement of the file name, which
    tells a triage consumer nothing it did not already have from `file`.

    Args:
        block: One traceback block from the FAILURES or ERRORS section.

    Returns:
        The first gutter line's text (e.g. ``AssertionError: bad state``), or
        ``None`` when the block carries no gutter (a `--tb=no` run, or the
        terse-message fallback standing in for an absent block).
    """
    match = _PYTEST_EXCEPTION_LINE.search(block)
    return match.group(1).strip() if match else None


def _pytest_failing_frame(block: str) -> str | None:
    """Return the deepest `path.py:NN` frame in a traceback block.

    pytest prints the originating frame as the final `path.py:NN: ExceptionType`
    line of a traceback, so the last match is the failure origin — identical
    across tests that share a root cause, which is what makes it a stable
    signature component.
    """
    # Isolate the traceback by discarding captured stdout/stderr/log sections.
    # Those `---`-ruled sections (e.g. `---- Captured stdout call ----`) do not
    # match `_PYTEST_SECTION_LINE` (which requires `=`-borders), so they remain
    # inside the block; a `foo.py:NN:`-shaped substring in captured output would
    # otherwise be mis-picked as the failing frame.
    traceback_part = block.split('\n---', 1)[0]
    matches = list(_PYTEST_FRAME_PATTERN.finditer(traceback_part))
    if not matches:
        return None
    last = matches[-1]
    return f'{last.group(1)}:{last.group(2)}'


def _pytest_failure_signature(message: str, frame: str) -> str:
    """Compute a dedup signature from assertion type + normalized message + frame.

    The signature collapses run-specific literals (hex addresses, quoted values,
    digit runs) so N failures sharing a single root cause map to ONE signature
    and therefore ONE captured detail block.
    """
    head = message.split(':', 1)[0].strip()
    assertion_type = head if _PYTEST_IDENTIFIER.fullmatch(head) else 'unknown'
    normalized = _PYTEST_HEX_ADDR.sub('0x#', message)
    normalized = _PYTEST_QUOTED.sub('#', normalized)
    normalized = _PYTEST_DIGIT_RUN.sub('#', normalized).strip().lower()
    return f'{assertion_type}|{normalized}|{frame}'


def _truncate_detail(block: str) -> str:
    """Bound a single detail block to `_MAX_DETAIL_LEN` characters."""
    if len(block) <= _MAX_DETAIL_LEN:
        return block
    return block[:_MAX_DETAIL_LEN] + '\n... (detail truncated)'


def _consume_pytest_block(
    key: str,
    blocks: dict[str, list[str]],
    cursors: dict[str, int],
    fallback: str,
) -> str:
    """Take the next unconsumed block for `key`, or `fallback` when none remains.

    The cursor is per-key so repeated names (across files or reruns) each keep
    their own block instead of all resolving to a single overwritten entry.
    """
    blocks_for_key = blocks.get(key, [])
    cursor = cursors.get(key, 0)
    if cursor >= len(blocks_for_key):
        return fallback
    cursors[key] = cursor + 1
    return blocks_for_key[cursor]


def _build_pytest_record(
    *,
    test: str,
    file_path: str,
    message: str,
    block: str,
    category: str,
    signature_details: dict[str, str],
) -> dict:
    """Assemble one parsed record, capturing its block once per signature.

    `signature_details` is threaded in (and mutated) so a representative
    traceback/assertion block is captured ONCE per unique failure signature and
    reused for every record sharing it — N failures with one root cause carry ONE
    block, not N copies.
    """
    line_num = _find_pytest_line_number(block, file_path)
    frame = _pytest_failing_frame(block) or f'{file_path}:{line_num}'
    signature = _pytest_failure_signature(message, frame)
    if signature not in signature_details:
        signature_details[signature] = _truncate_detail(block)

    return {
        'test': test,
        'file': file_path,
        'line': line_num,
        'message': message,
        'signature': signature,
        'detail': signature_details[signature],
        'category': category,
    }


def _collect_pytest_failure_records(content: str) -> list[dict]:
    """Collect one record per FAILED line, each with its per-signature block.

    Args:
        content: ANSI-stripped log content.

    Returns:
        A list of ``{test, file, line, message, signature, detail, category}``
        dicts in FAILED-line order.
    """
    failure_blocks = _extract_pytest_blocks(content, _PYTEST_FAILURES_BANNER, _pytest_block_key)
    block_cursors: dict[str, int] = {}
    signature_details: dict[str, str] = {}
    records: list[dict] = []

    for match in _PYTEST_FAILED_PATTERN.finditer(content):
        file_path = match.group(1)
        test_name = match.group(2)
        message = match.group(3) if match.group(3) else f'Test {test_name} failed'

        block = _consume_pytest_block(
            _pytest_block_key(test_name), failure_blocks, block_cursors, message
        )
        records.append(
            _build_pytest_record(
                test=test_name,
                file_path=file_path,
                message=message,
                block=block,
                category=CATEGORY_TEST_FAILURE,
                signature_details=signature_details,
            )
        )

    return records


def _collect_pytest_error_records(content: str) -> list[dict]:
    """Collect one record per ERROR line, each with its per-signature block.

    The counterpart to `_collect_pytest_failure_records` for pytest's `E` report
    character: a test module that raised while being COLLECTED, or a fixture that
    raised at setup/teardown. Such a run produces no FAILED line at all, so
    without this collector its `failures[]` is empty and a triage consumer learns
    nothing about what broke — which is the whole defect.

    A collection error names no test, so `test` falls back to the file path and
    the message falls back to naming the file rather than a test that does not
    exist.

    Args:
        content: ANSI-stripped log content.

    Returns:
        A list of ``{test, file, line, message, signature, detail, category}``
        dicts in ERROR-line order.
    """
    error_blocks = _extract_pytest_blocks(content, _PYTEST_ERRORS_BANNER, _pytest_error_block_key)
    block_cursors: dict[str, int] = {}
    signature_details: dict[str, str] = {}
    records: list[dict] = []

    for match in _PYTEST_ERROR_PATTERN.finditer(content):
        file_path = match.group(1)
        test_name = match.group(2)
        summary_message = match.group(3)
        if test_name:
            terse = f'Error in {test_name}'
        else:
            terse = f'Error collecting {file_path}'

        key = _pytest_block_key(test_name) if test_name else file_path
        block = _consume_pytest_block(key, error_blocks, block_cursors, terse)
        # Message precedence: the summary tail when pytest wrote one, then the
        # block's own `E   ` gutter, and only then the terse restatement of the
        # file name. The collection-error spelling always takes the middle rung —
        # it has no summary tail — so skipping it is what leaves a real
        # `AssertionError: ...` reported as `Error collecting <path>`.
        message = summary_message or _pytest_exception_message(block) or terse
        records.append(
            _build_pytest_record(
                test=test_name or file_path,
                file_path=file_path,
                message=message,
                block=block,
                category=CATEGORY_COLLECTION_ERROR,
                signature_details=signature_details,
            )
        )

    return records


def _collect_pytest_records(content: str) -> list[dict]:
    """Every reportable pytest record — the FAILED lines AND the ERROR lines.

    The single entry point shared by `_parse_pytest` (to build Issues) and the
    `parse` slice verb (`slice_failure_details`), so both surfaces report the
    same population and a collection error can never be visible to one and
    invisible to the other.
    """
    return _collect_pytest_failure_records(content) + _collect_pytest_error_records(content)


def _test_matches(record_test: str, query: str) -> bool:
    """Match a `--test <name>` query against a FAILED-line test identifier.

    The identifier renders as ``test_fn`` / ``TestClass::test_fn`` /
    ``test_fn[param]``. A query matches on exact equality, on the bare function
    name (class prefix + parametrization stripped), or as a suffix — so a leaf
    can pass either the short function name or the fully-qualified id.
    """
    if record_test == query:
        return True
    base = record_test.split('::')[-1].split('[')[0]
    return base == query or record_test.endswith(query)


def _dedup_records_by_signature(records: list[dict]) -> list[dict]:
    """Keep the first record for each unique failure signature."""
    seen: set[str] = set()
    deduped: list[dict] = []
    for record in records:
        if record['signature'] in seen:
            continue
        seen.add(record['signature'])
        deduped.append(record)
    return deduped


def _slice_record(record: dict) -> dict:
    """Project a failure record to the slice-output shape."""
    return {
        'test': record['test'],
        'file': record['file'],
        'line': record['line'],
        'detail': record['detail'],
    }


def slice_failure_details(
    log_file: str | Path,
    *,
    test_name: str | None = None,
    failures_detail: bool = False,
) -> dict:
    """Slice the per-signature traceback detail out of a build log.

    Backs the `parse --test <name>` / `parse --failures-detail` verb so a leaf
    can retrieve a named (or all) failing test's traceback without hand-scanning
    the raw log. Resolves against the C1 per-signature detail blocks captured by
    `_collect_pytest_records` — which covers pytest's ERROR lines as well as its
    FAILED lines, so a run whose test modules failed to import reports its real
    `total_failures` here instead of a zero over a demonstrably red build.

    Args:
        log_file: Path to the build log.
        test_name: When set, return only the failures whose test id matches
            (see `_test_matches`).
        failures_detail: When set (and `test_name` is None), return the
            deduped-by-signature set covering all failing tests.

    Returns:
        A result dict with ``status`` and a ``failures`` list of
        ``{test, file, line, detail}`` records (plus counts). ``status: error``
        with an ``error`` message when the log file is missing.
    """
    log_path = Path(log_file)
    if not log_path.exists():
        return {'status': 'error', 'error': f'Log file not found: {log_file}'}

    records = _collect_pytest_records(read_log_text(log_path))

    if test_name:
        matched = [r for r in records if _test_matches(r['test'], test_name)]
        return {
            'status': 'success',
            'test': test_name,
            'matched': len(matched),
            'failures': [_slice_record(r) for r in matched],
        }

    deduped = _dedup_records_by_signature(records)
    return {
        'status': 'success',
        'total_failures': len(records),
        'root_causes': len(deduped),
        'failures': [_slice_record(r) for r in deduped],
    }


# Independent per-count patterns for the pytest summary line. Each count is
# matched on its own so extraction is independent of the order in which pytest
# renders them (`N passed, M failed` vs `M failed, N passed`). Word boundaries
# keep `failed` / `passed` from matching inside `xfailed` / `xpassed`.
_PYTEST_SUMMARY_COUNTS: dict[str, re.Pattern[str]] = {
    'passed': re.compile(r'\b(\d+) passed\b'),
    'failed': re.compile(r'\b(\d+) failed\b'),
    'skipped': re.compile(r'\b(\d+) skipped\b'),
}

# Locates the actual pytest summary line before any count is extracted from
# it. pytest always renders the run duration (`in Ns`) on the summary line
# itself, so requiring that marker alongside a passed/failed/skipped keyword
# reliably isolates the summary line from unrelated log content (print
# statements, tracebacks, or other tool output) that could otherwise match the
# bare count patterns anywhere in the log and produce a false summary.
_PYTEST_SUMMARY_LINE_PATTERN = re.compile(
    r'^.*\b(?:passed|failed|skipped)\b.*\bin\s+[\d.]+s.*$',
    re.MULTILINE,
)

# Captures the run duration out of the `in Ns` marker the line pattern above
# already anchors on. Applied only to the resolved summary line, so it adds no
# line-location logic of its own.
_PYTEST_SUMMARY_DURATION_PATTERN = re.compile(r'\bin\s+(\d+(?:\.\d+)?)s')


def _extract_pytest_summary(content: str) -> UnitTestSummary | None:
    """Extract the pytest summary independent of count ordering.

    pytest renders its summary counts in a tool-determined order — a passing-
    dominant run shows `10308 passed, 1 failed` while a failing-dominant run can
    show `1 failed, 10308 passed`. To avoid false positives from unrelated log
    content that happens to contain `passed` / `failed` / `skipped` elsewhere,
    the actual summary line is located first (identified by its trailing
    `in Ns` duration marker) and each count is then matched only within that
    single line, so both count orderings still yield identical results.

    Args:
        content: Log file content (already ANSI-stripped by the caller).

    Returns:
        UnitTestSummary if a summary line with any of passed/failed/skipped is
        found, else None. ``duration_seconds`` carries the `in Ns` figure from
        the same resolved summary line when present.
    """
    summary_lines = _PYTEST_SUMMARY_LINE_PATTERN.findall(content)
    if not summary_lines:
        return None
    summary_line = summary_lines[-1]

    counts: dict[str, int] = {}
    for key, pattern in _PYTEST_SUMMARY_COUNTS.items():
        match = pattern.search(summary_line)
        if match:
            counts[key] = int(match.group(1))

    if not counts:
        return None

    passed = counts.get('passed', 0)
    failed = counts.get('failed', 0)
    skipped = counts.get('skipped', 0)
    duration_match = _PYTEST_SUMMARY_DURATION_PATTERN.search(summary_line)
    return UnitTestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=passed + failed + skipped,
        duration_seconds=float(duration_match.group(1)) if duration_match else None,
    )


# =============================================================================
# Content detection functions
# =============================================================================


def _has_mypy_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+: error:', content))


def _has_ruff_output(content: str) -> bool:
    return bool(re.search(r'\.py:\d+:\d+: [A-Z]+\d+', content))


def _has_pytest_output(content: str) -> bool:
    """Detect pytest output. Uses specific markers to avoid false positives."""
    # FAILED lines are definitive pytest markers
    if 'FAILED ' in content:
        return True
    # So are `ERROR <path>.py[::test]` short-summary lines. Without this, a run
    # pytest INTERRUPTED during collection routes to no parser at all: it emits
    # no FAILED line and its `N errors in Ns` summary carries neither `passed`
    # nor `failed`, so the fallback below misses it too and the whole ERROR
    # population is dropped before any of it can be parsed.
    if _PYTEST_ERROR_PATTERN.search(content):
        return True
    # pytest summary line uses '=' separators with pass/fail counts
    return '==' in content and ('passed' in content or 'failed' in content)


# =============================================================================
# Registry
# =============================================================================

_REGISTRY = ParserRegistry(
    [
        DetectionRule('mypy', ('mypy',), _has_mypy_output, _parse_mypy),
        DetectionRule('ruff', ('ruff',), _has_ruff_output, _parse_ruff),
        DetectionRule('pytest', ('pytest', 'test'), _has_pytest_output, _parse_pytest),
    ]
)


# =============================================================================
# Public API
# =============================================================================


def parse_log(log_file: str | Path) -> tuple[list[Issue], UnitTestSummary | None, str]:
    """Parse Python build log for errors.

    Handles output from mypy, ruff, and pytest using the shared
    ParserRegistry for detection and routing. When multiple tools
    are present in the output (common with pyprojectx verify),
    results from all matching parsers are combined.

    Args:
        log_file: Path to the log file.

    Returns:
        Tuple of (issues, test_summary, build_status)
    """
    # Python build output often contains output from multiple tools
    # (mypy + ruff + pytest in a single verify run), so we run all parsers
    # and combine results instead of using registry's single-match routing.
    return _REGISTRY.parse_multi(log_file)
