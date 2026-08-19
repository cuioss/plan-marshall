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
* a value that is not a list of names — a mapping, a number, a boolean.
  Coercing one into a name and then rejecting it as unregistered would name
  a target nobody wrote;
* frontmatter that is not well-formed YAML **and mentions the field**.
  Guessing at unparseable frontmatter is how a declaration goes unread, and
  the component then ships everywhere carrying an invalid declaration nobody
  was told about. Unparseable frontmatter that never mentions ``targets:``
  is somebody else's defect: this module has no declaration to misread
  there, and turning target scoping into the repository's YAML linter is a
  job the plan did not give it and a failure surface it should not widen.

Reading is delegated to ``yaml.safe_load`` rather than done here. Twelve
verification rounds on a hand-rolled line scanner produced sixteen
behavioural defects, every one of them a divergence from YAML, and three of
them the SAME fail-open in the same function answered by three successive
indentation rules. What this module still owns is the fence extraction —
markdown frontmatter is not a YAML document stream — and the SHAPE rules
above, which are policy rather than syntax.

One convenience is this module's own and not YAML's: ``targets: a, b`` is a
single string to YAML, and it is split on commas here. That is why a
registered target name may contain neither whitespace nor a comma.

Adding a rejection means adding it here **and** in the authoring standards'
validation table, and considering whether the doctor rule can see it. That
rule is an APPROXIMATION rather than a mirror — it is stdlib-only, so it
cannot parse YAML, and it stays silent on every shape it is not certain of.
Its promise is that anything it reports is a real build failure, never that
it reports every one; a soundness test over a shared corpus holds it to that.

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

import yaml

#: Frontmatter field a component uses to declare the targets it ships to.
TARGET_SCOPE_FIELD = 'targets'

#: Bundle sub-directories holding single-file components, keyed to nothing
#: else: the file itself is both the declaration site and the emission unit.
_FILE_COMPONENT_DIRS = ('agents', 'commands')

#: Bundle sub-directory holding directory-shaped components. The manifest
#: is ``{skill_dir}/SKILL.md`` and the emission unit is ``{skill_dir}``.
_SKILLS_DIR = 'skills'

#: Manifest filename of a directory-shaped component.
_SKILL_MANIFEST = 'SKILL.md'

#: A frontmatter fence line: three hyphens, then only spaces or tabs.
#:
#: The fences are found by pattern rather than handed to the YAML parser,
#: because a markdown frontmatter block is not a YAML document stream: the
#: body beneath the closing fence is markdown, and feeding the whole file to
#: ``safe_load_all`` would parse it as a second document. Each fence is
#: matched as a whole LINE, so a value containing three hyphens does not
#: truncate the block and hide the fields after it. Trailing spaces or tabs
#: are accepted because they are invisible in an editor.
_OPEN_FENCE_RE = re.compile(r'^---[ \t]*\n')
_CLOSE_FENCE_RE = re.compile(r'\n---[ \t]*(?:\n|$)')


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
    """
    text = text.lstrip('\ufeff')
    open_fence = _OPEN_FENCE_RE.match(text)
    if open_fence is None:
        return None
    start = open_fence.end()
    # From start - 1, so the newline ending the opening fence can also serve
    # as the newline opening the closing one. What that changes is a block
    # closed immediately (`---` / `---` / more text): the block is EMPTY, and
    # where a LATER fence closes it the body would otherwise be read as fields.
    close_fence = _CLOSE_FENCE_RE.search(text, start - 1)
    if close_fence is None:
        return None
    return text[start:close_fence.start()]


#: Returned when the ``targets:`` key is not present at all. A distinct
#: object from ``None``, because ``targets:`` with nothing after it IS
#: present and its value IS ``None`` — YAML's null. Conflating the two turns
#: an empty declaration, which must fail the build, into "ship everywhere".
_ABSENT = object()


def _declared_value(text: str) -> object:
    """Return the raw ``targets:`` value declared by ``text``, or :data:`_ABSENT`.

    :data:`_ABSENT` covers "no frontmatter", "frontmatter that is not a
    mapping", and "no such key" — all of which mean ship everywhere. The
    value is otherwise whatever YAML says it is, and :func:`_tokens` decides
    which shapes are a declaration.

    Raises:
        yaml.YAMLError: The frontmatter block is not well-formed YAML.
    """
    block = _frontmatter_block(text)
    if block is None:
        return _ABSENT
    document = yaml.safe_load(block)
    if not isinstance(document, dict):
        return _ABSENT
    return document.get(TARGET_SCOPE_FIELD, _ABSENT)


#: A ``targets`` key, however it is spelled, anywhere in a frontmatter block.
#: Used only to decide whether UNPARSEABLE frontmatter is this module's
#: business — never to read a value, which is what a scanner like this got
#: wrong sixteen times.
_MENTIONS_FIELD_RE = re.compile(rf'^\s*[\'"]?{TARGET_SCOPE_FIELD}[\'"]?\s*:', re.MULTILINE)


def _mentions_the_field(text: str) -> bool:
    """Whether unparseable frontmatter appears to declare ``targets:`` at all.

    Deliberately over-inclusive: it matches at any indentation and inside a
    quoted string, so it can only ever cause a malformed file to be REFUSED
    rather than let one through. What it cannot do is hide a declaration,
    because hiding one would need the block to omit the key entirely — and a
    block that omits the key declares no scope.
    """
    block = _frontmatter_block(text)
    return block is not None and _MENTIONS_FIELD_RE.search(block) is not None


def _tokens(value: object) -> list[str] | None:
    """Return the target names ``value`` declares, or ``None`` for "absent".

    YAML has already resolved the syntax, so what is left is the value's
    SHAPE, and exactly three shapes are a declaration:

    * a sequence — the canonical form, inline (``[a, b]``) or block (``- a``);
    * a string — ``targets: claude``, and by a deliberate convenience
      ``targets: claude, opencode``, which YAML reads as the single string
      ``"claude, opencode"``. Splitting it is this module's own rule, not
      YAML's, and it is why a registered target name may not contain a comma;
    * ``None`` — ``targets:`` with nothing after it. YAML calls that null;
      here it is an empty declaration, and the validator rejects it under its
      own name. Absence is :data:`_ABSENT`, a different object entirely.

    Anything else — a mapping, a number, a boolean, a date — is not a list of
    names in any reading, so it is reported as such rather than coerced into
    one and then rejected as an unknown target.

    Returns:
        The declared names, or ``None`` when the field is absent. Note that an
        EMPTY list is a declaration (and an invalid one), which is why absence
        is ``None`` and not ``[]``.

    Raises:
        _NotAList: The value is present but is not a sequence or a string.
    """
    if value is _ABSENT:
        return None
    if value is None:
        return []
    if isinstance(value, str):
        return [token.strip() for token in value.split(',') if token.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise _NotAList(value)


class _NotAList(Exception):
    """Internal marker: ``targets:`` holds a value that is not a list of names.

    Raised by :func:`_tokens`, which has no component path, and turned into a
    :class:`TargetScopeError` by :func:`read_target_scope`, which does.
    """


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
        value = _declared_value(text)
    except yaml.YAMLError as error:
        if not _mentions_the_field(text):
            return None
        raise TargetScopeError(
            f'{path}: the frontmatter block is not well-formed YAML, so the build cannot '
            f'tell whether it declares `{TARGET_SCOPE_FIELD}:` at all. Refusing rather '
            f'than guessing, because a declaration read wrongly — or missed — ships the '
            f'component to targets it never named. YAML says: {error}'
        ) from None
    try:
        tokens = _tokens(value)
    except _NotAList as not_a_list:
        raise TargetScopeError(
            f'{path}: `{TARGET_SCOPE_FIELD}:` is {type(not_a_list.args[0]).__name__}, not a '
            f'list of target names. Write `{TARGET_SCOPE_FIELD}: [a, b]`, a `- ` block, or a '
            f'single name. Registered targets are: {_named(registered_target_names())}.'
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
