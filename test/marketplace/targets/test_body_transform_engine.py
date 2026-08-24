# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the target-shared body-transform engine's frontmatter reader.

The engine carries the THIRD frontmatter reader in ``marketplace/targets/``,
beside ``opencode.frontmatter.parse_frontmatter`` and
``claude.variant_emitter.parse_frontmatter``. Both siblings anchor on a
newline-delimited fence; this one anchored on a raw ``---`` substring, which is
looser at both ends — it opens on a horizontal rule that is not a fence at all,
and closes at the first three-hyphen run before the real fence. Either way the
fields after the false boundary are dropped, and a dropped
``user-invocable`` reads as ``''`` — i.e. "not user-invocable" — so the loose
anchor fails by silently un-registering a skill rather than by erroring.

The README-tree check at the end of this module has its home here rather than
in a target sub-package because the tree it guards documents the whole
``marketplace/targets`` package, of which this engine is the target-shared
member; no per-target module owns it.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from conftest import PROJECT_ROOT
from marketplace.targets.body_transform_engine import (
    _frontmatter_field,
    build_user_invocable_lookup,
)

_TARGETS_DIR = Path(PROJECT_ROOT) / 'marketplace' / 'targets'
_README = _TARGETS_DIR / 'README.md'

#: A frontmatter block whose value continuation line LEADS with three hyphens.
#: The raw-substring close anchor ends the block there, so every field after it
#: — including the one the reader exists to find — is dropped.
_DASH_LEADING_VALUE_BLOCK = (
    '---\n'
    'name: demo-skill\n'
    'description: see the separator below\n'
    '---- not a fence, just a value line that starts with dashes\n'
    'user-invocable: true\n'
    '---\n'
    '# Body\n'
)

#: The well-formed control: the same fields with no dash-leading line.
_PLAIN_BLOCK = (
    '---\n'
    'name: demo-skill\n'
    'description: nothing unusual\n'
    'user-invocable: true\n'
    '---\n'
    '# Body\n'
)


def test_a_field_after_a_dash_leading_value_line_is_still_read():
    """The close fence is a whole ``---`` LINE, not the first three-hyphen run.

    A raw-substring search ends the block at the dash-leading value line, so
    ``user-invocable`` never enters the scan and the skill silently stops being
    registered for the slash-command rewrite. The failure is invisible: an
    absent field and a false field are the same empty string.
    """
    assert _frontmatter_field(_DASH_LEADING_VALUE_BLOCK, 'user-invocable') == 'true'


def test_the_well_formed_block_still_reads_every_field():
    """Matched control: tightening the anchor must not break the ordinary case."""
    assert _frontmatter_field(_PLAIN_BLOCK, 'user-invocable') == 'true'
    assert _frontmatter_field(_PLAIN_BLOCK, 'name') == 'demo-skill'


def test_a_leading_horizontal_rule_is_not_read_as_a_frontmatter_fence():
    """The OPEN fence is a whole ``---`` line too — ``----`` opens nothing.

    A document that begins with a markdown horizontal rule has no frontmatter.
    A ``startswith('---')`` anchor accepts it anyway and then scrapes the prose
    for ``field:`` lines, so a sentence mentioning the field is read as a
    declaration of it — a false positive, the opposite failure from the one
    above and equally silent.
    """
    prose = (
        '----\n'
        'This document has no frontmatter at all.\n'
        'user-invocable: true\n'
        '---\n'
    )

    assert _frontmatter_field(prose, 'user-invocable') == ''


def test_a_closing_fence_at_end_of_file_is_tolerated():
    """Same end-of-file tolerance the sibling readers carry.

    A file whose closing fence is the last line has no trailing newline after
    it, so the delimited form never matches. Tolerating that one shape
    explicitly is what lets the anchor stay strict everywhere else.
    """
    assert _frontmatter_field('---\nuser-invocable: true\n---', 'user-invocable') == 'true'


def test_an_absent_field_and_an_absent_block_both_read_empty():
    """Negative direction: the reader reports nothing when there is nothing."""
    assert _frontmatter_field(_PLAIN_BLOCK, 'no-such-field') == ''
    assert _frontmatter_field('# Just a heading\n', 'user-invocable') == ''


def test_the_lookup_still_registers_a_skill_whose_frontmatter_has_a_dash_leading_line(
    tmp_path: Path,
):
    """End to end: the anchor fix is what keeps the skill in the rewrite lookup.

    ``build_user_invocable_lookup`` is the only consumer, and a skill missing
    from it is a skill whose ``/name`` invocations are never rewritten for a
    non-verbatim target. That is the concrete cost of the dropped field.
    """
    skill = tmp_path / 'demo-bundle' / 'skills' / 'demo-skill' / 'SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text(_DASH_LEADING_VALUE_BLOCK, encoding='utf-8')

    lookup = build_user_invocable_lookup(tmp_path)

    assert lookup == {'demo-skill': 'demo-bundle-demo-skill'}


# =============================================================================
# README architecture tree — exhaustive over the package's modules (G5)
# =============================================================================

#: A tree entry line: the indent, its box-drawing connector, and the name that
#: follows it, e.g. ``fs_safety.py`` or ``claude/``.
#: ``MULTILINE`` because the same pattern is used two ways — ``finditer`` over
#: the whole tree block, and ``match`` against one line at a time — and the
#: line-start anchor is what makes the indent group measure the entry's own
#: nesting rather than whatever whitespace precedes the connector.
_TREE_ENTRY_RE = re.compile(r'^(?P<indent>[\s│]*)[├└]── (?P<name>[^\s#]+)', re.MULTILINE)
#: Columns one nesting level occupies in the tree (``"│   "`` or four spaces).
_TREE_INDENT_WIDTH = 4


def _architecture_tree() -> str:
    """The fenced tree block under the README's ``## Architecture`` heading."""
    text = _README.read_text(encoding='utf-8')
    heading = text.index('## Architecture')
    open_fence = text.index('```', heading)
    close_fence = text.index('```', open_fence + 3)
    return text[open_fence + 3:close_fence]


def _source_modules() -> list[Path]:
    """Every Python module in the package, relative to ``marketplace/targets``."""
    return sorted(
        p.relative_to(_TARGETS_DIR)
        for p in _TARGETS_DIR.rglob('*.py')
        if '__pycache__' not in p.parts
    )


def _tree_module_keys(tree_text: str) -> Counter[str]:
    """How many times each ``*.py`` module PATH appears in ``tree_text``.

    Keyed on the path relative to ``marketplace/targets`` — ``claude/target.py``,
    not ``target.py``. A basename is not identifying here: three sub-packages own
    a ``target.py`` and two own an ``emitter.py``, so a basename-keyed count is
    satisfied by three ``target.py`` entries regardless of which three, and a
    tree omitting one while duplicating another passes both directions of the
    comparison.

    Nesting is read from the connector's column, four per level, so each file is
    attributed to the directory entry that opened its level.
    """
    counts: Counter[str] = Counter()
    packages: list[str] = []
    for line in tree_text.splitlines():
        match = _TREE_ENTRY_RE.match(line)
        if match is None:
            continue
        depth = len(match.group('indent')) // _TREE_INDENT_WIDTH
        name = match.group('name')
        del packages[depth:]
        if name.endswith('/'):
            packages.append(name.rstrip('/'))
        elif name.endswith('.py'):
            counts['/'.join([*packages, name])] += 1
    return counts


def _source_module_keys() -> Counter[str]:
    """The same key space, computed from the modules on disk."""
    return Counter(m.as_posix() for m in _source_modules())


def _module_shortfall(tree_text: str) -> dict[str, tuple[int, int]]:
    """Modules the tree lists FEWER times than the package has them.

    Values are ``(on disk, in tree)``.
    """
    tree = _tree_module_keys(tree_text)
    return {
        name: (count, tree.get(name, 0))
        for name, count in _source_module_keys().items()
        if tree.get(name, 0) < count
    }


def _module_surplus(tree_text: str) -> dict[str, tuple[int, int]]:
    """Modules the tree lists MORE times than the package has them."""
    source = _source_module_keys()
    return {
        name: (source.get(name, 0), count)
        for name, count in _tree_module_keys(tree_text).items()
        if count > source.get(name, 0)
    }


def _tree_with_a_basename_preserving_swap() -> str:
    """The real tree, minus ``claude/target.py``, plus a second ``opencode/target.py``.

    Derived from the live README rather than written out, so it stays a mutation
    of the real population as that population changes. The swap preserves every
    BASENAME count exactly — one ``target.py`` line is removed and another
    duplicated — so a basename-keyed comparison sees a tree identical to the real
    one and reports it exhaustive. Only a path-keyed comparison notices that
    ``claude/target.py`` has become unlisted while ``opencode/target.py`` is
    listed twice.
    """
    kept: list[str] = []
    package: str | None = None
    for line in _architecture_tree().splitlines():
        match = _TREE_ENTRY_RE.match(line)
        if match is None:
            kept.append(line)
            continue
        name = match.group('name')
        if len(match.group('indent')) // _TREE_INDENT_WIDTH == 0:
            package = name.rstrip('/') if name.endswith('/') else None
        if package == 'claude' and name == 'target.py':
            continue
        kept.append(line)
        if package == 'opencode' and name == 'target.py':
            kept.append(line)
    return '\n'.join(kept)


def test_the_module_population_is_not_vacuous():
    """Anti-vacuity: an empty walk would make the exhaustiveness check pass."""
    modules = _source_modules()
    assert len(modules) >= 19, (
        f'expected at least nineteen Python modules under {_TARGETS_DIR}, walked '
        f'{[str(m) for m in modules]} — the exhaustiveness assertions below would '
        f'be vacuous over a short population'
    )


def test_every_module_appears_in_the_readme_architecture_tree():
    """The tree is exhaustive: a module absent from it is a defect in the tree.

    A partial tree reads as a map of the package while being a map of whatever
    its last editor touched, and the modules it omits are the shared ones
    (``fs_safety``, ``component_targets``, ``body_transform_engine``) a
    newcomer most needs to find.
    """
    short = _module_shortfall(_architecture_tree())

    assert not short, (
        'The README ## Architecture tree lists fewer entries than the package '
        f'has modules (name: (on disk, in tree)):\n  {short}\n'
        f'Full module set: {[str(m) for m in _source_modules()]}'
    )


def test_the_readme_tree_names_no_module_that_does_not_exist():
    """The other direction — a renamed or deleted module must not linger.

    Without this, the tree could satisfy the count above by listing a module
    twice, or keep advertising a file that was removed; either way a reader
    navigating by it lands nowhere.
    """
    surplus = _module_surplus(_architecture_tree())

    assert not surplus, (
        'The README ## Architecture tree names modules the package does not '
        f'have, or names one more times than it exists (name: (on disk, in tree)):\n  {surplus}'
    )


def test_a_basename_preserving_swap_in_the_tree_is_caught():
    """The comparison is keyed on the module PATH, not on its basename.

    Three sub-packages own a ``target.py`` and two own an ``emitter.py``, so a
    basename-keyed Counter is satisfied by three ``target.py`` entries no matter
    WHICH three. The tree can therefore omit ``claude/target.py`` while listing
    ``opencode/target.py`` twice and still be reported exhaustive in BOTH
    directions — a vacuous pass over a real, reachable defect in the very
    document these tests exist to check.
    """
    mutated = _tree_with_a_basename_preserving_swap()

    shortfall = _module_shortfall(mutated)
    surplus = _module_surplus(mutated)

    assert 'claude/target.py' in shortfall, (
        'a tree that dropped claude/target.py was reported exhaustive — the '
        f'comparison is not path-keyed. shortfall={shortfall}'
    )
    assert 'opencode/target.py' in surplus, (
        'a tree that lists opencode/target.py twice was reported clean — the '
        f'comparison is not path-keyed. surplus={surplus}'
    )
