#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Shared plan document parsing utilities.

Provides common parsing functions for plan documents (solution outlines,
deliverables) used across plan-marshall and plan-retrospective scripts.

Usage:
    from _plan_parsing import (
        parse_document_sections,
        extract_deliverable_headings,
        split_deliverable_blocks,
        extract_deliverables,
        declared_paths_by_intent,
        declared_paths_population,
        parse_toon_simple,
    )
"""

import os
import re
from typing import Any, NamedTuple

from constants import STEP_INTENT_READ, VALID_STEP_INTENTS

#: The ``<!-- bucket: X -->`` audit-trail comment recorded on the
#: ``**Profiles:**`` line. Owned here because ``_extract_profiles`` reads the
#: same line and must keep ignoring the comment while this pattern reads it.
#:
#: **Anchored to that line**, not free-floating over the deliverable body. The
#: body is prose an author writes, so a bucket-shaped comment appearing anywhere
#: in it — quoting this convention, or documenting a bucket in an example —
#: would otherwise be read as the deliverable's own declared bucket and could
#: fail validation against a write-set it was never describing.
_BUCKET_COMMENT_PATTERN = re.compile(
    r'^\*\*Profiles:\*\*[^\n]*?<!--\s*bucket:\s*([a-z_]+)\s*-->',
    re.IGNORECASE | re.MULTILINE,
)

_HEADER_VIRTUAL_FIELDS = ('plan_id', 'source', 'source_id', 'created')
_HEADER_FIELD_PATTERN = re.compile(
    rf'^({"|".join(re.escape(f) for f in _HEADER_VIRTUAL_FIELDS)}):\s*(.*)$',
    re.MULTILINE,
)

_SLUG_NON_ALNUM_PATTERN = re.compile(r'[^a-z0-9_-]+')

#: The single producer of "what counts as a deliverable heading".
#:
#: Every extractor in this module that enumerates deliverables — ``extract_deliverable_headings``
#: (id/title only) and ``split_deliverable_blocks`` (the per-block splitter that
#: ``extract_deliverables`` builds on) — matches through this one compiled pattern. That shared
#: reference is what makes the deliverable *count* identical across those extractors by
#: construction rather than by convention: a change to what a heading looks like changes one
#: object, so no caller can be left behind on a stale copy.
#:
#: Downstream consumers depend on that guarantee. ``manage-solution-outline list-deliverables``
#: counts through ``extract_deliverables`` → ``split_deliverable_blocks``; the metrics
#: ``deliverable_count`` denominator and the retrospective consistency check count through
#: ``extract_deliverable_headings``. Do NOT inline a copy of this regex — add the caller here.
DELIVERABLE_HEADING_PATTERN = re.compile(r'^###\s+(\d+)\.\s+(.+)$', re.MULTILINE)


def is_foreign_path(path: str, project_root: str) -> bool:
    """Return True when ``path`` resolves OUTSIDE ``project_root`` — the single
    foreign-vs-host discriminator.

    A deliverable's change is *foreign* when it lands in a repository other than
    the one being planned. There is no repository-target field on the record;
    the discriminator is derived purely from the declared path relative to the
    project root (the git toplevel), which is the axis the ``--project-dir``
    routing already instruments. This is the one place that rule is spelled out
    so ``manage-solution-outline list-deliverables`` (the ``foreign:`` column)
    and the phase-6 pre-archive landing gate agree by construction.

    The comparison is **lexical** (``os.path.normpath``/``commonpath``), never a
    filesystem ``resolve()``: the foreign repository's tree may not exist in the
    session doing the derivation, and a path that cannot be stat-ed must still be
    classified. An absolute path is normalised as-is; a relative path is joined
    onto ``project_root`` first, so a bare ``src/Foo.java`` is host while a
    ``../other-repo/src/Foo.java`` escape and an absolute ``/elsewhere/...`` path
    are both foreign.

    Args:
        path: The declared ``affected_files`` / ``steps[].target`` path.
        project_root: Absolute path of the project root (git toplevel).

    Returns:
        True when ``path`` lies outside ``project_root``; False when it is the
        root itself or under it.
    """
    if not path or not path.strip():
        return False
    root = os.path.normpath(os.path.abspath(project_root))
    candidate = path.strip()
    target = os.path.normpath(candidate if os.path.isabs(candidate) else os.path.join(root, candidate))
    try:
        return os.path.commonpath([root, target]) != root
    except ValueError:
        # Different drives / mixed absolute-relative that cannot share a root
        # (Windows edge). Un-shareable roots mean the target is not under the
        # project root — treat it as foreign rather than silently host.
        return True


def _slugify_section_name(name: str) -> str:
    """Normalize a section heading into a stable lookup slug.

    Algorithm:
        1. Lowercase the input.
        2. Collapse any run of characters outside ``[a-z0-9_-]`` into a single ``_``.
        3. Strip trailing ``_`` only — leading ``_`` is preserved so sentinel
           keys like ``_header`` (used by ``parse_document_sections`` for the
           metadata block before any H2) round-trip through the helper.

    The single regex pass means runs of whitespace, punctuation, or other
    non-allowed characters all collapse into one ``_`` rather than producing
    repeated separators. Trailing ``_`` (typical of headings ending in ``)``,
    ``!``, ``.``, etc.) is stripped so anchors stay tidy. Leading ``_`` is
    deliberately preserved — both to keep ``_header`` queryable and so inputs
    whose first character is non-alnum don't silently merge with adjacent
    headings.

    Args:
        name: Raw section heading (e.g., ``"Clarified Request"``).

    Returns:
        Lookup slug (e.g., ``"clarified_request"``).
    """
    return _SLUG_NON_ALNUM_PATTERN.sub('_', name.lower()).rstrip('_')


def parse_document_sections(content: str) -> dict[str, str]:
    """Parse markdown document into sections by ## heading.

    Section keys are lowercase with underscores (e.g., 'summary', 'deliverables').
    The content before any ## heading is stored under '_header'.

    After splitting on H2 headings, an allowlisted set of header metadata fields
    (``plan_id``, ``source``, ``source_id``, ``created``) is scanned from the
    ``_header`` block and promoted to virtual sections so callers can read them
    via the same section APIs. Only the allowlist is promoted — arbitrary
    ``key: value`` lines are ignored. If an H2 section with the same name
    already exists, it wins (virtual promotion does not overwrite it). The
    ``_header`` section itself is preserved unchanged.

    Args:
        content: Markdown document content

    Returns:
        Dictionary mapping section names to their content
    """
    sections: dict[str, str] = {}
    current_section = '_header'
    current_content: list[str] = []

    for line in content.split('\n'):
        if line.startswith('## '):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            # Start new section (lowercase with underscores)
            current_section = _slugify_section_name(line[3:].strip())
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    # Promote allowlisted header metadata fields to virtual sections.
    # H2-parsed sections take precedence on collision.
    header_text = sections.get('_header', '')
    if header_text:
        for match in _HEADER_FIELD_PATTERN.finditer(header_text):
            key, value = match.groups()
            if key not in sections:
                sections[key] = value.strip()

    return sections


def extract_deliverable_headings(content: str) -> list[dict[str, str]]:
    """Extract deliverable headings from Deliverables section.

    Simple extraction that only returns id and title - use for
    basic structural verification.

    Matches through the module-level :data:`DELIVERABLE_HEADING_PATTERN`, the same object
    ``split_deliverable_blocks`` uses, so this function and ``extract_deliverables`` enumerate
    the same set of headings by construction.

    Args:
        content: The Deliverables section content

    Returns:
        List of dicts with 'id' and 'title' keys
    """
    deliverables: list[dict[str, str]] = []

    for match in DELIVERABLE_HEADING_PATTERN.finditer(content):
        deliverables.append({'id': match.group(1), 'title': match.group(2).strip()})

    return deliverables


def split_deliverable_blocks(deliverables_section: str) -> list[dict[str, Any]]:
    """Split a Deliverables section into one block per ``### N. Title`` heading.

    Each block carries the heading's number and title plus the body content that
    belongs to that deliverable alone — everything from the end of its heading
    line up to the start of the next heading (or the end of the section for the
    last deliverable). Blocks are returned in document order, NOT sorted by
    number, so callers that need per-deliverable attribution see the document as
    written.

    Splits on the module-level :data:`DELIVERABLE_HEADING_PATTERN`, the same object
    ``extract_deliverable_headings`` matches with, so ``len()`` of this function's result and of
    that one's are equal by construction for any input.

    Args:
        deliverables_section: The Deliverables section content

    Returns:
        List of dicts with 'number' (int), 'title' (str), and 'content' (str) keys
    """
    blocks: list[dict[str, Any]] = []

    matches = list(DELIVERABLE_HEADING_PATTERN.finditer(deliverables_section))

    for i, match in enumerate(matches):
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(deliverables_section)
        blocks.append(
            {
                'number': int(match.group(1)),
                'title': match.group(2).strip(),
                'content': deliverables_section[start_pos:end_pos].strip(),
            }
        )

    return blocks


def extract_deliverables(deliverables_section: str) -> list[dict[str, Any]]:
    """Extract full deliverable information from Deliverables section.

    Parses `### N. Title` headings and extracts structured information
    including metadata, profiles, affected files, the declared file-type
    bucket, and verification.

    Args:
        deliverables_section: The Deliverables section content

    Returns:
        List of deliverable dicts with full metadata
    """
    deliverables: list[dict[str, Any]] = []

    for block in split_deliverable_blocks(deliverables_section):
        number = block['number']
        title = block['title']
        content = block['content']

        # Extract structured blocks
        metadata = _extract_metadata_block(content)
        profiles = _extract_profiles(content)
        affected_files = _extract_affected_files(content)
        survey_scope = extract_survey_scope(content)
        mutation_scope = extract_mutation_scope(content)
        verification = _extract_verification(content)
        has_success_criteria = bool(re.search(r'\*\*Success Criteria:\*\*', content, re.IGNORECASE))

        deliverables.append(
            {
                'number': number,
                'title': title,
                'reference': f'{number}. {title}',
                'metadata': metadata,
                'profiles': profiles,
                'affected_files': affected_files,
                'survey_scope': survey_scope,
                'mutation_scope': mutation_scope,
                'declared_bucket': extract_declared_bucket(content),
                'verification': verification,
                'has_success_criteria': has_success_criteria,
            }
        )

    return sorted(deliverables, key=lambda d: d['number'])


def _extract_metadata_block(content: str) -> dict[str, str]:
    """Extract **Metadata:** block fields from deliverable content."""
    metadata: dict[str, str] = {}

    metadata_match = re.search(r'\*\*Metadata:\*\*\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not metadata_match:
        return metadata

    metadata_text = metadata_match.group(1)
    field_pattern = re.compile(r'-\s*(\w+):\s*(.+)')
    for match in field_pattern.finditer(metadata_text):
        field_name = match.group(1).strip()
        field_value = match.group(2).strip()
        metadata[field_name] = field_value

    return metadata


def _extract_profiles(content: str) -> list[str]:
    """Extract **Profiles:** list from deliverable content.

    The ``**Profiles:**`` line MAY carry a trailing same-line HTML comment
    recording the file-type bucket — the documented canonical form is
    ``**Profiles:** <!-- bucket: documentation_only -->`` followed by the
    ``- `` bullet list on subsequent lines. The widened lead-in
    ``\\*\\*Profiles:\\*\\*[^\\n]*\\n\\s*`` tolerates any non-newline trailing
    content (the bucket comment, or nothing) on the ``**Profiles:**`` line
    before consuming the line break and any leading whitespace ahead of the
    first bullet. Profiles are still extracted only from the ``- `` bullets,
    so the comment text is never mis-read as a profile.
    """
    profiles: list[str] = []

    profiles_match = re.search(
        r'\*\*Profiles:\*\*[^\n]*\n\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE
    )
    if not profiles_match:
        return profiles

    profiles_text = profiles_match.group(1)
    profile_pattern = re.compile(r'-\s*(\w+)')
    for match in profile_pattern.finditer(profiles_text):
        profile = match.group(1).strip()
        if profile:
            profiles.append(profile)

    return profiles


#: The three declaration headings a deliverable may use to name its file
#: surface, and the intent each implies when a bullet carries no ``(intent)``
#: marker of its own.
#:
#: ``Affected files`` is the flat form. A **survey-scope deliverable** — one
#: whose mutation set is not knowable at authoring time — declares the other
#: two instead, per ``phase-3-outline/standards/outline-workflow-detail.md``
#: § "Survey-scope vs mutation-scope declaration": ``Files to survey`` is the
#: analysis-only candidate pool and ``Files expected to mutate`` is the
#: change-bearing subset.
#:
#: The survey pair is parsed here because a declaration no parser reads is a
#: declaration no downstream check can enforce. Before this, a deliverable
#: authored exactly as that standard mandates parsed to an EMPTY file list:
#: its expected-to-mutate paths belonged to no write-set, so every set-guarding
#: check downstream — the recall check, the bucket adjudication, the
#: verification-only guard — saw a deliverable that touched nothing.
_AFFECTED_FILES_HEADING = 'Affected files'
_SURVEY_SCOPE_HEADING = 'Files to survey'
_MUTATION_SCOPE_HEADING = 'Files expected to mutate'

#: The three declaration headings paired with the intent a marker-less bullet
#: under each one carries. The SINGLE enumeration of "every heading a deliverable
#: may declare its file surface under" — :func:`_walk_declared_paths` iterates it,
#: so a fourth heading added to the standard reaches the declared-footprint
#: derivation by editing this tuple alone.
#:
#: Only ``Files to survey`` supplies a default: it is analysis-only by definition,
#: so an unmarked bullet there IS a read. The two modification headings supply
#: ``None`` so an unmarked bullet stays distinguishable from a marked one rather
#: than being silently promoted to a write it never declared.
_DECLARATION_HEADINGS: tuple[tuple[str, str | None], ...] = (
    (_AFFECTED_FILES_HEADING, None),
    (_MUTATION_SCOPE_HEADING, None),
    (_SURVEY_SCOPE_HEADING, STEP_INTENT_READ),
)

#: The bucket a bullet lands in when it declares no intent this parser recognises.
#:
#: Deliberately OUTSIDE the closed :data:`constants.VALID_STEP_INTENTS` enum, and
#: deliberately not collapsed into either neighbour. A bullet with no ``(intent)``
#: marker stated no intent at all, and both available lies are worse than a bucket
#: of its own: filing it under a write invents a declaration the author never made,
#: while filing it under ``read`` subtracts the path from every change footprint
#: derived downstream. Keeping it separate lets the CONSUMER decide the direction
#: while still being able to report how many such bullets there were — so a set
#: that was filtered stays distinguishable from a set that was simply small.
#:
#: An unrecognised marker (the per-path ``(intent)`` group is parsed unvalidated,
#: and ``validate_deliverable_contract`` is what enum-checks it) lands here too:
#: it likewise declared no VALID intent, and routing it here keeps the returned
#: key set closed so a consumer can iterate it exhaustively.
INTENT_UNANNOTATED = 'unannotated'


def _extract_scope_field(
    content: str, heading: str, default_intent: str | None = None
) -> list[dict[str, Any]]:
    """Extract one ``**{heading}:**`` bullet list as ``{'path', 'intent'}`` entries.

    Shared by the three declaration headings. An entry's own parenthesized
    ``(intent)`` marker always wins; ``default_intent`` supplies the intent only
    when the bullet carries none, which is the documented form for the survey
    pair (neither ``Files to survey`` nor ``Files expected to mutate`` bullets
    carry markers in the standard's worked example).

    Args:
        content: The deliverable block body.
        heading: The bold heading text, without the ``**`` fence or the colon.
        default_intent: Intent applied to a marker-less bullet, or ``None`` to
            leave it unset so the validator reports the missing marker itself.

    Returns:
        The declared entries in document order; empty when the heading is absent.
    """
    files: list[dict[str, Any]] = []

    files_match = re.search(
        rf'\*\*{re.escape(heading)}:\*\*\s*((?:- [^\n]+\n?)+)', content, re.IGNORECASE
    )
    if not files_match:
        return files

    files_text = files_match.group(1)
    # Capture the backticked (or bare) path, then an optional trailing
    # ``(intent)`` marker. The intent group is left unvalidated here — the
    # validator enum-checks it against VALID_STEP_INTENTS.
    file_pattern = re.compile(r'-\s*`?([^`\n(]+?)`?\s*(?:\(([a-z-]+)\))?\s*$', re.MULTILINE)
    for match in file_pattern.finditer(files_text):
        file_path = match.group(1).strip()
        intent = match.group(2) or default_intent
        if file_path:
            files.append({'path': file_path, 'intent': intent})

    return files


def extract_survey_scope(content: str) -> list[dict[str, Any]]:
    """Extract the ``**Files to survey:**`` candidate pool.

    Analysis-only by definition, so a marker-less bullet is ``read``. These
    paths are the deliverable's declared *examination* scope — the set a
    declared sweep must actually cover — and are deliberately NOT part of the
    write-set.
    """
    return _extract_scope_field(content, _SURVEY_SCOPE_HEADING, STEP_INTENT_READ)


def extract_mutation_scope(content: str) -> list[dict[str, Any]]:
    """Extract the ``**Files expected to mutate:**`` change-bearing subset.

    A marker-less bullet is left unset rather than defaulted to a write, so the
    parsed record still distinguishes "declared a write" from "stated no
    intent". :func:`deliverable_write_set` counts an unmarked entry as a write
    either way, which is the conservative direction — the path reaches the
    write-set rather than being silently subtracted from the change footprint.

    ⚠ Unlike an unmarked ``**Affected files:**`` entry, an unmarked entry here
    is **not** reported by the validator: ``validate_deliverable_contract``'s
    check 3b walks ``affected_files`` only, deliberately (the survey pair's
    documented form carries no markers at all, so requiring them would fail
    every correctly-authored survey deliverable). The intent is therefore
    consumed but not enforced on this field.
    """
    return _extract_scope_field(content, _MUTATION_SCOPE_HEADING)


def _extract_affected_files(content: str) -> list[dict[str, Any]]:
    """Extract **Affected files:** list from deliverable content.

    The FLAT declaration heading only. It is one of the three headings
    :func:`declared_paths_by_intent` reads; a survey-scope deliverable declares
    ``Files expected to mutate`` / ``Files to survey`` instead and yields nothing
    here, so this extractor is never the whole declared surface on its own.

    The list is a *declaration* of the surface a deliverable expects to touch — a
    lower-bound estimate — and NEVER a record of what was actually touched; the
    authoritative touched-file record is the live footprint derived from the
    worktree. See ``manage-execution-manifest/standards/decision-rules.md``
    § "Declared surface vs. live footprint" for the consumer contract.

    The declared footprint is NOT frozen at outline time. ``references.affected_files``
    is re-derived from this structured data by ``manage-references sync-affected-files``
    at every point a later reader depends on it being current — before phase-4-plan
    composes the manifest, and again on the phase-6-finalize loop-back re-entry —
    because a faithful read of a stale value cannot detect its own staleness.

    Each entry is returned as a ``{'path': str, 'intent': str | None}`` object.
    The canonical annotated form is a backticked path followed by a
    parenthesized intent marker: ``- `path/to/file.ext` (write-new)``. An entry
    with no ``(intent)`` suffix yields ``intent=None`` so the validator — not
    this parser — produces the precise per-deliverable "missing marker" error.
    """
    return _extract_scope_field(content, _AFFECTED_FILES_HEADING)


def deliverable_write_set(deliverable: dict[str, Any]) -> list[str]:
    """Return the paths a deliverable declares it will MODIFY.

    The authoritative write-set: every ``affected_files`` **or**
    ``mutation_scope`` entry whose declared intent is not
    :data:`constants.STEP_INTENT_READ`. A ``read`` entry names a file the
    deliverable consults and leaves untouched, so it belongs to the
    deliverable's *reading* surface and to no part of its change footprint.

    ``mutation_scope`` — the ``**Files expected to mutate:**`` field a
    survey-scope deliverable declares INSTEAD of a flat ``Affected files``
    list — is unioned in rather than treated as a separate surface. It is a
    declaration of change intent by definition, and
    ``phase-3-outline/standards/outline-workflow-detail.md`` already documents
    it as "the list that downstream profile classification and the retrospective
    recall check consume". Leaving it out made that documented contract false:
    a correctly-authored survey-scope deliverable had an EMPTY write-set, so
    its expected-to-mutate paths were invisible to every set-guarding check
    downstream — the incomplete-derived-set failure in its purest form, since
    the missing paths were the ones nobody could see were missing.

    The two fields are disjoint by the standard's own disjointness requirement,
    so the union is deduplicated defensively rather than assumed disjoint: a
    path declared under both fields contributes one write-set member.

    Every classification derived from a deliverable's file list — its file-type
    bucket, whether it warrants a testing profile, what a build must cover —
    is a statement about what CHANGES, and must therefore be computed from this
    set rather than from ``affected_files`` wholesale. Computing it from the
    wholesale list lets a single read-only reference flip a classification: one
    consulted test file makes a deliverable look test-bearing, one consulted
    ``.py`` makes a documentation-only deliverable look like code.

    An entry with no intent marker at all is counted as a write. The marker is
    mandatory and its absence is already a validation error, so the missing
    intent is reported as the error it is rather than silently subtracting the
    path from the change footprint — an unmarked entry must never be quieter
    than a marked one.

    Args:
        deliverable: A record from :func:`extract_deliverables`.

    Returns:
        The declared write paths, in document order.
    """
    write_set: list[str] = []
    seen: set[str] = set()
    for field in ('affected_files', 'mutation_scope'):
        for entry in deliverable.get(field, []) or []:
            if not isinstance(entry, dict):
                continue
            if entry.get('intent') == STEP_INTENT_READ:
                continue
            path = entry.get('path')
            if isinstance(path, str) and path and path not in seen:
                seen.add(path)
                write_set.append(path)
    return write_set


class _DeclaredPathWalk(NamedTuple):
    """One walk of the outline's declared file surface: the paths and the population.

    The two faces are produced by the SAME pass so they cannot disagree about
    what was read. :func:`declared_paths_by_intent` and
    :func:`declared_paths_population` are thin views onto this pair.
    """

    by_intent: dict[str, set[str]]
    population: dict[str, int]


def _heading_present(content: str, heading: str) -> bool:
    """Return True when ``**{heading}:**`` appears in a deliverable block.

    Presence is asked separately from extraction because the two answers differ
    where it matters: :func:`_extract_scope_field` returns an empty list BOTH for
    a heading that is absent and for one that is present with no bullets beneath
    it. Counting only extractions would report those two states identically, and
    the second is the one worth seeing — an author who wrote the heading and then
    declared nothing under it.
    """
    return re.search(rf'\*\*{re.escape(heading)}:\*\*', content, re.IGNORECASE) is not None


def _walk_declared_paths(outline_content: str) -> _DeclaredPathWalk:
    """Walk every deliverable's every declaration heading exactly once.

    The single derivation behind both public faces. Returns the intent-keyed path
    sets plus the population the walk covered.
    """
    by_intent: dict[str, set[str]] = {intent: set() for intent in VALID_STEP_INTENTS}
    by_intent[INTENT_UNANNOTATED] = set()
    population = {'deliverables_scanned': 0, 'headings_found': 0, 'bullets_parsed': 0}

    sections = parse_document_sections(outline_content or '')
    deliverables_section = sections.get('deliverables')
    if not isinstance(deliverables_section, str) or not deliverables_section.strip():
        # No Deliverables section: nothing was walked. The zero population is the
        # signal — the caller can tell this from an outline whose deliverables
        # genuinely declare no paths, which reports a non-zero deliverable count.
        return _DeclaredPathWalk(by_intent, population)

    for block in split_deliverable_blocks(deliverables_section):
        population['deliverables_scanned'] += 1
        content = str(block.get('content') or '')
        for heading, default_intent in _DECLARATION_HEADINGS:
            if not _heading_present(content, heading):
                continue
            population['headings_found'] += 1
            for entry in _extract_scope_field(content, heading, default_intent):
                path = entry.get('path')
                if not isinstance(path, str) or not path:
                    continue
                population['bullets_parsed'] += 1
                intent = entry.get('intent')
                if intent not in VALID_STEP_INTENTS:
                    intent = INTENT_UNANNOTATED
                by_intent[intent].add(path)

    return _DeclaredPathWalk(by_intent, population)


def declared_paths_by_intent(outline_content: str) -> dict[str, set[str]]:
    """Return every path the outline DECLARES, keyed by the intent it declared.

    The single structured derivation of a plan's declared footprint. It reads all
    three declaration headings the outline standard defines — ``Affected files``,
    ``Files expected to mutate``, and ``Files to survey`` (:data:`_DECLARATION_HEADINGS`)
    — across every deliverable, so a **survey-scope deliverable's**
    expected-to-mutate paths reach the derivation. A survey-scope deliverable
    declares that pair INSTEAD of a flat ``Affected files`` list, so a derivation
    that read only the flat heading saw such a deliverable as declaring nothing
    at all, and its change-bearing paths belonged to no declared set anywhere.

    This function exists so ``references.affected_files`` is computed from the
    outline's STRUCTURED per-path ``intent`` data rather than composed by reading
    outline prose. A prose-scraped list can only be as complete as the reading
    that produced it, and nothing downstream can audit a reading — whereas this
    walk publishes the population it covered (:func:`declared_paths_population`).

    Returns:
        A mapping whose key set is CLOSED: every member of
        :data:`constants.VALID_STEP_INTENTS` plus :data:`INTENT_UNANNOTATED`.
        Every key is always present, so a consumer iterates the mapping rather
        than guessing which intents occurred; an intent nothing declared maps to
        an empty set. Values are deduplicated path sets — a path declared under
        two headings, or by two deliverables, contributes one member.

    Note:
        The returned sets answer "what was DECLARED", never "what was touched".
        The authoritative touched-file record is the live footprint derived from
        the worktree (``manage-references compute-footprint``); these two are
        reconciled against each other rather than substituted for one another.
    """
    return _walk_declared_paths(outline_content).by_intent


def declared_paths_population(outline_content: str) -> dict[str, int]:
    """Return the population :func:`declared_paths_by_intent` walked.

    Published so an empty derivation is never mistaken for a measured one. An
    outline the parser could not read and an outline whose deliverables declare
    no paths both yield empty path sets, and only the population separates them:
    the first reports ``deliverables_scanned: 0``, the second a positive count.
    A consumer that reports "0 declared paths" without this figure is reporting
    what it managed to read, not what the plan declared.

    Returns:
        ``deliverables_scanned`` — deliverable blocks walked;
        ``headings_found`` — declaration headings PRESENT across those blocks
        (a heading with no bullets under it still counts, which is what makes it
        distinguishable from an absent one);
        ``bullets_parsed`` — path bullets parsed under those headings, counted
        before deduplication, so it reports the walk rather than the result.
    """
    return _walk_declared_paths(outline_content).population


def extract_declared_bucket(content: str) -> str | None:
    """Extract the ``<!-- bucket: X -->`` comment from a deliverable's body.

    The comment rides on the ``**Profiles:**`` line and records the file-type
    bucket the author resolved. :func:`_extract_profiles` deliberately reads only
    the bullet list beneath that line, so the recorded bucket was parsed by
    nobody and could never be checked against the files it claims to describe.

    Args:
        content: A deliverable block body.

    Returns:
        The declared bucket string, or ``None`` when no bucket comment is
        present.
    """
    match = _BUCKET_COMMENT_PATTERN.search(content)
    return match.group(1) if match else None


def _extract_verification(content: str) -> dict[str, str]:
    """Extract **Verification:** section from deliverable content."""
    verification: dict[str, str] = {}

    verif_match = re.search(r'\*\*Verification:\*\*\s*\n?((?:- [^\n]+\n?)+)', content, re.IGNORECASE)
    if not verif_match:
        return verification

    verif_text = verif_match.group(1)

    cmd_match = re.search(r'-\s*Command:\s*(.+)', verif_text)
    if cmd_match:
        verification['command'] = cmd_match.group(1).strip()

    criteria_match = re.search(r'-\s*Criteria:\s*(.+)', verif_text)
    if criteria_match:
        verification['criteria'] = criteria_match.group(1).strip()

    return verification


def parse_toon_simple(content: str) -> dict[str, Any]:
    """Parse simple TOON format (key: value pairs and lists).

    Handles basic TOON structures:
    - Key: value pairs
    - Lists with [N]: header
    - Comments (# lines)

    Args:
        content: TOON format content

    Returns:
        Dictionary with parsed values
    """
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    current_list: list[str] = []

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Check for list header
        if '[' in line and line.endswith(':'):
            if current_list_key and current_list:
                result[current_list_key] = current_list
            key_part = line.split('[')[0]
            current_list_key = key_part
            current_list = []
            continue

        # Check if we're in a list
        if current_list_key:
            if ':' in line and not line.startswith(' '):
                result[current_list_key] = current_list
                current_list_key = None
                current_list = []
            else:
                current_list.append(line.strip())
                continue

        # Key-value pair
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()

    if current_list_key and current_list:
        result[current_list_key] = current_list

    return result
