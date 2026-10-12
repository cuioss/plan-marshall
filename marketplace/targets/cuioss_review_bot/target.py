# SPDX-License-Identifier: FSL-1.1-ALv2
"""CuiossReviewBotTarget — per-domain reviewer instruction-pack export target.

The ``cuioss-review-bot`` target emits the instruction packs the organisation's
reviewer (PR-Agent, running under the cuioss-review-bot identity) reads from the
settings repository ``cuioss/cuioss-review-bot``.

Reads the same source of truth as every other target (``marketplace/bundles/``)
and emits a REVIEWER ARTIFACT SET rather than an assistant bundle tree, written
flat under ``{output_dir}/packs/``. ``emits_bundle_tree`` is therefore ``False``,
so the CLI skips its generic bundle-tree post-emit steps (version stamping and
the dist-manifest) for this target.

The set is TWO derivations through one machinery:

* **The security set** — ``spine.md`` plus one ``{domain}.md`` per domain derived
  from the ``*-security`` / ``arch-gate-*`` / ``ext-triage-*`` standards skills.
* **The code-review set** — ``code-review-spine.md`` plus one
  ``code-review-{domain}.md`` per domain key the bundles declare through
  ``get_skill_domains()``. A domain's rules are the ``## Review Rules`` bullets of
  the default skills its ``core``, ``implementation``, ``module_testing`` and
  ``quality`` profiles name, restricted to skills of the declaring bundle; the
  spine carries ``ref-code-quality``'s ``## Review Categories`` and
  ``## Review Rules``. ``*-security`` skills and ``persona-security-expert`` are
  excluded by construction, so no security rule reaches a code-review artifact.

The code-review artifacts carry a name prefix rather than living in a
sub-directory because the publish workflow copies ``packs/*.md`` flat.

Three properties of the emission are load-bearing, for both sets alike:

* **The domain set is DERIVED, never hand-transcribed.** ``discover_domains``
  scans ``marketplace_dir`` for the per-domain standards skills — ``*-security``,
  ``arch-gate-*`` and ``ext-triage-*`` — so a bundle added to the marketplace
  appears in the derived set with no edit to this module.
* **The artifact set is ORTHOGONAL; a repository composes by SELECTING.**
  Composition is not an act of this module. A domain artifact carries that
  domain's part alone, and the cross-cutting charter appears exactly once —
  in the spine artifact. A repository that is several languages at once names
  several published artifacts instead of carrying one file that folds them
  together, so a charter change is published once rather than regenerated into
  every consumer.
* **A run EMITS the whole set, and the set stays equal to the derivation.** One
  artifact per derived domain plus the spine, under ``{output_dir}/packs/``.
  ``CuiossReviewBotTarget.generate`` accepts ``bundles`` for the base signature and
  ignores it, and ``_prune_stale_artifacts`` removes a generated artifact this
  run did not write, so a domain that stops deriving does not survive in the
  output. The spine is emitted unconditionally and is not selectable: a spine a
  consumer could omit is a charter a consumer could drop.

The four charter clauses are carried VERBATIM into each set's spine artifact, and
appear in no domain artifact of either set.

**The category ceiling is a two-part BUDGET, not a grouping.** The ceiling is an
observed organisation rule quoted in the ``cuioss/cuioss-review-bot`` settings
repository's documentation — past roughly ten entries the answer is a second
focused pass, not an eleventh bullet — so it is not this module's number to raise. The spine reserves one slot: it carries at
most :data:`MAX_CATEGORY_BULLETS` minus one category bullets, and each domain
artifact contributes exactly one. A single-domain assembly therefore lands
exactly at the ceiling. Grouping the domain bullets of a multi-domain assembly
back into one is the CONSUMER's obligation at assembly time; no assembled pack
exists in this repository, so that half of the budget is not provable here.
Rules are NOT categories and are deliberately not governed by that ceiling —
each domain artifact's rule list is capped at :data:`MAX_DOMAIN_RULES`.

The derivation rules live as module-level constants here rather than as a
sibling JSON config: a new ``marketplace/targets/**/*.json`` path is claimed by
no build extension and by no owner-less classifier rule, so it would resolve to
the ``unknown`` bucket. The existing ``opencode/*.json`` configs predate that
classifier and are not a precedent a new file may follow.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from marketplace.targets.base import TargetBase

# ---------------------------------------------------------------------------
# Derivation rules — how a domain is recognized in the source marketplace
# ---------------------------------------------------------------------------

#: Bundle holding the cross-cutting security spine every pack carries.
SPINE_BUNDLE = 'plan-marshall'
#: Skill inside :data:`SPINE_BUNDLE` whose ``standards/`` name the cross-cutting foundations.
SPINE_SKILL = 'persona-security-expert'

_SECURITY_SUFFIX = '-security'
_ARCH_GATE_PREFIX = 'arch-gate-'
_TRIAGE_PREFIX = 'ext-triage-'

KIND_SECURITY = 'security'
KIND_ARCH_GATE = 'arch-gate'
KIND_TRIAGE = 'ext-triage'

#: Deterministic kind ordering — governs both the domain-name preference and the
#: order contributed rules are harvested in.
_KIND_ORDER = (KIND_SECURITY, KIND_ARCH_GATE, KIND_TRIAGE)

#: Reviewer-facing label per contributing skill kind, used in the derived domain
#: category bullet. Keyed by KIND, never by domain, so a newly-discovered domain
#: gets a real bullet with no edit to this module.
_KIND_LABELS = {
    KIND_SECURITY: 'security',
    KIND_ARCH_GATE: 'architectural-boundary',
    KIND_TRIAGE: 'defect-triage',
}

#: Enforcement-block sub-headings whose bullets are harvested as domain rules.
_HARVESTED_ENFORCEMENT_HEADINGS = ('**Prohibited actions:**', '**Constraints:**')

#: Kinds whose enforcement block is harvested as DOMAIN RULES. All three kinds
#: participate in domain DISCOVERY, but only the security skill's enforcement
#: block states rules about the domain's CODE; ``arch-gate-*`` and
#: ``ext-triage-*`` state rules about how their own skill is operated, which is
#: noise in a reviewer's instruction pack.
_RULE_SOURCE_KINDS = (KIND_SECURITY,)

#: Withholding language never reaches a pack. Measured cause of five consecutive
#: empty reviews: these phrases instruct the reviewer to suppress a finding it
#: could otherwise substantiate. A harvested rule containing any of them is
#: DROPPED rather than rewritten — the source rule is addressed at an author, and
#: it reads as a suppression instruction once it lands in a reviewer prompt.
#: Matched case-insensitively.
_WITHHOLDING_PHRASES = (
    'do not duplicate',
    'avoid duplicating',
    'prefer one well-evidenced',
    'only when you can name the concrete input',
)

# ---------------------------------------------------------------------------
# Derivation rules — the code-review set
# ---------------------------------------------------------------------------

#: Where a bundle declares its skill domains. The file is READ as source, never
#: imported: executing it would run bundle code inside the generator and pull in
#: the extension runtime the publish workflow does not install.
_EXTENSION_RELPATH = Path('skills') / 'plan-marshall-plugin' / 'extension.py'

#: The class and method whose return value is the domain declaration.
_EXTENSION_CLASS = 'Extension'
_DOMAINS_METHOD = 'get_skill_domains'

#: The profiles whose DEFAULT skills feed a domain's code-review rules, in harvest
#: order. ``core`` is included because several domains state their own standards
#: only there; ``security`` is absent because the security set owns it.
_CODE_REVIEW_PROFILES = ('core', 'implementation', 'module_testing', 'quality')

#: Skill inside :data:`SPINE_BUNDLE` whose review blocks are the code-review spine.
CODE_REVIEW_SPINE_SKILL = 'ref-code-quality'

#: The harvestable block headings of the code-review rulebook.
_REVIEW_CATEGORIES_HEADING = '## Review Categories'
_REVIEW_RULES_HEADING = '## Review Rules'

#: Name prefix every code-review artifact carries. A prefix, not a sub-directory:
#: the publish workflow copies ``packs/*.md`` flat.
_CODE_REVIEW_PREFIX = 'code-review-'

# ---------------------------------------------------------------------------
# Composition limits and emission layout
# ---------------------------------------------------------------------------

#: Hard ceiling on the pack's category bullet list. ``cuioss/cuioss-review-bot``
#: § "Recall beats precision": past roughly ten entries the answer is a second
#: focused pass, not an eleventh bullet.
MAX_CATEGORY_BULLETS = 10

#: Ceiling on the harvested per-domain rule list, applied PER DOMAIN. Rules are
#: not review categories, so they are not governed by
#: :data:`MAX_CATEGORY_BULLETS`; the separate cap keeps an artifact from growing
#: without bound as standards are added. Each domain artifact carries up to this
#: many rules, and a repository selecting several domains reads several
#: artifacts — dropping a second domain's rules to hit a single total is exactly
#: the silent under-review this target exists to fix. The same holds within one
#: domain: a cap the real marketplace exceeds drops that domain's trailing rules
#: with no error, so the value sits at or above every real domain's harvested
#: count in both sets, and ``test_code_review_packs.py`` § ``TestRuleBudget`` fails
#: when a domain outgrows it.
MAX_DOMAIN_RULES = 15

#: Directory, under the target's output root, holding the emitted artifact set.
_PACKS_DIRNAME = 'packs'

#: Stem of the one artifact carrying the cross-cutting charter. It is emitted
#: unconditionally and is not a derived domain — a consumer applies it alongside
#: whichever domain artifacts it selects, and cannot deselect it.
_SPINE_ARTIFACT_NAME = 'spine'

#: The source repository every emitted artifact names in its header, so a reader
#: who finds an artifact in the published set can reach the derivation.
_SOURCE_REPOSITORY = 'cuioss/plan-marshall'

#: First line of every generated artifact's header. Both the renderer and the
#: stale-artifact prune read it from HERE rather than each spelling it out: the
#: prune may only reclaim files this generator produced, so the marker it
#: matches has to be the very one the renderer writes. Two copies of the string
#: could drift apart, and the drift would show up as the prune silently
#: reclaiming nothing.
_GENERATED_HEADER_MARKER = '<!-- GENERATED ARTIFACT — do not edit by hand.'

#: The argument-free command that reproduces the whole artifact set. Selection is
#: no longer an argument, so there is exactly one regenerate line for every
#: artifact — following it can no longer narrow what a repository gets. It is the
#: ``./pw`` wrapper form because ``uv`` lives only in the project-local
#: ``.pyprojectx/`` tree and is not on ``PATH``, so a bare ``uv run …`` exits 127
#: outside it — and this line is stamped into artifacts published to another
#: repository, where the reader has no such tree at all.
_REGENERATE_COMMAND = './pw generate --target cuioss-review-bot --output target/cuioss-review-bot'

# ---------------------------------------------------------------------------
# Charter text carried verbatim into both spine artifacts
# ---------------------------------------------------------------------------
#
# The same four clauses are stated in the code-review rubric
# (phase-6-finalize/standards/review-rubric.md § 9), so the in-run code review and
# the bot work to one charter; a test pins the two byte-identical.

#: The substantiation bar. Carried byte-identical from the org charter; the
#: generated spine artifact contains it. Kept on ONE line so the clause is a
#: contiguous substring and a guard can assert it verbatim.
SUBSTANTIATION_CLAUSE = (
    'For each finding, name the input or state that triggers it and what goes wrong. Overlap with '
    'other reviewers is acceptable — report the issue regardless of whether another tool might also '
    'catch it. Do not withhold a substantiated finding because it seems minor or obvious.'
)

#: The anti-fabrication clause. Load-bearing and must not be dropped when the
#: spine is next tuned: pressure to report more is exactly the pressure that
#: produces invented mechanisms. Carried byte-identical from the org charter.
ANTI_FABRICATION_CLAUSE = (
    'An empty list remains the correct answer when the diff genuinely carries nothing substantiable, and '
    'you must never invent a finding, pad the list, or report an issue whose mechanism you have not '
    'traced in the code shown. But do not return an empty list because nothing reached a bar of severity '
    'or importance. There is no such bar.'
)

#: Treat stated intent as a claim to check rather than as established fact.
INTENT_CLAUSE = (
    'If the pull request description states what the change is intended to do, treat that as a claim '
    'to be checked, not as established fact. Report where the implementation diverges from the stated '
    'intent, and never treat agreement with it as evidence that the code is correct.'
)

#: Severity is not a reporting threshold.
SEVERITY_CLAUSE = (
    'Severity is not a reporting threshold. Report a finding you can substantiate even when it is '
    'narrow, cheap to fix, or confined to test code — the reader decides what to act on, and a finding '
    'declined as minor costs one line of triage. Do not weigh whether an issue is important enough to '
    'mention.'
)

#: The cross-cutting review categories carried by the SPINE artifact alone. The
#: spine renders at most :data:`MAX_CATEGORY_BULLETS` minus one of them, reserving
#: the last slot for the single bullet each domain artifact contributes.
SPINE_CATEGORIES = (
    'Concurrency and time-of-check/time-of-use races; non-atomic file or state mutation; operations '
    'that are unsafe to retry or to run twice.',
    'Resource lifecycle: handles, locks, temporary files and subprocesses that leak or are not '
    'released on the error path.',
    'Fail-open error handling where fail-closed is required; swallowed exceptions; a guard whose '
    'predicate cannot fire; validation that admits the empty or degenerate input.',
    'Correctness bugs whose impact is data loss, state corruption, or a silently wrong result.',
    'Injection, deserialization, path traversal, SSRF and unsafe reflection.',
    'Authentication, authorization and trust-boundary errors; privilege escalation.',
    'Secret and credential handling, including values reaching logs or error messages.',
    'Dependency and supply-chain risk introduced by the change.',
    'Missing negative or adversarial test coverage for any of the above.',
)


# ---------------------------------------------------------------------------
# Derived domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainContribution:
    """One derived review domain and the source skills that compose its pack.

    Attributes:
        domain: The derived domain identifier (e.g. ``java``, ``python``).
        bundles: Source bundles that contributed to this domain, sorted.
        kinds: Contributing skill kinds present, in :data:`_KIND_ORDER` order.
        rules: Code-level enforcement rules harvested from the contributing
            skills of :data:`_RULE_SOURCE_KINDS`, deduped, withholding language
            dropped, and capped at :data:`MAX_DOMAIN_RULES`.
    """

    domain: str
    bundles: tuple[str, ...]
    kinds: tuple[str, ...]
    rules: tuple[str, ...]


def _classify_skill(skill_name: str) -> tuple[str, str] | None:
    """Classify a skill directory name as a domain-standards contributor.

    Returns:
        A ``(kind, domain_token)`` pair, or ``None`` when the skill is not a
        per-domain standards skill.
    """
    if skill_name.startswith(_ARCH_GATE_PREFIX):
        token = skill_name[len(_ARCH_GATE_PREFIX) :]
        return (KIND_ARCH_GATE, token) if token else None
    if skill_name.startswith(_TRIAGE_PREFIX):
        token = skill_name[len(_TRIAGE_PREFIX) :]
        return (KIND_TRIAGE, token) if token else None
    if skill_name.endswith(_SECURITY_SUFFIX):
        token = skill_name[: -len(_SECURITY_SUFFIX)]
        return (KIND_SECURITY, token) if token else None
    return None


def _harvest_enforcement_rules(skill_md: Path) -> list[str]:
    """Harvest the ``## Enforcement`` prohibited-action and constraint bullets.

    Every marketplace skill carries an ``## Enforcement`` block whose
    ``**Prohibited actions:**`` and ``**Constraints:**`` bullets state this
    organisation's own rules in mechanism-naming form — exactly the shape a
    reviewer needs. A skill without such a block contributes nothing.
    """
    try:
        text = skill_md.read_text(encoding='utf-8')
    except OSError:
        return []

    rules: list[str] = []
    in_enforcement = False
    collecting = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if raw_line.startswith('## '):
            in_enforcement = line == '## Enforcement'
            collecting = False
            continue
        if not in_enforcement:
            continue
        if line.startswith('**') and line.endswith(':**'):
            collecting = line in _HARVESTED_ENFORCEMENT_HEADINGS
            continue
        if not collecting:
            continue
        if line.startswith('- '):
            rule = line[2:].strip()
            if rule and not _is_withholding(rule):
                rules.append(rule)
        elif line:
            collecting = False
    return rules


def _is_withholding(text: str) -> bool:
    """Whether ``text`` carries any phrase from the withholding deny-list."""
    lowered = text.lower()
    return any(phrase in lowered for phrase in _WITHHOLDING_PHRASES)


def discover_domains(marketplace_dir: Path) -> dict[str, DomainContribution]:
    """Derive the review-domain set by scanning the source marketplace.

    A bundle contributes a domain when it holds at least one per-domain
    standards skill (``*-security``, ``arch-gate-*`` or ``ext-triage-*``). The
    domain identifier is taken from the highest-precedence contributing kind
    (:data:`_KIND_ORDER`), so ``pm-dev-frontend``'s ``javascript-security`` names
    the domain that ``arch-gate-js`` and ``ext-triage-js`` also feed.

    The spine bundle is excluded: it carries the cross-cutting foundations, not
    a domain of its own.

    The derivation takes NO bundle allow-list, and that absence is the contract
    rather than an omission: this target is not bundle-scopable (see
    :meth:`CuiossReviewBotTarget.generate`), so there is no parameter by which a caller
    could narrow the set. Removing the knob is what makes the whole-set claim
    true by construction instead of by convention.

    Args:
        marketplace_dir: Path to ``marketplace/bundles/``.

    Returns:
        Derived domain identifier -> :class:`DomainContribution`, ordered by
        domain identifier.
    """
    # bundle -> kind -> (domain_token, skill_dir)
    per_bundle: dict[str, dict[str, tuple[str, Path]]] = {}

    for bundle_dir in sorted(p for p in marketplace_dir.glob('*') if p.is_dir()):
        bundle = bundle_dir.name
        if bundle == SPINE_BUNDLE:
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(p for p in skills_dir.glob('*') if p.is_dir()):
            classified = _classify_skill(skill_dir.name)
            if classified is None:
                continue
            kind, token = classified
            # First match per kind wins; the sorted walk makes that deterministic.
            per_bundle.setdefault(bundle, {}).setdefault(kind, (token, skill_dir))

    contributions: dict[str, tuple[set[str], set[str], list[str]]] = {}
    for bundle in sorted(per_bundle):
        by_kind = per_bundle[bundle]
        present = [kind for kind in _KIND_ORDER if kind in by_kind]
        if not present:
            continue
        domain = by_kind[present[0]][0]
        seen_bundles, seen_kinds, rules = contributions.setdefault(domain, (set(), set(), []))
        seen_bundles.add(bundle)
        for kind in present:
            seen_kinds.add(kind)
            if kind in _RULE_SOURCE_KINDS:
                rules.extend(_harvest_enforcement_rules(by_kind[kind][1] / 'SKILL.md'))

    derived: dict[str, DomainContribution] = {}
    for domain in sorted(contributions):
        seen_bundles, seen_kinds, rules = contributions[domain]
        deduped: list[str] = []
        for rule in rules:
            if rule not in deduped:
                deduped.append(rule)
        derived[domain] = DomainContribution(
            domain=domain,
            bundles=tuple(sorted(seen_bundles)),
            kinds=tuple(kind for kind in _KIND_ORDER if kind in seen_kinds),
            rules=tuple(deduped[:MAX_DOMAIN_RULES]),
        )
    return derived


def discover_spine_topics(marketplace_dir: Path) -> tuple[str, ...]:
    """Derive the cross-cutting foundation topics from the spine skill's standards.

    The topics are the ``standards/*.md`` stems of
    ``{SPINE_BUNDLE}/skills/{SPINE_SKILL}``, so adding a cross-cutting standard
    widens every pack with no edit to this module. Returns an empty tuple when
    the spine skill is absent (a partial/fixture marketplace).
    """
    standards_dir = marketplace_dir / SPINE_BUNDLE / 'skills' / SPINE_SKILL / 'standards'
    if not standards_dir.is_dir():
        return ()
    return tuple(sorted(path.stem.replace('-', ' ') for path in standards_dir.glob('*.md')))


# ---------------------------------------------------------------------------
# Pack composition — two DISJOINT renderers
# ---------------------------------------------------------------------------


def _join_terms(terms: Sequence[str]) -> str:
    """Join terms as English prose: ``a``, ``a and b``, ``a, b and c``."""
    if not terms:
        return ''
    if len(terms) == 1:
        return terms[0]
    return f'{", ".join(terms[:-1])} and {terms[-1]}'


def _domain_category_bullet(contribution: DomainContribution) -> str:
    """Render the ONE derived category bullet a domain artifact contributes.

    Exactly one bullet per domain artifact — that is the domain half of the
    category budget. The spine reserves the matching slot by rendering at most
    :data:`MAX_CATEGORY_BULLETS` minus one of its own bullets, so a single-domain
    assembly lands exactly at a ceiling this module does not own (see the module
    docstring).

    The bullet states only what the artifact actually carries. A domain whose
    rules were harvested points at the "Domain rules" block; a domain that
    contributed no rules is instead named with the standards that govern it, so
    the reviewer is never promised a list that is not there.
    """
    if contribution.rules:
        clause = (
            f'the rules this organisation enforces for {contribution.domain} code are listed under "Domain rules" below'
        )
    else:
        labels = _join_terms([_KIND_LABELS[kind] for kind in contribution.kinds])
        clause = (
            f'this organisation governs {contribution.domain} through its {labels} standards — '
            f'apply every category above to {contribution.domain} sources and idioms, not only to '
            f"the repository's primary language"
        )
    return f'Defects specific to {contribution.domain}: {clause}.'


def compose_spine(spine_topics: tuple[str, ...]) -> str:
    """Compose the cross-cutting spine body — the charter, rendered exactly once.

    This is the half of the review instruction that does not vary by domain: the
    category preamble, the :data:`SPINE_CATEGORIES` bullets sliced at
    :data:`MAX_CATEGORY_BULLETS` minus one, the cross-cutting foundations line,
    and the four charter clauses verbatim. None of it appears in any domain
    artifact.

    The body is emitted unconditionally. Only the foundations line depends on
    ``spine_topics``, so a fixture marketplace carrying no spine skill still
    yields a spine artifact — with that one line omitted, and the clauses and
    categories intact.

    Args:
        spine_topics: Cross-cutting foundation topics, from
            :func:`discover_spine_topics`. Empty omits the foundations line.
    """
    lines: list[str] = ['Report every issue you can substantiate, in these categories:']
    lines.extend(f'- {category}' for category in SPINE_CATEGORIES[: MAX_CATEGORY_BULLETS - 1])

    if spine_topics:
        lines.append('')
        lines.append('Cross-cutting foundations to apply in every review: ' + ', '.join(spine_topics) + '.')

    for clause in (SUBSTANTIATION_CLAUSE, INTENT_CLAUSE, SEVERITY_CLAUSE, ANTI_FABRICATION_CLAUSE):
        lines.append('')
        lines.append(clause)

    return '\n'.join(lines) + '\n'


def compose_domain_pack(contribution: DomainContribution) -> str:
    """Compose ONE domain's body — the domain part alone, spine-free.

    The body is the scope line, exactly one category bullet, and the harvested
    "Domain rules" block when the domain is rule-bearing. No spine category, no
    foundations line and no charter clause appears here: that text lives in the
    spine artifact, once, and the two bodies are disjoint by construction rather
    than by subtraction.

    Args:
        contribution: The derived domain this artifact carries.
    """
    lines: list[str] = [
        f'Prioritise security and correctness over style. This pack is scoped to the {contribution.domain} domain.',
        '',
        f'- {_domain_category_bullet(contribution)}',
    ]

    if contribution.rules:
        lines.append('')
        lines.append(
            f"Domain rules — this organisation's own standards for {contribution.domain} code. A diff "
            f'that breaks one of these is a finding, and the rule already names the mechanism:'
        )
        lines.extend(f'- {rule}' for rule in contribution.rules)

    return '\n'.join(lines) + '\n'


def render_pack_artifact(name: str, body: str) -> str:
    """Render one published artifact: a do-not-edit header followed by ``body``.

    The header names the source repository, so a reader who found the artifact in
    the published set can reach the derivation that produced it, and the
    argument-free regenerate command, which reproduces the WHOLE set — selection
    is no longer an argument, so following the line can no longer narrow what a
    repository gets.

    A domain artifact's header additionally records where the charter lives and
    asks the reader to apply the spine artifact alongside it. That is stated as a
    REQUIREMENT ON THE READER, not as a guarantee: this generator writes separate
    files and nothing here makes the pairing hold, so a header claiming the spine
    "is not optional" would assert an enforcement no code in this repository
    performs. What is checkable is the fact behind the request — a domain artifact
    carries no charter text, so one read on its own has neither the substantiation
    nor the anti-fabrication bar.

    Args:
        name: The artifact stem — a derived domain, or the spine's own name.
        body: The composed body, from :func:`compose_domain_pack` or
            :func:`compose_spine`.
    """
    if name == _SPINE_ARTIFACT_NAME:
        role = (
            'This is the spine artifact. It carries the cross-cutting review charter exactly once.\n'
            'The generator emits it on every run, and it is meant to apply to every review whichever\n'
            'domain artifacts a repository selects.'
        )
    else:
        role = (
            f'This artifact carries the {name} domain part alone. The review charter lives in the\n'
            f'spine artifact ({_SPINE_ARTIFACT_NAME}.md) and appears in no domain artifact, so this file on its\n'
            'own carries none of it. Apply the spine artifact alongside this one.'
        )
    return _render_artifact(role, body)


def render_code_review_artifact(name: str, body: str) -> str:
    """Render one code-review artifact: the same do-not-edit header, a code-review role.

    The role text mirrors :func:`render_pack_artifact`'s for the security set, and
    carries the same caution: pairing a domain artifact with the code-review spine
    is a request to the reader, not a guarantee this generator enforces.

    Args:
        name: :data:`_SPINE_ARTIFACT_NAME` for the code-review spine, otherwise a
            derived code-review domain. The file stem is this name behind
            :data:`_CODE_REVIEW_PREFIX`.
        body: The composed body, from :func:`compose_code_review_domain_pack` or
            :func:`compose_code_review_spine`.
    """
    spine_file = f'{_CODE_REVIEW_PREFIX}{_SPINE_ARTIFACT_NAME}.md'
    if name == _SPINE_ARTIFACT_NAME:
        role = (
            'This is the code-review spine artifact. It carries the code-review charter, categories\n'
            'and cross-cutting rules exactly once. The generator emits it on every run, and it is meant\n'
            'to apply to every code review whichever code-review domain artifacts a repository selects.'
        )
    else:
        role = (
            f'This artifact carries the {name} code-review rules alone. The code-review charter lives in\n'
            f'the code-review spine artifact ({spine_file}) and appears in no code-review domain\n'
            'artifact, so this file on its own carries none of it. Apply the code-review spine artifact\n'
            'alongside this one.'
        )
    return _render_artifact(role, body)


def _render_artifact(role: str, body: str) -> str:
    """The shared header-plus-body rendering both artifact sets go through."""
    return (
        f'{_GENERATED_HEADER_MARKER}\n'
        f'Derived from the {_SOURCE_REPOSITORY} marketplace (marketplace/bundles/**).\n'
        f'Regenerate with:\n'
        f'  {_REGENERATE_COMMAND}\n'
        f'{role}\n'
        f'-->\n'
        f'\n'
        f'{body}'
    )


def compose_packs(marketplace_dir: Path) -> dict[str, str]:
    """Compose the spine-free body for every derived domain.

    The population is derived, not hand-written: a consumer enumerating packs
    (e.g. the artifact-set drift guard) asks this function rather than iterating
    a literal list, so a new domain is guarded the moment it is derivable. The
    spine is deliberately not a member — it is not a domain, and it is emitted
    separately by :func:`compose_spine`.

    Like :func:`discover_domains`, this takes no bundle allow-list: every caller
    gets the whole derived set, so no call site can publish a narrowed one.
    """
    return {
        domain: compose_domain_pack(contribution) for domain, contribution in discover_domains(marketplace_dir).items()
    }


# ---------------------------------------------------------------------------
# Code-review derivation — the second artifact set
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodeReviewDomain:
    """One derived code-review domain and the rule sources that compose its pack.

    Attributes:
        domain: The domain key a bundle declares through ``get_skill_domains()``.
        bundles: Bundles declaring this key, sorted.
        skills: The ``bundle:skill`` notations the rules were harvested from, in
            harvest order.
        rules: The ``## Review Rules`` bullets of those skills, withholding
            language dropped, deduped, and capped at :data:`MAX_DOMAIN_RULES`.
    """

    domain: str
    bundles: tuple[str, ...]
    skills: tuple[str, ...]
    rules: tuple[str, ...]


def _is_security_skill(skill: str) -> bool:
    """Whether ``skill`` belongs to the security set and is excluded from code review."""
    return skill.endswith(_SECURITY_SUFFIX) or skill == SPINE_SKILL


def _evaluate_declaration(
    node: ast.expr, methods: dict[str, ast.FunctionDef], source: Path, resolving: frozenset[str]
) -> object:
    """Evaluate one declaration expression without executing the extension.

    A literal evaluates as itself. Two non-literal shapes the bundles use are
    resolved structurally: a list whose elements need evaluating, and a zero-
    argument ``self._helper()`` call naming a sibling method that returns a
    literal. Anything else is refused — a declaration this reader cannot evaluate
    would otherwise vanish from the derived set without a trace.

    Raises:
        ValueError: The expression is not a literal and not one of the two shapes.
    """
    if isinstance(node, ast.List):
        return [_evaluate_declaration(element, methods, source, resolving) for element in node.elts]
    if (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'self'
    ):
        return _method_return_value(node.func.attr, methods, source, resolving)
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise ValueError(
            f'{source}: {_DOMAINS_METHOD} returns a value this generator cannot read statically '
            f'(line {node.lineno}); declare the domains as a literal'
        ) from exc


def _method_return_value(
    name: str, methods: dict[str, ast.FunctionDef], source: Path, resolving: frozenset[str]
) -> object:
    """Evaluate the single ``return`` of method ``name`` on the extension class."""
    if name in resolving:
        raise ValueError(f'{source}: {name} calls itself while declaring its domains')
    method = methods.get(name)
    if method is None:
        raise ValueError(f'{source}: {_EXTENSION_CLASS}.{name} is called but not defined')
    returns = [statement for statement in method.body if isinstance(statement, ast.Return)]
    if len(returns) != 1 or returns[0].value is None:
        raise ValueError(f'{source}: {_EXTENSION_CLASS}.{name} must end in exactly one return of its value')
    return _evaluate_declaration(returns[0].value, methods, source, resolving | {name})


def _read_declared_domains(extension_py: Path) -> list[dict]:
    """Read a bundle's ``get_skill_domains()`` declaration out of its source.

    Returns:
        The declared domain list; empty when the class defines no
        ``get_skill_domains`` (the inherited default declares no domain).

    Raises:
        ValueError: The file cannot be read or parsed, defines no extension class,
            or declares its domains in a shape that is not a list.
    """
    try:
        tree = ast.parse(extension_py.read_text(encoding='utf-8'), filename=str(extension_py))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f'cannot read the skill-domain declaration of {extension_py}: {exc}') from exc
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == _EXTENSION_CLASS]
    if len(classes) != 1:
        raise ValueError(f'{extension_py}: expected exactly one class {_EXTENSION_CLASS}, found {len(classes)}')
    methods = {node.name: node for node in classes[0].body if isinstance(node, ast.FunctionDef)}
    if _DOMAINS_METHOD not in methods:
        return []
    declared = _method_return_value(_DOMAINS_METHOD, methods, extension_py, frozenset())
    if not isinstance(declared, list) or not all(isinstance(item, dict) for item in declared):
        raise ValueError(f'{extension_py}: {_DOMAINS_METHOD} must return a list of domain mappings')
    return declared


def _domain_key(declaration: dict, source: Path) -> str:
    """The non-empty domain key of one declaration."""
    domain = declaration.get('domain')
    key = domain.get('key') if isinstance(domain, dict) else None
    if not isinstance(key, str) or not key:
        raise ValueError(f'{source}: a declared domain carries no domain.key')
    return key


def _default_skill_notations(declaration: dict, source: Path) -> list[str]:
    """The ``bundle:skill`` notations the code-review profiles name as defaults, in order.

    A profile entry is either the notation itself or a mapping carrying it under
    ``skill`` — the bundles use both forms.
    """
    profiles = declaration.get('profiles')
    if not isinstance(profiles, dict):
        return []
    notations: list[str] = []
    for profile in _CODE_REVIEW_PROFILES:
        spec = profiles.get(profile)
        defaults = spec.get('defaults') if isinstance(spec, dict) else None
        for entry in defaults or []:
            notation = entry.get('skill') if isinstance(entry, dict) else entry
            if not isinstance(notation, str) or notation.count(':') != 1:
                raise ValueError(f'{source}: profile {profile!r} names a default skill that is not bundle:skill')
            if notation not in notations:
                notations.append(notation)
    return notations


def _heading_level(heading_line: str) -> int:
    """The number of leading ``#`` characters of a Markdown heading line."""
    return len(heading_line) - len(heading_line.lstrip('#'))


def _harvest_section_bullets(skill_md: Path, heading: str) -> list[str]:
    """The top-level bullets of one ``##`` section of ``skill_md``.

    A bullet's indented continuation lines join it, so a wrapped rule is one rule.
    Fenced code is skipped. A skill without the section contributes nothing. The
    section ends at the next heading of the same or a higher level; a deeper
    subheading inside it keeps the section open, so the bullets under it are
    harvested rather than silently dropped.

    Raises:
        ValueError: The file cannot be read — a rule source that could not be read
            must stop the run, never yield a thinner pack that looks complete.
    """
    try:
        text = skill_md.read_text(encoding='utf-8')
    except OSError as exc:
        raise ValueError(f'cannot read the review-rule source {skill_md}: {exc}') from exc

    heading_level = _heading_level(heading)
    bullets: list[str] = []
    in_section = False
    in_fence = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if raw_line.startswith('#'):
            if raw_line.rstrip() == heading:
                in_section = True
            elif _heading_level(raw_line) <= heading_level:
                in_section = False
            continue
        if not in_section:
            continue
        if raw_line.startswith('- '):
            bullets.append(line[2:].strip())
        elif bullets and line and raw_line[:1].isspace():
            bullets[-1] = f'{bullets[-1]} {line}'
    return [bullet for bullet in bullets if bullet and not _is_withholding(bullet)]


def discover_code_review_domains(marketplace_dir: Path) -> dict[str, CodeReviewDomain]:
    """Derive the code-review domain set from the bundles' domain declarations.

    Every domain key a bundle declares through ``get_skill_domains()`` is a
    code-review domain, except those the spine bundle declares: its domain feeds
    the code-review spine, not a pack. A domain's rules come from the default
    skills its :data:`_CODE_REVIEW_PROFILES` name, restricted to skills of the
    declaring bundle — a shared skill another bundle owns feeds the spine instead —
    with every security skill excluded by construction.

    Like :func:`discover_domains`, this takes no bundle allow-list.

    Args:
        marketplace_dir: Path to ``marketplace/bundles/``.

    Returns:
        Domain key -> :class:`CodeReviewDomain`, ordered by domain key.

    Raises:
        ValueError: A declaration or a rule source cannot be read.
    """
    # domain -> (declaring bundles, harvested skill notations)
    collected: dict[str, tuple[set[str], list[str]]] = {}
    for bundle_dir in sorted(p for p in marketplace_dir.glob('*') if p.is_dir()):
        bundle = bundle_dir.name
        extension_py = bundle_dir / _EXTENSION_RELPATH
        if bundle == SPINE_BUNDLE or not extension_py.is_file():
            continue
        for declaration in _read_declared_domains(extension_py):
            key = _domain_key(declaration, extension_py)
            bundles, skills = collected.setdefault(key, (set(), []))
            bundles.add(bundle)
            for notation in _default_skill_notations(declaration, extension_py):
                skill_bundle, skill = notation.split(':')
                if skill_bundle != bundle or _is_security_skill(skill) or notation in skills:
                    continue
                skills.append(notation)

    derived: dict[str, CodeReviewDomain] = {}
    for key in sorted(collected):
        bundles, skills = collected[key]
        rules: list[str] = []
        for notation in skills:
            skill_bundle, skill = notation.split(':')
            skill_md = marketplace_dir / skill_bundle / 'skills' / skill / 'SKILL.md'
            for rule in _harvest_section_bullets(skill_md, _REVIEW_RULES_HEADING):
                if rule not in rules:
                    rules.append(rule)
        derived[key] = CodeReviewDomain(
            domain=key,
            bundles=tuple(sorted(bundles)),
            skills=tuple(skills),
            rules=tuple(rules[:MAX_DOMAIN_RULES]),
        )
    return derived


def discover_code_review_spine(marketplace_dir: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Harvest the code-review spine's categories and rules from :data:`CODE_REVIEW_SPINE_SKILL`.

    Returns:
        ``(categories, rules)`` — both empty when the spine skill is absent (a
        partial/fixture marketplace).

    Raises:
        ValueError: The skill declares more categories than the spine's half of
            the category budget holds. Over the ceiling the remedy is a second
            focused pass, so the run stops rather than silently dropping one.
    """
    skill_md = marketplace_dir / SPINE_BUNDLE / 'skills' / CODE_REVIEW_SPINE_SKILL / 'SKILL.md'
    if not skill_md.is_file():
        return (), ()
    categories = _harvest_section_bullets(skill_md, _REVIEW_CATEGORIES_HEADING)
    if len(categories) > MAX_CATEGORY_BULLETS - 1:
        raise ValueError(
            f'{skill_md} declares {len(categories)} review categories; the code-review spine '
            f'holds at most {MAX_CATEGORY_BULLETS - 1} (one slot is reserved for the domain bullet)'
        )
    return tuple(categories), tuple(_harvest_section_bullets(skill_md, _REVIEW_RULES_HEADING))


def compose_code_review_spine(categories: Sequence[str], rules: Sequence[str]) -> str:
    """Compose the code-review spine body — its charter, rendered exactly once.

    The harvested categories, the harvested cross-cutting rules, and the four
    charter clauses verbatim. The clauses are unconditional, so a marketplace
    without the spine skill still yields a spine carrying the charter.
    """
    lines: list[str] = ['Report every issue you can substantiate, in these categories:']
    lines.extend(f'- {category}' for category in categories)
    if rules:
        lines.append('')
        lines.append(
            "Cross-cutting review rules — this organisation's own rules for every change, whatever its "
            'language. A diff that breaks one of these is a finding, and the rule already names the mechanism:'
        )
        lines.extend(f'- {rule}' for rule in rules)
    for clause in (SUBSTANTIATION_CLAUSE, INTENT_CLAUSE, SEVERITY_CLAUSE, ANTI_FABRICATION_CLAUSE):
        lines.append('')
        lines.append(clause)
    return '\n'.join(lines) + '\n'


def compose_code_review_domain_pack(domain: CodeReviewDomain) -> str:
    """Compose ONE code-review domain's body — the domain part alone, charter-free.

    The scope line, exactly one category bullet (the domain half of the category
    budget), and the harvested "Domain rules" block when the domain is
    rule-bearing.
    """
    name = domain.domain
    if domain.rules:
        bullet = (
            f'Defects specific to {name}: the code-review rules this organisation states for {name} code '
            f'are listed under "Domain rules" below.'
        )
    else:
        bullet = (
            f'Defects specific to {name}: this organisation states no {name} review rules — apply every '
            f'code-review spine category to {name} sources and idioms.'
        )
    lines: list[str] = [f'This pack is scoped to the {name} domain of a code review.', '', f'- {bullet}']
    if domain.rules:
        lines.append('')
        lines.append(
            f"Domain rules — this organisation's own code-review standards for {name} code. A diff that "
            f'breaks one of these is a finding, and the rule already names the mechanism:'
        )
        lines.extend(f'- {rule}' for rule in domain.rules)
    return '\n'.join(lines) + '\n'


def compose_code_review_packs(marketplace_dir: Path) -> dict[str, str]:
    """Compose the charter-free body for every derived code-review domain.

    The code-review spine is not a member — it is emitted separately by
    :func:`compose_code_review_spine`.
    """
    return {
        key: compose_code_review_domain_pack(domain)
        for key, domain in discover_code_review_domains(marketplace_dir).items()
    }


def _prune_stale_artifacts(packs_dir: Path, keep: set[Path]) -> list[Path]:
    """Delete generated artifacts in ``packs_dir`` that this run did not write.

    A domain that stops deriving — its standards skill removed or renamed — used
    to leave its artifact behind, so the published set carried MORE artifacts
    than the derived set while every remaining file still looked freshly
    generated. Nothing downstream could tell the difference: the publish
    workflow's count-before-delete guard sees a plausible count either way, and
    a consumer selecting the stale stem gets rules for a domain this repository
    no longer states any.

    Two properties are load-bearing:

    * **It runs AFTER the new set is written.** A compose that raises therefore
      leaves the previous set intact, where clearing the directory first would
      publish an empty set on any failure.
    * **It reclaims only what this generator produced.** A file is removed only
      when it carries :data:`_GENERATED_HEADER_MARKER`, so a hand-written note
      someone dropped into ``packs/`` survives. The prune's job is to keep the
      generated set equal to the derived set, not to own the directory.

    Args:
        packs_dir: The emission directory, already written.
        keep: Absolute paths this run wrote — every one is left alone.

    Returns:
        The paths removed, sorted.
    """
    pruned: list[Path] = []
    for path in sorted(packs_dir.glob('*.md')):
        if path in keep:
            continue
        if not path.read_text(encoding='utf-8').startswith(_GENERATED_HEADER_MARKER):
            continue
        path.unlink()
        pruned.append(path)
    return pruned


# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


class CuiossReviewBotTarget(TargetBase):
    """Build target emitting the per-domain reviewer artifact set plus the spine."""

    @property
    def name(self) -> str:
        return 'cuioss-review-bot'

    @property
    def config_dir(self) -> Path:
        """Directory holding this target's rules — the package directory itself.

        The derivation rules are module-level constants rather than sibling JSON
        files; see the module docstring for why.
        """
        return Path(__file__).resolve().parent

    @property
    def emits_bundle_tree(self) -> bool:
        """This target emits a reviewer artifact set, not a bundle tree."""
        return False

    def supports_agents(self) -> bool:
        return False

    def supports_commands(self) -> bool:
        return False

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path | None,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        """Emit the whole derived artifact set under ``{output_dir}/packs/``.

        ``bundles`` is accepted to satisfy the :class:`TargetBase` signature and
        is deliberately IGNORED — this target is not bundle-scopable. Its
        published set must EQUAL the derived set, for two reasons that a narrowed
        run breaks together: every artifact stamps the argument-free
        :data:`_REGENERATE_COMMAND` into its header, so a narrowed set publishes
        artifacts whose own stated reproduction command does not reproduce them;
        and a consumer selecting a stem that a narrowed run happened to omit gets
        no artifact at all, with nothing in the published set saying why.

        Ignoring the filter — rather than rejecting it — is what keeps
        ``--target all --bundles X`` working: the CLI forwards ``bundles`` to
        every registered target, so a raise here would fail the whole fan-out
        run. The other targets scope; this one emits its whole set alongside
        them. There is consequently no parameter anywhere in this module by
        which the derived set can be narrowed (see :func:`discover_domains`).

        Args:
            marketplace_dir: Path to ``marketplace/bundles/``.
            output_dir: Root under which ``packs/`` is written. Required.
            bundles: Ignored — see above.

        Returns:
            The written artifact paths, sorted.
        """
        if output_dir is None:
            raise ValueError(
                'CuiossReviewBotTarget requires --output: pass an output directory '
                '(e.g. target/cuioss-review-bot, under which the packs/ artifact set is written)'
            )
        bodies = compose_packs(marketplace_dir)
        if not bodies:
            raise ValueError(
                f'no review domains derived from {marketplace_dir}: expected at least one bundle '
                f'carrying a *-security, arch-gate-* or ext-triage-* skill'
            )
        if _SPINE_ARTIFACT_NAME in bodies:
            # Fail CLOSED on a name collision. A bundle shipping a `spine-security`
            # (or `arch-gate-spine` / `ext-triage-spine`) skill derives the domain
            # `spine`, and a bare assignment would replace that domain's harvested
            # rules with the spine — dropping enforcement text from the published
            # set with no error, while the publish workflow's count-before-delete
            # guard still sees a non-zero count. A security control must not fail
            # open. `test_the_spine_stem_is_not_itself_a_derived_domain` catches
            # this in THIS repository's suite; this raise is what protects every
            # consumer that runs the generator without that test.
            raise ValueError(
                f'derived domain {_SPINE_ARTIFACT_NAME!r} collides with the spine artifact '
                f'name: one would silently replace the other. Rename the skill that derives '
                f'it, or reserve the name in _classify_skill.'
            )
        bodies[_SPINE_ARTIFACT_NAME] = compose_spine(discover_spine_topics(marketplace_dir))
        artifacts = {name: render_pack_artifact(name, body) for name, body in bodies.items()}

        code_review_bodies = compose_code_review_packs(marketplace_dir)
        if _SPINE_ARTIFACT_NAME in code_review_bodies:
            # The same fail-closed collision as above, for the code-review set: a
            # declared domain key `spine` would be replaced by the code-review spine.
            raise ValueError(
                f'declared code-review domain {_SPINE_ARTIFACT_NAME!r} collides with the code-review '
                f'spine artifact name: one would silently replace the other. Rename the domain key.'
            )
        code_review_bodies[_SPINE_ARTIFACT_NAME] = compose_code_review_spine(
            *discover_code_review_spine(marketplace_dir)
        )
        for name, body in code_review_bodies.items():
            stem = f'{_CODE_REVIEW_PREFIX}{name}'
            if stem in artifacts:
                # Both sets share one flat directory, so a security domain whose
                # name carries the code-review prefix would overwrite (or be
                # overwritten by) a code-review artifact. Refuse before writing.
                raise ValueError(
                    f'artifact {stem!r} is produced by both the security and the code-review set: '
                    f'one would silently replace the other. Rename the domain that derives it.'
                )
            artifacts[stem] = render_code_review_artifact(name, body)

        # Every artifact is composed before the first write, so a compose that
        # raises leaves the previous set intact.
        packs_dir = output_dir / _PACKS_DIRNAME
        packs_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for stem, text in artifacts.items():
            path = packs_dir / f'{stem}.md'
            path.write_text(text, encoding='utf-8')
            written.append(path)
        _prune_stale_artifacts(packs_dir, keep=set(written))
        return sorted(written)


__all__ = [
    'ANTI_FABRICATION_CLAUSE',
    'CODE_REVIEW_SPINE_SKILL',
    'CodeReviewDomain',
    'DomainContribution',
    'INTENT_CLAUSE',
    'MAX_CATEGORY_BULLETS',
    'MAX_DOMAIN_RULES',
    'CuiossReviewBotTarget',
    'SEVERITY_CLAUSE',
    'SPINE_CATEGORIES',
    'SUBSTANTIATION_CLAUSE',
    'compose_code_review_domain_pack',
    'compose_code_review_packs',
    'compose_code_review_spine',
    'compose_domain_pack',
    'compose_packs',
    'compose_spine',
    'discover_code_review_domains',
    'discover_code_review_spine',
    'discover_domains',
    'discover_spine_topics',
    'render_code_review_artifact',
    'render_pack_artifact',
]
