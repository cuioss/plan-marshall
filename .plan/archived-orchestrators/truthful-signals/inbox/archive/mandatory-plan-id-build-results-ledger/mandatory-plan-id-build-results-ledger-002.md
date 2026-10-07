envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:27:32Z

## Finding: `detect-artifacts` offers a RUNNING plan's own live artifacts as safe-to-delete

**Observed in**: main, during finalize of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.
**Relates to**: `PLAN-TRUTH-017`.

### What was observed

`detect-artifacts` returned **556 entries in `safe[]`** — not in `uncertain[]` — while
`git status --porcelain` was simultaneously silent. The classifier was therefore offering
a live, running plan's own working artifacts for deletion with full confidence, at the
exact moment the tree looked clean.

### Root cause — narrower than first hypothesized

The initial hypothesis (a broad safe-pattern over-reach) is wrong. The actual mechanism is
a **two-part defect**:

1. `git ls-files --others --ignored --exclude-standard` **cannot see inside NESTED git
   repos**. pytest fixture repos created under `.plan/temp/` are themselves git repos, so
   their contents are invisible to the outer repo's ignored-file enumeration and never
   pick up the gitignore-derived exclusion the classifier relies on.
2. Having escaped that exclusion, those paths then match the **explicit `".plan/temp/**"`
   safe pattern** and are promoted into `safe[]`.

Neither half is sufficient alone: the nested-repo blindness only matters because a broad
explicit safe pattern is waiting downstream to catch what the exclusion missed.

### Why it is on-theme

This is a confident-signal-hides-a-caveat instance in its purest form. `safe[]` vs
`uncertain[]` is precisely the "I know" vs "I cannot tell" discriminator, and the
classifier put 556 items it could not actually see into the *confident* bucket. The
correct verdict for a path the enumeration structurally cannot inspect is `uncertain`,
never `safe`.

### Suggested shape of a fix (not implemented)

- Detect the nested-repo case explicitly rather than inheriting the enumeration's silence,
  and route anything the ignore-enumeration could not inspect to `uncertain[]`.
- Re-examine whether an explicit `.plan/temp/**` safe pattern should be able to override
  an *unknown* classification at all, as opposed to only a *known-ignored* one.
