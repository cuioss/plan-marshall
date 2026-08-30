#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Documented-verb-set drift — the registered verb SET versus the documented one.

The defect this rule detects
----------------------------
A script's argparse surface and the verbs its skill documents drift apart in
both directions, and until now neither direction was structurally checked:

- ``verb_missing_from_docs`` — the script registers a verb for which the skill
  carries no example invocation in a fenced bash block. **No existing rule covers
  this direction.**

  ⛔ The compared population on the documentation side is *fenced bash
  invocations*, not "documentation" in general. A verb described only in a prose
  verb table is reported here, and that is intended — the fenced invocation is
  the copyable, machine-checkable surface every other verb rule keys on — but the
  finding must not be read as "this verb is undocumented". `manage-tasks
  loop-exit-guard` is the worked example: it carries a full prose table row and a
  dedicated section, and still has no fenced invocation. The message states the
  narrower fact rather than the stronger one the comparison does not support.
- ``phantom_documented_verb`` — the documentation names a verb the script does
  not register. Calling it is an argparse rejection.

Relationship to ``manage-invocation-invalid``
---------------------------------------------
⛔ The ``phantom_documented_verb`` class OVERLAPS the existing, default-on
``manage-invocation-invalid`` rule, which already rejects a documented
*invocation* naming an unregistered subcommand. The two are not redundant but
they are not independent either, and the difference is the unit of analysis:
that rule validates one written invocation at a time against a live ``--help``
walk, while this rule compares two SETS and can therefore also report the
opposite direction, which per-invocation analysis structurally cannot see (an
undocumented verb appears in no invocation, so there is nothing for a
per-invocation rule to inspect).

``verb_missing_from_docs`` is the class that carries this rule's independent
value. ``phantom_documented_verb`` is retained because a set comparison that
reported only one of its two directions would be a partial answer presented as
a whole — but a consumer running both rules should expect the phantom findings
to corroborate, not to add to, what ``manage-invocation-invalid`` already says.

Derivation, and why it does not reuse ``build_subparser_tree``
-------------------------------------------------------------
``_analyze_verb_chains.build_subparser_tree`` returns an empty dict for an
unreadable file, an unparseable file, AND a script that simply uses no
subparsers. Those are three different states, and this rule must not treat the
first two as "no verbs registered" — that would silently report every documented
verb as a phantom. So the AST walk here returns an explicit outcome that keeps
them apart (:class:`VerbSet`), recognising the same call shapes.

Fail-closed contract
--------------------
The rule SKIPS — it does not pass — whenever it cannot derive a trustworthy
registered set. A skip is reported as a finding carrying ``reason``, never as
silence, because a rule that says nothing about a script it could not read is
indistinguishable from one that read it and found it clean. The skip states are:

- ``unreadable_script`` / ``unparseable_script`` — the source could not be read
  or parsed.
- ``dynamic_verb_registration`` — an ``add_parser`` call whose verb name is not
  a literal string (a variable, an f-string, a loop over a table), or whose
  ``aliases=[...]`` list is not fully literal. The registered set is then
  unknowable — or, for aliases, knowable only in part — by static analysis, and
  any comparison against it would manufacture findings. An alias IS a registered
  verb: argparse accepts every ``aliases`` entry as a valid subcommand, so a
  derivation that collected only the positional name would under-derive the set
  and report a documented alias as a phantom.
- ``unresolved_subparser_group`` — an ``add_subparsers`` handle whose owning
  parser could not be resolved, so part of the tree is unreachable and the
  derived set is incomplete rather than empty.
- ``no_root_parser_resolved`` — ``add_parser`` calls exist but none attaches to a
  variable recognised as the root parser. ⛔ This is the fail-open the rule most
  needs to refuse: an empty derived set is a derivation failure, not the
  observation "registers nothing", and reporting it as the latter turns every
  documented verb into a phantom. Measured during development: treating an empty
  set as authoritative produced 60 phantom findings on the live tree, and the
  spot-checked ones were all real registered verbs.
- ``no_subparser_registration_in_file`` — no ``add_parser`` call in this file.
  The walk is deliberately file-local and does not follow imports, so several
  entry scripts that build their parser in a helper land here; the reason names
  what was observed rather than the stronger "has no subcommands" conclusion the
  observation does not support.

The skip count is the rule's own honest coverage gap and is reported, never
absorbed. No absolute finding or skip count is recorded here: the figures move on
any commit that adds a script or a fenced invocation, so a written-down number is
stale by the next one. Read the live figures from a run.

Population
----------
Two derivations, and both are from the tree rather than from a list:

- **Which skills are examined** — every skill whose ``SKILL.md`` carries a
  ``## Canonical invocations`` heading. Every finding publishes
  ``details.population_size``, and an empty population over a non-empty bundles
  tree emits its own finding — a rule that examined nothing must not read as a
  rule that examined everything and found it clean.
- **Which scripts are compared within a skill** — the UNION of the notations
  documented in fenced invocations and the entry scripts the skill OWNS on disk
  (:func:`owned_entry_scripts`). ⛔ The second half is load-bearing. Walking only
  the documented notations made ``verb_missing_from_docs`` unreachable for a
  script carrying no fenced invocation at all: it created no entry, never reached
  :func:`derive_registered_verbs`, and the rule returned clean over it — a
  detector that could not fire, of exactly the class this rule exists to detect.
  An owned script absent from the docs is compared against an EMPTY documented
  set, so every verb it registers is reported.

Findings have the shape::

    {
        'type': 'verb_missing_from_docs' | 'phantom_documented_verb'
                 | 'verb_set_drift_skipped' | 'verb_set_drift_empty_population',
        'rule_id': 'documented-verb-set-drift',
        'file': '<script or SKILL.md path>',
        'line': <int>,
        'severity': 'warning',
        'details': {'population_size': <int>, ...},
    }

Public API
----------
- ``analyze_documented_verb_set_drift(marketplace_root)`` — entry point.
- ``analyze_documented_verb_set_drift_with_population(marketplace_root)`` —
  returns ``(findings, population_size)`` from ONE derivation, for callers that
  need the coverage figure on a clean tree (where no finding carries it).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from _analyze_verb_chains import extract_invocations
from _doctor_shared import Finding
from _rule_registry import SCOPE_CORPUS_RELATIONAL, RuleDescriptor

RULE_ID = 'documented-verb-set-drift'
RULE_NAME = 'documented-verb-set-drift'

TYPE_MISSING_FROM_DOCS = 'verb_missing_from_docs'
TYPE_PHANTOM_DOCUMENTED = 'phantom_documented_verb'
TYPE_SKIPPED = 'verb_set_drift_skipped'
TYPE_EMPTY_POPULATION = 'verb_set_drift_empty_population'

#: ⛔ Registered but NOT wired into ``quality-gate``. The gate's status is
#: ``'fail' if all_issues else 'pass'`` — severity-blind, so it has no
#: registered-but-non-failing mode; any finding turns the tree red. Only
#: ``cmd_test_conventions`` derives status from error-severity findings, and its
#: scope is the test tree, not the bundle tree. This rule therefore lands
#: discoverable via ``analyze --rules documented_verb_set_drift`` and opt-in, with
#: the promotion proposal recorded in ``references/rule-catalog.md``. Promoting it
#: requires EITHER driving the drift count to zero first OR teaching the gate the
#: severity split ``test-conventions`` already has.
RULE_DESCRIPTOR = RuleDescriptor(
    rule_id='documented_verb_set_drift',
    severity='warning',
    category='structural',
    scope=SCOPE_CORPUS_RELATIONAL,
    opt_in=True,
    default_on=False,
)

_CANONICAL_BLOCK_HEADING = re.compile(
    r'^##\s+Canonical\s+invocations\s*$', re.IGNORECASE | re.MULTILINE
)

# ---------------------------------------------------------------------------
# Registered-verb derivation (AST)
# ---------------------------------------------------------------------------

SKIP_UNREADABLE = 'unreadable_script'
SKIP_UNPARSEABLE = 'unparseable_script'
SKIP_DYNAMIC = 'dynamic_verb_registration'
SKIP_UNRESOLVED_GROUP = 'unresolved_subparser_group'
SKIP_NO_SUBPARSERS = 'no_subparser_registration_in_file'
SKIP_NO_ROOT_PARSER = 'no_root_parser_resolved'


@dataclass
class VerbSet:
    """The outcome of deriving one script's registered top-level verb set.

    ``skip_reason`` set means the derivation is NOT trustworthy and the caller
    must skip the comparison rather than treat ``verbs`` as complete. This is the
    distinction ``build_subparser_tree``'s bare ``{}`` return cannot express.
    """

    verbs: set[str] = field(default_factory=set)
    skip_reason: str | None = None
    #: Line of the construct that forced the skip, for an actionable finding.
    skip_line: int = 1

    @property
    def trustworthy(self) -> bool:
        return self.skip_reason is None


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _receiver_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id
    return None


def _assigned_names(node: ast.Assign) -> list[str]:
    return [t.id for t in node.targets if isinstance(t, ast.Name)]


def derive_registered_verbs(script_path: Path) -> VerbSet:
    """AST-derive the TOP-LEVEL registered verb set of ``script_path``.

    Recognises the same call shapes as ``_analyze_verb_chains.build_subparser_tree``
    — ``ArgumentParser(...)`` assigned to a variable, ``<var>.add_subparsers(...)``
    registering a handle, and ``<handle>.add_parser('name', ...)`` in both the
    assigned and bare forms — but returns an explicit :class:`VerbSet` so an
    untrustworthy derivation is never mistaken for an empty one.

    An ``add_parser`` call's ``aliases=[...]`` entries join the same set as its
    positional name, because argparse registers each one as an independently
    callable subcommand.

    Only the ROOT parser's children are returned: the rule compares top-level
    verb sets, and a nested sub-verb is documented as part of its parent's chain.
    """
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return VerbSet(skip_reason=SKIP_UNREADABLE)

    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError as exc:
        return VerbSet(skip_reason=SKIP_UNPARSEABLE, skip_line=exc.lineno or 1)

    # variable -> True for any variable bound to an ArgumentParser.
    parser_vars: set[str] = set()
    # subparsers-handle variable -> owning parser variable.
    handle_owner: dict[str, str] = {}
    # parser variable -> the verbs registered directly under it.
    children: dict[str, set[str]] = {}
    # Verbs registered on a handle whose owner never resolved.
    unresolved_group_line: int | None = None
    dynamic_line: int | None = None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_func_name(node)
        if name == 'ArgumentParser':
            parent = _enclosing_assign(tree, node)
            if parent is not None:
                parser_vars.update(_assigned_names(parent))
        elif name == 'add_subparsers':
            owner = _receiver_name(node)
            parent = _enclosing_assign(tree, node)
            if parent is not None and owner is not None:
                for handle in _assigned_names(parent):
                    handle_owner[handle] = owner
        elif name == 'add_parser':
            receiver = _receiver_name(node)
            verb = _literal_first_arg(node)
            if verb is None:
                # A non-literal verb name: the registered set cannot be derived
                # statically at all, so nothing about it may be asserted.
                dynamic_line = dynamic_line or getattr(node, 'lineno', 1)
                continue
            aliases = _literal_aliases(node)
            if aliases is None:
                # An ``aliases=[...]`` list that is not fully literal. argparse
                # accepts every alias as a valid subcommand, so the derived set
                # would be PARTIAL — and a partial set compared as a complete one
                # reports a real alias as a phantom. Same fail-closed refusal the
                # non-literal verb name above takes.
                dynamic_line = dynamic_line or getattr(node, 'lineno', 1)
                continue
            owning_parser = handle_owner.get(receiver) if receiver else None
            if owning_parser is None:
                unresolved_group_line = unresolved_group_line or getattr(node, 'lineno', 1)
                continue
            children.setdefault(owning_parser, set()).add(verb)
            children[owning_parser].update(aliases)

    if dynamic_line is not None:
        return VerbSet(skip_reason=SKIP_DYNAMIC, skip_line=dynamic_line)
    if unresolved_group_line is not None:
        return VerbSet(skip_reason=SKIP_UNRESOLVED_GROUP, skip_line=unresolved_group_line)

    if not children:
        # No ``add_parser`` call in THIS FILE. That is not the same claim as "the
        # script has no subcommands": several entry scripts build their parser in
        # an imported helper, and this walk is deliberately file-local — it does
        # not follow imports. `git-workflow.py` is the worked example, carrying a
        # dozen registered verbs and not one argparse call of its own. So the
        # reason names what was observed (no registration in this file) rather
        # than the stronger conclusion the observation does not support.
        return VerbSet(skip_reason=SKIP_NO_SUBPARSERS)

    root_verbs: set[str] = set()
    for owner, verbs in children.items():
        if owner in parser_vars:
            root_verbs |= verbs

    if not root_verbs:
        # ⛔ THE FAIL-OPEN THIS RULE MUST NOT TAKE. ``add_parser`` calls exist, so
        # the script registers verbs, but none attached to a variable recognised
        # as the ROOT parser — the parser is built by an idiom this walker does
        # not model (constructed in a helper, reassigned, held on an object).
        # An empty set here is a DERIVATION FAILURE, not the observation "this
        # script registers nothing", and treating it as the latter reports every
        # documented verb as a phantom. Measured: doing so produced 60 phantom
        # findings across the live tree, of which the spot-checked ones were all
        # real registered verbs.
        return VerbSet(skip_reason=SKIP_NO_ROOT_PARSER)

    return VerbSet(verbs=root_verbs)


def _literal_first_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None


def _literal_aliases(node: ast.Call) -> list[str] | None:
    """The literal strings of an ``add_parser`` call's ``aliases=[...]`` keyword.

    argparse registers every ``aliases`` entry as a further valid subcommand, so
    an alias is part of the registered verb set exactly as the positional name is;
    collecting only the positional under-derives the set and reports a documented
    alias as a phantom.

    Three outcomes, and the middle one is the reason this is not a plain list
    return: ``[]`` when the call carries no ``aliases`` keyword (nothing to add),
    the collected names when every element is a string literal, and ``None`` when
    an ``aliases`` keyword IS present but is not fully literal-derivable — a
    variable, a comprehension, a splat, or a list holding any non-literal element.
    ``None`` is the fail-closed signal: the set is then partial, and a partial set
    must not be compared as a complete one.
    """
    for keyword in node.keywords:
        if keyword.arg != 'aliases':
            continue
        if not isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            return None
        names: list[str] = []
        for element in keyword.value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                names.append(element.value)
            else:
                return None
        return names
    return []


def _enclosing_assign(tree: ast.AST, target: ast.Call) -> ast.Assign | None:
    """Return the ``Assign`` whose value is ``target``, if any."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and node.value is target:
            return node
    return None


# ---------------------------------------------------------------------------
# Population + documented-verb derivation
# ---------------------------------------------------------------------------


def _has_canonical_block(skill_md: Path) -> bool:
    try:
        content = skill_md.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return False
    return bool(_CANONICAL_BLOCK_HEADING.search(content))


def derive_population(marketplace_root: Path) -> list[Path]:
    """Every skill directory whose SKILL.md carries a canonical-invocations block.

    Derived from the bundle tree at call time, never from a hard-coded list, so
    the figure a finding publishes describes the tree that was actually walked.
    """
    bundles = marketplace_root / 'bundles' if (marketplace_root / 'bundles').is_dir() else marketplace_root
    population: list[Path] = []
    for skill_md in sorted(bundles.glob('*/skills/*/SKILL.md')):
        if _has_canonical_block(skill_md):
            population.append(skill_md.parent)
    return population


def _markdown_targets(skill_dir: Path) -> list[Path]:
    """SKILL.md plus the sub-document trees canonical invocations may live in."""
    targets: list[Path] = []
    skill_md = skill_dir / 'SKILL.md'
    if skill_md.is_file():
        targets.append(skill_md)
    for sub in ('standards', 'references', 'workflow', 'recipes'):
        sub_dir = skill_dir / sub
        if sub_dir.is_dir():
            targets.extend(sorted(sub_dir.glob('*.md')))
    return targets


def documented_verbs_by_script(skill_dir: Path) -> dict[str, tuple[set[str], Path, int]]:
    """Map ``script_notation -> (documented top-level verbs, first doc path, line)``.

    Only invocations naming a script of THIS skill are collected: a skill's
    documentation legitimately cites other skills' scripts, and those verbs
    belong to the other skill's set.
    """
    skill_name = skill_dir.name
    collected: dict[str, tuple[set[str], Path, int]] = {}
    for md in _markdown_targets(skill_dir):
        for inv in extract_invocations(md):
            if inv.skill != skill_name or not inv.verb_chain:
                continue
            verbs, path, line = collected.get(inv.script_notation, (set(), md, inv.line))
            verbs.add(inv.verb_chain[0])
            collected[inv.script_notation] = (verbs, path, line)
    return collected


def _script_path(skill_dir: Path, script_name: str) -> Path | None:
    candidate = skill_dir / 'scripts' / f'{script_name}.py'
    return candidate if candidate.is_file() else None


def _is_dunder_name(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == '__name__'


def _is_main_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == '__main__'


def _is_main_guard_test(test: ast.expr) -> bool:
    """Is ``test`` exactly ``__name__ == '__main__'``, in either operand order?

    The comparison OPERATOR is inspected, not just the operands: ``__name__ !=
    '__main__'`` carries the same left/comparator shape and is not an entry-point
    guard, so admitting it would classify an ordinary module as an entry script.
    Only a single ``==`` qualifies — a chained compare is not this idiom.
    ``'__main__' == __name__`` is accepted because argparse-era style guides
    permit either order and the reversed form is a real entry script.
    """
    if not isinstance(test, ast.Compare):
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    left = test.left
    right = test.comparators[0]
    return (_is_dunder_name(left) and _is_main_literal(right)) or (
        _is_main_literal(left) and _is_dunder_name(right)
    )


def _declares_main_guard(path: Path) -> bool | None:
    """Does this module carry a TOP-LEVEL ``if __name__ == '__main__':`` guard?

    ``None`` when the file could not be read or parsed — an unknown, kept
    distinct from ``False`` so an unreadable file is admitted as a candidate and
    reported as a skip rather than silently dropped from the population.

    Only ``tree.body`` is scanned. Walking the whole tree counted a guard nested
    inside a function, which does not make the file an entry script: an imported
    helper module that happens to carry one in a nested scope would be admitted to
    the candidate set on a shape that says nothing about how the file is invoked.
    """
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return any(
        isinstance(node, ast.If) and _is_main_guard_test(node.test) for node in tree.body
    )


def owned_entry_scripts(skill_dir: Path) -> dict[str, Path]:
    """Map ``script_notation -> path`` for every entry script this skill OWNS.

    ⛔ This is the authoritative candidate surface, and deriving it from the
    filesystem rather than from the documentation is what makes
    ``verb_missing_from_docs`` reachable at all. A candidate set built from the
    notations appearing in fenced documentation can only ever visit scripts the
    docs already mention — so a skill containing a CLI script with NO fenced
    invocation created no entry, never reached :func:`derive_registered_verbs`,
    and the rule returned CLEAN for precisely the worst case it exists to catch:
    a script documented nowhere. A script with zero documented verbs now yields a
    finding per registered verb, compared against an EMPTY documented set.

    An entry script is discriminated structurally, by the
    ``if __name__ == '__main__':`` guard the script-architecture standard requires
    of every entry point. A leading-underscore filter would not do: this tree
    carries non-underscore helper MODULES that are imported, never invoked
    (``toon_parser.py``, ``retro_sections.py``), and admitting them would report a
    derivation skip for every one. A file that cannot be read or parsed is
    admitted anyway — that unknown is reported as a skip, never resolved to "not
    an entry script".
    """
    scripts_dir = skill_dir / 'scripts'
    if not scripts_dir.is_dir():
        return {}
    bundle_name = skill_dir.parent.parent.name
    skill_name = skill_dir.name
    return {
        f'{bundle_name}:{skill_name}:{path.stem}': path
        for path in sorted(scripts_dir.glob('*.py'))
        if _declares_main_guard(path) is not False
    }


# ---------------------------------------------------------------------------
# Finding construction
# ---------------------------------------------------------------------------


def _finding(
    finding_type: str,
    path: Path,
    line: int,
    population_size: int,
    *,
    message: str,
    **extra_details: object,
) -> dict:
    details: dict = {'population_size': population_size}
    details.update(extra_details)
    return Finding(
        type=finding_type,
        file=str(path),
        line=line,
        severity='warning',
        fixable=False,
        rule_id=RULE_ID,
        details=details,
        extra={'rule': RULE_NAME, 'message': message},
    ).to_dict()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def analyze_documented_verb_set_drift(marketplace_root: Path) -> list[dict]:
    """Compare each in-scope script's registered verb set against its documented one."""
    findings, _population = analyze_documented_verb_set_drift_with_population(marketplace_root)
    return findings


def analyze_documented_verb_set_drift_with_population(
    marketplace_root: Path,
) -> tuple[list[dict], int]:
    """Return ``(findings, population_size)`` from ONE derivation.

    A CLEAN run carries no findings and therefore no ``population_size`` on any
    finding — the only state a passing gate is ever in — so the figure is
    returned alongside for callers that publish coverage.
    """
    population = derive_population(marketplace_root)
    population_size = len(population)
    findings: list[dict] = []

    if population_size == 0:
        bundles = marketplace_root / 'bundles'
        tree_root = bundles if bundles.is_dir() else marketplace_root
        if any(tree_root.glob('*/skills/*/SKILL.md')):
            # A non-empty tree that yielded no population is a derivation
            # failure, not a clean result. Reporting it as zero findings would
            # be a vacuous pass over an unread population.
            findings.append(
                _finding(
                    TYPE_EMPTY_POPULATION,
                    tree_root,
                    1,
                    0,
                    message=(
                        'No skill carrying a "## Canonical invocations" block was '
                        'found, yet the bundles tree contains skills — the '
                        'population derivation found nothing to examine.'
                    ),
                    reason='empty_population',
                )
            )
        return findings, 0

    for skill_dir in population:
        documented_by_script = documented_verbs_by_script(skill_dir)
        owned = owned_entry_scripts(skill_dir)
        skill_md = skill_dir / 'SKILL.md'

        # The candidate set is the UNION of the two surfaces, not the documented
        # one alone. An owned entry script absent from the docs contributes an
        # EMPTY documented set and is compared anyway — that is the whole point of
        # deriving candidates from the script surface (see `owned_entry_scripts`).
        for notation in sorted(set(documented_by_script) | set(owned)):
            documented, doc_path, doc_line = documented_by_script.get(
                notation, (set(), skill_md, 1)
            )
            script = owned.get(notation) or _script_path(skill_dir, notation.split(':')[-1])
            if script is None:
                # The notation names no script file in this skill. That is
                # `notation-staleness` / `manage-invocation-invalid` territory,
                # not a verb-SET question, so this rule says nothing about it.
                continue

            verb_set = derive_registered_verbs(script)
            if not verb_set.trustworthy:
                findings.append(
                    _finding(
                        TYPE_SKIPPED,
                        script,
                        verb_set.skip_line,
                        population_size,
                        message=(
                            f'Verb-set comparison skipped for {notation}: '
                            f'{verb_set.skip_reason}. The registered set could not '
                            f'be derived, so neither drift direction is asserted.'
                        ),
                        reason=verb_set.skip_reason,
                        notation=notation,
                    )
                )
                continue

            for verb in sorted(verb_set.verbs - documented):
                findings.append(
                    _finding(
                        TYPE_MISSING_FROM_DOCS,
                        script,
                        1,
                        population_size,
                        message=(
                            f'{notation} registers verb "{verb}", for which the '
                            f'skill carries no example invocation in a fenced bash '
                            f'block. The verb may still be described in a prose '
                            f'verb table; what is absent is the copyable, '
                            f'machine-checkable invocation.'
                        ),
                        notation=notation,
                        verb=verb,
                        registered_verb_count=len(verb_set.verbs),
                        documented_verb_count=len(documented),
                    )
                )

            for verb in sorted(documented - verb_set.verbs):
                findings.append(
                    _finding(
                        TYPE_PHANTOM_DOCUMENTED,
                        doc_path,
                        doc_line,
                        population_size,
                        message=(
                            f'{notation} is documented with verb "{verb}", which the '
                            f'script does not register — the invocation is an '
                            f'argparse rejection.'
                        ),
                        notation=notation,
                        verb=verb,
                        registered_verb_count=len(verb_set.verbs),
                        documented_verb_count=len(documented),
                    )
                )

    return findings, population_size
