# SPDX-License-Identifier: FSL-1.1-ALv2
"""PrAgentTarget — per-domain PR-Agent instruction-pack export target.

Reads the same source of truth as every other target (``marketplace/bundles/``)
and emits a REVIEWER CONFIGURATION rather than an assistant bundle tree: a
repo-local ``.pr_agent.toml`` carrying exactly one composed instruction pack in
``[pr_reviewer].extra_instructions``. ``emits_bundle_tree`` is therefore
``False``, so the CLI skips its generic bundle-tree post-emit steps (version
stamping and the dist-manifest) for this target.

Two properties of the composition are load-bearing:

* **The domain set is DERIVED, never hand-transcribed.** ``discover_domains``
  scans ``marketplace_dir`` for the per-domain standards skills — ``*-security``,
  ``arch-gate-*`` and ``ext-triage-*`` — so a bundle added to the marketplace
  appears in the derived set with no edit to this module.
* **Pack SELECTION is an argument, not an accumulation.** A run emits exactly
  ONE pack to ``{output_dir}/.pr_agent.toml``; a second run REPLACES that file
  rather than appending to it, so a repository carries exactly one pack.

The substantiation clause and the anti-fabrication clause are carried VERBATIM
into every pack, and the category bullet list is capped at
:data:`MAX_CATEGORY_BULLETS` entries.

The pack-selection rules live as module-level constants here rather than as a
sibling JSON config: a new ``marketplace/targets/**/*.json`` path is claimed by
no build extension and by no owner-less classifier rule, so it would resolve to
the ``unknown`` bucket. The existing ``opencode/*.json`` configs predate that
classifier and are not a precedent a new file may follow.
"""

from __future__ import annotations

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

#: Ceiling on the harvested per-domain rule list. Rules are not review
#: categories, so they are not governed by :data:`MAX_CATEGORY_BULLETS`; the
#: separate cap keeps a pack from growing without bound as standards are added.
MAX_DOMAIN_RULES = 12

#: Pack emitted when the caller names none.
DEFAULT_PACK = 'python'

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


def _domain_category_bullet(contribution: DomainContribution) -> str:
    """Render the single derived domain category bullet.

    The bullet states only what the pack actually carries: it points at the
    "Domain rules" block when rules were harvested, and otherwise instructs the
    reviewer to apply every category to the domain's own sources — it never
    promises a list that is not there.
    """
    if contribution.rules:
        return (
            f'Defects specific to {contribution.domain}: the rules this organisation enforces for '
            f'{contribution.domain} code, listed under "Domain rules" below.'
        )
    labels = [_KIND_LABELS[kind] for kind in contribution.kinds]
    joined = f'{", ".join(labels[:-1])} and {labels[-1]}' if len(labels) > 1 else labels[0]
    return (
        f'Defects specific to {contribution.domain}: this organisation governs {contribution.domain} '
        f'through its {joined} standards — apply every category above to {contribution.domain} sources '
        f'and idioms, not only to the repository\'s primary language.'
    )


def compose_pack(contribution: DomainContribution, spine_topics: tuple[str, ...] = ()) -> str:
    """Compose one domain's instruction pack.

    The category bullet list is the cross-cutting spine plus exactly one derived
    domain bullet, capped at :data:`MAX_CATEGORY_BULLETS`; the domain bullet is
    never the entry dropped by the cap. The substantiation and anti-fabrication
    clauses are appended verbatim.
    """
    spine_budget = MAX_CATEGORY_BULLETS - 1
    categories = [*SPINE_CATEGORIES[:spine_budget], _domain_category_bullet(contribution)]

    lines: list[str] = [
        f'Prioritise security and correctness over style. This pack is scoped to the '
        f'{contribution.domain} domain.',
        '',
        'Report every issue you can substantiate, in these categories:',
    ]
    lines.extend(f'- {category}' for category in categories)

    if spine_topics:
        lines.append('')
        lines.append(
            'Cross-cutting foundations to apply in every review: ' + ', '.join(spine_topics) + '.'
        )

    if contribution.rules:
        lines.append('')
        lines.append(
            f'Domain rules — this organisation\'s own standards for {contribution.domain} code. A diff '
            f'that breaks one of these is a finding, and the rule already names the mechanism:'
        )
        lines.extend(f'- {rule}' for rule in contribution.rules)

    for clause in (SUBSTANTIATION_CLAUSE, INTENT_CLAUSE, SEVERITY_CLAUSE, ANTI_FABRICATION_CLAUSE):
        lines.append('')
        lines.append(clause)

    return '\n'.join(lines) + '\n'


def compose_packs(marketplace_dir: Path, bundles: list[str] | None = None) -> dict[str, str]:
    """Compose every pack the derived domain set can produce.

    The population is derived, not hand-written: a consumer enumerating packs
    (e.g. the charter regression guard) asks this function rather than iterating
    a literal list, so a new domain is guarded the moment it is derivable.
    """
    spine_topics = discover_spine_topics(marketplace_dir)
    return {
        domain: compose_pack(contribution, spine_topics)
        for domain, contribution in discover_domains(marketplace_dir, bundles=bundles).items()
    }


def render_config(domain: str, pack: str) -> str:
    """Render the repo-local ``.pr_agent.toml`` carrying exactly one pack.

    The pack is emitted as a TOML multi-line LITERAL string: harvested rule text
    can contain backslashes (regex fragments, path separators), which a basic
    ``\"\"\"`` string would read as escape sequences.
    """
    if "'''" in pack:
        raise ValueError('composed pack contains a TOML literal-string terminator; cannot render')
    return (
        '# Repository-local PR-Agent configuration — GENERATED, do not edit by hand.\n'
        '#\n'
        f'# Pack: {domain}. Regenerate with:\n'
        '#   python3 marketplace/targets/generate.py --target pr-agent --output .\n'
        '#\n'
        '# Merged ABOVE the organisation-wide cuioss/pr-agent-settings configuration, so this\n'
        '# file carries the per-domain reviewer pack ONLY and inherits every other key — model,\n'
        '# token budgets, output suppression — from that file. Restating those here would\n'
        '# decentralize the configuration that file exists to centralize.\n'
        '#\n'
        '# A repository carries exactly ONE pack: a regeneration REPLACES the pack below rather\n'
        '# than appending to it.\n'
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

    def __init__(self, pack: str = DEFAULT_PACK) -> None:
        """Bind the target to ONE pack selection.

        Args:
            pack: The derived domain whose pack this run emits. Selection is an
                argument, never an accumulation — one run, one pack.
        """
        self._pack = pack

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
    def pack(self) -> str:
        """The selected pack (derived-domain identifier) this run emits."""
        return self._pack

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
        packs = compose_packs(marketplace_dir, bundles=bundles)
        if not packs:
            raise ValueError(
                f'no review domains derived from {marketplace_dir}: expected at least one bundle '
                f'carrying a *-security, arch-gate-* or ext-triage-* skill'
            )
        if self._pack not in packs:
            raise ValueError(
                f'unknown pack {self._pack!r}; derived packs are: {", ".join(sorted(packs))}'
            )

        output_dir.mkdir(parents=True, exist_ok=True)
        config_path = output_dir / CONFIG_FILENAME
        config_path.write_text(render_config(self._pack, packs[self._pack]), encoding='utf-8')
        return [config_path]


__all__ = [
    'ANTI_FABRICATION_CLAUSE',
    'CONFIG_FILENAME',
    'DEFAULT_PACK',
    'DomainContribution',
    'INTENT_CLAUSE',
    'MAX_CATEGORY_BULLETS',
    'MAX_DOMAIN_RULES',
    'PrAgentTarget',
    'SEVERITY_CLAUSE',
    'SPINE_CATEGORIES',
    'SUBSTANTIATION_CLAUSE',
    'compose_pack',
    'compose_packs',
    'discover_domains',
    'discover_spine_topics',
    'render_config',
]
