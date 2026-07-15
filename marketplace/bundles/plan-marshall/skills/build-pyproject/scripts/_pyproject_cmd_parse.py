#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parse functionality for Pyproject (Python/pyprojectx) build output.

Uses the shared ParserRegistry for consistent detection and routing.
Handles output from mypy, ruff, and pytest.

Usage (internal):
    from _pyproject_cmd_parse import parse_log
"""

import re
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

# Failure-detail capture (deliverable 9). pytest renders per-test tracebacks
# under a `=== FAILURES ===` banner, each test block headed by an
# underscore-ruled `____ test_name ____` line and terminated by the next such
# header or the next top-level `=== section ===` line (short-summary / counts).
_PYTEST_FAILURES_BANNER = re.compile(r'^=+ FAILURES =+\s*$')
_PYTEST_BLOCK_HEADER = re.compile(r'^_{3,}\s+(.+?)\s+_{3,}\s*$')
_PYTEST_SECTION_LINE = re.compile(r'^=+\s+\S.*\s+=+\s*$')
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

    Extracts file locations from FAILED lines and attempts to find line numbers
    from traceback context in the output.
    """
    content = read_log_text(log_file)
    lines = content.split('\n')
    issues: list[Issue] = []
    seen: set[str] = set()

    # One record per FAILED line, each carrying the representative per-signature
    # detail block (deduped so N failures sharing one root cause share ONE
    # block). The same record set backs the `parse --failures-detail` slice verb.
    for record in _collect_pytest_failure_records(content):
        if not add_issue_deduped(
            issues,
            seen,
            file=record['file'],
            line=record['line'],
            message=record['message'],
            severity=SEVERITY_ERROR,
            category='test_failure',
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


def _extract_pytest_failure_blocks(content: str) -> dict[str, list[str]]:
    """Map each failing test key to its ordered list of traceback blocks.

    Scans the `=== FAILURES ===` section, splitting it into per-test blocks on
    the underscore-ruled `____ test_name ____` headers. A block runs until the
    next header or the next top-level `=== section ===` line (pytest's short
    test summary / final counts), which terminates the FAILURES section.

    The value is an ORDERED LIST, not a single block: when separate files or
    repeated pytest runs share a test name, each occurrence produces its own
    block. Storing one block per key would overwrite the earlier occurrences and
    lose their distinct tracebacks/signatures. `_collect_pytest_failure_records`
    consumes one block per matching FAILED line, in order, to keep them distinct.

    Args:
        content: ANSI-stripped log content.

    Returns:
        Dict mapping a normalized block key (see `_pytest_block_key`) to the
        ordered list of stripped block texts for that key. Empty when the log
        carries no FAILURES section (e.g. a `--tb=no` or summary-only run) —
        callers then fall back to the terse FAILED-line message.
    """
    blocks: dict[str, list[str]] = {}
    in_failures = False
    current_key: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_key is not None:
            blocks.setdefault(current_key, []).append('\n'.join(current_lines).strip())

    for raw in content.split('\n'):
        if _PYTEST_FAILURES_BANNER.match(raw):
            in_failures = True
            continue
        if not in_failures:
            continue

        header = _PYTEST_BLOCK_HEADER.match(raw)
        if header:
            _flush()
            current_key = _pytest_block_key(header.group(1))
            current_lines = []
            continue

        if _PYTEST_SECTION_LINE.match(raw):
            # A new top-level `=== section ===` closes the FAILURES section.
            _flush()
            current_key = None
            in_failures = False
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


def _collect_pytest_failure_records(content: str) -> list[dict]:
    """Collect one record per FAILED line, each with its per-signature block.

    Shared by `_parse_pytest` (to set `Issue.detail`) and the `parse` slice
    verb (`slice_failure_details`). A representative traceback/assertion block is
    captured ONCE per unique failure signature (assertion type + normalized
    message + failing frame) and reused for every failure sharing that
    signature, so N failures with one root cause carry ONE block, not N copies.

    Args:
        content: ANSI-stripped log content.

    Returns:
        A list of ``{test, file, line, message, signature, detail}`` dicts in
        FAILED-line order.
    """
    failure_blocks = _extract_pytest_failure_blocks(content)
    # Per-key cursor: consume one block per matching FAILED line, in order, so
    # repeated test names (across files or reruns) each keep their own block
    # instead of all resolving to a single overwritten entry.
    block_cursors: dict[str, int] = {}
    signature_details: dict[str, str] = {}
    records: list[dict] = []

    for match in _PYTEST_FAILED_PATTERN.finditer(content):
        file_path = match.group(1)
        test_name = match.group(2)
        message = match.group(3) if match.group(3) else f'Test {test_name} failed'

        key = _pytest_block_key(test_name)
        blocks_for_key = failure_blocks.get(key, [])
        cursor = block_cursors.get(key, 0)
        if cursor < len(blocks_for_key):
            block = blocks_for_key[cursor]
            block_cursors[key] = cursor + 1
        else:
            block = message

        line_num = _find_pytest_line_number(block, file_path)
        frame = _pytest_failing_frame(block) or f'{file_path}:{line_num}'
        signature = _pytest_failure_signature(message, frame)
        if signature not in signature_details:
            signature_details[signature] = _truncate_detail(block)

        records.append(
            {
                'test': test_name,
                'file': file_path,
                'line': line_num,
                'message': message,
                'signature': signature,
                'detail': signature_details[signature],
            }
        )

    return records


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
    `_collect_pytest_failure_records`.

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

    records = _collect_pytest_failure_records(read_log_text(log_path))

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
        found, else None.
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
    return UnitTestSummary(
        passed=passed,
        failed=failed,
        skipped=skipped,
        total=passed + failed + skipped,
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
