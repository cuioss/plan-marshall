#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""No shipped plan-marshall doc pins a build tool outside the allow-list.

``./pw`` and ``pyproject_build`` are this repository's own build tool — the
pyprojectx wrapper and the notation of the skill that wraps it. A consumer
project on Maven, Gradle or npm has neither, so a shipped instruction naming
one is an instruction that project cannot follow. Some sites name the tool
legitimately: the build skill's own documentation, a per-build-system table
row, a recorded observation about this repository, an example explicitly
declared meta-project-only.

**The document population is DERIVED from the tree** — every ``*.md`` under
``marketplace/bundles/plan-marshall/`` — so a doc added later is swept without
anyone remembering to list it. **The allow-list is derived from deliverable 1's
classification**, not composed here: it is the set of files carrying a token
after that classification and its remediation, and the two sub-lists below are
read straight off deliverable 1's record rather than re-judged.

Both sizes are published, because the two failure directions are different. An
empty population would pass every assertion over nothing; an allow-list that
grows unchecked would pass every assertion because nothing is left to fail. The
stale-entry sweep is what bounds the second: an allow-list entry that no longer
carries a token, or no longer exists, is reported rather than carried forever.

The token detector itself is paired with a matched control — it must fire on a
synthetic consumer-facing instruction and stay silent on a doc with no token —
so a typo in the token tuple fails here instead of emptying the sweep.
"""

from __future__ import annotations

from pathlib import Path

from conftest import MARKETPLACE_ROOT, PROJECT_ROOT

_BUNDLE = MARKETPLACE_ROOT / 'plan-marshall'

#: The concrete build-tool literals. ``./pw`` is the pyprojectx wrapper;
#: ``pyproject_build`` is the script segment of the build skill's notation.
#: Both are pyprojectx-specific — a project resolving Maven, Gradle or npm
#: through ``architecture resolve`` never produces either.
_BUILD_TOOL_TOKENS = ('./pw', 'pyproject_build')


def _shipped_docs() -> list[Path]:
    """Every markdown document the plan-marshall bundle ships, derived from the tree."""
    return sorted(_BUNDLE.rglob('*.md'))


def _tokens_in(path: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    return [token for token in _BUILD_TOOL_TOKENS if token in text]


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


_DOCS = _shipped_docs()

# Non-emptiness asserted at IMPORT, before anything sweeps the population. A
# glob that matched nothing would report a clean sweep over an empty tree, which
# is the confident-but-empty verdict this module exists to prevent elsewhere.
assert _DOCS, (
    f'No markdown document was found under {_rel(_BUNDLE)} — the pinned-build-'
    f'tool sweep would pass over an empty population'
)


def _scan(docs: list[Path]) -> dict[str, list[str]]:
    """Map each document that carries a build-tool token to the tokens it carries.

    One read per document: the population is swept again by the root conftest's
    report header at session start, so a second read per file would double a
    cost the whole suite pays before collection begins.
    """
    found: dict[str, list[str]] = {}
    for path in docs:
        tokens = _tokens_in(path)
        if tokens:
            found[_rel(path)] = tokens
    return found


_HITS = _scan(_DOCS)

#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``. The import-time assertion above fails an EMPTY
#: population; publishing the size is what makes a SHRUNKEN one visible on the
#: green run, where no failure message is ever rendered.
GUARD_POPULATION_LABEL = 'shipped plan-marshall docs swept for a pinned build tool'
GUARD_POPULATION_SIZE = len(_DOCS)


# ---------------------------------------------------------------------------
# The allow-list, derived from deliverable 1's classification
# ---------------------------------------------------------------------------
#
# Deliverable 1 walked the shipped plan-marshall bundle and classified every
# site it found as shape-A (the meta-project's own layout or tool, named at a
# site where a consumer's behaviour does not depend on it) or shape-B (a
# shipped instruction, guard or gate a consumer would execute and get a wrong
# or vacuous outcome from). Deliverables 2-5 then disposed of every shape-B.
#
# The two tuples below are read off that record, not re-judged here, and each
# carries a distinct, separately falsifiable obligation.

#: Shape-B files whose disposition REMOVED the build-tool literal. Each must now
#: carry no token at all — this is the sharpest assertion in the module, because
#: it fails the moment a remediation is reverted.
_D1_SHAPE_B_TOKEN_REMOVED = (
    'marketplace/bundles/plan-marshall/skills/lsp-client/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/manage-tasks/standards/task-contract.md',
)

#: Shape-B files whose disposition DECLARED the scope at the site rather than
#: removing the literal — a per-build-system example, a recorded observation, an
#: example marked meta-project-only. Each legitimately still carries a token.
_D1_SHAPE_B_SCOPE_DECLARED = (
    'marketplace/bundles/plan-marshall/skills/extension-api/standards/build-execution.md',
    'marketplace/bundles/plan-marshall/skills/manage-solution-outline/examples/plugin-feature.md',
    'marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/tool-usage-patterns.md',
    'marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md',
)

#: Files carrying a build-tool token against which deliverable 1 raised no
#: shape-B finding: the tool is named as this repository's own, in its own
#: documentation, in a per-build-system table, or as the token a rule forbids
#: pinning. Legitimate self-reference.
_SELF_REFERENCE = (
    'marketplace/bundles/plan-marshall/README.md',
    'marketplace/bundles/plan-marshall/skills/build-pyproject/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/build-pyproject/standards/pyproject-impl.md',
    'marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md',
    'marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md',
    'marketplace/bundles/plan-marshall/skills/manage-architecture/standards/resolve-command.md',
    'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/marshall-steward/references/architecture-setup.md',
    'marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md',
    'marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md',
    'marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md',
)

#: The allow-list is the UNION of the two legitimate categories. It is composed
#: from them rather than written out a third time, so a file cannot be allowed
#: without also being categorised.
_ALLOW_LIST = frozenset(_SELF_REFERENCE) | frozenset(_D1_SHAPE_B_SCOPE_DECLARED)

assert _ALLOW_LIST, 'The allow-list is empty — every hit would fail for the wrong reason'


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


def test_published_population_matches_a_live_sweep():
    """The published size must equal a live sweep, not its own definition.

    ``GUARD_POPULATION_SIZE`` is bound from ``_DOCS`` at import, so comparing it
    against ``len(_DOCS)`` is a value against its own definition and cannot fail.
    Re-invoking ``_shipped_docs()`` makes the check falsifiable for the drift it
    CAN see: the constant re-bound to something other than the swept population.

    What this does NOT catch, stated so the green is not read as wider than it
    is: the sweep re-enters the same ``_shipped_docs()`` the constant came from,
    so a SHRUNKEN population — the drift the module's own note at the
    ``GUARD_POPULATION_SIZE`` binding names — moves both sides of the equality
    together and stays green. Exposing a shrink needs a floor the tree cannot
    move, which this module does not carry.
    """
    live = _shipped_docs()

    assert live, (
        f'A live sweep of {_rel(_BUNDLE)} found no markdown document, so the '
        f'published population size describes an empty tree'
    )
    assert GUARD_POPULATION_SIZE == len(live), (
        f'Published population size {GUARD_POPULATION_SIZE} disagrees with a '
        f'live sweep ({len(live)}), so the number reported on a green run is '
        f'not the number swept'
    )
    assert GUARD_POPULATION_LABEL.strip(), (
        'The published label is empty, so the report header would carry a bare '
        'number with nothing naming what was counted'
    )


def test_the_token_scan_is_not_vacuous():
    """Some doc must carry a token, or the sweep proves nothing.

    A zero hit count here would not mean "no doc pins a build tool" — it would
    mean the detector matched nothing, which is what a broken token tuple looks
    like from the outside.
    """
    assert _HITS, (
        f'Not one of the {len(_DOCS)} swept documents carries any of '
        f'{_BUILD_TOOL_TOKENS}, so either the token tuple is broken or the '
        f'population is not the shipped bundle'
    )


def test_no_shipped_doc_pins_a_build_tool_outside_the_allow_list():
    offenders = {
        rel: tokens for rel, tokens in _HITS.items() if rel not in _ALLOW_LIST
    }

    assert not offenders, (
        f'These shipped documents name a concrete build tool and are not on the '
        f'legitimate-self-reference allow-list ({len(_ALLOW_LIST)} entries, '
        f'derived from deliverable 1\'s classification): {offenders}. '
        f'Either resolve the command through '
        f'`architecture resolve --command {{canonical}}`, or declare the '
        f'meta-project scope at the site and add the file to the allow-list '
        f'with the category that justifies it. '
        f'(population: {len(_DOCS)} docs, {len(_HITS)} carrying a token)'
    )


# ---------------------------------------------------------------------------
# The allow-list stays bounded — a stale entry is reported, never carried
# ---------------------------------------------------------------------------


def test_every_allow_list_entry_still_exists():
    missing = sorted(
        rel for rel in _ALLOW_LIST if not (PROJECT_ROOT / rel).is_file()
    )

    assert not missing, (
        f'These allow-list entries name no file in the tree, so the allow-list '
        f'is granting an exemption to nothing: {missing}'
    )


def test_every_allow_list_entry_still_carries_a_token():
    """An entry that no longer needs the exemption must lose it.

    Without this, the allow-list only ever grows: entries whose literal was
    later removed keep standing as a permanent, unfalsifiable licence to
    reintroduce one.
    """
    stale = sorted(
        rel
        for rel in _ALLOW_LIST
        if (PROJECT_ROOT / rel).is_file() and not _tokens_in(PROJECT_ROOT / rel)
    )

    assert not stale, (
        f'These allow-list entries carry no build-tool token any more, so their '
        f'exemption is stale and would silently re-license a reintroduced pin: '
        f'{stale} (allow-list: {len(_ALLOW_LIST)} entries)'
    )


def test_the_two_allow_list_categories_are_disjoint():
    """A file is exempt for exactly one reason.

    Overlap would let the union stay the same size while one category silently
    absorbed the other's members, and the categories carry different
    obligations.
    """
    overlap = sorted(frozenset(_SELF_REFERENCE) & frozenset(_D1_SHAPE_B_SCOPE_DECLARED))

    assert not overlap, (
        f'These files are listed in both allow-list categories, so which '
        f'obligation applies to them is undecided: {overlap}'
    )
    assert len(_ALLOW_LIST) == len(_SELF_REFERENCE) + len(_D1_SHAPE_B_SCOPE_DECLARED)


# ---------------------------------------------------------------------------
# Deliverable 1's remediated shape-B files stay remediated
# ---------------------------------------------------------------------------


def test_the_token_removed_shape_b_files_carry_no_build_tool_token():
    assert _D1_SHAPE_B_TOKEN_REMOVED, (
        'No token-removed shape-B file is registered, so this assertion sweeps '
        'nothing'
    )

    regressed = {}
    for rel in _D1_SHAPE_B_TOKEN_REMOVED:
        path = PROJECT_ROOT / rel
        assert path.is_file(), (
            f'{rel} no longer exists, so the remediation it records cannot be '
            f'verified'
        )
        tokens = _tokens_in(path)
        if tokens:
            regressed[rel] = tokens

    assert not regressed, (
        f'Deliverable 1 classified these as shipped instructions pinning a '
        f'build tool, and the fix REMOVED the literal. It is back: {regressed}'
    )


def test_the_token_removed_files_are_not_on_the_allow_list():
    """The two dispositions must not both apply to one file.

    A file whose literal was removed has no exemption to hold; carrying one
    anyway would let the literal return without failing anything.
    """
    both = sorted(frozenset(_D1_SHAPE_B_TOKEN_REMOVED) & _ALLOW_LIST)

    assert not both, (
        f'These files are recorded as having had their build-tool literal '
        f'removed AND are allow-listed to carry one: {both}'
    )


# ---------------------------------------------------------------------------
# Matched control — the detector fires, and only where it should
# ---------------------------------------------------------------------------


def test_token_detector_fires_on_a_consumer_facing_instruction(tmp_path):
    pinned = tmp_path / 'pinned.md'
    pinned.write_text(
        'Run the gate before pushing:\n'
        '\n'
        '```bash\n'
        './pw verify plan-marshall\n'
        '```\n',
        encoding='utf-8',
    )

    assert _tokens_in(pinned) == ['./pw'], (
        'The token detector did not fire on a synthetic consumer-facing '
        'instruction, so the sweep above would report a clean tree no matter '
        'what the docs say'
    )


def test_token_detector_stays_silent_on_a_resolver_backed_instruction(tmp_path):
    resolved = tmp_path / 'resolved.md'
    resolved.write_text(
        'Resolve the canonical and run what it returned:\n'
        '\n'
        '```bash\n'
        'python3 .plan/execute-script.py '
        'plan-marshall:manage-architecture:architecture \\\n'
        '  resolve --command verify --module {module} --audit-plan-id {plan_id}\n'
        '```\n',
        encoding='utf-8',
    )

    assert _tokens_in(resolved) == [], (
        'The token detector fires on the resolver-backed form, so every '
        'correctly-written document would be reported as an offender'
    )
