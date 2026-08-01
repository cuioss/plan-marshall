#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Private helper owning the N-attributor claim merge for the Axis-D seam.

Core owns the merge, the provenance, and the resolution order; it owns none of
the claims. This module is that merge: it calls each discovered
``PathAttributionBase`` implementor, validates and unions the claim sets, and
returns both the merged claims and a per-attributor report. It also owns
:func:`lookup_claim`, the single shared containment matcher both consuming call
sites use, so neither re-derives the predicate.

Claim side and candidate side canonicalize path spelling through ONE shared
normalizer. Two sides comparing paths under different spelling rules is how a
covered path answers a confident ``None``, so the symmetry is a property of the
module rather than a convention its callers are trusted to uphold.

Unlike the Axis-C edge union, a conflict IS expressible here. A claim is a
**keyed mapping** — the normalized path prefix is the identity and the claimed
module is the value — so two attributors naming one prefix but different modules
have genuinely disagreed. That case emits NO claim and a reported collision;
guessing an iteration-order winner would present a non-deterministic answer as a
confident one. Two attributors naming one prefix and the SAME module have not
disagreed — they have corroborated — so those collapse to one claim carrying both
producer ids.

See ``extension-api/standards/ext-point-path-attribution.md`` for the complete
four-face contract, the keyed-mapping merge semantics, the ambiguous-ownership
obligation, and the longest-prefix-is-resolution-order note this module
implements.
"""

from typing import Any

from plan_logging import log_entry

_STATUS_OK = 'ok'
_STATUS_ERROR = 'error'

#: Prefix marking a note the MERGE appended, distinguishing it from the notes the
#: attributor itself returned. Without the prefix a reader of the report cannot
#: tell whether the attributor suppressed the claim deliberately or the merge
#: discarded it.
_MERGE_NOTE_PREFIX = 'merge: '

#: Normalized prefixes that claim the whole tree (or nothing at all) rather than a
#: bounded subtree. A claim on one of these is dropped: it would attribute every
#: path in the repository to a single module, which is never a legitimate
#: ownership declaration.
_ROOT_ISH_PREFIXES = frozenset({'', '.', '..'})

#: First path segment marking a prefix that traverses OUT of the repository root.
#: A claim rooted there names a location no repo-relative candidate path can fall
#: inside, so admitting it would raise ``claim_count`` for a claim that can never
#: match — a confident number standing for nothing.
_TRAVERSAL_SEGMENT = '..'


def _normalize_spelling(raw: str) -> str:
    """Return ``raw`` in the one canonical spelling both sides of the seam compare in.

    The single shared spelling normalizer, consumed by BOTH :func:`_normalize_prefix`
    (the claim side) and :func:`lookup_claim` (the candidate side). Sharing ONE
    function is the whole point: the two sides applying DIFFERENT spelling rules is
    precisely how a covered path resolves to a confident ``None`` — a claim on
    ``.plan`` failing to match a candidate spelled ``./.plan/local`` or with a
    backslash separator. Because ``which-module`` is the mandated structured-query
    surface, callers hand it paths in whatever spelling they already hold, so the
    seam must absorb the spelling difference rather than oblige the caller to.

    Normalization is spelling-only: surrounding whitespace removed, backslashes
    folded to forward slashes, leading ``./`` runs collapsed, trailing slashes
    stripped. It resolves no symlink and touches no filesystem, and it deliberately
    does NOT collapse ``..`` segments — whether a traversing path is admissible is a
    POLICY question each side answers for itself, not a spelling question.

    Args:
        raw: A path or path prefix in any spelling.

    Returns:
        The canonically-spelled path.
    """
    spelling = raw.strip().replace('\\', '/')
    while spelling.startswith('./'):
        spelling = spelling[2:]
    return spelling.rstrip('/')


def _normalize_prefix(raw: str) -> str:
    """Return the identity key for a raw claimed path prefix.

    The identity a claim is keyed on is the prefix in the shared canonical spelling
    (:func:`_normalize_spelling`) — so ``'.plan'``, ``'.plan/'``, ``' .plan '`` and
    ``'./.plan'`` are ONE identity rather than four, and two attributors that
    spelled the same directory differently corroborate instead of silently
    producing two claims.

    A dot-relative prefix such as ``'./doc'`` is NORMALIZED to ``'doc'``, not
    dropped: its ownership intent is unambiguous, and normalizing it makes the
    claim real rather than discarding a stated declaration. A TRAVERSING prefix —
    one whose first segment is ``..`` — is the case that genuinely cannot be
    rescued: it names a location outside the repository root, so no repo-relative
    candidate path can ever fall inside it. Admitting it would raise
    ``claim_count`` for a claim no lookup can ever match, so it is dropped AND
    reported through the caller's blank-prefix branch.

    Args:
        raw: The path prefix exactly as the attributor declared it.

    Returns:
        The normalized identity key, or the empty string when the prefix is
        root-ish (blank, ``.``, ``..``, or bare ``/``) or traverses out of the
        repository root, and is therefore not a bounded-subtree claim.
    """
    prefix = _normalize_spelling(raw)
    if prefix in _ROOT_ISH_PREFIXES:
        return ''
    if prefix.split('/', 1)[0] == _TRAVERSAL_SEGMENT:
        return ''
    return prefix


def _coerce_pair(candidate: Any) -> tuple[str, str] | None:
    """Return ``candidate`` as a ``(path_prefix, module_name)`` string pair, or ``None``.

    An attributor is an extension-contributed implementor, so its return value is
    validated rather than trusted: a claim that is not a two-element sequence of
    strings is dropped instead of propagating a malformed entry into the ownership
    map.
    """
    if isinstance(candidate, str) or not isinstance(candidate, (tuple, list)):
        return None
    if len(candidate) != 2:
        return None
    prefix, module_name = candidate
    if not isinstance(prefix, str) or not isinstance(module_name, str):
        return None
    return prefix, module_name


def _coerce_notes(candidate: Any) -> list[str]:
    """Return ``candidate`` as a list of note strings.

    ``notes[]`` is the required channel for any condition that suppressed a claim,
    so a malformed notes value is normalized rather than dropped silently: a bare
    string becomes a one-element list, and non-string items are rendered via
    ``str`` so the condition still reaches the report.
    """
    if candidate is None:
        return []
    if isinstance(candidate, str):
        return [candidate]
    if isinstance(candidate, (tuple, list)):
        return [item if isinstance(item, str) else str(item) for item in candidate]
    return [str(candidate)]


def merge_path_claims(
    attributors: list[dict[str, Any]],
    module_names: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge every attributor's claim set into one provenance-carrying claim list.

    Calls each attributor's ``claim_paths``, unpacking the ``(claims, notes)``
    return and carrying that attributor's ``notes`` onto its report. Each candidate
    claim must survive three validity filters before it is unioned:

    1. **The claim must be well-formed** — a candidate that is not a two-element
       sequence of strings is dropped rather than propagated into the map.
    2. **The prefix must bound a subtree inside the repository** — a blank or
       root-ish prefix would attribute the whole repository to one module, and a
       traversing prefix (first segment ``..``) names a location outside the repo
       root that no repo-relative path can fall inside. Both are dropped. A merely
       dot-relative prefix (``./doc``) is NOT dropped — it is normalized to
       ``doc``, because its ownership intent is unambiguous.
    3. **The module must be a known module name** — a claim naming a module absent
       from ``module_names`` is dropped, so an attributor cannot invent an owner.

    **Every merge-side drop appends its own note.** The three filters above are the
    merge suppressing a claim, so each one records why, prefixed with ``merge:`` to
    keep it distinguishable from the notes the attributor itself returned. Without
    that, an attributor whose every candidate the merge discarded would report
    ``status: ok``, ``claim_count: 0`` and an empty ``notes`` list — a
    confident-looking zero indistinguishable from "ran and legitimately claimed
    nothing", which is exactly the vacuity this extension point exists to
    eliminate.

    Surviving claims are unioned keyed on the **normalized prefix**:

    - Same key, same module → ONE claim whose ``producers[]`` is the sorted list of
      contributing attributor ids. The attributors corroborated.
    - Same key, DIFFERENT modules → **no claim at all** for that prefix, plus a
      collision note naming every contending module appended to each implicated
      attributor's report. Resolving by iteration order would drop one well-formed
      ownership claim non-deterministically; abstaining and reporting keeps a
      disputed prefix distinguishable from an unclaimed one.

    Differently-scoped prefixes that both contain a path (``.plan`` and
    ``.plan/local``) are NOT a collision — they are two well-formed claims that
    :func:`lookup_claim` orders by prefix length at query time.

    An attributor that raises reports ``status: error`` with ``claim_count: 0`` and
    contributes no claims; its siblings still contribute. A ``claims`` value that is
    not a usable collection — a truthy non-iterable, or a bare string that would
    iterate into characters rather than pairs — is the same broken-implementor
    condition and degrades to that same error report rather than escaping as an
    uncaught ``TypeError``, because the claims are materialized inside the same
    guard that wraps the hook call. A FALSY non-iterable (``0``, ``None``, ``[]``)
    still means "claimed nothing" and reports ``status: ok``. An errored attributor
    never aborts the merge — a single broken implementor must not blank the
    ownership map.

    Zero attributors is a first-class, non-error outcome: the return is
    ``([], [])``, never an exception and never a fabricated claim. The caller
    distinguishes "no attributor ran" from "N attributors ran and none claimed
    this path" by the length of the returned report list.

    Args:
        attributors: Discovered attributor records from
            ``extension_discovery.discover_path_attributors()`` — each a
            ``{origin, id, module}`` dict.
        module_names: The authoritative known-module names every claim's module is
            validated against. Any iterable of strings (the keys of a module map,
            a list, or a set).

    Returns:
        A ``(claims, attributor_reports)`` tuple. ``claims`` is a list of
        ``{'prefix': str, 'module': str, 'producers': list[str]}`` dicts sorted by
        ``(prefix, module)`` for byte-stable output, each carrying a non-empty
        ``producers``. ``attributor_reports`` is one
        ``{'id', 'claim_count', 'status', 'notes'}`` dict per attributor, in the
        order the attributors were supplied.
    """
    known_modules = set(module_names)
    # Keyed on (normalized prefix, module); value is the set of contributing ids.
    producers_by_claim: dict[tuple[str, str], set[str]] = {}
    notes_by_id: dict[str, list[str]] = {}
    status_by_id: dict[str, str] = {}
    ordered_ids: list[str] = []

    for record in attributors:
        attributor_id = record.get('id', '')
        ordered_ids.append(attributor_id)

        # The module lookup and the hook call share one guarded block: a record
        # missing its ``module`` key is as much a broken-implementor condition as
        # a raising ``claim_paths``, and both resolve to the same error report
        # rather than aborting the merge.
        try:
            raw_claims, raw_notes = record['module'].claim_paths()
            # Materialize the claims collection INSIDE the guard. ``raw_claims``
            # is extension-contributed, so a truthy non-iterable (``123``) — or a
            # bare string, which iterates into characters rather than pairs — is a
            # broken-implementor condition of exactly the same class as a raising
            # ``claim_paths()``. Iterating it outside the guard would let a
            # TypeError escape and blank the whole ownership map, which is the one
            # outcome this merge exists to prevent.
            if isinstance(raw_claims, str):
                raise TypeError(
                    'claim_paths() returned a str as its claims collection; '
                    'expected an iterable of (path_prefix, module_name) pairs'
                )
            candidates = list(raw_claims or [])
        except Exception as e:
            log_entry(
                'script',
                None,
                'WARNING',
                f'[EXTENSION] claim_paths() failed for path attributor {attributor_id}: {e}',
            )
            status_by_id[attributor_id] = _STATUS_ERROR
            notes_by_id[attributor_id] = [f'claim_paths() failed: {e}']
            continue

        status_by_id[attributor_id] = _STATUS_OK
        notes = _coerce_notes(raw_notes)
        for candidate in candidates:
            pair = _coerce_pair(candidate)
            if pair is None:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped malformed candidate {candidate!r} — '
                    f'not a two-element pair of (path_prefix, module_name) strings'
                )
                continue
            raw_prefix, module_name = pair
            prefix = _normalize_prefix(raw_prefix)
            if not prefix:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped claim ({raw_prefix!r} -> {module_name}) — '
                    f'blank, root-ish, or repo-escaping prefix does not bound a subtree '
                    f'inside the repository'
                )
                continue
            if module_name not in known_modules:
                notes.append(
                    f'{_MERGE_NOTE_PREFIX}dropped claim ({prefix} -> {module_name}) — '
                    f'unknown module name'
                )
                continue
            producers_by_claim.setdefault((prefix, module_name), set()).add(attributor_id)
        notes_by_id[attributor_id] = notes

    modules_by_prefix: dict[str, set[str]] = {}
    for prefix, module_name in producers_by_claim:
        modules_by_prefix.setdefault(prefix, set()).add(module_name)
    contested_prefixes = {
        prefix for prefix, modules in modules_by_prefix.items() if len(modules) > 1
    }

    # The ambiguous-ownership obligation: a contested prefix yields no claim, and
    # every attributor that contended for it learns why from its own report. A
    # suppressed claim with an empty ``notes`` list is the failure this loop exists
    # to prevent.
    for prefix in sorted(contested_prefixes):
        contenders = ', '.join(sorted(modules_by_prefix[prefix]))
        note = (
            f'{_MERGE_NOTE_PREFIX}suppressed claim on prefix {prefix!r} — contested by '
            f'more than one module ({contenders}); a prefix two attributors assign to '
            f'different modules yields no attribution'
        )
        implicated = {
            attributor_id
            for (claim_prefix, _), ids in producers_by_claim.items()
            if claim_prefix == prefix
            for attributor_id in ids
        }
        for attributor_id in sorted(implicated):
            notes_by_id.setdefault(attributor_id, []).append(note)

    claims: list[dict[str, Any]] = []
    claim_count_by_id: dict[str, int] = {}
    for prefix, module_name in sorted(producers_by_claim):
        if prefix in contested_prefixes:
            continue
        producers = producers_by_claim[(prefix, module_name)]
        claims.append({'prefix': prefix, 'module': module_name, 'producers': sorted(producers)})
        for attributor_id in producers:
            claim_count_by_id[attributor_id] = claim_count_by_id.get(attributor_id, 0) + 1

    reports = [
        {
            'id': attributor_id,
            'claim_count': claim_count_by_id.get(attributor_id, 0),
            'status': status_by_id.get(attributor_id, _STATUS_OK),
            'notes': notes_by_id.get(attributor_id, []),
        }
        for attributor_id in ordered_ids
    ]
    return claims, reports


def lookup_claim(path: str, claims: list[dict[str, Any]]) -> str | None:
    """Return the module owning ``path``, or ``None`` when no claim contains it.

    The single shared containment matcher for the Axis-D seam, so every consuming
    call site resolves ownership identically rather than re-deriving the predicate.

    ``path`` is first put into the canonical spelling via the SAME
    :func:`_normalize_spelling` the claim side uses, so ``'./.plan/local'``,
    ``'.plan\\local'`` and ``'.plan/local/'`` all resolve through a ``.plan`` claim.
    Normalizing only one side is the defect this shared call closes: the claim side
    would canonicalize while the candidate side compared raw, and a covered path
    handed over in an unexpected-but-equivalent spelling would answer a confident
    ``None``. Normalization is spelling-only, so it does not weaken the nest-inside
    guard below — ``'./.plans/x'`` normalizes to ``'.plans/x'`` and still does not
    match a ``.plan`` claim.

    Containment is **prefix nesting, not fnmatch**::

        path == prefix or path.startswith(prefix + '/')

    The trailing-separator half is the nest-inside guard: a path belongs to a claim
    only when it nests inside the claimed directory, so ``.plans/x`` does NOT
    resolve through a ``.plan`` claim even though it shares the string prefix. An
    fnmatch ``**/``-shaped pattern is the wrong tool for the mirror-image reason —
    a single ``*`` spans ``/`` in fnmatch, and a ``**/``-prefixed glob would fail to
    match the bare root segment ``.plan`` itself.

    When several claims contain the path, the **longest** prefix wins. That is the
    resolution ORDER, not a tie-break over a collision: ``.plan`` owned by one
    module and ``.plan/local`` owned by another is a well-formed claim set with no
    ambiguity, and the merge has already suppressed any prefix two attributors
    genuinely disputed. Two distinct prefixes of equal length cannot both contain
    one path, so no further tie-break is reachable.

    Args:
        path: A repo-relative candidate path, in any spelling — it is canonicalized
            here rather than assumed already normalized.
        claims: The merged claim list from :func:`merge_path_claims`.

    Returns:
        The claimed module name for the longest containing prefix, or ``None`` when
        no claim contains ``path``.
    """
    path = _normalize_spelling(path)
    best_module: str | None = None
    best_length = -1
    for claim in claims:
        prefix = claim['prefix']
        if path == prefix or path.startswith(prefix + '/'):
            if len(prefix) > best_length:
                best_length = len(prefix)
                best_module = claim['module']
    return best_module
