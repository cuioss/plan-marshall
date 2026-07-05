#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Candidate detectors for self-review pre-submission surfacing.

Each ``_detect_*`` function scans the diff's added lines (and, where needed, the
worktree post-image) and returns a list of candidate dicts for the LLM
cognitive review pass to consume. Private helpers shared only among the
detectors live alongside them. Importers pull these by flat name (e.g.
``from _self_review_detectors import _detect_regexes``).
"""

import re
from pathlib import Path
from typing import Any

from _self_review_diff import (
    _read_post_image,
    _truncate,
)
from _self_review_patterns import (
    _ADD_ARGUMENT_FLAG,
    _ARGPARSE_FIELD,
    _CHECK_TRUE_KWARG,
    _CONSTANT_ASSIGN,
    _CONSUMER_GET_READ,
    _CONSUMER_SUBSCRIPT_READ,
    _COUNT_PROSE,
    _DEF_NAME,
    _DEF_OR_CLASS,
    _DEF_OR_CLASS_HEADER,
    _DEST_KWARG,
    _EXECUTE_SCRIPT_NOTATION,
    _FILE_IO_BOUNDARY,
    _FLAG_MEMBERSHIP_GUARD,
    _FLAG_STARTSWITH_GUARD,
    _FNMATCH_CALL,
    _FRONTMATTER_DESCRIPTION,
    _HELP_FIELD,
    _KEEP_MARKER,
    _MD_BULLET,
    _MD_HEADING,
    _MULTI_FORM_MARKER,
    _NORMALIZATION_TOKENS,
    _NORMATIVE_DIRECTIVE,
    _ORDERED_LIST_ITEM,
    _ORDINAL_NOUN_REFERENCE,
    _ORDINAL_PAREN_REFERENCE,
    _PAIR_TOKENS,
    _PRINT_CALL,
    _PRODUCER_SUBSCRIPT_ASSIGN,
    _RAISE_MESSAGE,
    _RAW_REGEX_LITERAL,
    _RE_CALL,
    _SUBPROCESS_BOUNDARY,
    _TOKENIZE,
    _TOON_FIELD_TOKEN,
    _TRIPLE_QUOTE,
    _TRY_OPENER,
)

# =============================================================================
# Detectors
# =============================================================================


def _detect_regexes(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for path, lineno, content in added:
        if not (path.endswith('.py') or path.endswith('.md')):
            continue
        for m in _RE_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _FNMATCH_CALL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
        for m in _RAW_REGEX_LITERAL.finditer(content):
            pattern = m.group(2)
            key = (path, lineno, pattern)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': path, 'line': lineno, 'pattern': _truncate(pattern, 120)})
    return out


def _detect_user_facing_strings(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev_def_or_class = False
    for path, lineno, content in added:
        if path.endswith('.md'):
            m_h = _MD_HEADING.match(content)
            if m_h is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_heading',
                        'text': _truncate(m_h.group(2), 200),
                    }
                )
                prev_def_or_class = False
                continue
            m_b = _MD_BULLET.match(content)
            if m_b is not None:
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'markdown_bullet',
                        'text': _truncate(m_b.group(1), 200),
                    }
                )
                prev_def_or_class = False
                continue
            prev_def_or_class = False
            continue
        if not path.endswith('.py'):
            prev_def_or_class = False
            continue
        if _DEF_OR_CLASS.match(content):
            prev_def_or_class = True
            continue
        if prev_def_or_class:
            m_t = _TRIPLE_QUOTE.match(content)
            if m_t is not None:
                tail = m_t.group(2)
                out.append(
                    {
                        'file': path,
                        'line': lineno,
                        'context': 'docstring',
                        'text': _truncate(tail, 200),
                    }
                )
                prev_def_or_class = False
                continue
        prev_def_or_class = False
        for m in _PRINT_CALL.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'print',
                    'text': _truncate(m.group(2), 200),
                }
            )
        for m in _ARGPARSE_FIELD.finditer(content):
            field = m.group(1)
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': f'argparse_{field}',
                    'text': _truncate(m.group(3), 200),
                }
            )
        for m in _RAISE_MESSAGE.finditer(content):
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'context': 'raise_message',
                    'text': _truncate(m.group(2), 200),
                }
            )
    return out


def _detect_markdown_sections(added: list[tuple[str, int, str]], project_dir: Path) -> list[dict[str, Any]]:
    """Emit one entry per added/edited heading, with sibling list (peer headings under same parent)."""
    md_files: dict[str, set[int]] = {}
    for path, lineno, content in added:
        if not path.endswith('.md'):
            continue
        if _MD_HEADING.match(content) is None:
            continue
        md_files.setdefault(path, set()).add(lineno)

    out: list[dict[str, Any]] = []
    for md_path, edited_lines in md_files.items():
        post_image = _read_post_image(project_dir, md_path)
        # Build a list of (line_no, depth, heading, parent_path) for every heading in the file.
        headings: list[dict[str, Any]] = []
        ancestor_stack: list[tuple[int, str]] = []  # (depth, heading)
        for idx, line in enumerate(post_image, start=1):
            m = _MD_HEADING.match(line)
            if m is None:
                continue
            depth = len(m.group(1))
            text = m.group(2)
            while ancestor_stack and ancestor_stack[-1][0] >= depth:
                ancestor_stack.pop()
            parent = ancestor_stack[-1][1] if ancestor_stack else ''
            headings.append({'line': idx, 'depth': depth, 'heading': text, 'parent': parent})
            ancestor_stack.append((depth, text))
        # For each edited heading, gather siblings under same parent at same depth.
        for h in headings:
            if h['line'] not in edited_lines:
                continue
            siblings = [
                other['heading']
                for other in headings
                if other is not h and other['depth'] == h['depth'] and other['parent'] == h['parent']
            ]
            out.append(
                {
                    'file': md_path,
                    'line': h['line'],
                    'heading': _truncate(h['heading'], 120),
                    'siblings': '; '.join(_truncate(s, 80) for s in siblings),
                }
            )
    return out


_FENCED_SCHEMA_BLOCK = re.compile(r'^```(json|toon)\b', re.MULTILINE)


def _find_skill_dir(modified_path: Path, project_dir: Path) -> Path | None:
    """Walk up from a modified file looking for a directory that contains SKILL.md.

    Returns the skill directory or None when the modified file is not nested
    inside a skill. The walk is bounded by ``project_dir`` so we never escape
    the worktree.
    """
    current = modified_path.parent if modified_path.is_file() else modified_path
    while True:
        try:
            current.relative_to(project_dir)
        except ValueError:
            return None
        if (current / 'SKILL.md').is_file():
            return current
        if current == project_dir or current.parent == current:
            return None
        current = current.parent


def _collect_skill_contract_sources(skill_dir: Path) -> list[Path]:
    """Return SKILL.md plus every standards/*.md inside the skill directory."""
    sources: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        sources.append(skill_md)
    standards_dir = skill_dir / 'standards'
    if standards_dir.is_dir():
        sources.extend(sorted(standards_dir.glob('*.md')))
    return sources


def _collect_schema_bearing_within_radius(
    modified_path: Path, project_dir: Path, radius: int
) -> list[tuple[Path, str]]:
    """Find *.md files reachable within ``radius`` directory levels of the
    modified file whose content contains a fenced JSON or TOON block.

    Walks up at most ``radius`` parents from the modified file's parent
    directory (bounded by ``project_dir``) to choose an anchor, then
    recursively collects every *.md file in the anchor's subtree. ``radius=0``
    restricts the scan to the modified file's own parent directory only.

    Returns a list of (path, format) tuples where format is 'json' or 'toon'.
    """
    if not modified_path.is_file():
        return []
    anchor = modified_path.parent
    for _ in range(radius):
        if anchor == project_dir or anchor.parent == anchor:
            break
        try:
            anchor.parent.relative_to(project_dir)
        except ValueError:
            break
        anchor = anchor.parent

    out: list[tuple[Path, str]] = []
    try:
        if radius == 0:
            md_iter = sorted(anchor.glob('*.md'))
        else:
            md_iter = sorted(anchor.rglob('*.md'))
    except OSError:
        return []

    for md in md_iter:
        try:
            text = md.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        m = _FENCED_SCHEMA_BLOCK.search(text)
        if m is not None:
            out.append((md, m.group(1)))
    return out


def _doc_referenced_skill_sources(
    md_added: list[tuple[int, str]], project_dir: Path
) -> list[str]:
    """Return repo-relative SKILL.md paths referenced by a doc's added lines.

    A doc *references* a sibling script's output contract when its added lines
    contain BOTH an ``execute-script.py`` invocation via ``{bundle}:{skill}:{script}``
    notation AND a TOON-field reference (a ``{field}`` interpolation token such as
    ``{status}`` or ``{error}``). The two signals need not appear on the same
    added line — the doc as a whole (its added hunk content) must satisfy both.

    For each distinct ``{bundle}:{skill}`` notation found, the referenced
    script's ``SKILL.md`` resolves to
    ``marketplace/bundles/{bundle}/skills/{skill}/SKILL.md``. A path is emitted
    only when that ``SKILL.md`` exists on disk under ``project_dir`` (a dangling
    notation surfaces nothing). The returned list is sorted and deduplicated.
    """
    has_toon_field = any(_TOON_FIELD_TOKEN.search(content) for _, content in md_added)
    if not has_toon_field:
        return []

    rel_sources: set[str] = set()
    for _, content in md_added:
        for m in _EXECUTE_SCRIPT_NOTATION.finditer(content):
            bundle, skill = m.group(1), m.group(2)
            rel = f'marketplace/bundles/{bundle}/skills/{skill}/SKILL.md'
            if (project_dir / rel).is_file():
                rel_sources.add(rel)
    return sorted(rel_sources)


def _detect_contract_sources(
    modified_files: list[str],
    project_dir: Path,
    radius: int,
    added: list[tuple[str, int, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (contract_sources, schema_bearing_files).

    ``contract_sources``: one entry per modified file that has any contract
    source. Sources come from two unioned origins:

    * **directory-structural** — when the modified file is nested inside a skill
      directory, every SKILL.md and standards/*.md in that skill;
    * **doc-prose script reference** (``.md`` files only) — when the doc's added
      lines reference a sibling script's output contract (an
      ``execute-script.py`` invocation via ``{bundle}:{skill}:{script}`` notation
      AND a TOON-field token such as ``{status}``), the referenced script's
      SKILL.md. See ``_doc_referenced_skill_sources``.

    The ``sources`` field is a ``; ``-joined, sorted, deduplicated string of the
    unioned repo-relative paths.

    ``schema_bearing_files``: a flat, deduplicated list of *.md files within
    ``radius`` directory levels of any modified file whose content contains a
    fenced JSON or TOON block. Entries reflect the dominant fence format.
    """
    contract_entries: list[dict[str, Any]] = []
    schema_seen: dict[Path, str] = {}

    # Group added lines by modified .md file so each doc's reference scan sees
    # only its own added hunk content. When ``added`` is None (callers that do
    # not pass diff content), the content-aware augmentation is simply inert.
    md_added_by_file: dict[str, list[tuple[int, str]]] = {}
    for added_path, added_lineno, added_content in added or []:
        if added_path.endswith('.md'):
            md_added_by_file.setdefault(added_path, []).append((added_lineno, added_content))

    for rel in modified_files:
        modified_path = (project_dir / rel).resolve()
        try:
            modified_path.relative_to(project_dir)
        except ValueError:
            continue

        union_sources: set[str] = set()

        skill_dir = _find_skill_dir(modified_path, project_dir)
        if skill_dir is not None:
            structural = _collect_skill_contract_sources(skill_dir)
            union_sources.update(str(p.relative_to(project_dir)) for p in structural)

        if rel.endswith('.md'):
            union_sources.update(
                _doc_referenced_skill_sources(md_added_by_file.get(rel, []), project_dir)
            )

        if union_sources:
            contract_entries.append(
                {
                    'file': rel,
                    'sources': '; '.join(sorted(union_sources)),
                }
            )

        for path, fmt in _collect_schema_bearing_within_radius(modified_path, project_dir, radius):
            schema_seen.setdefault(path, fmt)

    schema_entries = [
        {'file': str(p.relative_to(project_dir)), 'format': fmt} for p, fmt in sorted(schema_seen.items())
    ]
    return contract_entries, schema_entries


def _detect_keep_markers(
    added: list[tuple[str, int, str]], project_dir: Path
) -> tuple[list[dict[str, Any]], list[str]]:
    """Scan added lines for ``<!-- self-review: keep <id> -->`` markers.

    Returns ``(candidates, protected_identifiers)``:

    - ``candidates``: one entry per recognized marker. Each entry carries
      ``identifier``, ``file``, ``line``, and ``kind``. ``kind`` is
      ``keep_protected`` when the identifier is still grep-able in the
      file's post-image (outside the marker line itself), or
      ``keep_violation`` when the consolidation removed the protected
      token and the marker is now orphaned.
    - ``protected_identifiers``: the deduplicated, sorted set of every
      identifier whose marker resolved to ``keep_protected``. The LLM
      cognitive review consumes this list to refuse consolidations that
      drop a protected token.

    The marker line itself is excluded from the grep-ability check, so the
    marker token's presence in its own comment never counts as evidence
    that the protected identifier still exists.
    """
    # Group markers by file so each post-image is read at most once.
    by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        for m in _KEEP_MARKER.finditer(content):
            identifier = m.group(1)
            by_file.setdefault(path, []).append((lineno, identifier))

    candidates: list[dict[str, Any]] = []
    protected: set[str] = set()

    for path, markers in by_file.items():
        post_image = _read_post_image(project_dir, path)
        # Exclude ALL lines containing a keep marker so no marker comment's
        # own copy of the identifier (whether added in this diff or pre-existing)
        # can mask a removal.  Using line-number exclusion was insufficient
        # because it only covered markers added in the current diff, not
        # pre-existing markers that also carry the identifier text.
        non_marker_lines = [
            line
            for line in post_image
            if not _KEEP_MARKER.search(line)
        ]
        non_marker_blob = '\n'.join(non_marker_lines)

        for lineno, identifier in markers:
            # Use word-boundary guards to avoid false-positive substring matches
            # (e.g. identifier 'body' matching inside 'nobody' or 'method_body').
            pattern = re.compile(
                r'(?<![a-zA-Z0-9_-])' + re.escape(identifier) + r'(?![a-zA-Z0-9_-])'
            )
            still_present = bool(pattern.search(non_marker_blob))
            kind = 'keep_protected' if still_present else 'keep_violation'
            candidates.append(
                {
                    'file': path,
                    'line': lineno,
                    'identifier': identifier,
                    'kind': kind,
                }
            )
            if still_present:
                protected.add(identifier)

    return candidates, sorted(protected)


def _load_test_tree_blob(project_dir: Path) -> str:
    """Read every ``*.py`` file under ``{project_dir}/test`` once and return a
    single newline-joined blob of their contents.

    This is the read-once index that lets ``_symmetric_pair_has_test`` answer
    repeated membership queries without re-walking the test tree or re-reading
    files per call. A missing ``test/`` directory, a walk failure, or an
    unreadable file contributes nothing — the corresponding content is simply
    absent from the blob, preserving the original per-file fail-soft behaviour.
    The scan is read-only and stdlib-only.
    """
    test_root = project_dir / 'test'
    if not test_root.is_dir():
        return ''
    try:
        test_files = sorted(test_root.rglob('*.py'))
    except OSError:
        return ''
    chunks: list[str] = []
    for test_file in test_files:
        try:
            chunks.append(test_file.read_text(encoding='utf-8', errors='replace'))
        except OSError:
            continue
    return '\n'.join(chunks)


def _name_in_test_blob(name: str, test_blob: str) -> bool:
    """Return True when ``name`` occurs in ``test_blob`` on a word boundary.

    The word-boundary guard mirrors the identifier-first discipline used by
    ``_detect_keep_markers``: the same ``(?<![a-zA-Z0-9_-])`` /
    ``(?![a-zA-Z0-9_-])`` lookarounds avoid false-positive substring hits
    (e.g. ``save_state`` matching inside ``save_state_v2``). An empty blob
    (missing test tree, unreadable files, or no test sources) yields ``False``.
    """
    if not test_blob:
        return False
    pattern = re.compile(
        r'(?<![a-zA-Z0-9_-])' + re.escape(name) + r'(?![a-zA-Z0-9_-])'
    )
    return bool(pattern.search(test_blob))


def _symmetric_pair_has_test(name: str, project_dir: Path) -> bool:
    """Return True when the worktree's ``test/`` tree references ``name``.

    Searches every ``*.py`` file under ``{project_dir}/test`` for a
    word-boundary occurrence of the function name. ``test_present=false`` is
    the Tier-2 missing-test signal; a missing ``test/`` directory, an
    unreadable file, or no match yields ``False``. The scan is read-only and
    stdlib-only.

    This is the single-query entry point. It builds the test-tree blob via
    ``_load_test_tree_blob`` and delegates the word-boundary match to
    ``_name_in_test_blob``. Hot paths that issue many membership queries
    (e.g. ``_detect_symmetric_pairs``) MUST build the blob once via
    ``_load_test_tree_blob`` and call ``_name_in_test_blob`` directly to
    avoid re-reading the test tree per call.
    """
    return _name_in_test_blob(name, _load_test_tree_blob(project_dir))


def _detect_symmetric_pairs(added: list[tuple[str, int, str]], project_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Build the test-tree blob once for the whole detection pass so each
    # candidate's test_present query is an in-memory regex search rather than
    # a fresh O(M) walk + read of the test tree (eliminates the O(N*M) disk
    # I/O that re-reading per candidate would cause).
    test_blob = _load_test_tree_blob(project_dir)
    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _DEF_NAME.match(content)
        if m is None:
            continue
        name = m.group(1)
        parts = name.split('_')
        partner_name: str | None = None
        for tok_a, tok_b in _PAIR_TOKENS:
            if tok_a in parts:
                idx = parts.index(tok_a)
                swapped = list(parts)
                swapped[idx] = tok_b
                partner_name = '_'.join(swapped)
                break
            if tok_b in parts:
                idx = parts.index(tok_b)
                swapped = list(parts)
                swapped[idx] = tok_a
                partner_name = '_'.join(swapped)
                break
        if partner_name is None:
            continue
        out.append(
            {
                'file': path,
                'line': lineno,
                'name': name,
                'partner': partner_name,
                'test_present': _name_in_test_blob(name, test_blob),
            }
        )
    return out


def _detect_flag_guard_pairs(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect argument-presence guards over a ``--flag`` token and classify the
    flag *forms* each guard covers.

    Scans added ``.py`` lines for membership/substring guards
    (``'--flag' in args``) and ``startswith`` guards
    (``arg.startswith('--flag')``). The bare ``--flag`` token guards the
    space-separated form (``--flag value``); the ``--flag=`` prefix guards the
    equals form (``--flag=value``).

    Aggregates per ``(file, flag)``: when a flag is guarded only by its bare
    token the coverage is ``space``; only by its ``--flag=`` prefix it is
    ``equals``; when both appear in the same file it is ``both``. The ``line``
    field records the first guard occurrence for the flag in the file. The
    aggregation is what lets the cognitive review compare form coverage across
    two sibling guards in the same change — a ``both``/single-form asymmetry is
    the flag-form-coverage defect class.
    """
    # Per (file, flag): track covered forms and the first occurrence line.
    coverage: dict[tuple[str, str], set[str]] = {}
    first_line: dict[tuple[str, str], int] = {}
    order: list[tuple[str, str]] = []

    def _record(path: str, lineno: int, flag: str, has_equals: bool) -> None:
        key = (path, flag)
        if key not in coverage:
            coverage[key] = set()
            first_line[key] = lineno
            order.append(key)
        coverage[key].add('equals' if has_equals else 'space')

    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        for m in _FLAG_MEMBERSHIP_GUARD.finditer(content):
            _record(path, lineno, m.group(2), bool(m.group(3)))
        for m in _FLAG_STARTSWITH_GUARD.finditer(content):
            _record(path, lineno, m.group(2), bool(m.group(3)))

    out: list[dict[str, Any]] = []
    for key in order:
        forms = coverage[key]
        if forms == {'space', 'equals'}:
            forms_covered = 'both'
        elif forms == {'equals'}:
            forms_covered = 'equals'
        else:
            forms_covered = 'space'
        path, flag = key
        out.append(
            {
                'file': path,
                'line': first_line[key],
                'flag': flag,
                'forms_covered': forms_covered,
            }
        )
    return out


def _detect_producer_consumer(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect produced output keys that have no consumer in the same diff.

    A *producer* is a subscript assignment into an output dict
    (``output['key'] = ...``) in an added ``.py`` line. A *consumer* is any
    added ``.py`` line that READS that key back — a subscript read
    (``foo['key']`` that is NOT itself a producer assignment) or a
    ``.get('key')`` call. For each produced key with no consumer anywhere in
    the added lines the detector emits a candidate so the cognitive review can
    decide whether the dangling producer is a real defect (a value emitted but
    never read by any downstream branch).

    Each entry carries ``file``, ``line`` (the producer line), ``key``, and
    ``consumed`` (always ``false`` for an emitted candidate — only unconsumed
    producers are surfaced). The ``consumed`` field keeps the entry shape
    self-describing for the LLM consumer.
    """
    # Collect every produced key (first producer line wins) and every consumed
    # key across the whole added-line set. A key produced in one file and
    # consumed in another still counts as consumed — the producer-consumer
    # relation is diff-global, not per-file.
    produced: dict[str, tuple[str, int]] = {}
    for path, lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _PRODUCER_SUBSCRIPT_ASSIGN.match(content)
        if m is not None:
            key = m.group(2)
            produced.setdefault(key, (path, lineno))

    consumed: set[str] = set()
    for path, _lineno, content in added:
        if not path.endswith('.py'):
            continue
        # A producer line is not its own consumer: the LHS subscript on a
        # producer line (``output['k'] = ...``) must not register ``k`` as
        # consumed. Resolve the producer's own key once, then skip exactly that
        # key on the producer line — any OTHER key read on the same line still
        # counts as a consumption.
        producer_match = _PRODUCER_SUBSCRIPT_ASSIGN.match(content)
        producer_key = producer_match.group(2) if producer_match is not None else None
        for m in _CONSUMER_SUBSCRIPT_READ.finditer(content):
            read_key = m.group(2)
            if read_key == producer_key:
                continue
            consumed.add(read_key)
        for m in _CONSUMER_GET_READ.finditer(content):
            consumed.add(m.group(2))

    out: list[dict[str, Any]] = []
    for key in sorted(produced):
        if key in consumed:
            continue
        path, lineno = produced[key]
        out.append({'file': path, 'line': lineno, 'key': key, 'consumed': False})
    return out


def _detect_source_of_truth(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect a constant duplicated across two diff files with divergent values.

    Scans added ``.py`` lines for ``NAME = <literal>`` bindings where ``NAME``
    is an UPPER_SNAKE_CASE identifier (the conventional source-of-truth
    constant shape). When the SAME constant name is assigned in two or more
    distinct files within the diff AND the assigned literals are NOT all
    identical, the duplicate is a source-of-truth drift candidate — the diff
    changed the value in one declared SoT location but not the other.

    Each entry carries ``name`` (the constant), ``files`` (a ``; ``-joined,
    sorted list of the files declaring it), and ``values`` (a ``; ``-joined,
    sorted list of the distinct literal RHS values). Only constants with a
    cross-file value divergence are surfaced; a constant assigned the same
    value in two files, or a constant in a single file, is not a defect.
    """
    # Per constant name: map file -> set of literal RHS values declared there.
    by_name: dict[str, dict[str, set[str]]] = {}
    for path, _lineno, content in added:
        if not path.endswith('.py'):
            continue
        m = _CONSTANT_ASSIGN.match(content)
        if m is None:
            continue
        name = m.group(1)
        value = m.group(2)
        by_name.setdefault(name, {}).setdefault(path, set()).add(value)

    out: list[dict[str, Any]] = []
    for name in sorted(by_name):
        files = by_name[name]
        if len(files) < 2:
            continue
        all_values: set[str] = set()
        for value_set in files.values():
            all_values.update(value_set)
        if len(all_values) < 2:
            continue
        out.append(
            {
                'name': name,
                'files': '; '.join(sorted(files)),
                'values': '; '.join(_truncate(v, 80) for v in sorted(all_values)),
            }
        )
    return out


def _detect_same_document_consistency(added: list[tuple[str, int, str]]) -> list[dict[str, Any]]:
    """Detect added normative directives in a ``.md`` body for contradiction review.

    Scans added ``.md`` lines for RFC-2119-style normative keywords (``MUST``,
    ``MUST NOT``, ``SHALL``, ``SHALL NOT``, ``NEVER``, ``ALWAYS``, ``REQUIRED``,
    ``FORBIDDEN``). Each added normative directive is surfaced so the cognitive
    review can compare it against sibling directives ALREADY in the same
    document — a new normative rule that contradicts an existing one in the
    same file is the same-document-consistency defect (Mode 2: the surface MUST
    carry a candidate, never an empty surface, when a normative line is added).

    Each entry carries ``file``, ``line``, ``keyword`` (the normative keyword
    that fired), and ``text`` (the directive line, truncated).
    """
    out: list[dict[str, Any]] = []
    for path, lineno, content in added:
        if not path.endswith('.md'):
            continue
        m = _NORMATIVE_DIRECTIVE.search(content)
        if m is None:
            continue
        out.append(
            {
                'file': path,
                'line': lineno,
                'keyword': m.group(1),
                'text': _truncate(content.strip(), 200),
            }
        )
    return out


def _detect_description_vs_body(
    added: list[tuple[str, int, str]], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect a ``.md`` whose frontmatter description and body both changed.

    A frontmatter ``description:`` (or ``summary:``) line summarizes the
    document's model; the body implements it. When the diff touches a ``.md``
    file's body AND that file carries a frontmatter ``description``/``summary``
    key in its post-image, the description may now describe a model the body no
    longer implements (Mode 1 recurrence — the phase-3 frontmatter case where a
    deleted machinery left a stale description behind).

    The detector surfaces one candidate per modified ``.md`` file that (a) has
    at least one added body line (any added line below the closing frontmatter
    delimiter) AND (b) carries a frontmatter ``description``/``summary`` key in
    its post-image. The entry carries ``file``, ``line`` (the frontmatter
    description line in the post-image), ``key`` (``description`` or
    ``summary``), and ``description`` (the description value, truncated) so the
    cognitive review can read the description against the changed body.
    """
    # Group added lines per .md file.
    md_added_files: dict[str, list[int]] = {}
    for path, lineno, _content in added:
        if path.endswith('.md'):
            md_added_files.setdefault(path, []).append(lineno)

    out: list[dict[str, Any]] = []
    for md_path in sorted(md_added_files):
        post_image = _read_post_image(project_dir, md_path)
        if not post_image:
            continue
        # Resolve the frontmatter block: it opens with a ``---`` on line 1 and
        # closes at the next ``---``. The description key must live inside it.
        if not post_image or post_image[0].strip() != '---':
            continue
        fm_close = None
        for idx in range(1, len(post_image)):
            if post_image[idx].strip() == '---':
                fm_close = idx
                break
        if fm_close is None:
            continue
        desc_line_no: int | None = None
        desc_key: str | None = None
        desc_value: str | None = None
        for idx in range(1, fm_close):
            m = _FRONTMATTER_DESCRIPTION.match(post_image[idx])
            if m is not None:
                desc_line_no = idx + 1  # 1-based
                desc_key = m.group(1)
                desc_value = m.group(2)
                break
        if desc_line_no is None or desc_key is None or desc_value is None:
            continue
        # Require at least one added line in the document body (below the
        # closing frontmatter delimiter) — a pure frontmatter-only edit does
        # not surface a body-vs-description candidate.
        body_close_line = fm_close + 1  # 1-based line number of the closing ---
        has_body_edit = any(ln > body_close_line for ln in md_added_files[md_path])
        if not has_body_edit:
            continue
        out.append(
            {
                'file': md_path,
                'line': desc_line_no,
                'key': desc_key,
                'description': _truncate(desc_value, 200),
            }
        )
    return out


def _detect_unguarded_boundaries(
    added: list[tuple[str, int, str]], project_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Detect an added subprocess/file-I/O boundary call with no guard (Facet 1).

    Scans added ``.py`` lines for a boundary call and surfaces it when BOTH
    hold:

    1. the call is unguarded — for a ``subprocess.*`` call, ``check=True`` is
       absent on the same line; a file-I/O call (``open(``,
       ``Path.read_text``/``write_text``/``read_bytes``/``write_bytes``) is
       always treated as unguarded by criterion 1 since it has no ``check``
       kwarg; AND
    2. there is no enclosing ``try`` block in the same function — tracked by a
       per-file walk that opens an "inside try" window at a ``try:`` opener and
       closes it at the next def/class header.

    When ``project_dir`` is provided the function reads the full post-image of
    each changed ``.py`` file and walks every line to build accurate
    try-block / function-boundary state.  This ensures that pre-existing
    ``try`` blocks and ``def``/``class`` headers — which are absent from the
    diff's ``added`` lines — are correctly accounted for.  When the file is not
    present on disk (e.g. in unit tests without a ``project_dir``), the
    function falls back to scanning only the ``added`` lines, which preserves
    the original behaviour for test scenarios.

    Network calls (``socket.``, ``urllib.``, ``http.client.``) are out of scope
    and never matched (their absence from the boundary regexes is the exclusion).
    The existing sibling-envelope unguarded-pair detection is a separate concern
    and is not re-implemented here.

    Each entry carries ``file``, ``line``, ``boundary`` (the matched call kind),
    and ``guarded`` (always ``False`` for a surfaced entry).
    """
    out: list[dict[str, Any]] = []

    # Group added lines by file so we can process each file independently.
    added_by_file: dict[str, dict[int, str]] = {}
    for path, lineno, content in added:
        if path.endswith('.py'):
            added_by_file.setdefault(path, {})[lineno] = content

    for path, added_lines in added_by_file.items():
        post_image = _read_post_image(project_dir, path) if project_dir is not None else []

        if post_image:
            # Walk the full post-image so that pre-existing try blocks and
            # def/class headers outside the diff are properly tracked.
            inside_try = False
            for idx, line in enumerate(post_image, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if _DEF_OR_CLASS_HEADER.match(line):
                    inside_try = False
                    continue
                if _TRY_OPENER.match(line):
                    inside_try = True
                    continue
                if idx not in added_lines:
                    continue
                content = added_lines[idx]
                sub_match = _SUBPROCESS_BOUNDARY.search(content)
                if sub_match is not None:
                    guarded = inside_try or bool(_CHECK_TRUE_KWARG.search(content))
                    if not guarded:
                        out.append(
                            {
                                'file': path,
                                'line': idx,
                                'boundary': f'subprocess.{sub_match.group(1)}',
                                'guarded': False,
                            }
                        )
                    continue
                if _FILE_IO_BOUNDARY.search(content) is not None:
                    if not inside_try:
                        io_match = _FILE_IO_BOUNDARY.search(content)
                        token = io_match.group(0).rstrip('(') if io_match is not None else 'file_io'
                        out.append(
                            {
                                'file': path,
                                'line': idx,
                                'boundary': token.lstrip('.'),
                                'guarded': False,
                            }
                        )
        else:
            # Fallback: no post-image available — scan only the added lines.
            # A def/class header resets the window (a try cannot span a
            # function boundary), so the "enclosing try in the SAME function"
            # rule is honoured within the diff-only subset.
            inside_try = False
            for lineno, content in sorted(added_lines.items()):
                stripped = content.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if _DEF_OR_CLASS_HEADER.match(content):
                    inside_try = False
                    continue
                if _TRY_OPENER.match(content):
                    inside_try = True
                    continue
                sub_match = _SUBPROCESS_BOUNDARY.search(content)
                if sub_match is not None:
                    guarded = inside_try or bool(_CHECK_TRUE_KWARG.search(content))
                    if not guarded:
                        out.append(
                            {
                                'file': path,
                                'line': lineno,
                                'boundary': f'subprocess.{sub_match.group(1)}',
                                'guarded': False,
                            }
                        )
                    continue
                if _FILE_IO_BOUNDARY.search(content) is not None:
                    if not inside_try:
                        io_match = _FILE_IO_BOUNDARY.search(content)
                        token = io_match.group(0).rstrip('(') if io_match is not None else 'file_io'
                        out.append(
                            {
                                'file': path,
                                'line': lineno,
                                'boundary': token.lstrip('.'),
                                'guarded': False,
                            }
                        )
    return out


def _detect_count_prose(
    modified_files: list[str], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect count-prose in SKILL.md siblings of modified files (Facet 2).

    For each modified file nested inside a skill directory (reuse
    ``_find_skill_dir``), scan every ``SKILL.md`` in that same skill directory
    for count-prose — a digit OR an English number word immediately adjacent to
    one of the cardinality nouns (``operation``, ``field``, ``step``, ``rule``,
    ``command``). The cognitive review re-checks that the surfaced number is
    still correct after a sibling file in the directory changed.

    Each entry carries ``file`` (the SKILL.md path), ``line`` (the matched line
    number, 1-based), and ``text`` (the truncated matched line). Deduplicated
    per ``(file, line)``.
    """
    skill_dirs: set[Path] = set()
    for rel in modified_files:
        modified_path = (project_dir / rel).resolve()
        try:
            modified_path.relative_to(project_dir)
        except ValueError:
            continue
        skill_dir = _find_skill_dir(modified_path, project_dir)
        if skill_dir is not None:
            skill_dirs.add(skill_dir)

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for skill_dir in sorted(skill_dirs):
        skill_md = skill_dir / 'SKILL.md'
        if not skill_md.is_file():
            continue
        try:
            text = skill_md.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel_md = str(skill_md.relative_to(project_dir))
        for idx, line in enumerate(text.splitlines(), start=1):
            if _COUNT_PROSE.search(line) is None:
                continue
            key = (rel_md, idx)
            if key in seen:
                continue
            seen.add(key)
            out.append({'file': rel_md, 'line': idx, 'text': _truncate(line.strip(), 200)})
    return out


def _ordered_list_blocks(post_image: list[str]) -> list[dict[str, Any]]:
    """Return every contiguous ordered-list block in a ``.md`` post-image.

    A block is a maximal run of consecutive ``N.`` ordered-list item lines
    (interruptions by a blank line or a non-item line close the block). Each
    returned entry carries ``start`` (the 1-based post-image line of the block's
    first item), ``items`` (a mapping from each item's ordinal number to its
    1-based post-image line), and ``lines`` (the set of 1-based post-image lines
    the block spans, used to test whether the diff touched the block).

    The detector references blocks by the ordinal NUMBER appearing in an
    ``item N`` reference, so a block whose first item is renumbered after an
    insertion still resolves by the current item number present in the block.
    """
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    n_lines = len(post_image)
    for i in range(n_lines):
        idx = i + 1  # 1-based line number
        line = post_image[i]
        m = _ORDERED_LIST_ITEM.match(line)
        if m is not None:
            ordinal = int(m.group('n'))
            if current is None:
                current = {'start': idx, 'items': {}, 'lines': set()}
            current['items'].setdefault(ordinal, idx)
            current['lines'].add(idx)
            continue
        if line.strip() == '':
            # A blank line within an ordered list is tolerated only when it is
            # immediately followed by another item line; treat it as part of the
            # block by recording the line but not closing the block yet.
            if current is not None:
                next_item = next(
                    (post_image[j] for j in range(i + 1, n_lines)
                     if post_image[j].strip() != ''),
                    None,
                )
                if next_item is not None and _ORDERED_LIST_ITEM.match(next_item):
                    current['lines'].add(idx)
                else:
                    blocks.append(current)
                    current = None
            continue
        if current is not None:
            blocks.append(current)
            current = None
    if current is not None:
        blocks.append(current)
    return blocks


def _detect_ordinal_references(
    added: list[tuple[str, int, str]], project_dir: Path
) -> list[dict[str, Any]]:
    """Detect same-document ordinal cross-references into a touched ordered list.

    Scans added ``.md`` lines for an ordinal reference — ``item N`` / ``step N``
    / ``point N`` or a bare parenthesized ``(N)`` — that points at a numbered
    list item BY ITS POSITION. The reference is surfaced as a candidate only
    when, in the same document's post-image, the ordered-list block containing
    item ``N`` was ITSELF touched by the diff (at least one of the block's lines
    is among this file's added lines). That conjunction is the staleness signal:
    inserting or reordering a numbered-list item shifts the ordinals its
    positional cross-references point at, so any ordinal reference into a list
    the same change just edited is a re-verification candidate.

    Each entry carries ``file``, ``line`` (the reference's post-image line),
    ``text`` (the truncated reference line), and ``list_line`` (the 1-based
    post-image line of the referenced ordered-list block — the line of item
    ``N`` when it resolves, else the block's first item line). Deduplicated per
    ``(file, line, ordinal)``.
    """
    # Group added .md lines per file so each file's post-image is read once and
    # the touched-line set is scoped to that file.
    md_added_by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        if path.endswith('.md'):
            md_added_by_file.setdefault(path, []).append((lineno, content))

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for md_path in sorted(md_added_by_file):
        post_image = _read_post_image(project_dir, md_path)
        if not post_image:
            continue
        blocks = _ordered_list_blocks(post_image)
        added_lines = {ln for ln, _ in md_added_by_file[md_path]}

        for lineno, content in md_added_by_file[md_path]:
            for m in _ORDINAL_NOUN_REFERENCE.finditer(content):
                _record_ordinal_reference(
                    out, seen, blocks, added_lines, md_path, lineno, content, int(m.group('n'))
                )
            for m in _ORDINAL_PAREN_REFERENCE.finditer(content):
                _record_ordinal_reference(
                    out, seen, blocks, added_lines, md_path, lineno, content, int(m.group('n'))
                )
    return out


def _record_ordinal_reference(
    out: list[dict[str, Any]],
    seen: set[tuple[str, int, int]],
    blocks: list[dict[str, Any]],
    added_lines: set[int],
    md_path: str,
    lineno: int,
    content: str,
    ordinal: int,
) -> None:
    """Surface one ordinal reference when its referenced list block was touched.

    Resolves the ordered-list block containing item ``ordinal``; fires only when
    that block's line span intersects ``added_lines`` (the diff touched the
    list). Appends a deduplicated candidate to ``out`` carrying ``list_line``,
    the post-image line of item ``ordinal`` (or the block's first item line as a
    fallback). A reference whose ordinal resolves to no ordered-list block, or
    to a block the diff did not touch, surfaces nothing.
    """
    matches = [b for b in blocks if ordinal in b['items']]
    if not matches:
        return
    touched_matches = [b for b in matches if (b['lines'] & added_lines)]
    if not touched_matches:
        return
    target = min(
        touched_matches,
        key=lambda b: abs(b['items'].get(ordinal, b['start']) - lineno),
    )
    key = (md_path, lineno, ordinal)
    if key in seen:
        return
    seen.add(key)
    list_line = target['items'].get(ordinal, target['start'])
    out.append(
        {
            'file': md_path,
            'line': lineno,
            'text': _truncate(content.strip(), 200),
            'list_line': list_line,
        }
    )


def _detect_touched_claims(
    pairs: list[tuple[str, int, str, str]],
) -> list[dict[str, Any]]:
    """Detect near-identical ``-``/``+`` hunk pairs (Facet 3).

    For each adjacent removed/added line pair, tokenize both lines and fire when
    they differ by approximately one token: the two token sequences are equal in
    length AND differ in exactly one position. The ``+`` line is surfaced as a
    ``touched_claim`` candidate so the cognitive pass re-verifies the REST of the
    line's claims, not just the swapped token. A whitespace-only difference
    (identical token sequences) and a many-token difference are both excluded.

    Each entry carries ``file``, ``line`` (the ``+`` line's post-image line
    number), and ``text`` (the truncated ``+`` line).
    """
    out: list[dict[str, Any]] = []
    for path, lineno, removed, added in pairs:
        removed_tokens = _TOKENIZE.findall(removed)
        added_tokens = _TOKENIZE.findall(added)
        if len(removed_tokens) != len(added_tokens):
            continue
        differing = sum(
            1 for a, b in zip(removed_tokens, added_tokens, strict=True) if a != b
        )
        if differing != 1:
            continue
        out.append({'file': path, 'line': lineno, 'text': _truncate(added, 200)})
    return out


def _raw_pass_line_for_dest(
    file_lines: list[tuple[int, str]], dest: str
) -> tuple[int, str] | None:
    """Find a raw-value pass-through of ``args.<dest>`` among ``file_lines``.

    A *raw pass-through* is a use of the argparse destination attribute that
    forwards the externally-supplied value WITHOUT routing it through a
    normalization call first — ``str(args.<dest>)``, a bare ``args.<dest>``
    read, or an f-string interpolation ``{args.<dest>}``. A line that ALSO
    carries a normalization token (``normalize``/``parse``/``urlparse``/...) is
    NOT a raw pass — the value is reconciled there, so it is skipped.

    Returns the first ``(line, content)`` raw-pass occurrence, or ``None`` when
    no raw pass-through of ``args.<dest>`` exists in the candidate scope.
    """
    # Match args.<dest> (attribute access) NOT immediately followed by another
    # identifier char, so ``args.issue`` does not match ``args.issue_url``.
    access = re.compile(
        r'\bargs\.' + re.escape(dest) + r'(?![A-Za-z0-9_])'
    )
    for lineno, content in file_lines:
        if access.search(content) is None:
            continue
        if _NORMALIZATION_TOKENS.search(content) is not None:
            # The value is normalized on this line — not a raw pass-through.
            continue
        return lineno, content
    return None


def _resolve_dest_from_line(content: str) -> str | None:
    """Resolve the argparse dest from a single ``add_argument`` line.

    An explicit ``dest='name'`` kwarg wins; otherwise the long ``--flag`` token
    is mapped to a dest by replacing dashes with underscores. Returns ``None``
    when neither token is present on the line.
    """
    m_dest = _DEST_KWARG.search(content)
    if m_dest is not None:
        return m_dest.group(2)
    m_flag = _ADD_ARGUMENT_FLAG.search(content)
    if m_flag is not None:
        return m_flag.group(1).replace('-', '_')
    return None


def _resolve_dest_from_post_image(
    post_image: list[str], help_lineno: int
) -> str | None:
    """Resolve the dest by reconstructing a multi-line ``add_argument`` call.

    ``help_lineno`` is the 1-based post-image line of the ``help=`` string.
    The walk scans backwards from that line (inclusive) until it reaches the
    line carrying the opening ``add_argument(`` call, accumulating each line's
    flag/dest token along the way. The first resolvable token wins (an explicit
    ``dest=`` on any scanned line takes priority over a ``--flag``, matching the
    single-line precedence). Returns ``None`` when the call's opening cannot be
    located within ``_MAX_CALL_LOOKBACK`` lines or carries no flag/dest token.
    """
    if help_lineno < 1 or help_lineno > len(post_image):
        return None
    idx = help_lineno - 1  # 0-based index into post_image
    flag_dest: str | None = None
    steps = 0
    while idx >= 0 and steps <= _MAX_CALL_LOOKBACK:
        line = post_image[idx]
        m_dest = _DEST_KWARG.search(line)
        if m_dest is not None:
            # Explicit dest= on any line of the call wins immediately.
            return m_dest.group(2)
        if flag_dest is None:
            m_flag = _ADD_ARGUMENT_FLAG.search(line)
            if m_flag is not None:
                flag_dest = m_flag.group(1).replace('-', '_')
        if _ADD_ARGUMENT_OPEN.search(line) is not None:
            # Reached the call's opening line — stop the backward walk.
            return flag_dest
        idx -= 1
        steps += 1
    return None


# The opening token of an ``add_argument`` call. Used as the backward-walk
# terminator when reconstructing a multi-line call from the post-image.
_ADD_ARGUMENT_OPEN = re.compile(r'\.add_argument\s*\(')

# Upper bound on how many lines the backward walk inspects before giving up.
# A single ``add_argument`` call almost never spans more than a handful of
# lines; the cap guards against scanning the whole file when the opening token
# is somehow absent.
_MAX_CALL_LOOKBACK = 40


def _detect_advertised_form_help_strings(
    added: list[tuple[str, int, str]],
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Detect a multi-form ``help=`` string whose handler passes the raw value.

    An argparse ``help`` string that advertises more than one accepted input
    form (e.g. "Issue number or URL") promises the handler will accept every
    advertised form. When the handler then forwards the raw ``args.<dest>``
    value WITHOUT a normalization call (``str(args.issue)``, a bare
    ``args.issue`` read, or an f-string interpolation of it), the advertised
    contract drifts from the handler behaviour — only the form the raw value
    happens to be in actually works.

    For each added ``.py`` line that carries a multi-form ``help=`` string on an
    ``add_argument`` call, the detector resolves the argparse destination (from
    an explicit ``dest=`` kwarg, else from the long ``--flag`` with dashes
    mapped to underscores) and searches the SAME file's added lines for a raw
    pass-through of ``args.<dest>``. A candidate is surfaced only when both the
    multi-form help AND a raw-pass site are present in the diff with no
    intervening normalization on the raw-pass line.

    When ``help=`` sits on a continuation line of a multi-line ``add_argument``
    call, the ``--flag`` / ``dest=`` token lives on a preceding line that may
    not be present in the diff. In that case same-line dest resolution fails. To
    recover, the caller may pass ``project_dir``: the detector then walks
    backwards through the file's post-image from the ``help=`` line to the
    opening ``add_argument(`` and resolves the dest from the reconstructed call
    context. With ``project_dir=None`` (e.g. unit tests, or when the post-image
    is unavailable) the detector falls back to diff-only same-line resolution.

    Each entry carries ``file``, ``line`` (the help-string line), ``arg`` (the
    resolved destination), ``help_text`` (the truncated help string), and
    ``raw_pass_line`` (the post-image line number of the raw pass-through). The
    detector mirrors the review-anchor exclusion of ``contract_sources`` /
    ``schema_bearing_files`` / ``count_prose``: it is NOT summed into
    ``counts.total``.
    """
    # Group added .py lines per file so the raw-pass search is scoped to the
    # same file as the help string (a handler's argument definition and its
    # usage live in one module).
    py_lines_by_file: dict[str, list[tuple[int, str]]] = {}
    for path, lineno, content in added:
        if path.endswith('.py'):
            py_lines_by_file.setdefault(path, []).append((lineno, content))

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    post_image_cache: dict[str, list[str]] = {}
    for path, file_lines in py_lines_by_file.items():
        for lineno, content in file_lines:
            m_help = _HELP_FIELD.search(content)
            if m_help is None:
                continue
            help_text = m_help.group(2)
            if _MULTI_FORM_MARKER.search(help_text) is None:
                continue
            # Resolve the argparse destination: explicit dest= wins, else the
            # long --flag with dashes mapped to underscores. Both tokens may
            # sit on the same diff line as the help string.
            dest = _resolve_dest_from_line(content)
            if dest is None and project_dir is not None:
                # The flag/dest token is on a preceding line of a multi-line
                # add_argument call that is absent from the diff. Reconstruct
                # the call context from the file's post-image and retry.
                if path not in post_image_cache:
                    post_image_cache[path] = _read_post_image(project_dir, path)
                dest = _resolve_dest_from_post_image(
                    post_image_cache[path], lineno
                )
            if dest is None:
                continue
            raw_pass = _raw_pass_line_for_dest(file_lines, dest)
            if raw_pass is None:
                continue
            key = (path, lineno, dest)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    'file': path,
                    'line': lineno,
                    'arg': dest,
                    'help_text': _truncate(help_text, 200),
                    'raw_pass_line': raw_pass[0],
                }
            )
    return out
