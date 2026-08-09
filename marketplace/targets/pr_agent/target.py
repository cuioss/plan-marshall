# SPDX-License-Identifier: FSL-1.1-ALv2
"""PrAgentTarget — per-domain PR-Agent instruction-pack export target.

Reads the same source of truth as every other target (``marketplace/bundles/``)
and emits a REVIEWER CONFIGURATION rather than an assistant bundle tree: a
repo-local ``.pr_agent.toml`` carrying exactly one composed instruction pack in
``[pr_reviewer].extra_instructions``. ``emits_bundle_tree`` is therefore
``False``, so the CLI skips its generic bundle-tree post-emit steps (version
stamping and the dist-manifest) for this target.

Three properties of the composition are load-bearing:

* **The domain set is DERIVED, never hand-transcribed.** ``discover_domains``
  scans ``marketplace_dir`` for the per-domain standards skills — ``*-security``,
  ``arch-gate-*`` and ``ext-triage-*`` — so a bundle added to the marketplace
  appears in the derived set with no edit to this module.
* **A repository's pack may COMPOSE several domains.** A repository is not
  always one language: this marketplace is both Python and marketplace-tooling,
  so its reviewer needs the ``python`` and ``plugin`` rules together. The
  selection is therefore a SET of derived domains, and the composed pack carries
  every selected domain's rules.
* **Pack SELECTION is an argument, not an accumulation.** A run emits exactly
  ONE pack to ``{output_dir}/.pr_agent.toml``; a second run REPLACES that file
  rather than appending to it, so a repository carries exactly one pack — even
  when that one pack composes several domains.

The substantiation clause and the anti-fabrication clause are carried VERBATIM
into every pack, and the category bullet list is capped at
:data:`MAX_CATEGORY_BULLETS` entries.

**The category ceiling survives composition by GROUPING, not by widening.** The
ceiling is an observed organisation rule quoted in ``pr-agent-settings``'
README — past roughly ten entries the answer is a second focused pass, not an
eleventh bullet — so it is not this module's number to raise. A composed pack
therefore contributes exactly ONE domain category bullet naming every selected
domain, and groups the per-domain rules under the single "Domain rules" block.
Allocating one category per domain would put a two-domain pack at eleven
entries; grouping keeps an N-domain pack at exactly :data:`MAX_CATEGORY_BULLETS`
for every N. Rules are NOT categories and are deliberately not governed by that
ceiling — a composed pack's rule list grows with the number of domains, each
domain capped at :data:`MAX_DOMAIN_RULES`.

The pack-selection rules live as module-level constants here rather than as a
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
# Composition limits and defaults
# ---------------------------------------------------------------------------

#: Hard ceiling on the pack's category bullet list. ``pr-agent-settings``
#: § "Recall beats precision": past roughly ten entries the answer is a second
#: focused pass, not an eleventh bullet.
MAX_CATEGORY_BULLETS = 10

#: Ceiling on the harvested per-domain rule list, applied PER DOMAIN. Rules are
#: not review categories, so they are not governed by
#: :data:`MAX_CATEGORY_BULLETS`; the separate cap keeps a pack from growing
#: without bound as standards are added. A composed pack carries up to this many
#: rules per selected domain — composition widens the rule list on purpose,
#: because dropping a second domain's rules to hit a single total is exactly the
#: silent under-review this target exists to fix.
MAX_DOMAIN_RULES = 12

#: Separator for a multi-domain pack selection, in the CLI and in the target
#: constructor alike.
PACK_SEPARATOR = ','

#: Pack selection emitted when the caller names none. This repository is both a
#: Python codebase and a marketplace-tooling codebase, so its own reviewer needs
#: both domains' rules; a single-language default would silently under-review
#: whichever half it omitted.
DEFAULT_PACK = 'python,plugin'

#: Output filename. A run REPLACES this file — packs swap, they never accumulate.
CONFIG_FILENAME = '.pr_agent.toml'

# ---------------------------------------------------------------------------
# Charter text carried verbatim into every pack
# ---------------------------------------------------------------------------

#: The substantiation bar. Carried byte-identical from the org charter; every
#: generated pack contains it. Kept on ONE line so the clause is a contiguous
#: substring and a guard can assert it verbatim.
SUBSTANTIATION_CLAUSE = (
    'For each finding, name the input or state that triggers it and what goes wrong. Overlap with '
    'other reviewers is acceptable — report the issue regardless of whether another tool might also '
    'catch it. Do not withhold a substantiated finding because it seems minor or obvious.'
)

#: The anti-fabrication clause. Load-bearing and must not be dropped when a pack
#: is next tuned: pressure to report more is exactly the pressure that produces
#: invented mechanisms. Carried byte-identical from the org charter.
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

#: The cross-cutting review categories carried by EVERY pack. This is the spine's
#: review-category rendering; the domain adds exactly one further bullet, so a
#: pack lands at :data:`MAX_CATEGORY_BULLETS` entries.
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
# Pack composition
# ---------------------------------------------------------------------------


def _join_terms(terms: Sequence[str]) -> str:
    """Join terms as English prose: ``a``, ``a and b``, ``a, b and c``."""
    if not terms:
        return ''
    if len(terms) == 1:
        return terms[0]
    return f'{", ".join(terms[:-1])} and {terms[-1]}'


def parse_pack_selection(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize a pack selection into an ordered, deduped tuple of domains.

    Accepts either a :data:`PACK_SEPARATOR`-separated string (the CLI and config
    form) or an already-split sequence. Order is the caller's, because it is the
    order the domains are named in the composed pack's prose; duplicates are
    dropped so ``python,python`` cannot double a rule list.

    Raises:
        ValueError: When the selection names no domain at all.
    """
    raw = value.split(PACK_SEPARATOR) if isinstance(value, str) else list(value)
    selection: list[str] = []
    for item in raw:
        token = item.strip()
        if token and token not in selection:
            selection.append(token)
    if not selection:
        raise ValueError('empty pack selection: name at least one derived domain')
    return tuple(selection)


def _domain_category_bullet(contributions: Sequence[DomainContribution]) -> str:
    """Render the SINGLE derived domain category bullet covering every selection.

    Exactly one bullet regardless of how many domains the pack composes. That is
    the grouping that keeps a composed pack inside :data:`MAX_CATEGORY_BULLETS`:
    one category per domain would put a two-domain pack at eleven entries and
    over a ceiling this module does not own (see the module docstring).

    The bullet states only what the pack actually carries. Domains whose rules
    were harvested point at the "Domain rules" block; domains that contributed no
    rules are instead named with the standards that govern them, so the reviewer
    is never promised a list that is not there.
    """
    domains = [c.domain for c in contributions]
    with_rules = [c for c in contributions if c.rules]
    without_rules = [c for c in contributions if not c.rules]

    clauses: list[str] = []
    if with_rules:
        named = _join_terms([c.domain for c in with_rules])
        clauses.append(
            f'the rules this organisation enforces for {named} code are listed under '
            f'"Domain rules" below'
        )
    for contribution in without_rules:
        labels = _join_terms([_KIND_LABELS[kind] for kind in contribution.kinds])
        clauses.append(
            f'this organisation governs {contribution.domain} through its {labels} standards — '
            f'apply every category above to {contribution.domain} sources and idioms, not only to '
            f'the repository\'s primary language'
        )
    return f'Defects specific to {_join_terms(domains)}: ' + '; '.join(clauses) + '.'


def compose_pack(
    contributions: DomainContribution | Sequence[DomainContribution],
    spine_topics: tuple[str, ...] = (),
) -> str:
    """Compose one instruction pack over one or more derived domains.

    The category bullet list is the cross-cutting spine plus exactly ONE derived
    domain bullet — however many domains are composed — capped at
    :data:`MAX_CATEGORY_BULLETS`; the domain bullet is never the entry dropped by
    the cap. The substantiation and anti-fabrication clauses are appended
    verbatim.

    Args:
        contributions: One contribution, or the ordered set composing the pack.
        spine_topics: Cross-cutting foundation topics, from
            :func:`discover_spine_topics`.
    """
    selected = (contributions,) if isinstance(contributions, DomainContribution) else tuple(contributions)
    if not selected:
        raise ValueError('compose_pack requires at least one domain contribution')

    domains = [c.domain for c in selected]
    scope = f'{_join_terms(domains)} domain' + ('s' if len(domains) > 1 else '')

    spine_budget = MAX_CATEGORY_BULLETS - 1
    categories = [*SPINE_CATEGORIES[:spine_budget], _domain_category_bullet(selected)]

    lines: list[str] = [
        f'Prioritise security and correctness over style. This pack is scoped to the {scope}.',
        '',
        'Report every issue you can substantiate, in these categories:',
    ]
    lines.extend(f'- {category}' for category in categories)

    if spine_topics:
        lines.append('')
        lines.append(
            'Cross-cutting foundations to apply in every review: ' + ', '.join(spine_topics) + '.'
        )

    rule_bearing = [c for c in selected if c.rules]
    if rule_bearing:
        named = _join_terms([c.domain for c in rule_bearing])
        lines.append('')
        lines.append(
            f'Domain rules — this organisation\'s own standards for {named} code. A diff '
            f'that breaks one of these is a finding, and the rule already names the mechanism:'
        )
        # A composed pack tags each rule with the domain that contributed it, so
        # the reviewer can tell a Python rule from a marketplace-tooling one. A
        # single-domain pack needs no tag: the whole pack is that domain.
        tag = len(rule_bearing) > 1
        for contribution in rule_bearing:
            prefix = f'[{contribution.domain}] ' if tag else ''
            lines.extend(f'- {prefix}{rule}' for rule in contribution.rules)

    for clause in (SUBSTANTIATION_CLAUSE, INTENT_CLAUSE, SEVERITY_CLAUSE, ANTI_FABRICATION_CLAUSE):
        lines.append('')
        lines.append(clause)

    return '\n'.join(lines) + '\n'


def compose_packs(marketplace_dir: Path, bundles: list[str] | None = None) -> dict[str, str]:
    """Compose the single-domain pack for every derived domain.

    The population is derived, not hand-written: a consumer enumerating packs
    (e.g. the charter regression guard) asks this function rather than iterating
    a literal list, so a new domain is guarded the moment it is derivable.
    """
    spine_topics = discover_spine_topics(marketplace_dir)
    return {
        domain: compose_pack(contribution, spine_topics)
        for domain, contribution in discover_domains(marketplace_dir, bundles=bundles).items()
    }


def compose_selection(
    marketplace_dir: Path,
    selection: Sequence[str],
    bundles: list[str] | None = None,
) -> str:
    """Compose the ONE pack a repository carries for the given domain selection.

    This is the composition the target emits, and the one a guard must measure:
    a composed selection is a pack shape that :func:`compose_packs` — which only
    enumerates single-domain packs — never produces.

    Raises:
        ValueError: When the marketplace derives no domain at all, or when the
            selection names a domain that is not derivable.
    """
    derived = discover_domains(marketplace_dir, bundles=bundles)
    if not derived:
        raise ValueError(
            f'no review domains derived from {marketplace_dir}: expected at least one bundle '
            f'carrying a *-security, arch-gate-* or ext-triage-* skill'
        )
    unknown = [domain for domain in selection if domain not in derived]
    if unknown:
        raise ValueError(
            f'unknown pack {PACK_SEPARATOR.join(unknown)!r}; derived packs are: '
            f'{", ".join(sorted(derived))}'
        )
    return compose_pack(
        [derived[domain] for domain in selection],
        discover_spine_topics(marketplace_dir),
    )


def render_config(selection: Sequence[str], pack: str) -> str:
    """Render the repo-local ``.pr_agent.toml`` carrying exactly one pack.

    The pack is emitted as a TOML multi-line LITERAL string: harvested rule text
    can contain backslashes (regex fragments, path separators), which a basic
    ``\"\"\"`` string would read as escape sequences.

    The header states the selection and the command that reproduces the file,
    including ``--packs``. That is load-bearing for a composed selection: a
    regenerate line that omitted the selection would name a command producing a
    DIFFERENT file, and following it would silently narrow the repository's
    review to the default.
    """
    if "'''" in pack:
        raise ValueError('composed pack contains a TOML literal-string terminator; cannot render')
    joined = PACK_SEPARATOR.join(selection)
    return (
        '# Repository-local PR-Agent configuration — GENERATED, do not edit by hand.\n'
        '#\n'
        f'# Pack: {joined}. Regenerate with:\n'
        f'#   python3 marketplace/targets/generate.py --target pr-agent --output . --packs {joined}\n'
        '#\n'
        '# Merged ABOVE the organisation-wide cuioss/pr-agent-settings configuration, so this\n'
        '# file carries the per-domain reviewer pack ONLY and inherits every other key — model,\n'
        '# token budgets, output suppression — from that file. Restating those here would\n'
        '# decentralize the configuration that file exists to centralize.\n'
        '#\n'
        '# A repository carries exactly ONE pack: a regeneration REPLACES the pack below rather\n'
        '# than appending to it. One pack may COMPOSE several derived domains — a repository is\n'
        '# not always one language — and the composed pack still contributes exactly one review\n'
        '# category, so composition never widens the category ceiling.\n'
        '\n'
        '[pr_reviewer]\n'
        "extra_instructions = '''\n"
        f"{pack}'''\n"
    )


# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


class PrAgentTarget(TargetBase):
    """Build target emitting a per-domain PR-Agent instruction pack."""

    def __init__(self, pack: str | Sequence[str] = DEFAULT_PACK) -> None:
        """Bind the target to ONE pack selection, over one or more domains.

        Args:
            pack: The derived domain(s) whose composed pack this run emits —
                either a :data:`PACK_SEPARATOR`-separated string or a sequence.
                Selection is an argument, never an accumulation: one run emits
                one pack, and that pack may compose several domains.
        """
        self._packs = parse_pack_selection(pack)

    @property
    def name(self) -> str:
        return 'pr-agent'

    @property
    def config_dir(self) -> Path:
        """Directory holding this target's rules — the package directory itself.

        The pack-selection rules are module-level constants rather than sibling
        JSON files; see the module docstring for why.
        """
        return Path(__file__).resolve().parent

    @property
    def emits_bundle_tree(self) -> bool:
        """This target emits a reviewer configuration, not a bundle tree."""
        return False

    def supports_agents(self) -> bool:
        return False

    def supports_commands(self) -> bool:
        return False

    @property
    def packs(self) -> tuple[str, ...]:
        """The selected derived domains this run composes into one pack."""
        return self._packs

    @property
    def pack(self) -> str:
        """The selection in its canonical string form (the header/CLI spelling)."""
        return PACK_SEPARATOR.join(self._packs)

    def generate(
        self,
        marketplace_dir: Path,
        output_dir: Path | None,
        bundles: list[str] | None = None,
    ) -> list[Path]:
        if output_dir is None:
            raise ValueError(
                'PrAgentTarget requires --output: pass an output directory '
                '(e.g. the repository root, which is where .pr_agent.toml lives)'
            )
        pack = compose_selection(marketplace_dir, self._packs, bundles=bundles)

        output_dir.mkdir(parents=True, exist_ok=True)
        config_path = output_dir / CONFIG_FILENAME
        config_path.write_text(render_config(self._packs, pack), encoding='utf-8')
        return [config_path]


__all__ = [
    'ANTI_FABRICATION_CLAUSE',
    'CONFIG_FILENAME',
    'DEFAULT_PACK',
    'DomainContribution',
    'INTENT_CLAUSE',
    'MAX_CATEGORY_BULLETS',
    'MAX_DOMAIN_RULES',
    'PACK_SEPARATOR',
    'PrAgentTarget',
    'SEVERITY_CLAUSE',
    'SPINE_CATEGORIES',
    'SUBSTANTIATION_CLAUSE',
    'compose_pack',
    'compose_packs',
    'compose_selection',
    'discover_domains',
    'discover_spine_topics',
    'parse_pack_selection',
    'render_config',
]
