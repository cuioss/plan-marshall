# Epic Surface Derivation

The model behind `tools-epic-surface-partition`: how a spec's `## Expected
Surface` becomes a typed claim, how those claims — narrowed by the epic ledger's
record of which plans are still working — partition the real `test/` tree, and
what the report must assert.

The derivation reads **two** sources, and keeps them apart. The staged spec
corpus states what each plan CLAIMS; the epic ledger states whether that plan is
still working. Each is read by its own loader, and neither is consulted by the
other's — see [The plan-lifecycle input](#the-plan-lifecycle-input).

## Never a gate

⛔ This tool is a **derivation and report tool, never a CI gate**. The epic specs
and the epic ledger both live under `.plan/local/orchestrator/`, which is
git-ignored and therefore absent from a fresh clone — no CI check can read them,
so no CI check can depend on them. `report` exits 0 even when it renders
disagreements: a rendered disagreement is the product, not a failure.

The ledger's absence from a fresh clone is also why the degraded lifecycle read
is a first-class, reported state rather than an error — see
[The degradation path](#the-degradation-path).

The tool's only sanctioned write is the escalation path in
[The escalation path](#the-escalation-path). It edits no spec under any branch.

## Where the parse lives

⛔ **This skill owns the PARTITION, not the PARSE.** The `## Expected Surface`
grammar and its reader live in **`plan-marshall:script-shared`** as
`epic_spec_parser` — the marketplace's single reader of that section, consumed
here as stage 1 and by `plan-marshall:plan-orchestrator`'s disjointness gate
(`corpus surfaces`, `corpus cross-check`, and the Ordered Queue's Surface cell).
This skill imports it; it holds no second copy.

The home is `script-shared` because both bundles read the section, and two
readers of one grammar is the defect that made a spec declaring only directories
or globs resolve to nothing at the gate while resolving correctly here. A change
to the grammar therefore lands in `script-shared` and reaches every consumer at
once; adding a local parse back to this skill would re-open exactly that split.

What this skill continues to own is unchanged in kind: the partition verdicts,
the plan-lifecycle read that narrows them, the line-budget attribution, the CLI
surface, and the output contract. The lifecycle read is this skill's own because
it is a PROJECTION question — whether a plan's claim still competes for ownership
— and not a reading of the `## Expected Surface` grammar at all.

### The split the entry-shape rules run along

The marker rules that decide an entry's SHAPE are a grammar change, so they land
in `script-shared` with the rest of the grammar. The two halves of that fact are
stated in different places and neither is duplicated into the other:

- **The shape a marker resolves an entry to** is the reader's output. It is
  stated beside the entry-shape table below, because it is a property of the
  grammar and every consumer of the reader sees it.
- **The demotion of a lead-shaped entry to a partition verdict** is THIS skill's
  projection, stated with the verdicts. The reader publishes the shape and
  demotes nothing; a consumer decides what the shape means for its own question.

One reader buys one *resolution*; each consumer keeps its own *projection*. The
orchestrator's disjointness gate reads the same entries and deliberately does not
demote them, because a lead removed from its surface would make a colliding plan
read as disjoint.

## The three-class model

`classify` — the relocated reader's verdict, consumed here — assigns every spec
exactly one class and records the evidence for the verdict beside it.

| Class | Rule | Evidence recorded |
|-------|------|-------------------|
| `derived` | The section carries the uppercase `DERIVED` marker | The source line carrying the marker |
| `declarative` | Not `derived`, and at least one entry resolves to a path | The resolved count and the first path |
| `prose` | A section is present but resolves to no path entry | That the section is present and resolves to nothing |

The order is significant: `derived` is tested first, so a spec that declares its
surface a function of other plans' surfaces stays `derived` even when it also
names provisional paths.

⛔ A spec whose class **cannot be determined** — unreadable, or carrying no
`## Expected Surface` section — raises `UnclassifiableSpecError` naming the spec.
The run halts rather than defaulting to a class, because a spec silently
defaulted into `prose` would be indistinguishable from one that genuinely claims
nothing.

The corpus is enumerated by the `PLAN-*.md` glob and never by a hard-coded plan
list. A hard-coded list would reproduce, one level down, the very defect the
derivation exists to close.

## Entry kinds the parser resolves

An entry's `kind` is the GEOMETRY of the span it names. It is a different field
from its `shape`, which records whether the spec claims that span or merely
leads to it — see [Entry shape: claim or lead](#entry-shape-claim-or-lead).

| Kind | Example | Emitted `kind` |
|------|---------|----------------|
| Directory | `test/plan-marshall/manage-config/` | `directory` |
| Recursive glob | `test/pm-plugin-development/**` | `recursive_glob` |
| Filename glob | `plugin-doctor/test_test_conventions_rule*.py` | `filename_glob` |
| Named file | `test/test_runner_falsifiability.py` | `file` |
| Non-`test/` path | `pyproject.toml` | `file` |
| Relative continuation | `.../workflow-integration-github/`, or a bare sibling written after a rooted path in the same bullet | derived from the resolved path |

A relative continuation resolves against the base the bullet's first **rooted**
entry establishes — the directory a recursive glob names, or the parent of any
other kind. Both notations are supported: the explicit `.../` prefix, whose
leading token is stripped before the base is applied, and the bare sibling. A
continuation in a bullet that established no base is recorded in `unresolved[]`
rather than guessed at.

An entry is an **exclusion** when it follows the `excluding` keyword, when its
bullet opens with a negative claim (`No changes to ...`), or when it sits under
`## Out of Scope`.

`OBSERVED:` / `HYPOTHESIS:` label prefixes (including qualified forms), the `⛔`
and `⚠️` markers, `**bold**` spans, and trailing em-dash commentary are tolerated
and stripped. Trailing commentary is dropped rather than parsed, because it
cites paths as reasons rather than claiming them — except when it carries the
`excluding` keyword, which several specs write after the dash.

A backticked span is treated as a path only when it carries no character that
cannot appear in a repository path, and either spans multiple segments, globs, or
actually exists at the repository root. That is what keeps dotted symbol names
and the corpus's many other backticked tokens out while admitting `pyproject.toml`.

A span the parser recognises as a path but cannot anchor is recorded in
`unresolved[]` — a first-class result, never a silent drop.

## Entry shape: claim or lead

Independently of the spec's class, each resolved entry carries its own **shape**,
decided from its own bullet by the marker rules below. A spec routinely mixes the
two: the same `declarative` spec may claim one directory outright and merely
point at another.

| Shape | Means |
|-------|-------|
| `claim` | The spec asserts ownership of the path |
| `lead` | The spec names the path without claiming it |

| Rule | Marker | Why it is not a claim |
|------|--------|-----------------------|
| Deferred hypothesis | A `HYPOTHESIS` label, or the `verify-at-outline` deferral phrase | A candidate path named for outline-time verification |
| Collection constraint | The `testpaths` settings key | States where the runner collects from, not what the plan owns |
| Cross-plan reference | A `PLAN-`-prefixed identifier OTHER than the citing spec's own, or a slice ordinal, in the possessive, in the bullet's CLAIM HEAD | Quotes the cited plan's ownership rather than asserting the citing plan's |
| Hedged conditional claim | A conditional restriction on the claim, or an explicit denial of further coverage | The bullet withdraws the span it just named |

Each rule fires on its own and each is keyed on published grammar or on the
spec's own words — never on any plan identifier, so a spec added to the corpus is
shaped by the same rules with no edit to the reader.

⛔ The cross-plan-reference rule reads the bullet's **claim head alone**, and the
narrowing is load-bearing. A possessive citation in the head says the named span
IS the other plan's surface; the same citation in the trailing commentary
annotates a claim the bullet makes in its own right, and reading it there would
demote most of the corpus.

⛔ **ANOTHER plan's.** The cited identifier is compared against the citing spec's
own plan id, and a spec naming ITSELF possessively — `PLAN-170's own tests under
test/x/` — keeps its claim. A rule that fired on any possessive of plan shape
would drop the module from `claimed` to `not_derivable`, the exact inverse of the
co-ownership defect the rule closes.

⛔ The rule keys on the `PLAN-`-prefixed half of the plan-id grammar, not on the
bare `{SLUG}-{DIGITS}` half. That half is a plan id only in a spec FILENAME's
anchored leading position; in prose the identical shape belongs to the external
references specs cite — `CWE-1333`, `CVE-2021-1234`, `RFC-8259` — and reading one
of those as a plan citation demotes the claim beside it. The residual is stated
rather than hidden: a possessive citation of a bare code-slug sibling stays a
claim, the direction that never invents a demotion it cannot substantiate.

⛔ The shape is **additive**. It is recorded on the entry and moves nothing: an
entry keeps its membership of `claimed` or `excluded` whatever its shape, and the
spec's class is unchanged by it. What a lead MEANS is the consuming stage's
decision — see [The partition verdicts](#the-partition-verdicts).

## The partition verdicts

`partition` assigns every test module under `test/` exactly one verdict.

| Verdict | Rule |
|---------|------|
| `claimed` | Exactly one SLICE plan's owning entries cover it, once the lifecycle narrowing below has run |
| `contested` | Two or more slice plans still competing cover it — the residual genuine disagreement |
| `swept` | No slice plan covers it, but one or more SWEEP plans do |
| `not_derivable` | No plan's owning entries cover it, but a spec names it in an unresolved span or in a lead-shaped entry |
| `unclaimed` | No plan covers it and no spec names it |

An entry carries OWNERSHIP unless one of three independent ENTRY-level rules
removes it: the spec declares itself a sweep, the entry is lead-shaped, or the
spec's class is `derived`. A fourth rule operates on the PLAN rather than the
entry, and only where a contest already exists — see
[The plan-lifecycle input](#the-plan-lifecycle-input).

⛔ **A lead-shaped entry is demoted HERE, not by the shared reader.** Stage 1
states the shape and moves nothing, because its other consumer needs the surface
whole; this stage performs the demotion, which is the projection half of that
reader's contract. A lead names a path without claiming it, so honouring it as
ownership collapses the attribution into one contested bucket.

⛔ **A spec whose class is `derived` owns nothing.** It declares its surface the
union of OTHER plans' surfaces, so its entries restate their claims rather than
competing with them; its coverage is reported as `not_derivable` when no slice
claims the module, never as an ownership contest.

Exclusions subtract from the claiming plan's **own** set only. A plan that claims
a recursive glob while excluding a sub-directory does not claim the modules under
it; another plan's claim over those same modules is unaffected.

### Sweep plans

A **sweep plan** is one whose spec DECLARES ITSELF to cross the whole partition by
construction rather than claiming a slice of it. Such a plan pairs with every
other plan by design, so counting it as a competing owner marks the whole tree
contested and destroys the partition's signal. A slice that shares a module with
any number of sweeps therefore OWNS that module, and the sweeps crossing it are
recorded beside the verdict as a separate fact rather than as competing
ownership.

Sweep-ness is detected from the spec's own self-declaration and never from a
hard-coded plan list. The marker admits every settled phrasing of the one
declaration — the surface is the tree entire, it pairs with no other plan, it
crosses the epic's reduction slices, its sites do not respect the slice
boundaries — because a marker narrow enough to match only the specs sharing one
boilerplate sentence is that hard-coded list wearing a regex, and stops matching
the moment a plan declares its crossing in its own words.

⛔ A spec that REPRODUCES a sibling's declaration while claiming an ordinary slice
is not itself a sweep. Every one of the settled phrasings above is reproducible,
so the guard is applied UNIFORMLY: a marker occurrence lying wholly inside a
reproduction span is discarded, whichever phrasing it matched. The test sits at
the single point all the phrasings pass through rather than inside any one of
them — a guard fitted to one phrasing leaves the others carrying the identical
exposure while its own control still passes.

A **reproduction span** takes one of three forms, because a spec here reproduces
a sentence in three ways and a guard recognising one of them is escaped by the
other two — the same fitted-guard defect as a narrowing written into a single
phrasing, one level down:

- a **quotation** — straight or typographic double quotes, or the typographic
  single pair. It spans lines but never a paragraph: prose in this corpus is
  hard-wrapped, so a quotation's marks routinely land on different lines and a
  line-bounded span would miss the dominant real form outright, while the blank
  line still keeps an unpaired mark from reaching beyond its own paragraph.
- a **code span** — inline or fenced, closed only by a backtick run of the same
  length as the one that opened it. This is the corpus's most common way of
  setting off a phrase it discusses rather than asserts.
- a **blockquote** — a run of consecutive `>`-prefixed lines. Markdown's lazy
  continuation, where a blockquote runs on into following lines carrying no
  marker, is deliberately OUT OF SCOPE: which unprefixed line starts a new block
  can only be guessed, and a wrong guess SUPPRESSES a real declaration, whereas
  stopping at the last prefixed line merely leaves a marker uncontained and
  therefore firing.

Containment must be total: a marker merely overlapping a reproduction span still
counts, so a partial or mismatched delimiter can never suppress a real
declaration. The straight single quote is not read as a quotation mark at all,
because specs write the possessive apostrophe with it.

⛔ A sweep plan is a property of the PLAN; a **root span** is a property of an
ENTRY. The two are independent and neither implies the other.

An unresolved span *names* a module by shape. A file-shaped span names it by its
trailing segments, filename included. A **container**-shaped span — one written
with a trailing `/` or `**`, which is the notation the relative-continuation row
above uses — names a directory, so it names every module beneath that directory:
its segments are matched against the module's ancestor directories, never against
the filename. Matching a container span on the filename would make it name
nothing, and every module it covers would fall through to `unclaimed` — the merge
the next section forbids.

### Why `unclaimed`, `swept` and `not_derivable` must stay separate

⛔ These three are **never merged**. They answer different questions:

- `unclaimed` is a **partition defect** — a real gap in epic ownership that some
  plan must be made to cover.
- `swept` is a **deliberate crossing** — a plan that declared itself to cross the
  partition covers the module, and no owner is manufactured for it.
- `not_derivable` is a **limit of the derivation** — a spec does name the module,
  in prose the parser cannot resolve to a path or in an entry it named without
  claiming. Ownership may well exist; the tool simply cannot see it.

Folding either into `unclaimed` would report a deliberate crossing or a parser
limitation as a partition defect, manufacturing a disagreement the corpus does
not contain. The
size of the `not_derivable` population is the measure of how much epic ownership
still rests on prose no tool can check — which is why it is reported as a
first-class section, emitted even when empty.

### Root spans

An entry covering the whole population root — bare `test/`, or `test/**` —
discriminates nothing: it names every module. Several specs carry such a span as
passing prose rather than as an ownership claim, and honouring it as a claim
marks the entire tree `contested`, destroying the partition's signal.

Root spans are therefore excluded from claim matching and reported in
`root_claims[]`. The fact is **stated, not silently dropped** — the same
discipline `unresolved[]` follows.

## The plan-lifecycle input

Every rule above reads what a spec SAYS. This one reads whether the plan saying
it is still working — a fact no spec can state about itself, and the **only input
to this derivation that is not the spec corpus**.

**Where the authority comes from.** The epic ledger — `status.json`, beside the
`plans/` corpus in the same epic directory — is the orchestrator's record of the
plan queue, and its per-plan `status` field is authoritative there. This skill
reads it and never writes it, exactly as it reads and never writes the specs.
The ledger read is a **separate loader** from the corpus read: it opens one file,
consults no spec, and resolves no path, so a ledger fact cannot reach the join
dressed as a corpus fact. `classify` — the one verb that answers a
purely-about-the-spec question — does not read the ledger at all.

**What the partition means.** A plan whose work is FINISHED no longer competes
for ownership: its declared surface is a historical record, not a live claim. The
ledger's own status vocabulary is therefore partitioned in two:

| Lifecycle | Statuses | Means |
|-----------|----------|-------|
| `terminal` | `landed`, `shipped` | The work is finished; the surface is a record |
| `active` | `staged`, `running`, `parked` | The work is outstanding; the claim is live |

`parked` is ACTIVE because paused work is unfinished work: a parked plan resumes
onto the surface it declared, so retiring its claim would hand that surface away
while it waits.

⛔ The partition is over the ledger's **own status vocabulary** — never a
hard-coded plan-id list, and never the presence of a landing file. A status the
vocabulary does not cover raises `UnknownPlanStatusError` naming the plan and the
offending value, and the run halts. Bucketing an unrecognised status by guess is
how this input degenerates into the plan list the derivation exists to close, one
level down: defaulting to ACTIVE keeps a finished plan competing, defaulting to
TERMINAL retires a live one, and neither guess is derivable from the vocabulary.

**What the narrowing does.** It narrows a CONTEST and nothing else:

| Claimants | Outcome |
|-----------|---------|
| One, whatever its lifecycle | Untouched — `claimed` by that plan |
| Two or more, exactly one still active | `claimed` by the active plan; the finished plans are recorded in `retired` |
| Two or more, two or more still active | `contested` among the active plans, finished ones recorded in `retired` |
| Two or more, none still active | `contested`, unnarrowed, with nothing retired |

⛔ **An overlap between two ACTIVE plans is deliberately NOT adjudicated.**
Lifecycle narrows the competing set; it never picks a winner among live plans.
Two plans both still working over one module is a real disagreement about future
work that the corpus does not resolve and this tool has no basis to resolve
either — and a rule that quietly picked one would look exactly like a correct
attribution while inventing an ownership no plan has earned. That overlap is the
residual the derivation exists to surface, so it survives every rule.

⛔ **A module every one of whose claimants is finished is not narrowed either.**
This is the same refusal read in the other direction: with no live claimant left
standing there is no one to narrow to, and narrowing to nothing would manufacture
an ownerless module out of one that several plans really did claim.

The retired claims are recorded beside the verdict as a separate fact, in the
same way a sweep crossing is — a claim lifecycle set aside is **stated, never
silently dropped**.

### The degradation path

⛔ A missing or unusable ledger degrades to treating **every plan as active**,
which is the behaviour that held before this input existed, and the degradation
is REPORTED rather than absorbed:

| `degradation` | Cause |
|---------------|-------|
| `ledger_absent` | No `status.json` beside the corpus |
| `ledger_unreadable` | Present, but not readable as JSON |
| `ledger_malformed` | Read, but carrying no usable plan queue — the document is not an object, the queue is not a list, or a row carries no plan id |

Read `available` FIRST. When it is `false` the terminal set is empty because
nothing was read, NOT because every plan is live — the two readings produce the
same partition and claim entirely different things, which is why the reason is
published beside it. A run reporting all-plans-active with a `degradation` set is
in a **declared state, not a defect**; the same output with no reason attached
would be a partition that quietly attributed nothing on no evidence.

An EMPTY plan queue is a read ledger, not a degraded one: an epic with nothing
queued was measured, and reports `available: true` with no degradation.

A plan whose spec is in the corpus but whose row is absent from the ledger keeps
competing — the conservative direction, and the same one the degraded read takes.

## The attribution

`attribution` groups the test-module line-budget findings by owning plan.

The findings are **re-derived from the current tree**. A published baseline is
only ever a post-hoc comparison, never an input; any delta between the two is
reported **per instance** as drift, never as a failure. An absent baseline is
reported as unsupplied rather than as an empty one, so "no baseline given" can
never be read as "nothing drifted".

Every file is attributed exactly once. A `claimed` module is attributed to its
owning slice however many sweeps also cross it. Modules with no single owning
slice land in explicit ownerless buckets rather than being folded into any plan's
total, mirroring the partition's refusal to merge the populations:

| Bucket | Holds |
|--------|-------|
| `<unclaimed>` | Over-budget modules no plan claims |
| `<contested>` | Over-budget modules two or more still-competing slice plans claim |
| `<swept>` | Over-budget modules only self-declared sweeps cover |
| `<not-derivable>` | Over-budget modules named only in unresolved spans or lead-shaped entries |

## The report's sections

`report` renders the sections below, in this order. Each carries the command that
produced it, so every figure can be independently reproduced. The table is the
single statement of what is rendered: no count of it is asserted anywhere, so
adding a section leaves no stale number behind.

| # | Section | Asserts |
|---|---------|---------|
| 1 | `partition` | Every verdict with its population size |
| 2 | `attribution` | Budget findings grouped by owning plan |
| 3 | `disagreements` | Every unclaimed and contested entry **per instance**, not merely counted |
| 4 | `contested` | The residual genuine disagreement, isolated from the rest of `disagreements` |
| 5 | `lifecycle` | The ledger's terminal/active partition, the modules its narrowing attributed, and — when no ledger could be read — the stated degradation |
| 6 | `swept` | The self-declared sweep plans and the modules they cross |
| 7 | `not_derivable` | The modules and the specs the derivation cannot resolve — emitted even when empty |
| 8 | `injected_controls` | The injected-failure demonstrations, each naming the control that demonstrates it |
| 9 | `test_count` | The declared-test count before and after, both by the one static method the section names |
| 10 | `baseline_drift` | The per-instance delta against a supplied baseline, or that nothing was compared |
| 11 | `provenance` | The placement claims and the overlap verdict below |

### What `provenance` must assert

Two things, so neither survives only as prose:

1. **The location the script-architecture standard gave**, with its citation:
   `test/{bundle}/{skill}/` for the test mirror (`testing-standards.md`), and
   `marketplace/bundles/{bundle}/skills/{skill}/scripts/` for the script
   directory (`cross-skill-integration.md`, `python-implementation.md`).
2. **Whether the `marketplace/bundles/**` overlap is live or inert**, naming the
   overlapping entries it derived from the parsed corpus rather than from a
   hand-written list. The section is emitted with an explicit verdict even when
   the overlap set is empty — an omitted section is indistinguishable from one
   that found nothing.

## The escalation path

The `report` subcommand itself writes nothing. After the report is produced, the
executing agent compares the derived partition against the epic's own claim over
the tool's test directory and takes exactly one of two actions, recording which:

- **Contradiction found** → file one `finding` inbox message via
  `orchestrator inbox write` and edit no spec.
- **No contradiction** → no message is owed; the run records that outcome.

`orchestrator inbox list` is the check that shows which branch was taken. No spec
under the orchestrator store is edited under either branch.
