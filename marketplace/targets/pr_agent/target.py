# SPDX-License-Identifier: FSL-1.1-ALv2
"""PrAgentTarget — per-domain PR-Agent instruction-pack export target.

Reads the same source of truth as every other target (``marketplace/bundles/``)
and emits a REVIEWER ARTIFACT SET rather than an assistant bundle tree: one
Markdown artifact per derived domain, plus one spine artifact, written under
``{output_dir}/packs/``. ``emits_bundle_tree`` is therefore ``False``, so the
CLI skips its generic bundle-tree post-emit steps (version stamping and the
dist-manifest) for this target.

Three properties of the emission are load-bearing:

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
* **A run EMITS the whole set.** One artifact per derived domain plus the
  spine, under ``{output_dir}/packs/``. The spine is emitted unconditionally
  and is not selectable: a spine a consumer could omit is a charter a consumer
  could drop.

The substantiation clause and the anti-fabrication clause are carried VERBATIM
into the spine artifact, and appear in no domain artifact.

**The category ceiling is a two-part BUDGET, not a grouping.** The ceiling is an
observed organisation rule quoted in ``pr-agent-settings``' README — past roughly
ten entries the answer is a second focused pass, not an eleventh bullet — so it
is not this module's number to raise. The spine reserves one slot: it carries at
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
# Composition limits and emission layout
# ---------------------------------------------------------------------------

#: Hard ceiling on the pack's category bullet list. ``pr-agent-settings``
#: § "Recall beats precision": past roughly ten entries the answer is a second
#: focused pass, not an eleventh bullet.
MAX_CATEGORY_BULLETS = 10

#: Ceiling on the harvested per-domain rule list, applied PER DOMAIN. Rules are
#: not review categories, so they are not governed by
#: :data:`MAX_CATEGORY_BULLETS`; the separate cap keeps an artifact from growing
#: without bound as standards are added. Each domain artifact carries up to this
#: many rules, and a repository selecting several domains reads several
#: artifacts — dropping a second domain's rules to hit a single total is exactly
#: the silent under-review this target exists to fix.
MAX_DOMAIN_RULES = 12

#: Directory, under the target's output root, holding the emitted artifact set.
_PACKS_DIRNAME = 'packs'

#: Stem of the one artifact carrying the cross-cutting charter. It is emitted
#: unconditionally and is not a derived domain — a consumer applies it alongside
#: whichever domain artifacts it selects, and cannot deselect it.
_SPINE_ARTIFACT_NAME = 'spine'

#: The source repository every emitted artifact names in its header, so a reader
#: who finds an artifact in the published set can reach the derivation.
_SOURCE_REPOSITORY = 'cuioss/plan-marshall'

#: The argument-free command that reproduces the whole artifact set. Selection is
#: no longer an argument, so there is exactly one regenerate line for every
#: artifact — following it can no longer narrow what a repository gets.
_REGENERATE_COMMAND = (
    'uv run python marketplace/targets/generate.py --target pr-agent --output target/pr-agent'
)

# ---------------------------------------------------------------------------
# Charter text carried verbatim into the spine artifact
# ---------------------------------------------------------------------------

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
        token = skill_name[len(_ARCH_GATE_PREFIX):]
        return (KIND_ARCH_GATE, token) if token else None
    if skill_name.startswith(_TRIAGE_PREFIX):
        token = skill_name[len(_TRIAGE_PREFIX):]
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


def discover_domains(marketplace_dir: Path, bundles: list[str] | None = None) -> dict[str, DomainContribution]:
    """Derive the review-domain set by scanning the source marketplace.

    A bundle contributes a domain when it holds at least one per-domain
    standards skill (``*-security``, ``arch-gate-*`` or ``ext-triage-*``). The
    domain identifier is taken from the highest-precedence contributing kind
    (:data:`_KIND_ORDER`), so ``pm-dev-frontend``'s ``javascript-security`` names
    the domain that ``arch-gate-js`` and ``ext-triage-js`` also feed.

    The spine bundle is excluded: it carries the cross-cutting foundations, not
    a domain of its own.

    Args:
        marketplace_dir: Path to ``marketplace/bundles/``.
        bundles: Optional bundle allow-list. ``None`` scans every bundle.

    Returns:
        Derived domain identifier -> :class:`DomainContribution`, ordered by
        domain identifier.
    """
    allowed = set(bundles) if bundles else None
    # bundle -> kind -> (domain_token, skill_dir)
    per_bundle: dict[str, dict[str, tuple[str, Path]]] = {}

    for bundle_dir in sorted(p for p in marketplace_dir.glob('*') if p.is_dir()):
        bundle = bundle_dir.name
        if bundle == SPINE_BUNDLE:
            continue
        if allowed is not None and bundle not in allowed:
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
            f'the rules this organisation enforces for {contribution.domain} code are listed under '
            f'"Domain rules" below'
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
        lines.append(
            'Cross-cutting foundations to apply in every review: ' + ', '.join(spine_topics) + '.'
        )

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
        f'Prioritise security and correctness over style. This pack is scoped to the '
        f'{contribution.domain} domain.',
        '',
        f'- {_domain_category_bullet(contribution)}',
    ]

    if contribution.rules:
        lines.append('')
        lines.append(
            f'Domain rules — this organisation\'s own standards for {contribution.domain} code. A diff '
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

    A domain artifact's header additionally states that the spine artifact is
    applied alongside it and is not optional. That sentence is the consumer-facing
    half of the orthogonality contract: a domain artifact deliberately carries no
    charter text, so reading one on its own would silently drop the substantiation
    and anti-fabrication bars.

    Args:
        name: The artifact stem — a derived domain, or the spine's own name.
        body: The composed body, from :func:`compose_domain_pack` or
            :func:`compose_spine`.
    """
    if name == _SPINE_ARTIFACT_NAME:
        role = (
            'This is the spine artifact. It carries the cross-cutting review charter exactly once,\n'
            'and applies to every review regardless of which domain artifacts a repository selects.\n'
            'It is not selectable: a repository cannot deselect it.'
        )
    else:
        role = (
            f'This artifact carries the {name} domain part alone. The spine artifact ({_SPINE_ARTIFACT_NAME}.md)\n'
            'is applied alongside it and is not optional — the review charter lives there and appears\n'
            'in no domain artifact.'
        )
    return (
        f'<!-- GENERATED ARTIFACT — do not edit by hand.\n'
        f'Derived from the {_SOURCE_REPOSITORY} marketplace (marketplace/bundles/**).\n'
        f'Regenerate with:\n'
        f'  {_REGENERATE_COMMAND}\n'
        f'{role}\n'
        f'-->\n'
        f'\n'
        f'{body}'
    )


def compose_packs(marketplace_dir: Path, bundles: list[str] | None = None) -> dict[str, str]:
    """Compose the spine-free body for every derived domain.

    The population is derived, not hand-written: a consumer enumerating packs
    (e.g. the artifact-set drift guard) asks this function rather than iterating
    a literal list, so a new domain is guarded the moment it is derivable. The
    spine is deliberately not a member — it is not a domain, and it is emitted
    separately by :func:`compose_spine`.
    """
    return {
        domain: compose_domain_pack(contribution)
        for domain, contribution in discover_domains(marketplace_dir, bundles=bundles).items()
    }


# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


class PrAgentTarget(TargetBase):
    """Build target emitting the per-domain PR-Agent artifact set plus the spine."""

    @property
    def name(self) -> str:
        return 'pr-agent'

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
        if output_dir is None:
            raise ValueError(
                'PrAgentTarget requires --output: pass an output directory '
                '(e.g. target/pr-agent, under which the packs/ artifact set is written)'
            )
        bodies = compose_packs(marketplace_dir, bundles=bundles)
        if not bodies:
            raise ValueError(
                f'no review domains derived from {marketplace_dir}: expected at least one bundle '
                f'carrying a *-security, arch-gate-* or ext-triage-* skill'
            )
        bodies[_SPINE_ARTIFACT_NAME] = compose_spine(discover_spine_topics(marketplace_dir))

        packs_dir = output_dir / _PACKS_DIRNAME
        packs_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for artifact_name, body in bodies.items():
            path = packs_dir / f'{artifact_name}.md'
            path.write_text(render_pack_artifact(artifact_name, body), encoding='utf-8')
            written.append(path)
        return sorted(written)


__all__ = [
    'ANTI_FABRICATION_CLAUSE',
    'DomainContribution',
    'INTENT_CLAUSE',
    'MAX_CATEGORY_BULLETS',
    'MAX_DOMAIN_RULES',
    'PrAgentTarget',
    'SEVERITY_CLAUSE',
    'SPINE_CATEGORIES',
    'SUBSTANTIATION_CLAUSE',
    'compose_domain_pack',
    'compose_packs',
    'compose_spine',
    'discover_domains',
    'discover_spine_topics',
    'render_pack_artifact',
]
