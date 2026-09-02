# Epic Surface Derivation

The model behind `tools-epic-surface-partition`: how a spec's `## Expected
Surface` becomes a typed claim, how those claims partition the real `test/`
tree, and what the report must assert.

## Never a gate

⛔ This tool is a **derivation and report tool, never a CI gate**. The epic specs
live under `.plan/local/orchestrator/`, which is git-ignored and therefore absent
from a fresh clone — no CI check can read them, so no CI check can depend on
them. `report` exits 0 even when it renders disagreements: a rendered
disagreement is the product, not a failure.

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
the line-budget attribution, the CLI surface, and the output contract.

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

## Entry shapes the parser resolves

| Shape | Example | `kind` |
|-------|---------|--------|
| Directory | `test/plan-marshall/manage-config/` | `directory` |
| Recursive glob | `test/pm-plugin-development/**` | `recursive_glob` |
| Filename glob | `plugin-doctor/test_test_conventions_rule*.py` | `filename_glob` |
| Named file | `test/test_runner_falsifiability.py` | `file` |
| Non-`test/` path | `pyproject.toml` | `file` |
| Relative continuation | `.../workflow-integration-github/`, or a bare sibling written after a rooted path in the same bullet | derived from the resolved path |

A relative continuation resolves against the base the bullet's first **rooted**
entry establishes — the directory a recursive glob names, or the parent of any
other shape. Both notations are supported: the explicit `.../` prefix, whose
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
| Cross-plan reference | Another plan's or another slice's identifier in the possessive, in the bullet's CLAIM HEAD | Quotes the cited plan's ownership rather than asserting the citing plan's |
| Hedged conditional claim | A conditional restriction on the claim, or an explicit denial of further coverage | The bullet withdraws the span it just named |

Each rule fires on its own and each is keyed on published grammar or on the
spec's own words — never on any plan identifier, so a spec added to the corpus is
shaped by the same rules with no edit to the reader.

⛔ The cross-plan-reference rule reads the bullet's **claim head alone**, and the
narrowing is load-bearing. A possessive citation in the head says the named span
IS the other plan's surface; the same citation in the trailing commentary
annotates a claim the bullet makes in its own right, and reading it there would
demote most of the corpus.

⛔ The shape is **additive**. It is recorded on the entry and moves nothing: an
entry keeps its membership of `claimed` or `excluded` whatever its shape, and the
spec's class is unchanged by it. What a lead MEANS is the consuming stage's
decision — see [The partition verdicts](#the-partition-verdicts).

## The partition verdicts

`partition` assigns every test module under `test/` exactly one verdict.

| Verdict | Rule |
|---------|------|
| `claimed` | Exactly one SLICE plan's owning entries cover it |
| `contested` | Two or more slice plans cover it — the residual genuine disagreement |
| `swept` | No slice plan covers it, but one or more SWEEP plans do |
| `not_derivable` | No plan's owning entries cover it, but a spec names it in an unresolved span or in a lead-shaped entry |
| `unclaimed` | No plan covers it and no spec names it |

An entry carries OWNERSHIP unless one of three independent rules removes it: the
spec declares itself a sweep, the entry is lead-shaped, or the spec's class is
`derived`.

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

⛔ A spec that QUOTES a sibling's crossing declaration while claiming an ordinary
slice is not itself a sweep. The marker deliberately does not read the phrasing an
analysing spec quotes when it cites another plan.

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
| `<contested>` | Over-budget modules two or more slice plans claim |
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
| 5 | `swept` | The self-declared sweep plans and the modules they cross |
| 6 | `not_derivable` | The modules and the specs the derivation cannot resolve — emitted even when empty |
| 7 | `injected_controls` | The injected-failure demonstrations, each naming the control that demonstrates it |
| 8 | `test_count` | The declared-test count before and after, both by the one static method the section names |
| 9 | `baseline_drift` | The per-instance delta against a supplied baseline, or that nothing was compared |
| 10 | `provenance` | The placement claims and the overlap verdict below |

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
