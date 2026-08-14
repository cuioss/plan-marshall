> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# CI and supply-chain hardening — a template-injection surface and an unscoped token

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Ten `.github/` and packaging findings survive re-verification. **Two are security-relevant and lead the
plan:**

- **A template-injection surface in a `contents: write` workflow.** A tag-creating step interpolates
  `${{ github.ref_name }}` **directly into a bash `run:` block** that runs git commands. **Ref names can
  carry shell metacharacters** — a classic injection shape.
- **A workflow with no `permissions:` block at all**, so its token inherits the repository or
  organisation default — potentially read-write — for a job that only runs a generator.

The rest are least-privilege, trigger-topology, and packaging hygiene. **One component, one PR.**

⛔ **And three of them turn on something not visible from inside the repository: the branch-protection
ruleset.** Whether code-owner review is required, and which checks are required, decide whether adding
an owners file enforces anything and whether narrowing permissions wedges a gate. ⛔ **Changing workflow
permissions against a guessed ruleset is how a required check wedges.**

## Goal

No workflow interpolates untrusted context into a shell, every workflow declares the least privilege it
needs, the required-check topology is settled against the actual ruleset rather than a guess, and CI
stops running the full suite twice per push.

## Deliverables

1. **D1 — Close the template-injection surface.** Pass the ref via `env:` and reference it as a quoted
   shell variable.
   *Done when:* no context expression appears inside a `run:` block in that workflow.
   ⛔ **Never interpolate a context into a shell.** This is the rule, not just this instance's fix.
2. **D2 — Add a least-privilege `permissions:` block to the generator-check workflow.**
   *Done when:* it declares read-only content access.
3. **D3 — Narrow the distribution workflow's workflow-wide write scope.** Pushes use a separate token,
   so the default token's write scope is **unnecessary breadth on checkout and generate steps.** Default
   to read; grant write **per step**.
   *Done when:* the workflow-level default is read.
4. **D4 — GATE: settle the ruleset question ONCE, then act on the three items that depend on it.**
   - Whether a code-owners file would enforce anything (it does not exist today).
   - Whether the path-filtered generator check is, or should be, a required check — ⛔ **if it is ever
     made required, PRs not touching those paths wait FOREVER.**
   - Whether the verify workflow's read-only grants silently degrade a reusable workflow that posts
     coverage or annotations.
   *Done when:* the ruleset's actual requirements are known, and all three are decided together.
   ⛔ **These are DECISIONS, not fixes, and the ruleset is NOT visible in the repository.** ⛔ **ASK; do
   not assume.** ⚠ **If the answer cannot be obtained in this run, RECORD A PROPOSAL** naming each option
   and its consequence, and **do not change the permissions blind.**
5. **D5 — Stop the duplicate CI runs.** For a working branch with an open PR, **both the push and
   pull-request triggers fire, running the full verify suite twice per push.** Add a concurrency group,
   or drop the push trigger for those prefixes.
   *Done when:* one push produces one verify run.
   ⭐ **A straight compute saving with no behaviour change** — but see the blast-radius warning below.
6. **D6 — Fix the vendored wrapper's install fallback.** A non-Windows fallback splices a PowerShell
   cmdlet into a `curl` line, breaking that path.
   *Done when:* the fallback works.
   ⚠ **This is upstream wrapper code.** ⛔ **Prefer regenerating from a fixed upstream release over
   hand-patching a vendored file — and RECORD which was done.**
7. **D7 — Reconcile the three private-contact channels.** Vulnerability email, commercial licensing, and
   the licence file's pointer currently route three different ways.
   *Done when:* they cross-reference each other consistently.
   ⛔ **Confirming the security mailbox is actually monitored is an OPERATOR action, not a code change.**
   **The plan must not report it as done** — record it as owed.
8. **D8 — Decide on a PR template.** One does not exist, while the contributing guide assumes one may.
   *Done when:* **the decision is recorded either way.** ⛔ **Optional — drop it if a template is not
   wanted**, but do not leave the question open.
9. **D9 — A workflow-lint control where testable.** The `env:`-passing form and the permissions block are
   **assertable**.
   *Done when:* a lint check asserts them, **rather than relying on review**.
   ⭐ This is the deliverable that stops D1 and D2 from silently regressing.

Nine deliverables, under the raised cap.

## Out of scope

- **A dependency-lock refresh.** An earlier finding reported the lock file locking **zero** dependencies
  while the build invoked a locked runner. ✅ **It has since been fixed** — refreshed during an unrelated
  change, as an operator decision. ⭐ **An unrelated plan closed a review finding nobody had connected to
  it.** Recorded **so it is not re-filed**.
- **Changing what the verify workflow verifies.** This plan changes permissions, triggers, and
  injection safety — never the build's content.
- **Contacting the security mailbox owner.** See D7. Outside the run's reach.

## Expected surface

- `.github/workflows/claude-distribute.yml` — the injection surface and the write scope.
- `.github/workflows/opencode-generate-check.yml` — the missing permissions block and the path filter.
- `.github/workflows/python-verify.yml` — the grants and the trigger topology.
- `.github/` — a possible owners file and PR template.
- `SECURITY.md`, `LICENSE.md` — the contact channels.
- The vendored build wrapper.
- A workflow-lint check (D9).

⛔⛔ **The verify workflow is the file every plan's CI depends on. A mistake here breaks the merge gate
for every other plan in flight.** Treat the trigger and permission items as **the highest-blast-radius
work in the plan.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Two context interpolations sit inside a `run:` block in a write-scoped workflow | HYPOTHESIS | that workflow — **cheap, exact, and the highest-severity item** |
| The generator-check workflow has no `permissions:` block | HYPOTHESIS | that file — an asserted **absence**, verified as a presence |
| The distribution workflow declares workflow-wide write | HYPOTHESIS | that file |
| No code-owners file exists | HYPOTHESIS | the `.github/` directory — asserted **absence** |
| The generator check is path-filtered | HYPOTHESIS | its trigger block — ⛔ **the fact that makes "required check" dangerous** |
| The verify workflow grants only read scopes | HYPOTHESIS | that file — and then: **does the reusable workflow it calls need more?** |
| Both triggers fire for a working branch with an open PR | HYPOTHESIS | both trigger blocks — ⭐ **derivable entirely from the workflow files** |
| The vendored wrapper's fallback splices the wrong command | HYPOTHESIS | that file — cheap and exact |
| The three contact channels diverge | HYPOTHESIS | those documents |
| No PR template exists | HYPOTHESIS | asserted **absence** |
| **What the branch-protection ruleset actually requires** | HYPOTHESIS | ⛔⛔ **NOT ESTABLISHED and NOT VISIBLE IN THE REPOSITORY.** Three deliverables turn on it. **ASK; do not assume** |
| The security mailbox is monitored | HYPOTHESIS | ⛔ **cannot be settled from the repository at all.** Record as owed |
| The lock-file finding is fixed | HYPOTHESIS | that file — ⛔ **re-verify before relying on the exclusion** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1's fix must be verified against a ref name containing a shell metacharacter**, not merely by
  reading the changed YAML. The point is that the value cannot escape the variable.
- ⛔ **D4's outputs must be explicit in the report — decided or proposed, per item.** ⛔ **Changing a
  required-check topology on a guess is the one action in this plan that can wedge every other plan's
  merge gate.**
- ⛔ **D5 must be verified by observing a single verify run on this plan's own PR** — this plan is its own
  fixture, which is the cheapest available check and the only one that exercises the real triggers.
- **D9's lint check must be seen to fail** on a deliberately re-introduced interpolation, then pass.
- ⚠ **Land this in a quiet window.** The trigger and permission changes alter the checks a PR produces,
  and **a plan in its merge window could see its required check disappear or duplicate.** ⛔ **Do not run
  concurrently with a plan that is mid-merge.**
- Workflow and documentation changes are expected; confirm the build gate's path from git evidence.

## Notes

- ⭐ **Two security items lead the plan deliberately.** If the run has to stop early, D1 and D2 are the
  two that should have landed.
- ⛔ **Do not go looking for the orchestrator spec, the retired review document, or any landing record.**
  The first and last live under `.plan/`; the review is being retired and its surviving findings are
  transcribed above. Everything needed is in this file — **except the ruleset, which is named as
  unreachable rather than guessed at.**
