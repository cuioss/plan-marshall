#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Doc-corpus cross-reference extraction and resolution (Axis-C materializer).

The documentation domain's edge derivation joins over cross-document references —
AsciiDoc ``xref:`` / ``link:`` / ``include::`` / ``<<anchor>>`` targets and Markdown
``[text](target)`` links. Resolving those targets means reading files from disk
(does the target file exist, does the ``#anchor`` resolve to a real heading), which
a derivation resolver may NOT do: the Axis-C contract requires ``derive_edges`` to
be a pure function of its arguments. So the reading happens HERE, at discovery
time, and the result is materialized onto the documentation module's
``component_refs`` field for the resolver to join over.

Each materialized entry is a ``{target_bundle, dep_type, resolved}`` triple, matching
the shared ``component_refs`` schema (see
``extension-api/standards/module-discovery.md``). ``dep_type`` is always ``path`` —
a doc reference is a relative-path reference. ``resolved`` is ``False`` when the
target file (or, for an anchored reference, the target anchor) does not exist, so
the resolver can suppress and REPORT a dangling reference rather than silently
dropping it — the "deleted heading / dangling anchor" class the documentation
domain uniquely detects.

The reference-extraction and anchor-resolution vocabulary is the documentation
domain's own, carried over from the ``ref-asciidoc`` link-verification engine
(``ref-asciidoc/scripts/_cmd_verify_links.py``); this module reuses the same
regexes so the two surfaces agree on what a reference is and when it resolves.
"""

import re
from pathlib import Path
from typing import Any

# Reference schemes that name an EXTERNAL target rather than a repo-relative doc
# path. An external reference is not a cross-document reference this engine
# resolves — it is skipped entirely (never materialized, never reported), because
# its resolvability is not a fact about this repository.
_EXTERNAL_SCHEMES: tuple[str, ...] = ('http://', 'https://', 'mailto:', 'ftp://', 'ftps://', '//')

# The documentation corpus file suffixes the engine scans and resolves against.
_DOC_SUFFIXES: tuple[str, ...] = ('.adoc', '.md')

# Reserved module name for a target that resolves to (or is intended for) the
# project root rather than a marketplace bundle or the doc tree. Matches the
# ``get_root_module`` convention (the module at path ``.``); when the project's
# root module is named otherwise the resolver reports the edge as an
# ``unknown-endpoint`` rather than emitting a wrong one.
_ROOT_MODULE = 'default'

# The documentation module name — the owner of ``doc/**`` and the value a doc
# reference into the doc tree (or a same-file anchor) is attributed to.
_DOC_MODULE = 'documentation'

_MARKETPLACE_PREFIX = 'marketplace/bundles/'


def _is_external(target: str) -> bool:
    """Return True when ``target`` names an external (non-repo) reference scheme."""
    lowered = target.strip().lower()
    return any(lowered.startswith(scheme) for scheme in _EXTERNAL_SCHEMES)


def _has_doc_suffix(token: str) -> bool:
    """Return True when ``token`` (the pre-``#`` part) names a documentable file.

    Used to tell a file-path reference from a bare anchor id: a target ending in a
    documentation or web suffix is a file, everything else (``execution-modes``) is
    treated as an id. The set is intentionally broader than :data:`_DOC_SUFFIXES`
    because a reference MAY point at a non-doc file (``.py``, ``.html``); those are
    resolved for file existence but never for anchors.
    """
    lowered = token.split('#', 1)[0].lower()
    return '.' in lowered.rsplit('/', 1)[-1]


def _heading_anchor_forms(title: str) -> set[str]:
    """Return every id form a section/heading title could be referenced by.

    Reference resolution has to be **convention-tolerant** — a false "dangling
    anchor" report on a valid reference is the misleading signal this whole
    substrate is built to avoid — so a heading contributes ALL the anchor forms a
    real cross-reference might legitimately use:

    - the **AsciiDoc default auto-id** (``idprefix``/``idseparator`` both ``_``):
      ``Where things live`` → ``_where_things_live``. This is the form the
      overwhelming majority of AsciiDoc ``xref:file.adoc#id`` references use, and
      the one a naive GitHub-style slug misses;
    - the **GitHub-style slug** (lower-case, hyphen-separated, no prefix):
      ``Where things live`` → ``where-things-live``. This is the Markdown ATX
      heading form, and also the form an AsciiDoc author who set
      ``:idseparator: -`` would use;
    - the **raw lower-cased title** (``where things live``), so a natural
      cross-reference ``<<Where things live>>`` — which AsciiDoc resolves by title
      text, not by id — is not falsely flagged.

    The over-approximation is deliberate and one-directional: it can only make a
    reference resolve, never make a valid reference fail. The cost is that a
    genuinely-dangling anchor whose slug happens to collide with one of these
    forms is missed; that under-reporting is the correct bias for a signal whose
    whole value is that a positive is trustworthy.
    """
    cleaned = re.sub(r'\{[^\}]+\}', '', title)
    cleaned = re.sub(r'link:https?://[^\[]+\[[^\]]+\]', '', cleaned)
    cleaned = re.sub(r'[`*_]', '', cleaned).strip().lower()
    forms: set[str] = set()
    if cleaned:
        forms.add(cleaned)
    # GitHub-style: strip non-word/space/hyphen, spaces → hyphens.
    github = re.sub(r'[^\w\s-]', '', cleaned)
    github = re.sub(r'[\s-]+', '-', github).strip('-')
    if github:
        forms.add(github)
    # AsciiDoc default auto-id: non-alphanumeric runs → '_', leading/trailing
    # stripped, then the '_' idprefix prepended.
    body = re.sub(r'[^a-z0-9]+', '_', cleaned).strip('_')
    if body:
        forms.add(f'_{body}')
        forms.add(body)
    return forms


def extract_anchors(text: str) -> set[str]:
    """Return every anchor a reference in this file could target.

    Covers explicit anchors plus every id form a heading title could be
    referenced by (see :func:`_heading_anchor_forms`):

    - ``[[id]]`` and ``[#id]`` explicit AsciiDoc block anchors;
    - ``anchor:id[]`` inline anchor macros and ``[id="id"]`` block-attribute ids;
    - ``{#id}`` / ``<a name="id">`` explicit Markdown anchors;
    - AsciiDoc section titles (``== Heading``) and Markdown ATX headings
      (``## Heading``), each contributing their AsciiDoc auto-id, GitHub slug, and
      raw-title forms.

    The explicit-form set is intentionally broad rather than exhaustive: matching
    can only add anchors, so a form this list misses under-reports (a valid
    reference resolves anyway when the target also carries a heading or another
    recognised anchor), never over-reports. A heading under a non-default
    ``:idprefix:`` is the residual gap and is not resolved here.
    """
    anchors: set[str] = set()
    for line in text.splitlines():
        for explicit in (
            re.findall(r'\[\[([^\],]+)', line)
            + re.findall(r'\[#([^\]]+)\]', line)
            + re.findall(r'anchor:([^\[\s]+)\[', line)
            + re.findall(r'\[id=["\']?([\w:.-]+)', line)
            + re.findall(r'\{#([^\}]+)\}', line)
            + re.findall(r'<a\s+name="([^"]+)"', line)
        ):
            # Anchor matching is case-insensitive (a leniency bias — see
            # ``_heading_anchor_forms``), so explicit anchors are stored lowered
            # to compare against a lowered reference.
            anchors.add(explicit.strip().lower())
        heading = re.match(r'^\s*(={1,6}|#{1,6})\s+(.+?)\s*$', line)
        if heading:
            anchors.update(_heading_anchor_forms(heading.group(2)))
    return anchors


def extract_references(text: str) -> list[tuple[str, str]]:
    """Return the ``(target, anchor)`` references outbound from one doc file's body.

    ``target`` is the raw relative path an ``xref:`` / ``link:`` / ``include::`` /
    Markdown-link names (empty for a same-file ``<<anchor>>`` or a bare ``#anchor``
    link). ``anchor`` is the fragment after ``#`` (empty when none). External
    references (``http(s)://``, ``mailto:``) are dropped here — they are not
    repo-relative doc references. Code blocks (``----`` / ``....`` fences) are
    skipped so a reference shown as an example is not mistaken for a real one.
    """
    refs: list[tuple[str, str]] = []
    in_code_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith('----') or stripped.startswith('....') or stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Strip inline code spans (`` `...` ``) before extracting. A reference
        # shown as inline code — ``<<step-configuration>>`` quoted in prose, an
        # ``xref:`` written as a syntax example — is documentation ABOUT a
        # reference, not a live one, exactly like the fenced-block case above.
        # Not stripping it produces a false dangling-reference report on a report
        # that merely mentions the reference.
        line = re.sub(r'`[^`]*`', '', raw_line)

        # AsciiDoc same-file cross-reference: <<anchor>> / <<anchor,label>>. A
        # form carrying a path (<<file.adoc#a>>) is the deprecated spelling and is
        # handled as a path reference; the bare-anchor form is the common one.
        for match in re.finditer(r'<<([^,>]+?)(?:,[^>]*)?>>', line):
            token = match.group(1).strip()
            if _has_doc_suffix(token) or '/' in token:
                target, _, anchor = token.partition('#')
                refs.append((target.strip(), anchor.strip()))
            else:
                refs.append(('', token))

        # AsciiDoc xref: / link: / include:: — path[#anchor] in the macro target.
        for match in re.finditer(r'(xref|link|include)::?([^\[\s]+)\[[^\]]*\]', line):
            macro, token = match.group(1), match.group(2).strip()
            if _is_external(token):
                continue
            target, _, anchor = token.partition('#')
            # A bare ``xref:`` target with no file suffix and no path separator is
            # an ANCHOR ID / natural reference (``xref:execution-modes[]``), not a
            # file path. Treating it as a file would resolve it against a
            # non-existent ``execution-modes`` file and report a false dangling
            # reference. ``link:`` / ``include::`` always name a file, so only
            # ``xref:`` takes this disambiguation.
            if macro == 'xref' and target and not anchor and not _has_doc_suffix(target) and '/' not in target:
                refs.append(('', target.strip()))
            else:
                refs.append((target.strip(), anchor.strip()))

        # Markdown inline link: [text](target) — target may be a bare #anchor.
        for match in re.finditer(r'\[[^\]]*\]\(([^)\s]+)\)', line):
            token = match.group(1).strip()
            if _is_external(token):
                continue
            target, _, anchor = token.partition('#')
            refs.append((target.strip(), anchor.strip()))

    return refs


def _map_target_to_module(rel_path: str) -> str:
    """Project a repo-relative target path onto its owning module name.

    Best-effort, path-prefix driven — the same path-to-name convention the crawl
    uses. A target under ``marketplace/bundles/{X}/`` maps to bundle module ``X``;
    a target under the doc tree maps to ``documentation``; anything else maps to
    the root module. A mis-mapped target for a genuinely-present file surfaces as
    an ``unknown-endpoint`` in the resolver (reported, never a silent wrong edge),
    and a mis-mapped target for an ABSENT file is reported as ``unresolved-target``
    regardless of the name, so the mapping's imperfection never hides a dangling
    reference.
    """
    # ``removeprefix`` strips one exact leading ``./`` — never a character-set
    # left-strip of the dot-slash pair, which would eat every leading ``.``/``/``
    # and rewrite ``.claude/x`` into a different in-tree path.
    normalized = rel_path.replace('\\', '/').removeprefix('./')
    if normalized.startswith(_MARKETPLACE_PREFIX):
        remainder = normalized[len(_MARKETPLACE_PREFIX):]
        bundle = remainder.split('/', 1)[0]
        if bundle:
            return bundle
    if normalized == 'doc' or normalized.startswith('doc/'):
        return _DOC_MODULE
    return _ROOT_MODULE


def _resolve_one(
    ref_file: Path,
    project_root: Path,
    target: str,
    anchor: str,
    self_anchors: set[str],
    anchor_cache: dict[str, set[str]],
) -> tuple[str, bool]:
    """Resolve one ``(target, anchor)`` reference to a ``(target_module, resolved)`` pair.

    A same-file reference (empty ``target``) resolves against ``self_anchors``. A
    cross-file reference resolves the relative ``target`` against ``ref_file``'s
    directory; ``resolved`` is True only when the target file exists AND — when an
    ``anchor`` is present — the anchor exists in the target file. ``target_module``
    is the best-effort owning module of the resolved-or-intended target path.
    """
    if not target:
        # Same-file anchor reference. Its owner is the documentation module.
        return _DOC_MODULE, (anchor.lower() in self_anchors if anchor else True)

    resolved_path = (ref_file.parent / target).resolve()
    try:
        rel = resolved_path.relative_to(project_root).as_posix()
    except ValueError:
        # Target escapes the repository root — treat as an unresolved external.
        rel = target
    target_module = _map_target_to_module(rel)

    if not resolved_path.exists():
        return target_module, False
    if not anchor:
        return target_module, True

    # Anchored reference into an existing file: the anchor must resolve too.
    key = str(resolved_path)
    if key not in anchor_cache:
        try:
            anchor_cache[key] = (
                extract_anchors(resolved_path.read_text(encoding='utf-8'))
                if resolved_path.suffix in _DOC_SUFFIXES
                else set()
            )
        except OSError:
            anchor_cache[key] = set()
    # A non-doc target file has no extractable anchors; a fragment into it is
    # treated as resolved (the file exists), since anchor semantics only apply to
    # the doc corpus this engine understands.
    if resolved_path.suffix not in _DOC_SUFFIXES:
        return target_module, True
    return target_module, anchor.lower() in anchor_cache[key]


def build_doc_component_refs(project_root: str, doc_module_rel: str) -> list[dict[str, Any]]:
    """Materialize the documentation module's outbound ``component_refs``.

    Walks every ``.adoc`` / ``.md`` file under ``doc_module_rel``, extracts each
    outbound cross-document reference, resolves it (file existence + anchor
    existence), projects the target onto a module name, and returns the
    deduplicated ``{target_bundle, dep_type, resolved}`` triples — the same schema
    the markdown/python resolvers consume, so the documentation resolver joins over
    it identically. ``dep_type`` is always ``path``.

    Deduplication is on the ``(target_bundle, dep_type, resolved)`` triple, so the
    list stays proportional to the module count. A doc corpus with no outbound
    references returns an empty list (never a missing key).

    Reads files from disk — this is discovery-time work, never resolver-time. An
    unreadable file contributes nothing rather than aborting the walk.
    """
    root = Path(project_root).resolve()
    doc_root = (root / doc_module_rel).resolve()
    if not doc_root.is_dir():
        return []

    triples: set[tuple[str, str, bool]] = set()
    anchor_cache: dict[str, set[str]] = {}

    doc_files = sorted(
        p
        for suffix in _DOC_SUFFIXES
        for p in doc_root.rglob(f'*{suffix}')
        if 'target' not in p.parts and not p.is_symlink()
    )
    for doc_file in doc_files:
        try:
            text = doc_file.read_text(encoding='utf-8')
        except OSError:
            continue
        self_anchors = extract_anchors(text)
        for target, anchor in extract_references(text):
            target_module, resolved = _resolve_one(
                doc_file, root, target, anchor, self_anchors, anchor_cache
            )
            triples.add((target_module, 'path', resolved))

    return [
        {'target_bundle': target_bundle, 'dep_type': dep_type, 'resolved': resolved}
        for target_bundle, dep_type, resolved in sorted(triples)
    ]
