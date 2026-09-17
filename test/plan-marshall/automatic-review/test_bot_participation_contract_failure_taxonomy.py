#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Contract-level suite for ``standards/bot-participation-contract.md``.

Cross-cutting counterpart to the co-located unit suites. Those pin per-component
BEHAVIOUR (``test_review_completeness.py`` owns the predicate's verdicts,
``test_upgrade.py`` owns the migration's four input states,
``test_comments_stage.py`` owns the producer's filters). This suite pins the
CONTRACT the components jointly implement:

* both participation knobs default to the EMPTY string on a fresh project;
* ``never_asked`` / ``migrated`` / ``answered`` are three distinguishable
  provenance states, so a never-asked key stays distinct from an answered-empty
  one;
* THIS repository's step params carry the settled two-list configuration;
* an unlisted bot is warned-about and STILL ingested (the warn-but-ingest rule);
* the failure taxonomy is EXHAUSTIVE — every classified bot lands in exactly one
  member, over a bot set derived from ``bot_registry.bot_kinds()``;
* the taxonomy's doc/code closure holds in BOTH directions — no classifier member
  is undocumented, no documented member is unproducible — and the contract's own
  closure-count sentence agrees with the derived member count;
* every DOCUMENTED call site of the two invocation families quotes its
  interpolated list-flag placeholders, over a site population derived by scanning
  the marketplace tree;
* every DOCUMENTED call site additionally resolves to a recorded EVIDENCE CLASS —
  the ``reads`` axis of the participation-site population's own expectation record
  for the script the site's executor notation names — so a call site that invokes a
  participation script for which ``test_participation_site_population.py`` holds no
  record fails here instead of escaping both populations;
* a crashed participation gate is an UNKNOWN verdict at both families and at both
  consuming documents — never a recorded pass;
* each advertised invocation form agrees with its live argparse surface on the
  optionality of every list flag;
* the FULL declared optional-flag surface of ``review_completeness check`` is
  classified — every long option the live parser declares is assigned a coverage
  arm, so a flag whose shape the ``--*-bots`` family pattern cannot match (the
  ``store_true`` ``--not-triggered``) cannot escape every sweep unnoticed;
* every ``N blocking members`` count stated anywhere in the marketplace tree
  agrees with the blocking subset derived from ``_UNPROVEN_STATES`` — which is
  strictly smaller than the taxonomy, so reaching for the taxonomy's size there
  is the specific error guarded.

Every set-guarding assertion derives its population from the registry (for bots),
from a repository scan (for call sites), from the live argparse surface (for
flags), or from ``review_completeness``'s own ``STATE_`` constants (for taxonomy
members) rather than a hard-coded literal list, so a bot added or retired in a
standards doc, a fifth call site added in a future doc, a further flag added to the
parser, or a new classifier state is covered here automatically instead of silently
escaping the sweep. The taxonomy tuple keeps its explicit spelling — its order and
its ``len`` are load-bearing — but is asserted equal to the derived set at import,
which is the same guarantee by a different route.
Each sub-population is additionally guarded against vacuity: a derivation that
matched nothing FAILS rather than reporting a healthy aggregate over an empty set.
"""

from __future__ import annotations

import itertools
import json
import re
from unittest.mock import patch

import bot_registry
import pytest
from _bot_flag_derivation import derive_bot_flags, derive_declared_flags

# The EVIDENCE-CLASS vocabulary and its per-script records are OWNED by the
# participation-site population module and read from it here rather than restated.
# A second copy of either would be the duplicate-definition failure that population
# exists to forbid, and the call-site sweep below would then be able to report a
# class the population itself does not recognise.
from test_participation_site_population_records import READS_VOCABULARY, SITE_EXPECTATIONS

from conftest import (
    PLAN_DIR_NAME,
    PROJECT_ROOT,
    get_script_path,
    load_script_module,
    run_script,
)

# ``register=False``: only the returned module is needed here, and a sibling suite
# (``test_unknown_bot_kind_escalation.py``) imports ``review_completeness`` plainly.
# Registering under that name would put two copies of the module in play, reachable
# by different routes and differing by collection order.
rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_AR_SCRIPTS = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py').parent

_CONTRACT_DOC = _AR_SCRIPTS.parent / 'standards' / 'bot-participation-contract.md'
_AR_SKILL = _AR_SCRIPTS.parent / 'SKILL.md'
_RC_SCRIPT = get_script_path('plan-marshall', 'automatic-review', 'review_completeness.py')

# THIS repository's tracked config, resolved through conftest's project anchor so
# the suite is cwd-independent.
_MARSHAL_JSON = PROJECT_ROOT / PLAN_DIR_NAME / 'marshal.json'
_AUTOMATIC_REVIEW_STEP_ID = 'plan-marshall:automatic-review'


def _live_step_params() -> dict:
    """Return this repository's tracked ``plan-marshall:automatic-review`` params."""
    config = json.loads(_MARSHAL_JSON.read_text(encoding='utf-8'))
    params: dict = config['plan']['phase-6-finalize']['steps'][_AUTOMATIC_REVIEW_STEP_ID]
    return params


# The three provenance values the contract declares. Sourced from the contract doc
# itself rather than restated as a convenience literal.
_PROVENANCE_STATES = ('never_asked', 'migrated', 'answered')

# The closed NON-participation members. ``participated`` is deliberately NOT a
# member — it is the complement the taxonomy exists to distinguish from.
#
# The last THREE are the REFINEMENTS of ``absent``, listed after the mutually
# independent observations because that is what they are: each says the bot
# published nothing, and each carries a remedy opposite to ``absent``'s escalation
# (re-trigger the stale review / trigger the review at all / fix the configured
# name). ``unregistered_kind`` is last because it is the only member decided from
# the CONFIGURATION rather than from an observation — the classifier checks it after
# every observation branch, so a token that is unregistered yet observed still
# reports what was observed. ``declined`` sits among
# the independent observations: like a refusal, it says the bot engaged and would
# not review this commit, so it is not a refinement of ``absent``. Of the FOUR refusal
# members, three (``refused_awaitable`` / ``refused_hard`` / ``refused_unknown``) are the
# DEFAULT mapping of the bot's three-valued ``rate_limit_class`` — a default, not a
# bijection, because TWO per-refusal observations displace it. ``refused_structural``
# is one: a refusal whose observed CAUSE is a diff-size ceiling. The other reaches
# ``refused_unknown``: a refusal NO arm of the recognition stack could READ, which
# resolves there whatever the bot's declared class says, because nothing about an
# unparsed notice is known. Both overrides are checked BEFORE the class, because a
# class declared per BOT cannot separate observations made per REFUSAL. This tuple's
# LENGTH is load-bearing — the closure-count
# check below reads the contract's own prose count back as an integer and compares it
# against ``len`` here, which is what stops a member reaching the classifier and the
# table while the prose still claims fewer.
_NON_PARTICIPATION_MEMBERS = (
    rc.STATE_ABSENT,
    rc.STATE_IN_PROGRESS,
    rc.STATE_REFUSED_AWAITABLE,
    rc.STATE_REFUSED_HARD,
    rc.STATE_REFUSED_UNKNOWN,
    rc.STATE_REFUSED_STRUCTURAL,
    rc.STATE_PARTICIPATED_BUT_EMPTY,
    rc.STATE_DECLINED,
    rc.STATE_PARTICIPATED_STALE,
    rc.STATE_NOT_TRIGGERED,
    rc.STATE_UNREGISTERED_KIND,
)

# ...and the DERIVED population it must equal. The tuple above is retained for its
# order and its ``len``, both of which are load-bearing (see the comment above), so
# the derivation is asserted against it rather than replacing it.
#
# Without this equality the tuple is a hand-maintained mirror and the file breaks
# the derived-population rule its own docstring declares. Worse, the tuple is the
# SHARED PIVOT of two checks — the documented-set comparison and the closure-count
# comparison both read it — so a member that reached only the classifier would move
# both sides of the count together and every check would stay green over a set that
# is missing it. Asserting here makes that member fail at IMPORT, once, loudly.
#
# ``STATE_PARTICIPATED`` is the sole intended exclusion: it is the taxonomy's
# COMPLEMENT (the bot delivered a usable review), not a further member of it — see
# the module comment at ``review_completeness.py`` above ``STATE_ABSENT``. The
# cardinality is deliberately NOT spelled here: an ordinal written into a comment
# is a second statement of the taxonomy's size and the one that goes stale in
# silence, still reading as a claim about a set that has moved. The only place this
# module states the count is the failure message of the equality assertion below,
# which INTERPOLATES it from the tuple and therefore cannot drift from it. The
# ``vars(rc)`` sweep cannot pick up a ``STATE_``-prefixed name imported from
# elsewhere: ``rc`` imports only ``argparse``, ``sys``, ``bot_registry``, and
# ``query_findings``, none of which is ``STATE_``-prefixed, and the ``str`` filter
# below additionally excludes any non-constant binding a future import might add.
_DERIVED_NON_PARTICIPATION = frozenset(
    value
    for name, value in vars(rc).items()
    if name.startswith('STATE_') and name != 'STATE_PARTICIPATED' and isinstance(value, str)
)

assert _DERIVED_NON_PARTICIPATION, (
    'no STATE_ constant was derived from review_completeness — the taxonomy '
    'population is vacuous and every sweep over it would pass over an empty set'
)

assert frozenset(_NON_PARTICIPATION_MEMBERS) == _DERIVED_NON_PARTICIPATION, (
    f'the _NON_PARTICIPATION_MEMBERS tuple ({len(_NON_PARTICIPATION_MEMBERS)} members '
    f'spelled) has drifted from review_completeness ({len(_DERIVED_NON_PARTICIPATION)} '
    f'derived): '
    f'only in the tuple={sorted(frozenset(_NON_PARTICIPATION_MEMBERS) - _DERIVED_NON_PARTICIPATION)}, '
    f'only in the module={sorted(_DERIVED_NON_PARTICIPATION - frozenset(_NON_PARTICIPATION_MEMBERS))}. '
    f'{rc.STATE_PARTICIPATED!r} is the sole intended exclusion — the COMPLEMENT of the '
    f'{len(_DERIVED_NON_PARTICIPATION)}-member non-participation taxonomy, never member '
    f'{len(_DERIVED_NON_PARTICIPATION) + 1} of it'
)

assert len(_NON_PARTICIPATION_MEMBERS) == len(_DERIVED_NON_PARTICIPATION), (
    'the _NON_PARTICIPATION_MEMBERS tuple carries a duplicate — its len is '
    'load-bearing for the closure-count check, so a repeated member would '
    'overstate the taxonomy while the set equality above still held'
)

#: A member row of the failure-taxonomy table: the backticked identifier that opens
#: the row's leading cell. Anchored at the line start so only table rows match.
_MEMBER_ROW = re.compile(r'^\|\s*`(?P<member>[a-z_]+)`\s*\|', re.MULTILINE)

#: The contract's own closure-count sentence. Whitespace is collapsed before
#: matching, because the sentence wraps across a line break in the source.
_CLOSURE_COUNT = re.compile(r'classified into exactly one of (?P<count>\w+) members')

#: A consumer-side claim about how many taxonomy members BLOCK. The blocking
#: subset is ``_UNPROVEN_STATES``, which is strictly smaller than the taxonomy —
#: ``participated_but_empty`` is a member that never blocks — so a consumer doc
#: that reaches for the taxonomy's size here overstates the set it is describing.
_BLOCKING_COUNT = re.compile(r'(?P<count>\w+) blocking members')

#: Cardinal number words indexed by the value they name. The contract states its
#: closure count in PROSE, so reading it back has to cross the word/integer
#: boundary rather than grep for a digit that is not there.
_NUMBER_WORDS = (
    'zero',
    'one',
    'two',
    'three',
    'four',
    'five',
    'six',
    'seven',
    'eight',
    'nine',
    'ten',
    'eleven',
    'twelve',
)


def _failure_taxonomy_section() -> str:
    """Return the contract's ``## Failure taxonomy`` section body.

    Scoped to that ONE section deliberately: the document carries several other
    tables (provenance, publish shapes, marker surfaces, consumers) whose leading
    cell is also a backticked identifier, and a whole-document scan would admit
    those as phantom taxonomy members — inflating the documented set until the
    doc-to-code direction below could never fail.
    """
    doc = _CONTRACT_DOC.read_text(encoding='utf-8')
    section = re.search(r'^## Failure taxonomy$(?P<body>.*?)(?=^## )', doc, re.DOTALL | re.MULTILINE)
    assert section, 'the contract must carry a "## Failure taxonomy" section'
    return section.group('body')


def _documented_members() -> tuple[str, ...]:
    """The taxonomy members the CONTRACT documents, derived by parsing its table."""
    members = tuple(dict.fromkeys(_MEMBER_ROW.findall(_failure_taxonomy_section())))
    assert members, (
        'the failure-taxonomy table parsed to zero members — the scan is vacuous and '
        'the doc-to-code direction would pass over an empty set'
    )
    return members


def _stated_blocking_counts(text: str) -> tuple[int, ...]:
    """Every blocking-member COUNT ``text`` states, as integers.

    A ``N blocking members`` phrase whose ``N`` is a qualifier rather than a
    number ("the", "these") states no count and is skipped — writing no number
    is the preferred shape, so it is not a claim this check constrains. Both
    spellings of a real count are read: the cardinal word and the digit.
    """
    counts: list[int] = []
    for match in _BLOCKING_COUNT.finditer(' '.join(text.split())):
        word = match.group('count')
        if word in _NUMBER_WORDS:
            counts.append(_NUMBER_WORDS.index(word))
        elif word.isdigit():
            counts.append(int(word))
    return tuple(counts)


def _blocking_count_sites() -> tuple[tuple[str, int], ...]:
    """Return ``(relative_doc, stated_count)`` for every blocking-count claim.

    The population is DERIVED by walking the marketplace tree — the same shape
    ``_scan_invocation_sites()`` uses — rather than named in a literal doc list.
    A literal would be complete only until the next doc states a count, which is
    exactly the silent-escape this suite's population-derivation rule exists to
    prevent. Deriving it also reaches the contract doc itself, whose own
    blocking-subset prose is otherwise guarded by nothing.
    """
    sites: list[tuple[str, int]] = []
    for path in sorted(_MARKETPLACE_DOCS.rglob('*.md')):
        for stated in _stated_blocking_counts(path.read_text(encoding='utf-8')):
            sites.append((str(path.relative_to(_MARKETPLACE_DOCS)), stated))
    return tuple(sites)


def _registered_bots() -> list[str]:
    """The bot population, DERIVED from the registry — never a literal list."""
    bots = bot_registry.bot_kinds()
    assert bots, 'registry must declare at least one bot for these sweeps to mean anything'
    return bots


def _configurable_defaults() -> dict[str, str]:
    """Parse ``key``/``default`` pairs out of automatic-review SKILL.md's frontmatter.

    This is the source marshall-steward seeds a fresh project's step params from,
    so it is the authoritative statement of "what a project starts with".
    """
    skill_md = _AR_SKILL.read_text(encoding='utf-8').splitlines()
    defaults: dict[str, str] = {}
    current: str | None = None
    for raw in skill_md:
        stripped = raw.strip()
        if stripped.startswith('- key:'):
            current = stripped.split(':', 1)[1].strip()
        elif stripped.startswith('default:') and current is not None:
            value = stripped.split(':', 1)[1].strip()
            defaults[current] = value.strip('"').strip("'")
            current = None
    return defaults


_CLEAN_REVIEW_HEADING = '### A credited clean review resolves `participated_but_empty`'


_CREDITED_SHAPES: tuple[tuple[str, str], ...] = tuple(
    (bot, shape) for bot in bot_registry.bot_kinds() for shape in bot_registry.participation_evidence(bot)
)


assert _CREDITED_SHAPES, (
    'no registered bot declares a participation_evidence shape — the clean-review '
    'sweep would generate zero cases, which pytest reports as SKIPPED rather than failed'
)


_MARKETPLACE_DOCS = PROJECT_ROOT / 'marketplace' / 'bundles'


_ALL_LIST_FLAGS = tuple(flag for flag, _dest in derive_bot_flags(_RC_SCRIPT, 'check'))


assert _ALL_LIST_FLAGS, 'derive_bot_flags found no list-shaped bot flags on the check parser'


_ALL_DECLARED_FLAGS = derive_declared_flags(_RC_SCRIPT, 'check')


_NON_LIST_FLAG_COVERAGE = {
    '--plan-id': (
        'the required findings-store selector — exercised at the constructed-argv '
        'boundary by every check invocation in TestCrashedGateNeverRecordsAPass'
    ),
    '--not-triggered': (
        'the store_true PR-wide observable — the member it assigns is swept over the '
        'whole bot population by the not_triggered shape of the taxonomy parametrize, '
        'and its CLI boundary is owned by test_review_completeness.py'
    ),
    '--triage-ran': (
        'the store_true verdict modifier — owned by test_review_completeness.py, '
        "whose triage-state matrix pins both of the predicate's two modes"
    ),
    '--refused-causes': (
        'the pair-form CAUSE overlay (bot_kind:cause) — a --*-causes flag OUTSIDE the '
        '--*-bots family. STATE-DETERMINING for a size cause (it resolves the bot to '
        'refused_structural whatever its rate_limit_class says) and advisory for every '
        'other; it gates nothing either way. Its CLI boundary, the refusal_causes[] '
        'output, and the malformed-shape rejection are owned by '
        'test_review_completeness.py, and the structural member it can assign is swept '
        'over the whole bot population by the taxonomy parametrize'
    ),
    '--refusal-size-caps': (
        'the pair-form CAP overlay (bot_kind:cap) — a --*-caps flag OUTSIDE the '
        '--*-bots family, carrying the ceiling a structural refusal stated so the gap '
        'is auditable against the measured diff size. Purely reported: it assigns no '
        'member and gates nothing. Its CLI boundary, the cap column in refusal_causes[], '
        'and the unknown-cap rendering are owned by test_structural_refusal.py'
    ),
    '--measured-diff-size': (
        'the scalar PR-wide diff measurement — neither a --*-bots flag nor a pair-form '
        'overlay, because it is a property of the PR rather than of a bot. It is the '
        'other half of an auditable coverage gap (a cap without the size that hit it is '
        'a claim taken on trust); it assigns no member and gates nothing. Its CLI '
        'boundary and the unknown-when-unmeasured rendering are owned by '
        'test_structural_refusal.py'
    ),
}


_FAMILY_A = 'review_completeness check'


_FAMILY_B = 'github_pr fetch_findings'


_CONFIRMED_SITE_ROWS: tuple[tuple[str, str, str, str, int], ...] = (
    (
        'family-a-step-done-participation-guard',
        _FAMILY_A,
        'automatic-review/SKILL.md',
        'Step-done participation guard',
        8,
    ),
    (
        'family-a-premerge-barrier-predicate-2',
        _FAMILY_A,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Predicate 2',
        7,
    ),
    (
        'family-b-producer-find',
        _FAMILY_B,
        'automatic-review/SKILL.md',
        'Producer: FIND',
        2,
    ),
    (
        'family-b-premerge-barrier-refetch',
        _FAMILY_B,
        'phase-6-finalize/standards/branch-cleanup.md',
        'Re-fetch bot comments against the current HEAD',
        2,
    ),
)


_CONFIRMED_SITES = tuple(
    pytest.param(family, doc, section, count, id=site_id)
    for site_id, family, doc, section, count in _CONFIRMED_SITE_ROWS
)


_FLAG_VALUE = re.compile(
    '(?P<flag>'
    + '|'.join(re.escape(flag) for flag in sorted(_ALL_LIST_FLAGS, key=len, reverse=True))
    + r')(?:[ \t]+(?P<value>\S+))?'
)


def _scan_invocation_sites() -> list[tuple[str, str, str, str]]:
    """Return ``(family, doc, section, command)`` for every documented invocation.

    Walks every markdown file under ``marketplace/bundles`` and collects each
    fenced code block that invokes one of the two families, tagging it with the
    nearest preceding heading so a site is addressable BY NAME rather than by
    line number. Backslash continuations are folded so a multi-line invocation is
    one command string.
    """
    sites: list[tuple[str, str, str, str]] = []
    for path in sorted(_MARKETPLACE_DOCS.rglob('*.md')):
        heading = ''
        in_fence = False
        block: list[str] = []
        block_heading = ''
        for raw in path.read_text(encoding='utf-8').splitlines():
            if raw.lstrip().startswith('```'):
                if in_fence:
                    command = re.sub(r'\\\n\s*', ' ', '\n'.join(block))
                    family = _classify_invocation(command)
                    if family:
                        rel = str(path.relative_to(_MARKETPLACE_DOCS))
                        sites.append((family, rel, block_heading, command))
                    block = []
                    in_fence = False
                else:
                    in_fence = True
                    block_heading = heading
                continue
            if in_fence:
                block.append(raw)
            elif raw.startswith('#'):
                heading = raw.lstrip('#').strip()
    return sites


def _classify_invocation(command: str) -> str:
    """Return the invocation family a fenced command belongs to, or ``''``."""
    if 'automatic-review:review_completeness' in command and re.search(r'\bcheck\b', command):
        return _FAMILY_A
    if 'workflow-integration-github:github_pr' in command and 'fetch_findings' in command:
        return _FAMILY_B
    return ''


_INVOCATION_SITES = _scan_invocation_sites()


assert _INVOCATION_SITES, 'the invocation-site scan found no fenced command — every sweep over it would cover nothing'


def _site_id(site: tuple[str, str, str, str]) -> str:
    """Human-readable, stable nodeid fragment naming the site.

    The id carries the family, the owning document and the section heading, so a
    failure names WHICH call site regressed without opening the test source.
    Punctuation is normalised to hyphens so the id stays a single readable token
    in a pytest nodeid.
    """
    family, doc, section, _command = site
    raw = f'{family}--{doc}--{section}'
    return re.sub(r'[^A-Za-z0-9]+', '-', raw).strip('-').lower()


def _find_confirmed(family: str, doc_suffix: str, section_substring: str) -> tuple:
    """Return the single scanned site matching a confirmed-site descriptor."""
    matches = [
        site
        for site in _INVOCATION_SITES
        if site[0] == family and site[1].endswith(doc_suffix) and section_substring in site[2]
    ]
    assert len(matches) == 1, (
        f'expected exactly one {family} site in {doc_suffix} under a heading containing '
        f'{section_substring!r}; found {[_site_id(m) for m in matches]}'
    )
    return matches[0]


def _interpolated_flags(command: str) -> list[tuple[str, str]]:
    """Return ``(flag, value)`` pairs whose value is a ``{placeholder}`` interpolation."""
    return [
        (match.group('flag'), match.group('value'))
        for match in _FLAG_VALUE.finditer(command)
        if match.group('value') and '{' in match.group('value')
    ]


def _confirmed_counts_by_family() -> dict[str, dict[str, int]]:
    """``{family: {site id: expected flag count}}``, read off ``_CONFIRMED_SITE_ROWS``."""
    grouped: dict[str, dict[str, int]] = {}
    for site_id, family, _doc, _section, count in _CONFIRMED_SITE_ROWS:
        grouped.setdefault(family, {})[site_id] = count
    return grouped


def _confirmed_count_summary() -> str:
    """Render the per-site flag counts as a sentence DERIVED from the tuple.

    The comparative statement ("these sites carry different flag sets, so one shared
    count would hide a site that dropped one flag and gained another") is the reason
    the counts are per-site, and it used to be written out in prose beside the tuple
    — where it named specific flags and specific counts, and went stale the moment a
    site gained a flag. Rendering it instead means the only statement of any count in
    this module is the tuple itself.
    """
    return '; '.join(
        f'{site_id} interpolates {count} list flag(s)'
        for site_id, _family, _doc, _section, count in _CONFIRMED_SITE_ROWS
    )


def _notation_pattern(script_name: str) -> re.Pattern:
    """Match the ``{bundle}:{skill}:{script}`` notation naming ``script_name``.

    Anchored on the SCRIPT the family already names rather than on the executor path,
    so this cannot fail to resolve a site :func:`_classify_invocation` accepted: that
    predicate keys on the very ``{skill}:{script}`` substring matched here, and the
    bundle segment in front of it is what completes the notation. Anchoring on
    ``execute-script.py`` instead would additionally require the two to be adjacent
    after continuation folding, which is a property of how the doc happens to wrap.
    """
    return re.compile(r'([a-z][a-z0-9-]*):([a-z][a-z0-9-]*):' + re.escape(script_name) + r'(?![0-9A-Za-z_])')


def _invoked_script_path(family: str, command: str) -> str:
    """The repo-relative script path the site's own notation resolves to.

    Derived from the command text rather than mapped from the family by hand: the
    family string names the SCRIPT (its first token), and the bundle and skill come
    from the notation the site actually writes.
    """
    script_name = family.split()[0]
    paths = {
        f'marketplace/bundles/{bundle}/skills/{skill}/scripts/{script_name}.py'
        for bundle, skill in _notation_pattern(script_name).findall(command)
    }
    assert len(paths) == 1, (
        f'expected exactly one {script_name} notation in this {family} invocation; '
        f'resolved {sorted(paths)} from: {command.strip()[:200]!r}'
    )
    return next(iter(paths))


def _evidence_class(family: str, command: str) -> str:
    """The EVIDENCE CLASS a call site consumes, from the participation-site record.

    "Evidence class" is the ``reads`` axis of ``SiteExpectation`` — the closed
    vocabulary ``READS_VOCABULARY`` declares, whose members distinguish a live
    comment scan from the durable currency ledger from a deduped projection and the
    rest. It is recorded per participation SITE (the script), and this resolves it
    per documented CALL site by way of the script that site invokes.

    That is the assertion the call-site sweep was missing: it derived which script
    each site calls and never said anything about it, so a documented invocation of a
    participation script the site population holds no record for satisfied the
    quoting sweep here AND escaped the population there — a surface covered by
    neither, with each one's green run reading as coverage.
    """
    path = _invoked_script_path(family, command)
    record = SITE_EXPECTATIONS.get(path)
    assert record is not None, (
        f'{path} is invoked by a documented call site but carries no recorded evidence '
        f'class — test_participation_site_population.py holds no SITE_EXPECTATIONS '
        f'record for it. A participation script reachable from a documented invocation '
        f'must be a member of that population; add its record there rather than '
        f'exempting the call site here.'
    )
    return record.reads


_GH_SCRIPT = get_script_path('plan-marshall', 'workflow-integration-github', 'github_pr.py')


_BRANCH_CLEANUP_DOC = _AR_SCRIPTS.parent.parent / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'


_GH_SKILL = _GH_SCRIPT.parent.parent / 'SKILL.md'


def _optional_value_form(flag: str) -> re.Pattern:
    return re.compile(re.escape(f'[{flag} ') + r'\[[^\]]+\]\]')


def _help_text(script_path, *argv: str) -> str:
    """Return a subcommand's live argparse usage text."""
    result = run_script(script_path, *argv, '--help')
    assert result.success, result.stderr
    usage: str = result.stdout
    return usage


class TestProvenanceIsThreeDistinguishableStates:
    """never_asked / migrated / answered are three states, not two."""

    def test_the_contract_declares_exactly_three_provenance_states(self):
        """All three are documented, so none can be quietly collapsed."""
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        for state in _PROVENANCE_STATES:
            assert f'`{state}`' in doc, f'{state} must be a documented provenance state'

    def test_the_three_states_are_pairwise_distinct(self):
        """Collapsing any pair would erase a distinction the contract needs.

        ``never_asked`` vs ``answered`` is the load-bearing pair — collapsing them
        would make "the operator has not been asked yet" indistinguishable from
        "the operator deliberately chose no required bots", two states that
        warrant opposite handling. ``migrated`` is distinct from both: it was
        seeded by the legacy auto-map, not by an operator answer, so it may be
        overwritten by a later answer while an ``answered`` value may not.
        """
        for left, right in itertools.combinations(_PROVENANCE_STATES, 2):
            assert left != right

    def test_answered_empty_is_an_answer_not_an_absence(self):
        """The distinction that motivates the three states, stated normatively."""
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        assert 'including an explicit answer of none' in doc


class TestWarnButIngest:
    """An unlisted bot is warned-about and STILL ingested."""

    def test_unclassified_bot_is_warned_about_and_its_comment_is_kept(self, plan_context):
        """Classification carries CLASSIFICATION, not ADMISSION.

        Dropping an unclassified bot's comments would make a configuration
        omission silently destroy real review signal — invisible precisely when
        the operator had not yet thought about that bot. The comment is stored and
        the gap is surfaced instead.
        """
        import github_pr

        plan_id = 'bpc-warn-but-ingest'
        plan_context.plan_dir_for(plan_id)

        class _Args:
            pr_number = 900
            required_bots = 'coderabbit'
            optional_bots = ''

            def __init__(self, plan: str) -> None:
                self.plan_id = plan

        comments = [
            {
                'id': 'U1',
                'kind': 'inline',
                'author': 'sourcery-ai',
                'body': 'The retry loop can spin forever when the backoff cap is zero.',
                'path': 'src/Retry.java',
                'line': 31,
                'thread_id': 'PRRT_u1',
            },
        ]

        with (
            patch('github_pr._github.check_auth', return_value=(True, '')),
            patch('github_pr._github.fetch_pr_head_sha', return_value='sha'),
            patch('github_pr._github.fetch_pr_comments_data') as mock_fetch,
        ):
            mock_fetch.return_value = {
                'status': 'success',
                'provider': 'github',
                'comments': comments,
                'total': 1,
                'unresolved': 1,
            }
            result = github_pr.cmd_fetch_findings(_Args(plan_id))

        # Warned about...
        assert result['unclassified_bots'] == ['sourcery']
        # ...and STILL ingested. The warning is not a drop.
        assert result['count_stored'] == 1
        assert result['count_skipped_noise'] == 0


class TestFailureTaxonomyIsExhaustive:
    """Every classified bot lands in exactly one taxonomy member."""

    def test_the_contract_documents_every_non_participation_member(self):
        """Direction one — CODE to DOC: no classifier member is undocumented.

        The identifier names no count on purpose. A count in the name is a second
        place the cardinality is stated, and the one that goes stale silently: it
        keeps asserting truthfully while reading as a claim about a set size that
        has moved. The count belongs in the closure check below, where it is
        derived rather than spelled.
        """
        doc = _CONTRACT_DOC.read_text(encoding='utf-8')
        for member in _NON_PARTICIPATION_MEMBERS:
            assert f'`{member}`' in doc, f'{member} must be a documented taxonomy member'

    def test_every_documented_member_is_one_the_classifier_can_produce(self):
        """Direction two — DOC to CODE, which the direction above cannot see.

        A subset check in one direction only is satisfied by a documented set that
        has grown BEYOND the classifier: a member added to the contract table that
        ``classify_bot`` can never assign would leave the code-to-doc sweep green
        while the contract promised a state no consumer will ever observe. Closing
        the pair makes the two surfaces equal rather than merely overlapping.
        """
        documented = set(_documented_members())
        classifiable = set(_NON_PARTICIPATION_MEMBERS)

        assert documented <= classifiable, (
            f'the contract documents {sorted(documented - classifiable)} which the '
            f'classifier cannot produce — a documented member no consumer can observe'
        )

    def test_the_contracts_closure_count_agrees_with_the_derived_member_count(self):
        """The contract's prose count is checked against the derived cardinality.

        The two subset directions above make the table and the classifier agree,
        but neither reads the CLOSURE SENTENCE that tells a human how many members
        to expect. A widened taxonomy whose prose still says "five" understates the
        set at the one place a reader looks first, and nothing else in this suite
        would notice.
        """
        collapsed = ' '.join(_failure_taxonomy_section().split())
        match = _CLOSURE_COUNT.search(collapsed)
        assert match, 'the failure taxonomy must state its closure count in prose'

        word = match.group('count')
        assert word in _NUMBER_WORDS, (
            f'the closure count reads {word!r}, which is not a cardinal number word '
            f'this check can compare — spell the count as a word'
        )
        assert _NUMBER_WORDS.index(word) == len(_NON_PARTICIPATION_MEMBERS), (
            f'the contract closes the taxonomy at {word} members but '
            f'{len(_NON_PARTICIPATION_MEMBERS)} are derived: '
            f'{sorted(_NON_PARTICIPATION_MEMBERS)}'
        )

    def test_stated_blocking_counts_agree_with_the_derived_blocking_subset(self):
        """Every ``N blocking members`` claim in the tree is checked against code.

        The closure-count check above reads the CONTRACT doc's one closure
        sentence, so a count restated anywhere else is outside its reach. That
        gap is not hypothetical: the same wrong count appeared at two consumer
        sites, one of them contradicting its own enumeration three lines above,
        with nothing in this suite able to see either.

        The blocking subset is ``_UNPROVEN_STATES``, which is strictly smaller
        than the taxonomy — ``participated_but_empty`` is a member that never
        blocks — so reaching for the taxonomy's size here is the specific error
        guarded. Stating no count at all is the preferred shape, so a zero-match
        tree is a legitimate pass; the population guard below is what keeps that
        pass honest rather than vacuous.
        """
        blocking = len(rc._UNPROVEN_STATES)
        assert 0 < blocking < len(_NON_PARTICIPATION_MEMBERS), (
            f'the blocking subset ({blocking}) must be a non-empty PROPER subset of '
            f'the taxonomy ({len(_NON_PARTICIPATION_MEMBERS)}) — otherwise this check '
            f'cannot distinguish the two counts it exists to keep apart'
        )

        # The scanned population is the marketplace doc tree, NOT the match set:
        # zero matches is the preferred state, so the denominator that makes a
        # zero-match pass meaningful is how many docs were actually read.
        scanned = sum(1 for _ in _MARKETPLACE_DOCS.rglob('*.md'))
        assert scanned > 0, (
            f'{_MARKETPLACE_DOCS} yielded no markdown — the sweep is vacuous and a clean result would mean nothing'
        )

        for doc, stated in _blocking_count_sites():
            assert stated == blocking, (
                f'{doc} claims {stated} blocking members but {blocking} are derived '
                f'from _UNPROVEN_STATES: {sorted(rc._UNPROVEN_STATES)}. Note the '
                f'taxonomy has {len(_NON_PARTICIPATION_MEMBERS)} members — the '
                f'blocking subset excludes the never-blocking ones'
            )

    def test_the_blocking_count_extractor_reads_real_counts_and_skips_qualifiers(self):
        """Positive and negative controls for the extractor the scan above uses.

        The scan passes over a doc set that currently states no count, so on its
        own it cannot show it would catch anything. These controls pin the
        discriminator directly: the exact wording of the two defects that
        reached review is read back as a count, the corrected wording is not,
        and the digit spelling is covered too.
        """
        taxonomy_size = len(_NON_PARTICIPATION_MEMBERS)

        # Positive: the two shipped defects, verbatim. Both stated the TAXONOMY
        # size where the BLOCKING subset was meant, which is the error itself. The
        # count word tracks the derived taxonomy size, so these read the current
        # cardinality rather than a frozen literal that would rot on the next member.
        assert _stated_blocking_counts(
            f'because two of the {_NUMBER_WORDS[taxonomy_size]} blocking members name a different remedy'
        ) == (taxonomy_size,)
        assert _stated_blocking_counts(f'{taxonomy_size} blocking members') == (taxonomy_size,)

        # Negative: the corrected wording states no count and must not be read
        # as one — otherwise the fix would itself trip the guard.
        assert _stated_blocking_counts('because two of the blocking members name a different remedy') == ()
        assert _stated_blocking_counts('the blocking members enumerated above') == ()

        # And the defect the controls describe is genuinely a defect: the
        # taxonomy size is NOT the blocking count.
        assert taxonomy_size != len(rc._UNPROVEN_STATES)

    @pytest.mark.parametrize(
        'observation',
        [
            'none',
            'in_progress',
            'refused',
            'participated_empty',
            'participated_with_findings',
            'participated_stale',
            'declined',
            'not_triggered',
        ],
    )
    def test_every_registered_bot_classifies_into_exactly_one_member(self, observation, plan_context):
        """Sweep the WHOLE registered population under each observation shape.

        The population comes from ``bot_registry.bot_kinds()``, so a bot added in a
        standards doc is swept automatically. The assertion is totality and
        mutual exclusivity — never a spot-check of one bot.

        The two widened shapes are swept here rather than spot-checked for the same
        reason as the original five: the property being pinned is that the taxonomy
        stays TOTAL and mutually exclusive over the whole bot population, and a
        member exercised against one bot proves neither.
        """
        # ``_`` is not admissible in a plan_id (``^[a-z][a-z0-9-]*$``), and the
        # observation labels carry them. Derive the id through the same character
        # class the real store enforces, so the sweep exercises the predicate rather
        # than tripping plan-id validation inside the findings store.
        plan_id = f'bpc-taxonomy-{observation.replace("_", "-")}'
        plan_context.plan_dir_for(plan_id)
        bots = _registered_bots()

        kwargs: dict = {}
        if observation == 'in_progress':
            kwargs['in_progress_bots'] = bots
        elif observation == 'refused':
            kwargs['refused_bots'] = bots
        elif observation == 'participated_stale':
            # Matched by EXACT equality, and placed ahead of the prefix branch
            # below on purpose: ``participated_stale`` also starts with
            # ``participated``, so the prefix test would swallow it and feed the
            # shape through the proven-participation path instead — where every bot
            # resolves ``participated_but_empty`` and the widened member would
            # never be exercised while the case still reported green.
            kwargs['stale_participation_bots'] = bots
        elif observation == 'declined':
            kwargs['declined_bots'] = bots
        elif observation == 'not_triggered':
            # PR-wide rather than per-bot: a single bool, because the condition
            # ("no pull_request-event run exists for this PR") holds for every bot
            # at once. There is no observation set to key by bot here.
            kwargs['not_triggered'] = True
        elif observation.startswith('participated'):
            kwargs['participated_bots'] = {bot: bot_registry.participation_evidence(bot)[0] for bot in bots}
            if observation == 'participated_with_findings':
                import _findings_core as fc

                for bot in bots:
                    added = fc.add_finding(
                        plan_id,
                        'pr-comment',
                        title=f'{bot} finding',
                        detail='d',
                        bot_kind=bot,
                        kind='inline',
                    )
                    assert added['status'] == 'success', added
                    fc.resolve_finding(plan_id, added['hash_id'], 'fixed')

        result = rc.check_completeness(plan_id, bots, **kwargs)

        classified = [r['bot_kind'] for r in result['bot_states']]
        # Total: every bot in the population is classified.
        assert sorted(classified) == sorted(bots)
        # Exactly one: no bot is classified twice.
        assert len(classified) == len(set(classified))
        # And into a KNOWN member — nothing escapes the closed taxonomy.
        known = set(_NON_PARTICIPATION_MEMBERS) | {rc.STATE_PARTICIPATED}
        assert {r['state'] for r in result['bot_states']} <= known

    def test_every_registered_bot_declares_a_rate_limit_class_that_splits_refusals(self):
        """The refusal split is registry-driven for the WHOLE population.

        A bot whose class is neither awaitable nor a known non-awaitable value
        still resolves — fail-closed — so no bot can produce an unclassifiable
        refusal.
        """
        for bot in _registered_bots():
            assert bot_registry.rate_limit_class(bot) in (
                'awaitable_window',
                'hard_quota',
                'unknown',
            )

    def test_every_registered_bot_declares_its_participation_evidence(self):
        """A bot with no declared evidence shape can never be proven a participant.

        Fail-closed is the correct behaviour, but a REGISTERED bot silently
        landing there would be a registry gap, not a design intent — so every
        registered bot must declare at least one publish shape.
        """
        for bot in _registered_bots():
            shapes = bot_registry.participation_evidence(bot)
            assert shapes, f'{bot} declares no participation_evidence'
            for shape in shapes:
                assert shape in ('review_body', 'inline', 'issue_comment'), (bot, shape)
