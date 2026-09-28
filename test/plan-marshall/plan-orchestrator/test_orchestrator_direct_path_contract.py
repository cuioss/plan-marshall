#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""An orchestrator direct-file ledger instruction addresses the resolved epic tree.

The orchestrator verb workflows author the epic's narrative documents with the
Read/Write/Edit tools and commit ledger files with git. A tool call is not a
Python seam: a cwd-relative ``.plan/orchestrator/{slug}/`` path lands on the
checkout the session runs in, which with ``orchestrator.use_worktree`` on is not
the checkout the store lives in. Every such instruction therefore addresses the
tree ``orchestrator resolve-path`` returns — ``{epic_dir}/…`` for a file tool,
``git -C {store_checkout}`` for a ledger commit — and this module makes an
unrebased instruction a red test.

**Population.** Every ``*.md`` under the ``plan-orchestrator`` and
``persona-plan-orchestrator`` skill directories, globbed at test time and never
listed; a non-vacuity guard requires it to contain ``workflow/init.md``,
``workflow/decompose.md`` and ``standards/orchestration-model.md``.

**Unit.** The blank-line-delimited paragraph outside fenced blocks (headings are
boundaries, not paragraphs). Within a paragraph a **clause** is a span split on
sentence ends, on ``;`` and on line breaks — a list item or a table row is its
own statement — so a negation in one clause cannot excuse another. A match is
**negated** when a whole-word, case-insensitive ``never``, ``not``, ``no`` or
``cannot`` PRECEDES it within its clause; a negation after the match (a trailing
"when no archived tree exists", or a predicate "… path is never used") governs a
different phrase and excuses nothing, so a negated instruction states its
negation first. A hyphenated compound (``no-op``) is not a negation, and a
hyphenated ``commit`` (``pre-commit``) is not the verb. The **file-tool marker**
is the Read / Write / Edit tool named as a tool: ``Read/Write/Edit``,
``Write/Edit``, a backticked tool name, or ``the Read|Write|Edit tool`` with the
article in either case — never the lowercase verbs.

**Rules.**

1. A paragraph carrying a file-tool marker AND a clause with a non-negated
   ledger-document token carries ``{epic_dir}``.
2. In a paragraph carrying a file-tool marker, every clause carrying the literal
   ``.plan/orchestrator/`` or ``.plan/archived-orchestrators/`` prefix negates it.
   An occurrence inside the logical hand-off pointer (``implement
   .plan/orchestrator/…``, the ``source_id`` that stays logical) is not a tool
   address and is skipped.
3. On the orchestrator's own instruction surfaces, a paragraph carrying a clause
   with a non-negated git-write instruction (``git add``, ``git commit``, or a
   verb form of ``commit``) carries ``{store_checkout}``.
4. A document whose text carries ``{epic_dir}`` or ``{store_checkout}`` carries
   the ``resolve-path`` invocation or cross-references the direct-file-write
   carve-out that states it.

⚠ **Residual.** The rules are paragraph-scoped, so a rewording that separates the
file-tool marker from the ledger token across a blank line escapes Rules 1 and 2.
A negation that precedes the match but governs another phrase in the same
clause (a leading "When no tree exists, write …") still excuses it.
"""

import re
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT

_SKILLS = Path(MARKETPLACE_ROOT) / 'plan-marshall' / 'skills'
_ORCH = _SKILLS / 'plan-orchestrator'
_PERSONA = _SKILLS / 'persona-plan-orchestrator'
_MODEL = _PERSONA / 'standards' / 'orchestration-model.md'

_FLOOR = (_ORCH / 'workflow' / 'init.md', _ORCH / 'workflow' / 'decompose.md', _MODEL)

_EPIC_DIR = '{epic_dir}'
_STORE_CHECKOUT = '{store_checkout}'

_FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
_HEADING_RE = re.compile(r'^ {0,3}#{1,6}[ \t]+(?P<title>.*)$')
_CLAUSE_SPLIT_RE = re.compile(r'(?<=[.!?;])\s+|\n')
#: Word edges exclude a hyphen on either side: ``no-op`` or ``pre-commit`` is a
#: compound noun, never the negation or the verb the bare word would be.
_NEGATION_RE = re.compile(r'(?<![\w-])(?:never|not|no|cannot)(?![\w-])', re.IGNORECASE)
_FILE_TOOL_RE = re.compile(r'Read/Write/Edit|Write/Edit|`(?:Read|Write|Edit)`|\b[Tt]he (?:Read|Write|Edit) tool\b')
_LEDGER_DOC_TOKENS = (
    'epic.md',
    'history.md',
    'settled.md',
    'references.json',
    'workstreams/WS-',
    'plans/PLAN-',
    'landings/PLAN-',
)
_LITERAL_PREFIXES = ('.plan/orchestrator/', '.plan/archived-orchestrators/')
_HANDOFF_POINTER_RE = re.compile(r'implement \.plan/(?:orchestrator|archived-orchestrators)/')
_GIT_WRITE_RE = re.compile(
    r'(?<![\w-])(?:git add|git commit|commit(?:s|ting|ted)?)(?![\w-])',
    re.IGNORECASE,
)
#: Rule 3 exemption 1 — the noun sense of ``commit``. A determiner or a
#: possessive never precedes a verb, so ``commit`` after one is the noun or the
#: attributive participle; the unrebased tree read that way in "the committed
#: `queue-view.md`" (plan-orchestrator/SKILL.md § resume-summary,
#: orchestration-model.md § Persist / Stop-Resume Contract, orchestrate.md § Step 2
#: and § Step 3, resume.md § Step 3), "walk every commit"
#: (orchestration-model.md § Ledger Write Pattern), "a sibling epic's commit"
#: (orchestration-model.md § Re-Grounding Verdict Field), "the commit, the PR"
#: (cleanup.md § Step 4 (A2)) and "landing its commits" (orchestration-model.md
#: § Shared ledger worktree).
_NOUN_FOLLOWERS = ('message', 'sha', 'hash', 'trailer', 'range', 'history', 'log')
_NOUN_PRECEDERS = ('merge', 'squash', 'the', 'a', 'an', 'every', 'each', 'its')
_POSSESSIVE_SUFFIX = "'s"
#: ``git add/add`` names a merge-conflict class, not a command
#: (orchestration-model.md § Staging identity).
_CONFLICT_CLASS_SUFFIX = '/add'
#: Rule 3 exemption 2 — a clause describing a plan's own commits: the plan noun
#: phrase followed directly by the verb. Anything between them fails closed.
_PLAN_SUBJECT_RE = re.compile(
    r'^(?:a plan|the plan|an executing plan)\s+commit(?:s|ted|ting)?(?![\w-])',
    re.IGNORECASE,
)
#: Rule 3 exemption 3 — a commit in another repository, already addressed at its
#: own checkout (orchestration-model.md § Lessons-Handling Mode Contract,
#: cross-repo lesson removal).
_FOREIGN_REPO_TARGET = 'git -C {remote_repo}'
_LEAD_IN_RE = re.compile(r'^[\s>*_`|-]*(?:\d+\.\s*)?[\s*_`]*')
_RESOLVE_REFERENCES = ('resolve-path', 'direct-file-write-carve-out')


def _population() -> list[Path]:
    return sorted({path for root in (_ORCH, _PERSONA) for path in root.rglob('*.md')})


def _instruction_surfaces() -> list[Path]:
    return sorted({*(_ORCH / 'workflow').glob('*.md'), _ORCH / 'SKILL.md', _PERSONA / 'SKILL.md', _MODEL})


def _paragraphs(text: str) -> list[tuple[str, str]]:
    """Every ``(enclosing heading, paragraph)`` pair outside fenced blocks."""
    found: list[tuple[str, str]] = []
    current: list[str] = []
    heading = ''
    fence = ''

    def flush() -> None:
        if current:
            found.append((heading, '\n'.join(current)))
            current.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if fence:
            if stripped and set(stripped) == {fence[0]} and len(stripped) >= len(fence):
                fence = ''
            continue
        opener = _FENCE_RE.match(line)
        if opener:
            flush()
            fence = opener.group(1)
            continue
        titled = _HEADING_RE.match(line)
        if titled:
            flush()
            heading = titled.group('title').strip()
            continue
        if not stripped:
            flush()
            continue
        current.append(line)
    flush()
    return found


def _clauses(paragraph: str) -> list[str]:
    return [clause for clause in _CLAUSE_SPLIT_RE.split(paragraph) if clause.strip()]


def _affirms(clause: str, start: int | None) -> bool:
    """Whether the match at ``start`` stands un-negated — no negation word precedes it in ``clause``."""
    return start is not None and not _NEGATION_RE.search(clause[:start])


def _first_start(text: str, needles: tuple[str, ...]) -> int | None:
    return min((text.find(needle) for needle in needles if needle in text), default=None)


def _rule1_triggers(paragraph: str) -> bool:
    return bool(_FILE_TOOL_RE.search(paragraph)) and any(
        _affirms(clause, _first_start(clause, _LEDGER_DOC_TOKENS)) for clause in _clauses(paragraph)
    )


def rule1_violated(paragraph: str) -> bool:
    return _rule1_triggers(paragraph) and _EPIC_DIR not in paragraph


def _rule2_literal_clauses(paragraph: str) -> list[tuple[str, int]]:
    """Every ``(clause, literal-prefix start)`` pair, with the hand-off pointer stripped first."""
    if not _FILE_TOOL_RE.search(paragraph):
        return []
    found = []
    for clause in _clauses(paragraph):
        stripped = _HANDOFF_POINTER_RE.sub('', clause)
        start = _first_start(stripped, _LITERAL_PREFIXES)
        if start is not None:
            found.append((stripped, start))
    return found


def rule2_violated(paragraph: str) -> bool:
    return any(_affirms(clause, start) for clause, start in _rule2_literal_clauses(paragraph))


def _git_write_start(clause: str) -> int | None:
    """Where the first git-write instruction in ``clause`` starts, or ``None`` when it carries none."""
    if _PLAN_SUBJECT_RE.match(_LEAD_IN_RE.sub('', clause)) or _FOREIGN_REPO_TARGET in clause:
        return None
    for match in _GIT_WRITE_RE.finditer(clause):
        if match.group().lower().startswith('git '):
            if clause[match.end() :].startswith(_CONFLICT_CLASS_SUFFIX):
                continue
            return match.start()
        following = clause[match.end() :].split()
        preceding = clause[: match.start()].split()
        if following and following[0].strip('`*.,;:()').lower() in _NOUN_FOLLOWERS:
            continue
        if preceding:
            word = preceding[-1].strip('`*.,;:()').lower()
            if word in _NOUN_PRECEDERS or word.endswith(_POSSESSIVE_SUFFIX):
                continue
        return match.start()
    return None


def _rule3_triggers(paragraph: str) -> bool:
    return any(_affirms(clause, _git_write_start(clause)) for clause in _clauses(paragraph))


def rule3_violated(paragraph: str) -> bool:
    return _rule3_triggers(paragraph) and _STORE_CHECKOUT not in paragraph


def _uses_tokens(text: str) -> bool:
    return _EPIC_DIR in text or _STORE_CHECKOUT in text


def rule4_violated(text: str) -> bool:
    return _uses_tokens(text) and not any(reference in text for reference in _RESOLVE_REFERENCES)


def _flagged(paths: list[Path], violated) -> list[str]:
    return [
        f'{path.relative_to(_SKILLS)} § {heading or "(top)"}: {" ".join(paragraph.split())[:160]}'
        for path in paths
        for heading, paragraph in _paragraphs(path.read_text(encoding='utf-8'))
        if violated(paragraph)
    ]


def _count_triggers(paths: list[Path], trigger) -> int:
    return sum(
        1 for path in paths for _, paragraph in _paragraphs(path.read_text(encoding='utf-8')) if trigger(paragraph)
    )


class TestPopulation:
    def test_the_population_is_globbed_and_reaches_the_floor(self):
        population = _population()

        missing = [str(path) for path in _FLOOR if path not in population]

        assert len(population) > len(_FLOOR), f'{len(population)} documents globbed under {_ORCH} and {_PERSONA}'
        assert missing == [], f'the globbed population of {len(population)} documents misses {missing}'


class TestRebasedTree:
    def test_rule1_every_ledger_document_instruction_names_the_resolved_tree(self):
        flagged = _flagged(_population(), rule1_violated)

        assert flagged == [], (
            f'Rule 1 — {len(flagged)} paragraph(s) name a ledger document beside a file tool: {flagged}'
        )

    def test_rule2_the_literal_prefix_is_only_a_negated_mention(self):
        flagged = _flagged(_population(), rule2_violated)

        assert flagged == [], f'Rule 2 — {len(flagged)} paragraph(s) address the literal store prefix: {flagged}'

    def test_rule3_every_ledger_commit_targets_the_store_checkout(self):
        flagged = _flagged(_instruction_surfaces(), rule3_violated)

        assert flagged == [], f'Rule 3 — {len(flagged)} paragraph(s) commit without {_STORE_CHECKOUT}: {flagged}'

    def test_rule4_every_document_using_the_tokens_resolves_them(self):
        unresolved = [
            str(path.relative_to(_SKILLS)) for path in _population() if rule4_violated(path.read_text(encoding='utf-8'))
        ]

        assert unresolved == [], f'Rule 4 — documents using the tokens with no resolve reference: {unresolved}'

    def test_every_rule_trigger_matches_a_real_paragraph(self):
        # A checker whose trigger matches nothing passes every rule vacuously.
        population = _population()
        counts = {
            'rule1': _count_triggers(population, _rule1_triggers),
            'rule2': _count_triggers(population, _rule2_literal_clauses),
            'rule3': _count_triggers(_instruction_surfaces(), _rule3_triggers),
            'rule4': sum(1 for path in population if _uses_tokens(path.read_text(encoding='utf-8'))),
        }

        assert all(counts.values()), f'a rule trigger matched no real paragraph or document: {counts}'


class TestRuleControls:
    def test_rule1_rejects_an_unrebased_instruction_and_accepts_its_twin(self):
        assert rule1_violated('Instantiate `epic.md` from the template via the Write tool.')
        assert not rule1_violated('Instantiate `{epic_dir}/epic.md` from the template via the Write tool.')

    def test_rule1_reads_a_sentence_initial_tool_article(self):
        assert rule1_violated('The Write tool instantiates epic.md from the template.')
        assert not rule1_violated('The Write tool instantiates {epic_dir}/epic.md from the template.')

    def test_rule2_rejects_an_affirmative_literal_and_accepts_a_negated_one(self):
        assert rule2_violated('Write `.plan/orchestrator/{slug}/epic.md` with the Write tool.')
        assert not rule2_violated(
            'Every direct Read/Write/Edit addresses `{epic_dir}/…`; never use a cwd-relative '
            '`.plan/orchestrator/{slug}/` path for a tool call.'
        )

    def test_rule2_scopes_the_negation_to_its_own_clause(self):
        assert rule2_violated(
            'Never touch `logs/` directly; use the Write tool on `.plan/orchestrator/{slug}/epic.md`.'
        )

    def test_a_trailing_negation_does_not_excuse_the_instruction(self):
        # The negation must precede the matched token: a stray "no" after it negates another phrase.
        assert rule1_violated('Instantiate `epic.md` via the Write tool when no archived tree exists.')
        assert rule2_violated(
            'Write `.plan/orchestrator/{slug}/epic.md` with the Write tool when no archived tree exists.'
        )
        assert rule3_violated('Commit the closed ledger when no archived tree exists.')

    def test_a_leading_negation_still_excuses_the_instruction(self):
        assert not rule1_violated('Never instantiate `epic.md` via the Write tool from the session checkout.')
        assert not rule2_violated('Never Write `.plan/orchestrator/{slug}/epic.md` with the Write tool.')
        assert not rule3_violated('Never commit the closed ledger from the session checkout.')

    def test_rule2_skips_the_logical_handoff_pointer(self):
        assert not rule2_violated(
            'After the `Read` of the spec, emit `/plan-marshall task="implement .plan/orchestrator/{slug}/plans/x.md"`.'
        )

    def test_rule3_rejects_a_commit_naming_no_ledger_file(self):
        assert rule3_violated('Commit it with the closed ledger.')
        assert not rule3_violated('Commit it with the closed ledger via `git -C {store_checkout}`.')

    def test_rule3_leaves_the_noun_sense_and_a_plan_subject_alone(self):
        assert not rule3_violated('Record the merge commit in the landing.')
        assert not rule3_violated('Quote the commit message verbatim.')
        assert not rule3_violated('A plan commits its own changes through its PR.')
        assert not rule3_violated('The plan commits its own changes through its PR.')
        assert not rule3_violated('An executing plan commits its inbox message through its PR.')

    @pytest.mark.parametrize(
        'clause',
        [
            'The plan landing is committed with the ledger.',
            'The plan queue row is committed',
            'The plan-orchestrator commits the ledger.',
        ],
        ids=['plan-as-modifier', 'plan-as-modifier-phrase', 'hyphenated-compound'],
    )
    def test_rule3_flags_a_subject_that_only_starts_with_plan(self, clause):
        assert rule3_violated(clause)

    def test_rule3_reads_hyphenated_compounds_as_neither_verb_nor_negation(self):
        assert not rule3_violated('Run the pre-commit hook on the anchor file.')
        assert rule3_violated('Treat it as a no-op and commit the anchor file.')

    def test_rule3_leaves_a_commit_addressed_at_another_repository_alone(self):
        assert not rule3_violated('Remove the file and commit it via `git -C {remote_repo}`.')
        assert rule3_violated('Remove the file and commit it via `git -C {path}`.')

    def test_rule3_leaves_a_determiner_possessive_and_conflict_name_alone(self):
        assert not rule3_violated('It says whether the committed `queue-view.md` still matches.')
        assert not rule3_violated('Walk every commit that touched the ledger.')
        assert not rule3_violated("A sibling epic's commit makes that test true.")
        assert not rule3_violated('A duplicate id surfaces as a git add/add conflict.')

    def test_rule3_still_flags_the_verb_beside_those_exemptions(self):
        assert rule3_violated('Regenerate the view, then commit the anchor file.')
        assert rule3_violated('Merge the source files and git add the result.')

    def test_rule4_requires_the_resolve_reference(self):
        assert rule4_violated('Edit `{epic_dir}/epic.md`.')
        assert not rule4_violated('Run `orchestrator resolve-path --slug S`, then edit `{epic_dir}/epic.md`.')
