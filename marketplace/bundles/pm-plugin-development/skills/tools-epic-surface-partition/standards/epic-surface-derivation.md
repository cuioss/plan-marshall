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

## The three-class model

`classify` assigns every spec exactly one class and records the evidence for the
verdict beside it.

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

## The four partition verdicts

`partition` assigns every test module under `test/` exactly one verdict.

| Verdict | Rule |
|---------|------|
| `claimed` | Exactly one plan's resolved entries cover it |
| `multiply_claimed` | More than one plan covers it |
| `not_derivable` | No plan's resolved entries cover it, but a spec names it in an unresolved span |
| `unclaimed` | No plan covers it and no spec names it |

Exclusions subtract from the claiming plan's **own** set only. A plan that claims
a recursive glob while excluding a sub-directory does not claim the modules under
it; another plan's claim over those same modules is unaffected.

### Why `unclaimed` and `not_derivable` must stay separate

⛔ These two are **never merged**. They answer different questions:

- `unclaimed` is a **partition defect** — a real gap in epic ownership that some
  plan must be made to cover.
- `not_derivable` is a **limit of the derivation** — a spec does name the module,
  in prose the parser cannot resolve to a path. Ownership may well exist; the
  tool simply cannot see it.

Folding `not_derivable` into `unclaimed` would report a parser limitation as a
partition defect, manufacturing a disagreement the corpus does not contain. The
size of the `not_derivable` population is the measure of how much epic ownership
still rests on prose no tool can check — which is why it is reported as a
first-class section, emitted even when empty.

### Root spans

An entry covering the whole population root — bare `test/`, or `test/**` —
discriminates nothing: it names every module. Several specs carry such a span as
passing prose rather than as an ownership claim, and honouring it as a claim
marks the entire tree `multiply_claimed`, destroying the partition's signal.

Root spans are therefore excluded from claim matching and reported in
`root_claims[]`. The fact is **stated, not silently dropped** — the same
discipline `unresolved[]` follows.

## The attribution

`attribution` groups the test-module line-budget findings by owning plan.

The findings are **re-derived from the current tree**. A published baseline is
only ever a post-hoc comparison, never an input; any delta between the two is
reported rather than silenced.

Every file is attributed exactly once. Modules with no single owning plan land in
three explicit buckets rather than being folded into any plan's total, mirroring
the partition's refusal to merge the populations:

| Bucket | Holds |
|--------|-------|
| `<unclaimed>` | Over-budget modules no plan claims |
| `<multiply-claimed>` | Over-budget modules more than one plan claims |
| `<not-derivable>` | Over-budget modules named only in unresolved spans |

## The report's seven sections

`report` renders all seven, in this order. Each carries the command that produced
it, so every figure can be independently reproduced.

| # | Section | Asserts |
|---|---------|---------|
| 1 | `partition` | The four verdicts with their population sizes |
| 2 | `attribution` | Budget findings grouped by owning plan |
| 3 | `disagreements` | Every unclaimed and multiply-claimed entry **per instance**, not merely counted |
| 4 | `not_derivable` | The modules and the specs the derivation cannot resolve — emitted even when empty |
| 5 | `injected_controls` | The injected-failure demonstrations, each naming the control that demonstrates it |
| 6 | `test_count` | The declared-test count before and after, both by the one static method the section names |
| 7 | `provenance` | The placement claims and the overlap verdict below |

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
