# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-component target scoping — the ``targets:`` frontmatter filter.

A capability that exists only on some assistants has no good home in a
build that ships every component everywhere: it either lands on targets
where it cannot work, or it is forced into a runtime no-op. This module
is the fourth home the placement model names — a component declares the
targets it ships to, and on every other target it is simply ABSENT.

Contract
--------
A component (an ``agents/*.md``, a ``commands/*.md``, or a skill's
``SKILL.md``) MAY declare a top-level ``targets:`` frontmatter field:

.. code-block:: yaml

    ---
    name: tools-fix-intellij-diagnostics
    description: ...
    targets: [claude]
    ---

* **Field absent** — the component ships to every target. This is the
  default and the overwhelmingly common case; no existing component
  changes behaviour.
* **Field present** — the component is emitted only by a target whose
  registry name the list contains.

A skill's declaration governs the whole skill DIRECTORY, since a skill is
a directory whose ``SKILL.md`` is its manifest. An agent's or a command's
governs that one file. Files *inside* a skill are not individually
scopable — that would need a file-level mechanism this one deliberately
is not.

Fail closed
-----------
Silent exclusion is prohibited, so every declaration is validated the
moment it is read and an invalid one aborts the build
(:class:`TargetScopeError`):

* a name absent from ``TARGET_REGISTRY`` — almost always a typo, and one
  that would otherwise silently narrow the component's reach;
* an empty list — a component shipped nowhere is an authoring error, not
  an intent; omitting the field is how you say "everywhere";
* a list naming ONLY targets that emit no component tree (``pr-agent``
  derives a single reviewer configuration from skill rules, so it has no
  component to filter) — such a declaration passes a registry-membership
  check while still shipping the component nowhere;
* a value spanning more than one line — this parser reads a value from one
  physical line, so accepting one would silently narrow the scope to
  whatever fitted on that line.

That last rejection is ONE condition, tested at two sites that cannot both
apply: an INLINE value that is not a flow sequence and is followed by an
indented line, or a key with no inline value whose indented continuation is
neither a ``- `` item nor a flow sequence. (A ``- `` block IS followed by an
indented line and is accepted, so the condition is about the value's shape,
not about indentation alone.) Three names appear in the message because
three different YAML constructs produce it — a plain scalar continued across
lines, a quoted scalar continued across lines, and a block scalar
(``>``/``|``) — and naming the wrong one sends the author looking for a
defect that is not in their file. Which name is chosen is a DIAGNOSIS made
after the decision to reject; misclassifying cannot change whether the build
fails, only what the failure calls the construct.

Adding a rejection means adding it here **and** in the doctor rule that
mirrors this validation, its rule-catalog and rule-provenance rows, and the
authoring standards' validation table. A behaviour change has landed in the
code alone before; every one of those registers then stated a count that was
one short.

The valid names are derived from ``TARGET_REGISTRY`` and from each
target's own :attr:`~marketplace.targets.base.TargetBase.emits_bundle_tree`
capability, never enumerated here, so a target registered later needs no
edit to this module to be a legal value or to be exempt.

What derivation does NOT give you
---------------------------------
That derivation governs which names are LEGAL. It does not make a new
target honour the filter: ENFORCEMENT is per-target wiring — each
component-tree target calls :func:`emits_to` (or
:func:`excluded_emission_roots`) from its own emit path, and a target that
simply never called it would emit every scoped-out component with nothing
here to stop it. The obligation is stated on
:meth:`~marketplace.targets.base.TargetBase.generate` and in
``marketplace/targets/README.md`` § "Adding a New Target", and it is pinned
by a test that generates through EVERY registered component-tree target and
asserts a scoped-out component is absent from its output — so an unwired
target fails the suite rather than shipping quietly.

Degradation
-----------
A component file that cannot be read or decoded yields "no declaration",
i.e. the pre-existing emit-everywhere behaviour.

That is a choice between two bad outcomes, not a safe default, and an
earlier version of this paragraph argued only one side of it. Failing open
also SHIPS a scoped component onto a target it excluded — the same silent
widening this module treats as a defect elsewhere, and the reason an
unrecognised quoted key was fixed rather than tolerated. The vanish
direction is judged the worse of the two: a component missing from a target
it belongs on is absent from the output and breaks a runtime that expects
it, while a surplus component is present and inspectable. So a read fault
degrades towards shipping. The unreadable file itself still fails wherever
it is actually consumed.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

#: Frontmatter field a component uses to declare the targets it ships to.
TARGET_SCOPE_FIELD = 'targets'

#: Approximates "a new key starts here" — an unquoted, letter-or-underscore
#: initial identifier at column 0 followed by a colon. It bounds the fold of
#: an unclosed flow sequence.
#:
#: Requiring an identifier before the colon is what distinguishes this from
#: the looser ``^[^\s#][^:]*:`` it replaced, which matched any non-indented,
#: non-comment line containing a colon anywhere. That looser form broke two
#: VALID declarations: a continuation line carrying a trailing comment with a
#: URL in it, and one whose value is a quoted string containing a colon. Both
#: are ordinary YAML, and both were then rejected naming a target nobody
#: wrote — the defect the fold exists to prevent. This form is still only an
#: approximation of a YAML key; see :func:`_join_flow_sequence` for what it
#: misses and why that is safe here.
_TOP_LEVEL_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_.-]*\s*:')

#: Bundle sub-directories holding single-file components, keyed to nothing
#: else: the file itself is both the declaration site and the emission unit.
_FILE_COMPONENT_DIRS = ('agents', 'commands')

#: Bundle sub-directory holding directory-shaped components. The manifest
#: is ``{skill_dir}/SKILL.md`` and the emission unit is ``{skill_dir}``.
_SKILLS_DIR = 'skills'

#: Manifest filename of a directory-shaped component.
_SKILL_MANIFEST = 'SKILL.md'


#: A whole YAML block-scalar header: the ``>`` or ``|`` indicator, plus an
#: optional indentation indicator and an optional chomping indicator in
#: either order. A value of this shape is not a plain scalar at all — the
#: indented lines beneath it are the value's content — so calling it "a
#: plain scalar continued across lines" is a wrong diagnosis on a
#: declaration a YAML reader parses perfectly well.
#:
#: The first version of this matched a fixed set of the six chomping
#: spellings and so misdiagnosed every header carrying an indentation
#: indicator (``|2``, ``>3-``, ``|-2``). The grammar admits 96 headers — two
#: indicators × {bare, indent 1-9, chomp, and both orders of the two} — so
#: that set covered 6 and misdiagnosed **90**, under the very message it was
#: added to remove. This form matches all 96, and over-matches only the ten
#: ``0``-bearing spellings, which YAML rejects as headers anyway.
_BLOCK_SCALAR_HEADER_RE = re.compile(r'^[>|](?:[0-9][-+]?|[-+][0-9]?)?$')

#: A frontmatter fence line: exactly three hyphens, then only spaces or
#: tabs. Trailing whitespace on a fence is invisible in an editor, and the
#: tree's own canonical frontmatter reader (``_dep_detection`` in the
#: ``tools-marketplace-inventory`` skill, which the plugin-doctor imports)
#: accepts it — so refusing it here made the two parsers
#: disagree about whether such a file has frontmatter at all, and a
#: ``targets:`` declaration beneath a space-suffixed fence went unread.
#:
#: Parity is restored for trailing whitespace and for nothing else. That
#: reader matches ``\n---`` as a PREFIX, so it also treats ``----`` as a
#: closing fence where this one does not, and the two still disagree there.
#: Adopting the prefix match would re-open the defect the whole-line match
#: exists to prevent: a value containing three hyphens would truncate the
#: block and hide every field after it.
_OPEN_FENCE_RE = re.compile(r'^---[ \t]*\n')
_CLOSE_FENCE_RE = re.compile(r'\n---[ \t]*(?:\n|$)')

#: The three YAML constructs that can produce a value spanning more than one
#: line. Naming them is a DIAGNOSIS, never a decision — see
#: :func:`_multiline_shape`.
_SHAPE_BLOCK_SCALAR = 'block-scalar'
_SHAPE_QUOTED_SCALAR = 'quoted-scalar'
_SHAPE_PLAIN_SCALAR = 'plain-scalar'

#: How each shape is named in the build failure. The remedy is the same for
#: all three, so only the noun differs — but a YAML reader parses each of
#: them perfectly well, and an author told they wrote the wrong construct
#: goes looking for a defect that is not in their file.
_MULTILINE_NOUN = {
    _SHAPE_BLOCK_SCALAR: 'a YAML block scalar (`>` or `|`), whose value is the indented '
                         'lines beneath it',
    _SHAPE_QUOTED_SCALAR: 'a quoted scalar continued across lines',
    _SHAPE_PLAIN_SCALAR: 'a plain scalar continued across lines',
}


class _MultilineValue(Exception):
    """Internal marker: the value spans more than one physical line.

    Carries the name of the construct it is written in (one of the
    ``_SHAPE_*`` constants) so the diagnostic names the shape the author
    actually wrote. Raised by the parser, which has no component path, and
    turned into a :class:`TargetScopeError` by :func:`read_target_scope`,
    which does.
    """

    def __init__(self, shape: str) -> None:
        super().__init__(shape)
        self.shape = shape


class TargetScopeError(RuntimeError):
    """Raised when a component's ``targets:`` declaration is invalid.

    Carries the offending component path and the offending value, so the
    build failure names the file an author has to edit.
    """


# ---------------------------------------------------------------------------
# Registry-derived target sets
# ---------------------------------------------------------------------------


def registered_target_names() -> frozenset[str]:
    """Return every registered target's registry name.

    The import is deferred to call time. This module is imported from inside
    the target sub-packages that ``marketplace.targets`` imports for their
    registration side-effect, so a module-level ``from marketplace.targets
    import TARGET_REGISTRY`` would bind the registry before any target had
    registered into it. That happens to work — the registry is mutated in
    place rather than rebound — but it makes correctness rest on that detail.
    Reading it at call time does not.
    """
    from marketplace.targets import TARGET_REGISTRY  # noqa: PLC0415

    return frozenset(TARGET_REGISTRY)


def component_tree_target_names() -> frozenset[str]:
    """Return the registry names of targets that emit a component tree.

    Derived from each target's ``emits_bundle_tree`` capability rather than
    enumerated. The capability is an instance property, so each registered
    class is constructed — every target is constructible with no arguments
    (the one target taking a selection defaults it).
    """
    from marketplace.targets import TARGET_REGISTRY  # noqa: PLC0415

    return frozenset(
        name for name, target_cls in TARGET_REGISTRY.items() if target_cls().emits_bundle_tree
    )


# ---------------------------------------------------------------------------
# Frontmatter extraction
# ---------------------------------------------------------------------------


def _frontmatter_block(text: str) -> str | None:
    """Return the leading ``---``-fenced block's inner text, or ``None``.

    A UTF-8 BOM is stripped first: ``read_text`` leaves it in the string, and
    a file carrying one would otherwise look like it had no frontmatter at
    all — which reads as "declares no scope" and silently ships the component
    everywhere.

    Each fence is matched as a whole LINE rather than as a bare ``---``
    substring, so a value that itself contains three hyphens does not
    truncate the block and hide the fields after it. Trailing spaces or tabs
    on either fence are accepted \u2014 see :data:`_OPEN_FENCE_RE`.
    """
    text = text.lstrip('\ufeff')
    open_fence = _OPEN_FENCE_RE.match(text)
    if open_fence is None:
        return None
    start = open_fence.end()
    # From start - 1, so the newline ending the opening fence can also serve
    # as the newline opening the closing one. What that changes is a block
    # closed immediately (`---` / `---` / more text): the block is then EMPTY,
    # and any keys below the second fence are body, not frontmatter. Searching
    # from `start` would skip that fence and read them as fields.
    close_fence = _CLOSE_FENCE_RE.search(text, start - 1)
    if close_fence is None:
        return None
    return text[start:close_fence.start()]


def _strip_comment(value: str) -> str:
    """Drop a trailing YAML comment from a scalar or flow-sequence value.

    ``targets: [claude]  # note`` and ``targets: claude  # note`` both carry a
    comment the value parser would otherwise fold into a token, producing a
    diagnostic that names ``[claude] # note`` as the unknown target. A ``#``
    is a comment only when it opens a token, which is what YAML requires and
    what keeps a hypothetical name containing ``#`` intact.
    """
    head, sep, _tail = value.partition('#')
    if not sep:
        return value
    if head and not head[-1].isspace():
        return value
    return head.rstrip()


def _join_flow_sequence(value: str, rest: list[str]) -> str:
    """Return ``value``, extended across the lines a flow sequence spans.

    ``targets: [claude,`` continued on the next line is one value, not a
    truncated one. Reading only the first physical line yields the token
    ``[claude`` and a diagnostic naming a target nobody wrote, so the
    continuation lines are folded in until the closing bracket.

    A sequence that never closes is malformed YAML, and folding in the rest
    of the block would make the diagnostic name the following FIELDS as
    targets — the same "names a target nobody wrote" defect one shape over.
    So the fold stops at the first non-indented line matching
    :data:`_TOP_LEVEL_KEY_RE`.

    That pattern is a HEURISTIC for "a new key starts here", not a YAML key
    parser, and it is wrong in both directions: a digit-initial or quoted key
    (``2fa: no``, ``"q": v``) does not match it and is folded in, while a
    flow item whose first token ends in a colon (a bare ``https://…`` at
    column 0) does match it and ends the fold early.

    Both misreads are safe HERE, and the reason is specific rather than
    hopeful: in the bracketed form every misread leaves the joined value
    holding a token no registered name matches — an absorbed ``2fa: no``, or
    a truncated ``[claude`` — so :func:`_validate` rejects it and the build
    stops. A misread can widen or truncate the text that gets REJECTED; it
    cannot produce a scope the author did not write, and the reason is
    structural rather than statistical:

    * a fold that runs too far joins the surplus line in with a **space**
      (``' '.join``), and no registered target name contains a space, so any
      token drawn from more than one source line cannot match one;
    * a fold that stops too early leaves the value opening ``[`` with no
      closing ``]``, which :func:`_split_inline` therefore does not unwrap,
      so the first token keeps its bracket.

    Both land outside the registry, so :func:`_validate` rejects. The space
    is the load-bearing half: an earlier version of this paragraph claimed
    the surplus always carries a colon, which is false — absorbing a plain
    continuation line yields ``opencode opencode``, no colon in sight. It is
    still rejected, but for the reason stated here rather than that one.

    This is a property of THIS fold only — a duplicate top-level key
    resolves to the first declaration here and to the last in YAML, and both
    spellings may be bracketed.
    """
    head = _strip_comment(value)
    if not head.startswith('[') or ']' in head:
        return head
    parts = [head]
    for line in rest:
        if _TOP_LEVEL_KEY_RE.match(line):
            break
        segment = _strip_comment(line.strip())
        if segment:
            parts.append(segment)
        if ']' in segment:
            break
    return ' '.join(parts)


def _split_inline(value: str) -> list[str]:
    """Split an inline scalar or flow-sequence value into tokens.

    Accepts both ``[a, b]`` and the bare ``a, b`` spelling. ``[]`` yields the
    empty list, which the validator rejects — an empty declaration is an
    authoring error rather than a silent no-op.
    """
    inner = _strip_comment(value)
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]
    return [token.strip().strip('"').strip("'") for token in inner.split(',') if token.strip()]


def _collect_block_items(lines: list[str]) -> list[str]:
    """Collect a YAML block sequence's items, stopping at the first non-item.

    A blank line and a whole-line ``#`` comment are skipped rather than
    ending the sequence: ending there would read a commented list as an
    EMPTY one and reject a component that declares its targets perfectly
    well, under a message describing a file that does not exist.
    """
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if not stripped.startswith('-'):
            break
        item = _strip_comment(stripped[1:].strip()).strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _unquote_key(key: str) -> str:
    """Return ``key`` with a MATCHED pair of surrounding quotes removed.

    ``"targets": [claude]`` is the same declaration as ``targets: [claude]``
    to any YAML reader, and not recognising it fails OPEN — the component
    ships everywhere with its declaration unread.

    The pair must MATCH. ``str.strip`` takes a character set rather than a
    prefix, so stripping quotes with it also turns ``targets"`` into
    ``targets`` — and that key is NOT ``targets`` to YAML, so a component
    that declared no scope would be silently narrowed to someone else's
    list. That is the same defect in the opposite direction, and the one the
    module docstring calls prohibited, so the quotes are removed only when
    they genuinely surround the key.
    """
    key = key.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in {'"', "'"}:
        return key[1:-1]
    return key


def _first_meaningful(lines: list[str]) -> tuple[int, str]:
    """Return ``(index, line)`` of the first line that carries structure.

    Blank lines and whole-line ``#`` comments carry none: YAML ignores both
    when deciding what a block contains and how deeply it is indented.
    ``(-1, '')`` when there is no such line.
    """
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            return index, line
    return -1, ''


def _dedent_block(block: str) -> list[str]:
    """Split ``block`` into lines, dedented by the common indent of its keys.

    Top-level is relative to the BLOCK, not to column zero: a frontmatter
    block whose every key is indented by the same amount has all of them at
    top level, and YAML reads it that way. Scanning for column-zero keys
    instead reported "no declaration" — the component then shipped to every
    target with its declaration unread, and an INVALID declaration passed the
    build unreported.

    ``textwrap.dedent`` is not enough on its own, and that is not a detail:
    it ignores blank lines but not comment lines, so a single ``# note`` at
    column 0 above an indented block pinned the common prefix at zero and
    re-opened the whole hole. The indent is therefore computed over lines
    that carry structure — see :func:`_first_meaningful` — and comment lines
    are dedented along with everything else.

    A non-blank, non-comment line at column zero legitimately sets the indent
    to zero: YAML has a node there, so keys beneath it are nested and must
    stay skipped. The residue is exotic spellings that are neither a comment
    nor a node — a ``...`` document-end marker, a ``%YAML`` directive — which
    read as column-zero content and suppress the dedent.
    """
    lines = block.split('\n')
    indents = [
        len(line) - len(line.lstrip())
        for line in lines
        if line.strip() and not line.strip().startswith('#')
    ]
    if not indents:
        return lines
    common = min(indents)
    if not common:
        return lines
    return [line[common:] if line[:common].isspace() else line.lstrip() for line in lines]


def _has_continuation(rest: list[str]) -> bool:
    """Whether the next meaningful line continues the value rather than ending it.

    An indented line after a plain-scalar value is YAML's multi-line plain
    scalar: ``targets: claude,`` / ``  opencode`` is the single value
    ``claude, opencode``. Reading only the first physical line yields
    ``claude`` alone — the declared scope SILENTLY NARROWED by one target,
    which is the one direction this module must never fail in. Detecting it
    is what lets the caller reject rather than guess.
    """
    return _first_meaningful(rest)[1][:1].isspace()


def _multiline_shape(value: str) -> str:
    """Name the YAML construct a rejected multi-line value is written in.

    Diagnosis only. The caller has ALREADY decided to reject; this picks the
    noun the message uses, so a misclassification can change what the failure
    calls the construct but never whether the build fails. That separation is
    deliberate: every earlier version tangled the shape test into the
    rejection condition, and each one then changed the verdict on some valid
    input while trying to improve a sentence.

    ``value`` is the raw post-``strip`` value, not the comment-stripped one:
    a ``#`` inside a quoted scalar is content, and stripping it first would
    hide the quote this looks for.

    The quoted test asks only whether the opening quote recurs, so a value
    carrying an ESCAPED quote reads as terminated and falls through to
    ``plain-scalar``. Both spellings of that are valid YAML rather than
    malformed input, so the noun is simply wrong on them; they are rejected
    either way, and getting it right would need a second quote parser, which
    is the cure this module keeps trying not to re-invent.
    """
    if _BLOCK_SCALAR_HEADER_RE.match(_strip_comment(value)):
        return _SHAPE_BLOCK_SCALAR
    if value[:1] in {'"', "'"} and value.count(value[0]) < 2:
        return _SHAPE_QUOTED_SCALAR
    return _SHAPE_PLAIN_SCALAR


def _declared_tokens(text: str) -> list[str] | None:
    """Return the raw ``targets:`` tokens declared by ``text``, or ``None``.

    ``None`` means the field is absent (ship everywhere). An empty list means
    the field is present but names nothing, which the validator rejects.

    Only a TOP-LEVEL key counts — see :func:`_dedent_block` for what
    "top-level" means here. A ``targets:`` indented BEYOND its siblings still
    belongs to a nested mapping and is still a different field.

    The inline value is tested AFTER its comment is stripped. ``targets: # w``
    has no inline value to YAML, so the list that follows is the value;
    testing the raw text instead treated the comment as the value and
    reported the declaration empty.
    """
    block = _frontmatter_block(text)
    if block is None:
        return None
    lines = _dedent_block(block)
    for index, line in enumerate(lines):
        if line[:1].isspace():
            continue
        key, separator, value = line.partition(':')
        if not separator or _unquote_key(key) != TARGET_SCOPE_FIELD:
            continue
        head = _strip_comment(value.strip())
        rest = lines[index + 1:]
        if head:
            # ONE rejection, three diagnoses. A flow sequence spans lines
            # legitimately and is folded; anything else that is continued is
            # a value this parser reads only the first line of.
            if not head.startswith('[') and _has_continuation(rest):
                raise _MultilineValue(_multiline_shape(value.strip()))
            return _split_inline(_join_flow_sequence(head, rest))
        return _continued_value(rest)
    return None


def _continued_value(rest: list[str]) -> list[str]:
    """Read the value of a ``targets:`` key that carries none on its own line.

    Three shapes are legal and one is not:

    * a ``- `` block sequence — the ordinary block spelling;
    * a flow sequence opening on the next line (``targets:`` / ``  [a, b]``),
      which is one value spanning as many lines as it needs;
    * nothing at all, or a non-indented next line — an EMPTY declaration,
      which the validator rejects under its own name;
    * an indented line that is none of the above — a plain scalar whose
      content begins on the next line (``targets:`` / ``  claude`` is the
      value ``claude`` to YAML). Reporting that as "declares an empty list"
      describes a file the author did not write.
    """
    items = _collect_block_items(rest)
    if items:
        return items
    index, line = _first_meaningful(rest)
    if not line[:1].isspace():
        return items
    head = _strip_comment(line.strip())
    if head.startswith('['):
        return _split_inline(_join_flow_sequence(head, rest[index + 1:]))
    raise _MultilineValue(_SHAPE_PLAIN_SCALAR)


# ---------------------------------------------------------------------------
# Validation and the public predicate
# ---------------------------------------------------------------------------


def _named(names: frozenset[str] | list[str]) -> str:
    return ', '.join(sorted(names))


def _validate(tokens: list[str], path: Path) -> frozenset[str]:
    """Validate declared tokens against the registry, or raise.

    Every message names the offending component and the offending value, so
    the build failure is actionable without re-deriving what went wrong.
    """
    tree_targets = component_tree_target_names()
    if not tokens:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` declares an empty list — a component that '
            f'ships to no target is an authoring error. Omit the field to ship to every '
            f'target, or name at least one of: {_named(tree_targets)}.'
        )
    registered = registered_target_names()
    unknown = sorted(token for token in tokens if token not in registered)
    if unknown:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` names unknown target(s): {", ".join(unknown)}. '
            f'Registered targets are: {_named(registered)}.'
        )
    if not tree_targets.intersection(tokens):
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}: [{", ".join(tokens)}]` names only target(s) that '
            f'emit no component tree, so the component would ship nowhere. Name at least one '
            f'of: {_named(tree_targets)}.'
        )
    return frozenset(tokens)


def read_target_scope(path: Path) -> frozenset[str] | None:
    """Return the validated target scope declared by ``path``, or ``None``.

    Args:
        path: The component file — an ``agents/*.md``, a ``commands/*.md``,
            or a skill's ``SKILL.md``.

    Returns:
        The declared registry names, or ``None`` when the component declares
        no scope (ship to every target).

    Raises:
        TargetScopeError: The declaration is invalid — see the module
            docstring's fail-closed rules.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tokens = _declared_tokens(text)
    except _MultilineValue as multiline:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` is {_MULTILINE_NOUN[multiline.shape]}. '
            f'That is one YAML value spanning several lines, and this parser reads a value '
            f'from one physical line — so it would silently narrow the declared scope to '
            f'whatever fitted on the first line rather than read what you wrote. Write the '
            f'list explicitly — `{TARGET_SCOPE_FIELD}: [a, b]` or a `- ` block — so what '
            f'ships is what you wrote.'
        ) from None
    if tokens is None:
        return None
    return _validate(tokens, path)


def emits_to(path: Path, target_name: str) -> bool:
    """Whether the component at ``path`` is emitted by ``target_name``.

    Raises:
        TargetScopeError: The component's declaration is invalid. Validation
            runs on every read, so an invalid declaration aborts any run that
            calls this predicate. What that covers is every component-tree
            target's emit, plus the Claude target's validate-only mode (which
            re-walks each bundle's components for this check alone). A
            ``pr-agent``-only run does NOT validate: it opens skill manifests
            to harvest rule text, but it never asks whether a component is
            in scope, because it emits no component. The plugin-doctor
            ``targets-scope-invalid`` rule is the authoring-time net there.
    """
    scope = read_target_scope(path)
    return scope is None or target_name in scope


# ---------------------------------------------------------------------------
# Bundle-level helpers
# ---------------------------------------------------------------------------


def iter_component_manifests(bundle_dir: Path) -> Iterator[tuple[Path, Path]]:
    """Yield ``(manifest, emission_root)`` for every component in ``bundle_dir``.

    ``manifest`` is the file carrying the ``targets:`` declaration;
    ``emission_root`` is what the declaration governs — the component file
    itself for an agent or a command, the whole skill directory for a skill.
    Both are absolute paths.
    """
    for subdir_name in _FILE_COMPONENT_DIRS:
        subdir = bundle_dir / subdir_name
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.iterdir()):
            if path.is_file() and path.suffix == '.md' and not path.name.startswith('.'):
                yield path, path

    skills_dir = bundle_dir / _SKILLS_DIR
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            manifest = skill_dir / _SKILL_MANIFEST
            if skill_dir.is_dir() and manifest.is_file():
                yield manifest, skill_dir


def excluded_emission_roots(bundle_dir: Path, target_name: str) -> frozenset[Path]:
    """Return the bundle-relative paths ``target_name`` must NOT emit.

    An entry is either a component file (agent, command) or a skill
    directory; a caller skips a path that equals an entry or lies beneath
    one. Validating every component of the bundle — not only the excluded
    ones — is deliberate: an invalid declaration fails the build even when
    the generating target would have included it anyway.

    Raises:
        TargetScopeError: Some component in the bundle declares an invalid
            scope.
    """
    excluded: set[Path] = set()
    for manifest, emission_root in iter_component_manifests(bundle_dir):
        if not emits_to(manifest, target_name):
            excluded.add(emission_root.relative_to(bundle_dir))
    return frozenset(excluded)


def is_under_any(rel: Path, roots: frozenset[Path]) -> bool:
    """Whether the bundle-relative ``rel`` is one of ``roots`` or inside one."""
    if not roots:
        return False
    return rel in roots or any(parent in roots for parent in rel.parents)


__all__ = [
    'TARGET_SCOPE_FIELD',
    'TargetScopeError',
    'component_tree_target_names',
    'emits_to',
    'excluded_emission_roots',
    'is_under_any',
    'iter_component_manifests',
    'read_target_scope',
    'registered_target_names',
]
