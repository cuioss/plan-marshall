# PLAN-CIS-001: Content Search Is Not a Capability, and the Prescribed Remedy Is Unavailable to Leaves

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The substrate can answer "which files match this path glob" but not "which files contain this
string". `CLAUDE.md` prescribes the `Grep` tool as the remedy for content search — satisfiable in
main context, but **revoked at runtime for dispatched leaves**, while the bare-`grep` prohibition
stays enforced against them. Leaves fall back to `git grep`, which is documented **nowhere**.

Give the substrate a first-class content-search capability, delivered as a **script seam** so it
reaches dispatched leaves without any harness or tool-permission change.

## Deliverables

1. A content-search verb on `manage-architecture` (`search --content` or equivalent) backed by
   `git grep`, returning module-attributed, category-attributed hits in the same shape `find`
   returns path hits.
2. Point `CLAUDE.md`'s no-shell-file-ops rule at the **new verb** as the content-search remedy, so
   the prohibition names an available path rather than a revoked one.
   ⛔ **`git grep` is NOT documented as a primitive — it is ELIMINATED as a practice.** It becomes an
   implementation detail *inside* the script and appears in no operator-facing or agent-facing doc.
   Documenting it would promote an improvisation into sanctioned practice and permanently entrench
   the incoherence below.
3. **Close the carve-out once the replacement exists.** Today `git grep` passes the enforcement hook
   only because it rides the incidental git allowance, while bare `grep` is blocked — a distinction
   resting on which binary is invoked, not on any principle. Decide and implement whether the hook
   should treat `git grep` as a file operation once a sanctioned verb exists.
   ⚠ **HYPOTHESIS, and it must be settled before implementing**: that `git grep` can be blocked
   without collateral damage to legitimate git usage. Confirm/refute against the hook's actual
   matching rules (verify-at-outline). If it cannot be cleanly separated, the fallback is an explicit
   documented deprecation rather than an enforced block — but **do not silently leave the carve-out
   open and undocumented**, which is exactly today's state.
4. **DO NOT REINTRODUCE THE `git grep` CARVE-OUT.** ✅ **PR #1046 was CLOSED WITHOUT MERGING**
   (verified 2026-07-29: absent from the open-PR list; operator confirms `state: CLOSED`,
   `mergedAt: null`, `mergeCommit: null`; branch, remote branch and worktree removed; recorded as
   **closed-superseded, not shipped**). **Nothing from it reached `main`, so there is NOTHING TO
   REMOVE** — this deliverable inverts from *retire the carve-out* to *do not recreate it*.
   ⛔ The escalation contract in `agents/execution-context.md` — leaf returns the coverage gap to the
   main-context orchestrator — **is intact on `main` and stays primary** until deliverable 1 ships a
   real replacement. The surfaces below are recorded as the **blast radius any future carve-out would
   have to touch**, i.e. the list this plan must keep clean, NOT a removal worklist:
   - `CLAUDE.md` — the carve-out clause on the no-shell-file-operations rule
   - `AGENTS.md` — the mirrored clause
   - `marketplace/bundles/plan-marshall/agents/execution-context.md` — `git grep` promoted to primary,
     orchestrator escalation demoted to "residual path only"
   - `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` (+16) —
     § "Bash: No file operations"
   - `.../persona-plan-marshall-agent/standards/tool-usage-patterns.md` (+30) — § "Broad content sweep"
   - `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md`
   - `test/.../test_leaf_content_sweep_primitive_contract.py` (225 lines) and
     `test_claude_pretooluse_hook.py` (+9) — the two tests that would have **pinned** the carve-out.
     ⭐ Never merged, so test-pins-the-defect was **avoided, not repaired** — the cheapest possible
     outcome, and the reason closing beat merge-then-revert.

   ⚠ **The surface list above is a SAMPLE, not an enumeration.** #1046's own retrospective found
   **four** surfaces restating the old contract, and **two were not named in its request** —
   `ref-workflow-architecture/standards/agents.md` and `AGENTS.md`, the latter a **hand-maintained
   mirror that no sync step updates**. ⛔ This plan MUST derive the population of contract-restating
   surfaces rather than trusting any list, including this one.
5. Correct the `find` verb's advertised contract so it is unambiguous that it is a **path glob** and
   points to the content verb for content questions.
6. **Documentation across all three trees.** `doc/user/` — how to search code and docs, so the
   capability is discoverable by an operator rather than only by an agent. `doc/concepts/` — extend
   the substrate page PLAN-02 creates with content search as the Tier 0 capability it is.
   `doc/user/enforcement-hook.adoc` — the rule change from deliverables 2-3.
   ⛔ **No doc in any tree names `git grep` as a way to search.** ⛔ Ship docs **in this plan**.

⛔ **AT 6 DELIVERABLES THIS SPEC IS AT THE SPLIT GUARD AND SHOULD PRESUMPTIVELY SPLIT.** It grew from
3 to 6 in one session as the carve-out scope emerged. The natural cut is **capability** (D1, D5, D6)
from **carve-out retirement** (D2, D3, D4) — and the second half is only actionable once #1046's fate
is known, which is an argument for splitting rather than blocking the capability behind it.
**Re-evaluate at outline; proceeding unsplit requires a recorded decision.**

## Ordering constraint against PR #1046

⚠ **Deliverable 4 is CONDITIONAL and its condition must be re-read at outline** — do not scope it
from this spec's snapshot:

- **If #1046 is still open** — deliverable 4 may be unnecessary. Closing the PR is cheaper than
  merging then reverting six surfaces and two tests, and this plan then only has to avoid
  *reintroducing* the carve-out. **Escalate to the operator; do not decide this inside the plan** —
  it is another epic's PR.
- **If #1046 has merged** — deliverable 4 is live exactly as scoped above.
- ⛔ **In BOTH cases the ordering is the same**: the carve-out may only be retired once deliverable 1
  ships a working replacement. Removing it first would leave dispatched leaves with **no** content
  search at all, which is strictly worse than the carve-out and is the state #1046 was written to fix.
  The pre-#1046 escalation contract (leaf returns the coverage gap to main context) is the correct
  interim answer and this plan restores it as primary.

## Claim Labels

- **OBSERVED, and deliberately DE-EMPHASISED**: `architecture find --pattern "recipe-match"` returns
  0 while `--pattern "*recipe_match*"` returns 4 path matches. `manage-architecture/SKILL.md`
  classifies `find` under "Files-inventory readers (categorised paths, reverse lookup, **glob
  search**)".
  ⛔ **`find` is a path glob WORKING AS DESIGNED, and faulting it for not being a content search is
  the weak half of this plan's case — flagged for removal from the reasoning by #1046's
  retrospective, and it MUST NOT propagate.** The case for deliverable 1 rests entirely on the
  capability gap for dispatched leaves, which is independently established above. Deliverable 5's
  contract correction is a **clarity** fix (make the glob-only scope unambiguous and point at the
  content verb), **not** a defect fix — do not scope it as one.
- **OBSERVED**: `git grep` appears **nowhere** in `marketplace/`, `CLAUDE.md`, or `doc/` — verified by
  a repo-wide search returning zero hits across all three — yet leaves demonstrably fall back to it.
  ⛔ **READ THIS FINDING CORRECTLY: the defect is NOT that `git grep` is undocumented, and the fix is
  NOT to document it.** The orchestrator initially framed it that way and the operator corrected it.
  The defect is that **dispatched leaves have no sanctioned content-search path at all**, so they
  improvise with whatever survives the hook. `git grep` survives only via the incidental git
  allowance, so the live distinction — bare `grep` blocked, `git grep` permitted — rests on which
  binary is invoked rather than on any principle. Documenting the improvisation would promote it to
  sanctioned practice and entrench that incoherence permanently. **The remedy is the verb
  (deliverable 1); `git grep` is eliminated as a practice (deliverables 2-3).**
- **OBSERVED**: dispatched leaves retain `Bash` and the executor even though the `Grep` tool is
  revoked — every `execution-context-{level}` agent declares `Bash`. ⭐ **This is the mechanism that
  reprices the fix**: a script seam reaches leaves today, so no harness change is needed and the
  problem was never a permissions problem.

### Evidence inherited from PR #1046's run (`truthful-signals` PLAN-105, closed-superseded)

⭐ **This is the durable value of that closed PR — its investigation, not its remedy.** Do not
re-derive it.

- **OBSERVED (arch-constraint `2026-07-29-08-001`)**: `Grep`/`Glob` were revoked from **six separate
  dispatched leaves in one run**, although the agent frontmatter declares them and
  `permissions.deny` is `[]`. **Neither project surface withholds the tool — the revocation happens
  at harness runtime, above both.** ⛔ **"Grant `Grep` to leaves" is therefore NOT an available
  repair.** Do not scope one; the seam is the only path.
- **OBSERVED (where `git grep` cannot reach — two independent blind spots)**:
  1. **Gitignored paths.** `.claude/settings.json` was invisible to `git grep`; a leaf needed `Read`
     on an already-known path. ⭐ **No `git grep` approach covers this**, which is a direct argument
     for the script seam over any shell primitive.
  2. **R1 pattern constraint.** A pattern containing `&&`, `;`, a backtick, or `$(` is denied before
     it runs — so the workaround fails on exactly the patterns a code sweep most needs.
- ⚠ **Consequence for deliverable 1's design**: the verb must cover **git-tracked and untracked
  files both**, and must accept patterns containing shell metacharacters. A `git grep`-only backend
  satisfies neither. This supersedes the weaker `git grep`-backend hypothesis recorded below —
  re-read both before scoping.
- **OBSERVED (historical)**: this same verb already produced one confident-wrong answer and was fixed
  once (`truthful-signals` PLAN-43, PR #989). PLAN-01 establishes a second offence. The recurrence is
  an argument for fixing the *capability*, not the instance.
- **HYPOTHESIS**: `git grep` is the right backend versus a Python-side walk — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` § the
  `find` implementation, weighing `.gitignore` semantics and untracked-file visibility
  (verify-at-outline). ⚠ `git grep` sees only tracked files; if untracked files must be searchable,
  the backend choice changes.
- **Verify-first clause**: settle the untracked-file question against actual consumer need before
  scoping. A content search that silently skips untracked files would reproduce this epic's own
  archetype at a new surface.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — new content-search verb alongside `find` (verify-at-outline)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/architecture.py` — argparse surface registration
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md` — verb documentation and the Canonical invocations block
- **OBSERVED**: `CLAUDE.md` — the no-shell-file-ops rule and its prescribed remedy
- **OBSERVED**: `test/plan-marshall/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-01. ⛔ Both touch `manage-architecture` — **never pair them**; PLAN-01 runs
  first.
- **Overlaps with**: PLAN-01 and PLAN-02 on `manage-architecture`.
- **Adjacent to**: `truthful-signals` PLAN-105 (the search primitive). ⛔ **CORRECTED 2026-07-30 — it
  is NOT in flight, and this line previously said it was.** PLAN-105 is **superseded**: its PR #1046
  was **closed unmerged**, superseded by this very seam. It shipped **nothing**, so deliverable 2 does
  NOT shrink and there is nothing to avoid duplicating — this plan owns the whole problem including
  the leaf-permission half.
- ⚠ **Why the stale line survived, which is the reusable part.** Their row sat at `status: staged`
  while `landings/PLAN-105.md` was a *closure* record, and nothing reconciled the two — **a closure
  record is not a closed row**. Their epic corrected the row to `superseded` on 2026-07-30 only after
  a sibling's message prompted the check. At outline, verify a cross-epic dependency's state from the
  sibling's `status.json` row AND its landing record, never from either alone.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-001-content-search-seam.md"
```

## D1's Framing Principle (adopted verbatim from `truthful-signals-006`)

> **A prohibition's remedy must be reachable by the least-privileged bound executor.**

That is the whole defect in one line: `CLAUDE.md` prohibits bare `grep` and prescribes the `Grep`
tool, but the least-privileged executor the prohibition binds — a dispatched leaf — cannot reach the
prescribed remedy. **Adopt this as D1's framing**; it generalises beyond content search and is the
most reusable output of the closed PLAN-105.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
