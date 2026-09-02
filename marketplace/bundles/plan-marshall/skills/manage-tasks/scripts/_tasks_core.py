#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared utilities for manage-tasks.py modular implementation.

Contains:
- JSON persistence utilities (storage format)
- TOON output formatting (LLM-optimized output)
- Task file operations
- Validation functions
"""

import json
import re
from pathlib import Path
from typing import Any, NamedTuple, NotRequired, TypedDict

from constants import (
    DIR_TASKS,
    VALID_SOURCE_EXTENSIONS,
    VALID_STEP_INTENTS,
    VALID_TASK_ORIGINS,
)
from file_ops import (  # noqa: F401 - re-exported
    get_plan_dir,
    normalize_to_repo_relative,
    now_utc_iso,
)
from input_validation import require_valid_plan_id  # noqa: F401 - re-exported
from toon_parser import (
    ToonParseError,
    classify_simple_array_line,
    list_item_min_indent,
    parse_toon,
    value_needs_quoting,
)

# =============================================================================
# Type definitions
# =============================================================================


class VerificationDict(TypedDict, total=False):
    commands: list[str]
    criteria: str
    manual: bool


class StepDict(TypedDict):
    number: int
    target: str
    status: str
    intent: str
    intent_override: NotRequired[list[dict[str, str]]]


class TaskDict(TypedDict, total=False):
    number: int
    title: str
    status: str
    domain: str | None
    profile: str | None
    origin: str
    description: str
    steps: list[StepDict]
    deliverable: int
    depends_on: list[str]
    skills: list[str]
    verification: VerificationDict
    current_step: int


# =============================================================================
# Constants
# =============================================================================

# Domains are arbitrary strings - defined in marshal.json, not hardcoded
# Profiles are arbitrary strings - defined in marshal.json per-domain, not hardcoded
VALID_ORIGINS = VALID_TASK_ORIGINS
VALID_FILE_EXTENSIONS = VALID_SOURCE_EXTENSIONS


# =============================================================================
# Basic utilities
# =============================================================================


def slugify(title: str, max_length: int = 40) -> str:
    """Convert title to kebab-case slug."""
    slug = title.lower().replace(' ', '-')
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug[:max_length]
    slug = slug.rstrip('-')
    return slug


# =============================================================================
# Validation functions
# =============================================================================


def validate_deliverable(deliverable_input) -> int:
    """Validate deliverable number. 0 for holistic tasks, >= 1 for deliverable-linked tasks."""
    if deliverable_input is None:
        raise ValueError('Deliverable is required')

    if isinstance(deliverable_input, int):
        if deliverable_input < 0:
            raise ValueError(f'Invalid deliverable number: {deliverable_input}. Must be non-negative integer.')
        return deliverable_input
    else:
        item_str = str(deliverable_input).strip()
        if item_str.isdigit():
            return int(item_str)
        else:
            raise ValueError(f'Invalid deliverable format: {item_str}. Expected non-negative integer.')


def validate_domain(domain: str) -> str:
    """Validate domain value (accepts any non-empty string).

    Domains are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not domain or not domain.strip():
        raise ValueError('Domain cannot be empty')
    return domain.strip()


def validate_profile(profile: str) -> str:
    """Validate profile value (accepts any non-empty string).

    Profiles are arbitrary keys in marshal.json. Validation happens
    at skill resolution time, not at task creation time.
    """
    if not profile or not profile.strip():
        raise ValueError('Profile cannot be empty')
    return profile.strip()


def validate_origin(origin: str) -> str:
    """Validate origin value."""
    if origin not in VALID_ORIGINS:
        raise ValueError(f'Invalid origin: {origin}. Must be one of: {", ".join(VALID_ORIGINS)}')
    return origin


def validate_step_intent(intent: str | None) -> str:
    """Validate a required per-step intent value.

    intent is REQUIRED (no None default): an absent/empty value is a schema
    violation, as is a value outside the closed VALID_STEP_INTENTS vocabulary.
    Accepts ``None`` only to surface the canonical "intent is required" error
    (callers commonly pass ``dict.get('intent')`` / ``getattr(args, 'intent')``).
    Returns the normalized (stripped) value on success.
    """
    if intent is None or not str(intent).strip():
        raise ValueError(
            'Step intent is required. Must be one of: ' + ', '.join(VALID_STEP_INTENTS)
        )
    normalized = str(intent).strip()
    if normalized not in VALID_STEP_INTENTS:
        raise ValueError(
            f'Invalid step intent: {normalized}. Must be one of: ' + ', '.join(VALID_STEP_INTENTS)
        )
    return normalized


def validate_skills(skills: list[str]) -> list[str]:
    """Validate skills list format (bundle:skill)."""
    if not skills:
        return []

    validated = []
    for skill in skills:
        skill = skill.strip()
        if not skill:
            continue
        if ':' not in skill:
            raise ValueError(f"Invalid skill format: {skill}. Must be in 'bundle:skill' format.")
        validated.append(skill)

    return validated


def validate_steps_are_file_paths(steps: list[str]) -> tuple[list[str], list[str]]:
    """Validate that steps are file paths, not descriptive text."""
    errors = []
    warnings = []

    for i, step in enumerate(steps, 1):
        step = step.strip()
        has_path_separator = '/' in step
        has_valid_extension = any(step.endswith(ext) for ext in VALID_FILE_EXTENSIONS)

        if not has_path_separator and not has_valid_extension:
            errors.append(
                f"Step {i}: '{step[:50]}...' is not a file path. "
                f"Steps MUST be file paths the deliverable declares (Affected files, Files expected to mutate, or Files to survey)."
            )
            continue

        descriptive_patterns = [
            'update ',
            'create ',
            'implement ',
            'add ',
            'fix ',
            'migrate ',
            'convert ',
            'modify ',
            'change ',
            'remove ',
            'delete ',
            ' to ',
            ' from ',
            ' with ',
            ' for ',
        ]
        step_lower = step.lower()
        for pattern in descriptive_patterns:
            if pattern in step_lower:
                warnings.append(f"Step {i}: '{step[:50]}' looks like descriptive text rather than a file path.")
                break

    return errors, warnings


def normalize_step_path(path: str) -> str:
    """Normalize absolute file paths to repo-relative paths.

    Delegates to file_ops.normalize_to_repo_relative().
    """
    return normalize_to_repo_relative(path)


# =============================================================================
# Dependency parsing
# =============================================================================


def parse_depends_on(depends_str: str) -> list[str]:
    """Parse depends_on field from TOON format."""
    if not depends_str or depends_str.strip().lower() == 'none':
        return []

    parts = [p.strip() for p in depends_str.split(',')]
    result = []
    for part in parts:
        if part.startswith('TASK-'):
            result.append(part)
        elif part.isdigit():
            result.append(f'TASK-{int(part)}')
    return result


def format_depends_on(deps: list[str]) -> str:
    """Format depends_on for file storage."""
    if not deps:
        return 'none'
    return ', '.join(deps)


# =============================================================================
# Task file operations
# =============================================================================


def get_tasks_dir(plan_id: str) -> Path:
    """Get the tasks directory for a plan."""
    return get_plan_dir(plan_id) / DIR_TASKS


def parse_task_file(content: str) -> dict[str, Any]:
    """Parse a task JSON file into a dictionary.

    Uses stdlib json for robust parsing.
    """
    task: dict[str, Any] = json.loads(content)

    # Ensure required fields have defaults
    if 'steps' not in task:
        task['steps'] = []
    if 'deliverable' not in task:
        task['deliverable'] = 0
    if 'depends_on' not in task:
        task['depends_on'] = []
    if 'skills' not in task:
        task['skills'] = []
    if 'verification' not in task:
        task['verification'] = {'commands': [], 'criteria': '', 'manual': False}
    if 'domain' not in task:
        task['domain'] = None
    if 'profile' not in task:
        task['profile'] = None
    if 'origin' not in task:
        task['origin'] = 'plan'

    return task


def format_task_file(task: dict) -> str:
    """Format a task dictionary as JSON file content.

    Uses stdlib json for robust serialization.
    """
    return json.dumps(task, indent=2, ensure_ascii=False)


def find_task_file(task_dir: Path, number: int) -> Path | None:
    """Find task file by number."""
    direct = task_dir / f'TASK-{number:03d}.json'
    return direct if direct.exists() else None


def get_next_number(task_dir: Path) -> int:
    """Get next available task number."""
    if not task_dir.exists():
        return 1

    max_num = 0
    for f in task_dir.glob('TASK-*.json'):
        try:
            num = int(f.name[5:8])
            max_num = max(max_num, num)
        except (ValueError, IndexError):
            pass

    return max_num + 1


def get_all_tasks(task_dir: Path) -> list:
    """Get all tasks sorted by number."""
    if not task_dir.exists():
        return []

    tasks = []
    for f in sorted(task_dir.glob('TASK-*.json')):
        content = f.read_text(encoding='utf-8')
        task = parse_task_file(content)
        tasks.append((f, task))

    return sorted(tasks, key=lambda x: x[1].get('number', 0))


def calculate_progress(task: dict) -> tuple[int, int]:
    """Calculate step completion progress."""
    steps = task.get('steps', [])
    completed = sum(1 for s in steps if s['status'] in ('done', 'skipped'))
    return completed, len(steps)


# =============================================================================
# Stdin parsing
# =============================================================================


# A TOON step item carries its required intent as a trailing parenthesized
# suffix: ``path/to/file.ext (write-new)``. The path group is non-greedy up to
# the final ``(intent)`` marker; the intent group is validated separately
# against VALID_STEP_INTENTS by validate_step_intent.
_STEP_INTENT_SUFFIX_RE = re.compile(r'^(?P<target>.+?)\s*\((?P<intent>[a-z-]+)\)\s*$')

#: List fields a task definition may carry. ``serialize_toon`` emits these in
#: the canonical length-declared form (``skills[2]:``), but a hand-written
#: definition commonly uses the bare YAML-style block header (``skills:``),
#: which the canonical parser reads as a nested object rather than a list.
#: ``_normalize_list_headers`` rewrites the bare form so one parser reads both.
#: Only the HEADER patterns live here. Which rows belong to a header once it is
#: found is not restated in this module — ``classify_simple_array_line`` in
#: ``plan-marshall:ref-toon-format`` is the one authority, so the rows this
#: module sees and the rows ``parse_toon`` reads are the same rows by
#: construction rather than by two rules agreeing.
_BARE_LIST_HEADER_RE = re.compile(r'^(?P<indent> *)(?P<key>steps|skills|commands):[ \t]*$')
_DECLARED_LIST_HEADER_RE = re.compile(r'^(?P<indent> *)(?P<key>steps|skills|commands)\[\d+\]:[ \t]*$')

#: Opens a TOON block scalar — a key whose whole value is the ``|`` marker, as in
#: ``description: |``. Everything indented beneath it is opaque PROSE that
#: ``toon_parser._parse_multiline_value`` consumes verbatim, never document
#: structure. A line inside such a body that happens to read ``steps:`` is a
#: sentence, so the list-header patterns above must not be tested against it.
_BLOCK_SCALAR_HEADER_RE = re.compile(r'^(?P<indent> *)[\w_-]+:[ \t]*\|[ \t]*$')

#: Top-level keys the task schema recognises. Anything else the canonical
#: parser returns is named on a validation failure rather than silently
#: discarded, so a mis-serialised field is attributable.
_KNOWN_TASK_KEYS = frozenset(
    {
        'title',
        'deliverable',
        'domain',
        'profile',
        'origin',
        'skills',
        'description',
        'steps',
        'depends_on',
        'verification',
    }
)


class _RawListItem(NamedTuple):
    """One raw list-item text plus the provenance of the header that opened it.

    The outer-quote guard cannot decide from an item's CONTENT alone whether its
    outer quote was the serializer's or a human's: an item the guard must accept
    (a real ``serialize_toon`` command, quoted because it embeds ``"``) and one it
    must reject are byte-for-byte the same SHAPE. The header form is the
    discriminator that content cannot supply, so it rides with each item.

    Provenance is per ITEM rather than per key because one document may open the
    same field name in both forms (a bare ``steps:`` block and a nested
    ``commands[1]:`` block), and collapsing them would let one header's form
    speak for the other's items.

    Attributes:
        text: The raw, still-quoted item text exactly as written.
        bare_header: True when the item was introduced by the bare YAML-style
            header ``key:``; False for the length-declared ``key[N]:`` form.
    """

    text: str
    bare_header: bool


def _copy_block_scalar_body(lines: list[str], start: int, header_indent: int, out: list[str]) -> int:
    """Copy a block scalar's body through untouched and report where it ends.

    The extent rule mirrors ``toon_parser._parse_multiline_value`` exactly, because
    a body this function walks past must be the same body the canonical parser
    later reads: the block runs while lines are blank or indented deeper than the
    ``key: |`` header, and closes at the first non-blank line indented at or
    outside it. Deriving the boundary a second way would let the two disagree
    about which lines are prose.

    Args:
        lines: The document's lines.
        start: Index of the first line after the block-scalar header.
        header_indent: Leading-space count of the ``key: |`` header line.
        out: Output accumulator; body lines are appended verbatim.

    Returns:
        Index of the first line past the block body.
    """
    i = start
    while i < len(lines):
        line = lines[i]
        if line.strip() and len(line) - len(line.lstrip()) <= header_indent:
            break
        out.append(line)
        i += 1
    return i


def _normalize_list_headers(content: str) -> tuple[str, dict[str, list[_RawListItem]]]:
    """Rewrite bare list-block headers to the canonical length-declared form.

    ``serialize_toon`` emits a list field as ``key[N]:`` followed by ``  - item``
    rows, and ``toon_parser.parse_toon`` reads exactly that shape. A hand-written
    task definition may instead open the list with the bare YAML-style header
    ``key:``, which the canonical parser reads as a nested object and yields no
    items for. Rewriting the bare header to ``key[N]:`` lets the one canonical
    parser read both shapes, so this module keeps no list reader of its own.

    The scan carries block-scalar state, so it only ever tests lines the canonical
    parser reads as document STRUCTURE. A ``description: |`` block's body is
    free-form prose, and a documented task description may legitimately contain an
    indented ``steps:`` line with ``- `` rows beneath it. Without that state such a
    line matches the bare-header pattern: its prose rows would be harvested into
    ``raw_items`` and put before the outer-quote guard, and the header itself would
    be rewritten to ``steps[N]:`` inside the user's own text. Block bodies are
    therefore copied through verbatim by ``_copy_block_scalar_body``.

    Which rows belong to a header is likewise NOT decided here: the body walk
    calls the canonical parser's own ``classify_simple_array_line`` under the
    boundary ``list_item_min_indent`` reports. A second, stricter rule here —
    "strictly deeper than the header" — silently disabled the outer-quote guard
    for every row the canonical parser admits at the header's own indent: a
    column-0 row under a top-level ``steps[1]:``, or an indent-2 row under a
    nested ``commands[1]:``. Those rows parsed, so the item reached the task
    record, but were never collected, so the guard never saw them. Deriving one
    boundary two ways is precisely what makes such a row visible to one reader
    and invisible to the other.

    Args:
        content: The raw TOON task definition.

    Returns:
        A tuple of the normalized content and a mapping from list-field key to
        the ``_RawListItem`` records found beneath it — each the RAW, still-quoted
        item text paired with whether its header was written in the bare form.
        Those raw texts are what the outer-quote guards inspect: ``parse_toon``
        unquotes values, so the quoting a caller actually wrote is observable only
        before parsing. The header form travels with them because it is the only
        signal that distinguishes serializer-produced quoting from hand-added
        quoting once the two have identical content — this function is where that
        distinction is observable, so discarding it here would lose it for good.

        The mapping carries every list key the header patterns match, ``skills``
        included, while ``_build_task_record`` guards only ``steps`` and
        ``verification.commands``. That is deliberate, not a dropped consumer:
        the items are collected for the ``key[N]:`` length rewrite regardless,
        and the guard is inapplicable to ``skills`` for the reason given at the
        guard call site.
    """
    lines = content.split('\n')
    raw_items: dict[str, list[_RawListItem]] = {}
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        block = _BLOCK_SCALAR_HEADER_RE.match(line)
        if block:
            out.append(line)
            i = _copy_block_scalar_body(lines, i + 1, len(block.group('indent')), out)
            continue

        bare = _BARE_LIST_HEADER_RE.match(line)
        header = bare or _DECLARED_LIST_HEADER_RE.match(line)
        if not header:
            out.append(line)
            i += 1
            continue

        key = header.group('key')
        header_indent = len(header.group('indent'))
        is_bare = bare is not None

        # Walk the header's body under the canonical parser's own membership rule.
        min_item_indent = list_item_min_indent(header_indent)
        items: list[_RawListItem] = []
        j = i + 1
        while j < len(lines):
            classified = classify_simple_array_line(lines[j], min_item_indent)
            if classified.kind == 'end':
                break
            if classified.kind == 'item':
                items.append(_RawListItem(classified.value.strip(), is_bare))
            j += 1

        raw_items.setdefault(key, []).extend(items)
        out.append(f'{header.group("indent")}{key}[{len(items)}]:' if bare and items else line)
        out.extend(lines[i + 1 : j])
        i = j

    return '\n'.join(out), raw_items


def _reject_hand_quoted_items(raw_items: list[_RawListItem], field_label: str) -> None:
    """Raise when a list item carries an outer double-quote a human added.

    An outer-quoted item is accepted ONLY when ``serialize_toon`` could have
    produced it — which takes two agreeing signals, because content alone cannot
    decide it. The item this guard must accept (a real serialized command, quoted
    because it embeds ``"``) and the item it must reject are structurally
    identical: outer-quoted, colon-bearing, escaped inner quotes. So the guard
    reads both the item and its header:

    - **Header provenance.** ``serialize_toon`` never emits a bare ``key:`` list
      header; it always writes the length-declared ``key[N]:`` form. An outer
      quote under a bare header therefore cannot be the serializer's, whatever
      the value contains, and is rejected outright.
    - **Value provenance.** Under a length-declared header the serializer is
      OBLIGED to wrap any value ``value_needs_quoting`` reports on — a skill
      notation containing ``:``, a command containing an embedded ``"``. Such a
      quote round-trips correctly and is accepted. A quote on a value that needed
      none is the hand-written anti-pattern, and is rejected. Consulting the
      serializer's own exported predicate keeps both sides of that decision in
      one place instead of re-deriving the rule here.

    The guard runs ahead of ``_coerce_steps`` so an illegal outer quote is named
    as an outer-quote violation, not misreported downstream as a missing intent
    marker — a rejection naming the wrong cause sends a caller to fix something
    already correct.

    Args:
        raw_items: The raw, still-quoted items for one list field, each paired
            with its header's form.
        field_label: Field name used in the message (``steps`` /
            ``verification.commands``).

    Raises:
        ValueError: When an item is wrapped in outer double-quotes that
            ``serialize_toon`` would not have produced.
    """
    for raw, bare_header in raw_items:
        if len(raw) < 2 or not (raw.startswith('"') and raw.endswith('"')):
            continue
        if not bare_header and value_needs_quoting(raw[1:-1].replace('\\"', '"')):
            continue
        raise ValueError(
            f'Task contract violation - {field_label} items must not be '
            f'wrapped in outer double-quotes: {raw!r}. Write list items without '
            f'outer quotes (inner double-quotes are allowed). See plan-marshall:phase-4-plan SKILL.md.'
        )


def _coerce_steps(raw_steps: Any) -> list[dict[str, str]]:
    """Normalize the parsed ``steps`` value to ``[{target, intent}, ...]``.

    Accepts both shapes the canonical parser produces: the simple-list form
    (``steps[N]:`` with ``path (intent)`` rows), where the intent rides as a
    parenthesized suffix, and the uniform-array form
    (``steps[N]{target,intent}:``) that ``serialize_toon`` emits for a stored
    task record, where target and intent are already separate columns.

    Args:
        raw_steps: The ``steps`` value as returned by ``parse_toon``.

    Returns:
        The normalized step list; empty when the field carried no rows.

    Raises:
        ValueError: When a simple-list row omits its required ``(intent)``
            marker, or an intent is outside the closed vocabulary.
    """
    if not isinstance(raw_steps, list):
        return []

    steps: list[dict[str, str]] = []
    for raw_step in raw_steps:
        if isinstance(raw_step, dict):
            target = str(raw_step.get('target') or '').strip()
            intent = validate_step_intent(raw_step.get('intent'))
        else:
            text = str(raw_step).strip()
            if not text:
                continue
            match = _STEP_INTENT_SUFFIX_RE.match(text)
            if not match:
                raise ValueError(
                    f"Task contract violation - step item '{text}' is missing its "
                    f'required intent marker. Each step MUST be written as '
                    f"'path (intent)' where intent is one of: "
                    + ', '.join(VALID_STEP_INTENTS)
                    + '. See plan-marshall:manage-tasks/standards/task-contract.md.'
                )
            target = match.group('target').strip()
            intent = validate_step_intent(match.group('intent'))
        normalized_target = normalize_step_path(target)
        if normalized_target:
            steps.append({'target': normalized_target, 'intent': intent})
    return steps


def _build_task_record(parsed: dict[str, Any], raw_items: dict[str, list[_RawListItem]]) -> dict[str, Any]:
    """Apply the task schema to a parsed TOON document.

    Structural parsing has already happened in the canonical parser; everything
    here is task-schema validation — the two outer-quote guards, the required
    fields, and the per-field validators.

    Args:
        parsed: The document as returned by ``parse_toon``.
        raw_items: Raw, still-quoted list items keyed by list field — each
            carrying its header's form — as collected by
            ``_normalize_list_headers``. The outer-quote guards run FIRST, ahead
            of ``_coerce_steps``, so an illegal quote is named as such rather
            than surfacing later as a missing intent marker.

    Returns:
        The normalized task record.

    Raises:
        ValueError: On any schema violation.
    """
    # ``skills`` is the third list field and is deliberately NOT guarded. The
    # guard's two conjuncts only discriminate where the value conjunct can come
    # out either way, and on ``skills`` it cannot: ``validate_skills`` requires a
    # ``:`` in every entry, and ``value_needs_quoting`` is True on ``:``, so every
    # legal skill is a value the serializer WOULD quote. The guard would collapse
    # to its header conjunct alone and reject ``skills:`` + ``- "bundle:skill"`` —
    # a hand-written form that quotes precisely because the notation carries a
    # colon, which is reasonable rather than an anti-pattern. On ``steps`` and
    # ``verification.commands`` the value conjunct does discriminate, so the guard
    # names an actual anti-pattern there.
    _reject_hand_quoted_items(raw_items.get('steps', []), 'steps')
    _reject_hand_quoted_items(raw_items.get('commands', []), 'verification.commands')

    title = str(parsed.get('title') or '').strip()
    domain_raw = str(parsed.get('domain') or '').strip()
    profile_raw = str(parsed.get('profile') or 'implementation').strip() or 'implementation'
    origin_raw = str(parsed.get('origin') or 'plan').strip() or 'plan'

    raw_verification = parsed.get('verification')
    if not isinstance(raw_verification, dict):
        raw_verification = {}
    manual_raw = raw_verification.get('manual', False)
    verification: dict[str, Any] = {
        'commands': [str(c) for c in (raw_verification.get('commands') or []) if str(c).strip()],
        'criteria': str(raw_verification.get('criteria') or ''),
        'manual': manual_raw is True or str(manual_raw).strip().lower() == 'true',
    }

    steps = _coerce_steps(parsed.get('steps'))

    depends_raw = parsed.get('depends_on') or ''
    depends_on = parse_depends_on(
        ', '.join(str(d) for d in depends_raw) if isinstance(depends_raw, list) else str(depends_raw)
    )

    raw_skills = parsed.get('skills')
    skills = [str(s).strip() for s in raw_skills if str(s).strip()] if isinstance(raw_skills, list) else []

    if not title:
        raise ValueError('Missing required field: title')

    deliverable_raw = parsed.get('deliverable', 0)
    if deliverable_raw is None or (isinstance(deliverable_raw, str) and not deliverable_raw.strip()):
        deliverable_raw = 0
    deliverable = validate_deliverable(deliverable_raw)
    if deliverable == 0 and origin_raw != 'holistic':
        raise ValueError('Missing required field: deliverable')
    if not domain_raw:
        raise ValueError('Missing required field: domain')
    if not steps:
        raise ValueError('Missing required field: steps (at least one step required)')

    domain = validate_domain(domain_raw)
    profile = validate_profile(profile_raw)
    validated_skills = validate_skills(skills)
    if origin_raw:
        validate_origin(origin_raw)

    if profile != 'verification':
        step_errors, _ = validate_steps_are_file_paths([s['target'] for s in steps])
        if step_errors:
            raise ValueError(
                'Task contract violation - steps must be file paths:\n'
                + '\n'.join(step_errors)
                + '\n\nContract reference: plan-marshall:manage-tasks/standards/task-contract.md'
            )

    return {
        'title': title,
        'deliverable': deliverable,
        'domain': domain,
        'profile': profile,
        'skills': validated_skills,
        'origin': origin_raw,
        'description': str(parsed.get('description') or ''),
        'steps': steps,
        'depends_on': depends_on,
        'verification': verification,
    }


def parse_stdin_task(stdin_content: str) -> dict[str, Any]:
    """Parse a task definition from its TOON representation.

    Structural parsing is delegated wholly to the canonical
    ``plan-marshall:ref-toon-format`` parser, so every shape that parser reads is
    accepted: the length-declared list ``skills[2]:``, the uniform array
    ``steps[2]{target,intent}:`` that ``serialize_toon`` emits for a stored task
    record, and — after header normalization — the bare block ``steps:``. So
    ``parse_stdin_task(serialize_toon(task))`` reproduces ``steps``, ``skills``
    and ``verification.commands`` without loss, and this module keeps no TOON
    reader of its own.

    The round trip is stated over those three fields, not over the whole record,
    because ``serialize_toon`` has no block-scalar emitter: a multi-line
    ``description`` is written as a quoted value containing a raw newline, which
    re-parses truncated. The scope here matches ``manage-tasks`` SKILL.md and
    ``test_parse_stdin_task_round_trips_serialize_toon_output`` exactly.

    Task-schema validation stays here: the required ``(intent)`` marker, the
    step file-path contract, the required-field checks, and the two deliberate
    outer-double-quote guards.

    Args:
        stdin_content: The TOON task definition.

    Returns:
        The normalized task record.

    Raises:
        ValueError: On any schema violation. When the input also carried keys
            the schema does not recognize, the message names them, so a
            mis-serialized field is reported instead of silently discarded. A
            successful parse stays silent about them.
    """
    normalized, raw_items = _normalize_list_headers(stdin_content)

    try:
        parsed = parse_toon(normalized)
    except ToonParseError as e:
        raise ValueError(f'Malformed TOON task definition: {e}') from e

    try:
        return _build_task_record(parsed, raw_items)
    except ValueError as e:
        unrecognized = sorted(k for k in parsed if k not in _KNOWN_TASK_KEYS)
        if unrecognized:
            raise ValueError(f'{e} Unrecognized field(s) in input: {", ".join(unrecognized)}.') from e
        raise


def output_error(message: str, error_code: str = 'error') -> dict:
    """Build error result dict."""
    return {'status': 'error', 'error': error_code, 'message': message}


def get_deliverable_context(deliverable: int) -> dict:
    """Get deliverable details for including in task context."""
    return {
        'deliverable': deliverable,
        'deliverable_source': f'See solution_outline.md section: ### {deliverable}.',
    }
