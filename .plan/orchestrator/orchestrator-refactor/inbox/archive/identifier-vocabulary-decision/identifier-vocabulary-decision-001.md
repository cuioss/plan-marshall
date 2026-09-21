envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=finding
created=2026-09-19T17:04:14Z
revision=1
amended=2026-09-19T17:07:49Z

# PLAN-05 execution brief — the identifier-vocabulary rename

Handed over by PLAN-04, which decided the vocabulary (ADR-023) and amended the
governing rules, and renamed nothing. Everything below is derived from this
repository's state at PLAN-04's head; every figure names the population it was
computed over.

## 1. Sized surface

**Population**: git's own tracked-and-not-ignored path set — 3207 files, of
which 1929 are Python and 1074 are prose (`.md`, `.adoc`, `.json`, `.yml`,
`.yaml`, `.txt`). Zero files were unreadable, so the counts below have clean
coverage.

Occurrences are partitioned by the **marshalling family** the spelling appears
in, because each family needs a different edit and a different sweep:

| Family | What it is | Files |
|---|---|---:|
| A. argparse declaration | `add_argument('--flag'` in a bundle script | 8 |
| B. Python-marshalled | the `'--flag'` literal elsewhere in Python (subprocess argv, accept-set literals, test fixtures) plus the `ns.attr` / `args.attr` destination argparse derives | 29 |
| A ∪ B — **source files to touch** | | **31** |
| C. prose-marshalled | the `--flag` token in a doc, excluding PLAN-04's own two artifacts, which discuss the spellings rather than invoke them | **43** |
| A ∪ B ∪ C — **total files to touch** | | **76** |

Per retired spelling (declaration sites / Python files / prose files):

| Retired | Decided | A | B | C |
|---|---|---:|---:|---:|
| `--slug` | `--epic` | 2 | 18 | 21 |
| `--slug-value` | `--plan-slug` | 1 | 3 | 4 |
| `--plan` | `--plan-id` | 1 | 5 | 2 |
| `--target-plan` | `--plan-id` | 1 | 1 | 3 |
| `--transition` | `--plan-id` + mode split | 1 (orchestrator only) | 5 | 7 |
| `--set-row` | `--plan-id` + mode split | 1 | 2 | 5 |
| `--add-row` | `--plan-id` + mode split | 1 | 3 | 6 |
| `--name` | `--module` / `--component` at 4 of 9 sites | 5 | 9 | 23 |

`--slug` dominates: 286 Python occurrences across 18 files, 15 of them test
modules under `test/plan-marshall/plan-orchestrator/`. The rename is mostly a
test-suite migration, not a source edit.

### The request's flagged floor is NOT reproduced — and it measures a different set

The originating request carried a flagged floor of **38 source files / 215 doc
files**. Neither figure is reproducible from the request, because the set
behind it is not stated. Measuring both candidate sets:

| Set | Source files | Prose files |
|---|---:|---:|
| The **rename** surface (the retired spellings above) | 31 | 43 |
| The **`--plan-id` incumbent** surface (NOT renamed) | 32 declaring, 424 mentioning | 229 |

The floor's magnitude matches the **incumbent** surface, not the rename
surface. `--plan-id` is the spelling ADR-023 decision (b) explicitly keeps at
all 282 of its argparse sites, so if the 215 figure was the intended rename
scope, that scope is refuted by the decision rather than merely re-measured.

⛔ **Do not size PLAN-05 from 38 / 215.** Use 31 source files and 43 prose
files, and re-derive them at PLAN-05's own head — the harness is
`.plan/temp/d4_size_surface.py` in PLAN-04's worktree, which is a throwaway and
will not survive; the method is a `git ls-files` walk plus the three
family-specific regexes above.

### One false member the sweep must exclude

`--transition` is declared on **two unrelated parsers**:

- `plan-orchestrator:orchestrator queue --transition PLAN-NN` — "Plan id to
  transition". **In the rename set.**
- `workflow-integration-sonar:sonar_rest transition --transition
  {accept,falsepositive,wontfix}` — "Transition to apply". A selector enum that
  names no entity. **NOT in the rename set, and renaming it is a defect.**

A spelling-level sweep over `--transition` hits both. Every `--transition` edit
must be scoped to `orchestrator.py` and its tests.

## 2. Ordering — the constraint that makes PLAN-05 non-trivial

`ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` cross-checks each canonical-forms row
in `argument-naming.md` against the live argparse declaration of the script the
row prescribes, and it is **build-failing**. Any window in which the two
disagree fails `quality-gate`.

**The argparse declaration and its canonical-forms row move in the SAME
commit.** The natural "rename everything, then fix the docs" sequence is
forbidden: it fails the gate on every commit between the two halves. So is its
mirror ("fix the table first").

### The gate's real reach is narrower than the table — derived, not assumed

Running the rule's own parser (`_parse_canonical_forms`) over the amended
`argument-naming.md`:

- **71** data rows live under `## Canonical Forms`.
- The rule cross-checks **30** of them.
- **41 are not cross-checked at all.**

The parser matches only a three-column row whose third cell is a *lone*
backticked form. Excluded by construction:

- the three `manage-*` rows carrying trailing prose after the backticks (the
  `(alias: …)` rows for `manage-lessons`, `manage-status`, `manage-tasks`);
- every row of the three two-column per-script tables — `git-workflow` (9
  rows), `ci` (22 rows), `doctor-marketplace` (7 rows).

Two consequences for PLAN-05, in opposite directions:

1. The same-commit constraint **binds only those 30 rows**. The other 41 may be
   updated in a separate commit without failing the gate.
2. Those 41 rows also **rot silently**. Nothing will tell PLAN-05 it missed
   one. They need the manual sweep in section 3, and the owning script's
   `## Canonical invocations` section is authoritative where the two disagree.

### Suggested commit shape

One commit per script whose argparse changes, each carrying: the
`add_argument` edits, the `ns.attr` / argv-literal updates in that script's own
module, that script's tests, its `## Canonical invocations` block, and any
canonical-forms row the rule cross-checks for it. Prose-only files that merely
document the flag may follow in a separate commit.

`orchestrator queue` is the exception: it is a redesign, not a substitution
(see section 4), and warrants its own commit.

## 3. Survivor-sweep method

ADR-007 records that **no rename-survivor detector exists**, that building one
is deliberately deferred, and that any future one derives its inputs
git-natively via `list_tracked_files` / `hash_objects` — **never by parsing
unified-diff text** (the abandoned approach, rejected because diff text is a
presentation format, not a data model).

PLAN-05 therefore cannot rely on a gate to prove completeness, and must prove
it itself.

### What the existing gates DO cover

- `ARGUMENT_NAMING_FLAG_UNKNOWN` sweeps every `python3 .plan/execute-script.py`
  invocation in marketplace markdown against the live argparse surface. A
  **documented invocation** left on a retired spelling is caught — that is the
  deleted-CLI-flag survivor class ADR-007 names as already owned.
- `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` covers the 30 rows above.

### What they do NOT cover — the residual PLAN-05 owns

Mapped onto ADR-007's survivor taxonomy (a rename is a deletion plus an
addition, so it reduces to the deleted-symbol class):

| Residual | Why no gate sees it |
|---|---|
| Family B — Python-marshalled argv | The rules scan markdown only. A `'--slug'` literal in a subprocess argv or a test fixture is invisible to them, and it is the LARGEST family (286 occurrences for `--slug` alone). |
| The 41 uncovered canonical-forms rows | Outside the drift parser's row shape. |
| Prose that NAMES a flag without invoking it | The extractor keys on the executor-invocation shape, so a sentence mentioning `--slug` in running text is never examined. |
| `doc/` and `.claude/` prose | Outside the rules' markdown corpus, which is `marketplace/bundles/*` only. |

### The method

Run at PLAN-05's head, after the last rename commit, git-natively:

1. Enumerate the path universe with `git ls-files` — git's own
   tracked-and-not-ignored set, the `list_tracked_files` primitive ADR-007
   names. No custom filter, no diff text.
2. For each retired spelling, sweep all three families with the
   family-specific patterns in section 1, over that whole universe — not over
   the changed files, since a survivor by definition lives in a file the change
   never touched.
3. **Expect zero, and publish the population.** A zero hit count is only
   evidence when the run states how many files it read and how many it could
   not (ADR-019). A sweep that reports `0` without its population is
   indistinguishable from a sweep that read nothing.
4. Subtract the two legitimate residues before declaring clean: ADR-023 itself
   and this brief both *discuss* the retired spellings, and both must keep
   naming them. Any other hit is a survivor.
5. `sonar_rest --transition` stays. It is expected in the `--transition` sweep
   and is not a survivor.

⛔ Do NOT build a detector for this. ADR-007 decided no new gate, and a
one-shot sweep script under `.plan/temp/` is the sanctioned shape.

## 4. `orchestrator queue` is a redesign, not a substitution

On one subparser the epic is `--slug` while the plan is spelled four ways:
`--transition PLAN-NN`, `--set-row PLAN-NN`, `--add-row PLAN-NN` (three
mutually exclusive **mode selectors that each carry a plan id**) and
`--slug-value SLUG` (the plan's slug).

Renaming all three mode selectors to `--plan-id` is a duplicate option string
on one parser — an `argparse.ArgumentError` at construction — and would erase
the mode. The identity must be separated from the mode: promote the mode to a
verb (`queue transition` / `queue set-row` / `queue add-row`, each taking
`--plan-id`), or keep one explicit mode flag alongside a single `--plan-id`.

### The orchestrator carries TWO plan-identifier vocabularies, not one

Observed while transmitting this brief: `orchestrator inbox write --sender-id`
rejects `PLAN-04` with `invalid_sender_id` and demands `^[a-z][a-z0-9-]*$` —
the plan-marshall kebab plan id. Meanwhile `orchestrator queue --transition`,
`--set-row` and `--add-row` all take `PLAN-NN`, and the queue's own `--field`
choices include `plan_marshall_plan_id` as a settable row field.

So the orchestrator holds two distinct plan identities — the **epic-local**
`PLAN-NN` ordinal and the **plan-marshall** kebab id — and spells them
inconsistently across its own verbs. ADR-023's suffix set covers this
(`--plan-id` for the kebab id; the epic-local ordinal is a *different value for
the same entity* and needs its own spelling), but PLAN-04 did not enumerate
which orchestrator verb wants which. **PLAN-05 must decide that per verb before
renaming anything on `orchestrator`** — a sweep that maps both to `--plan-id`
would silently accept the wrong identity at half the call sites, and the
validator above only catches it on the one verb that happens to validate.

`platform_runtime session push-title-token` is the other site that needs care,
and ADR-023 records it as a named Consequence: `--plan-id` and `--slug` are
declared on the same parser, mutually exclusive by the `--store` value rather
than by argparse, and **not jointly required**. Under the decision it becomes
`--plan-id` and `--epic` — two distinct option strings — so the `--store`-keyed
validation is unchanged. That parser is built lazily inside a hand-rolled
operation dispatcher whose top level rejects `--help`, so **no live-derivation
instrument in the tree can see it**; PLAN-05 must take it from source.

## 5. Coverage caveat carried forward

PLAN-04's population was derived by running every registered notation's own
`--help` through `script-shared`'s `argparse_surface`: 159 registered
notations, **111 derived**, **48 `NotDerivable`** — all with reason code
`help_failed`. Of the 48, 43 declare no argparse at all (shared library modules
registered as notations), and 5 do. Only one is material:
`plan-marshall:platform-runtime:platform_runtime`, whose hand-rolled dispatcher
hides 30 long flags including one of the two `--slug` declaration sites.

Any re-derivation PLAN-05 performs inherits that gap. Report it as an
unevaluated cell per ADR-019; do not let a clean derived count stand in for a
complete one.

### Two "registered notations" counts exist — reconciled here so they are not read as a contradiction

PLAN-04 reports **159 / 111 derived / 48 NotDerivable**. The plugin-doctor
argument-naming corpus over the same tree reports **165 / 117 derivable / 48
omitted**. Both are correct; they count different domains:

- **159** is `generate_executor.discover_scripts` over `marketplace/bundles/` —
  the notation set this rename is scoped to.
- **165** is the executor's own `SCRIPTS` literal, which additionally carries 6
  project-local `default-bundle:` notations from `.claude/skills/`
  (`audit-archived-plan-retrospectives`, `finalize-step-era-stamp-fill`,
  `finalize-step-review-retrospective`, and three `sync-plugin-cache` scripts).

The inventory set is a strict subset of the registry — zero notations are in the
inventory but absent from the registry. The 6 extras are meta-project-only,
live outside `marketplace/bundles/`, and are **not** in the rename surface. The
`48` is identical on both sides, so the coverage gap above is the same gap in
either framing.

## 6. Independent check already performed at PLAN-04's head

The whole-tree argument-naming corpus — the assertion
`test_argument_naming_real_tree_corpus.py` makes — was run directly against
PLAN-04's head after the `argument-naming.md` amendment landed:

```text
substrate_status: present   markdown_targets: 657   invocations: 2955
registered_notations: 165   derivable_surfaces: 117 non_derivable_omitted: 48
blind_spots: 312            findings: 0
```

It was run directly because that test lives in `pm-plugin-development`, whose
`module-tests` resolve to an orchestrator-tier build (963s, above the Bash
ceiling) that a dispatched leaf may not run.

⚠ **That asymmetry is itself a finding PLAN-05 inherits.** `argument-naming.md`
is attributed by `which-module` to **`plan-marshall`**, but the test that
actually exercises it lives in **`pm-plugin-development`**. A module-scoped gate
on the attributed module would not have run it. PLAN-05 touches the same file
and the same cluster, so its per-deliverable gate must cover
`pm-plugin-development` explicitly rather than rely on the attributed module.

Relatedly, `manage-config build-decision` returns `not_necessary` for a
footprint of only `.md` / `.adoc` files, and the freshness gate then returns
`exempt`. That verdict is correct about *buildable artifacts* and blind to this
risk: a markdown edit can fail a real-tree test while no build_map glob is
touched. Do not read `exempt` as "nothing could break".
