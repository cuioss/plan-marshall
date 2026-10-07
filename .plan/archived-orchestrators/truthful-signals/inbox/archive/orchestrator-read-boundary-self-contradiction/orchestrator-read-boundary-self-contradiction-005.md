envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:10:10Z

component=plan-marshall:execution-context
category=bug
created=2026-07-28
bundle=plan-marshall

# A dispatched execution-context leaf has no documented working broad-search path

## What happened

Observed across every dispatch in this plan's run, and NOT fixed (out of scope for
PR #1040). Recording it because it silently caps the coverage of every sweep-class
deliverable.

Three facts hold simultaneously:

1. **`Grep` and `Glob` were denied to every dispatched subagent this session.** The
   `execution-context` agent declares them in `tools:`, but the runtime grant was
   narrower — which the agent body itself anticipates ("the harness MAY deny them to a
   subagent").
2. **Bash `grep` / `find` are hook-blocked unconditionally**, by the project's
   "No shell file operations" hard rule and its enforcement hook — explicitly, per the
   agent body, *not* a fallback whether or not `Grep`/`Glob` were granted.
3. **The documented fallback cannot do the job.** `architecture find --pattern P`
   queries the structured inventory (registered scripts/modules); it does not do
   free-text content matching across markdown and AsciiDoc prose. `Read` scans inside an
   *already-known* file. Neither answers "which documents in this repo restate sentence
   S".

So a leaf asked to perform a content sweep has, on paper, **no permitted primitive that
can perform it**. This plan's D2 sweep completed only via `git grep` — Bash `git`, which
is sanctioned (git operations are an explicit Bash carve-out) and therefore not caught by
the file-operation hook. That path is nowhere documented as the sweep primitive; it was
improvised.

## Solution

Pick one and document it — the current state is a contract with no satisfying assignment:

- **Grant `Grep` to `execution-context` leaves** at the harness level, so the declared
  tool surface and the granted surface agree; or
- **Document `git grep` as the sanctioned broad-content-sweep primitive** for dispatched
  leaves, in `persona-plan-marshall-agent` § "Bash: No file operations" as an explicit
  carve-out alongside the existing git carve-out, and reference it from the
  `execution-context` runtime-tool-availability section.

Either way, the `execution-context` body's degradation instruction needs to name a
primitive that actually works. Today it says: perform discovery through the structured
architecture inventory, scan known files with `Read`, and *"when a deliverable genuinely
needs a broad content sweep that the structured queries and `Read` cannot cover, the leaf
MUST NOT silently degrade to spot-checks — it returns the coverage gap to the
orchestrator."* Taken literally with no working primitive, **every** sweep-class dispatch
should be bouncing back to the orchestrator, and none are.

## Impact

On-theme for `truthful-signals`, and structurally so. A leaf that returns
`"42 candidates examined, 0 findings"` without a working search primitive is emitting a
confident coverage signal whose caveat — *the sweep was a sample, not an enumeration* —
is invisible at the return site. This is the same shape as the recorded
**volume-read-as-coverage** archetype ("250 candidates examined" is a volume, not a
coverage number), but with a *tooling* root cause rather than a reporting one: here the
leaf could not have enumerated even if it intended to.

The compounding risk: the epic's remaining plans are largely sweep-class (doc-contract
reconciliation, SSOT-drift detection). Every one of them will hit this. It is worth
fixing before staging more of them, not after.

**Related but distinct** — do not merge: the harness-denial of `Grep`/`Glob` is a
*runtime grant* problem; the hook-block of Bash `grep` is a *deliberate project rule*
working as designed. The defect is the absence of a documented intersection, not either
constraint individually.
