> ⛔ **SURFACE CORRECTED 2026-08-08 — the spec named the wrong module.**
>
> The spec's Expected Surface points at `manage-status` (`status.metadata.worktree_sha`). **Verified at
> HEAD: `manage-status.py` and `_status_core.py` contain ZERO occurrences of `worktree_sha`, `main_sha`
> or `config_hash`.** The capture surface actually lives at:
>
> - **`marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`** — `_capture_main_sha`
>   (`:437`), `_capture_worktree_sha` (`:517`), `_capture_config_hash` (`:1258`), the invariant registry
>   (`:1392-1400`) and the blocking-phase maps (`:1495-1509`).
> - **`manage-change-ledger.py`** — the heaviest non-test consumer (29 `worktree_sha` references).
>
> ⇒ **Re-scope the surface before outline.** A plan aimed at `manage-status` would have found nothing.
>
> **On the premise itself — PLAUSIBLE, NOT SETTLED.** `_capture_main_sha` returns `git_head(_repo_root())`,
> and `_repo_root()` derives from `get_base_dir()`. Its own docstring *asserts* it is the **main** checkout
> root; whether it is depends entirely on whether `get_base_dir()` is main-anchored when called from inside
> a worktree. ⛔ **Settle it by reading `get_base_dir()`'s resolution, not `_repo_root()`'s docstring** —
> the docstring asserting "main" while the resolution may return the worktree is *itself* the
> doc-contract-divergence archetype, and would make the invariant's name a claim rather than a fact.
>
> ⭐ **UNRELATED DEFECT FOUND AT THE SAME SITE — route to `PLAN-TRUTH-064`.** `_filter_main_dirty_paths`
> (`:445`) drops **every path beginning with `.plan/`**, on the stated rationale that `.plan/` writes are
> normal bookkeeping. **That is the identical exemption `post_run_source_guard` uses**, and it has the
> identical hole: 14 files under `.plan/` are git-TRACKED (including `.plan/marshal.json`), so a tracked
> `.plan/` edit is invisible to this invariant too. **Second site, same class.**

# PLAN-TRUTH-046: `main_sha` records the worktree HEAD, and `config_hash` fires at every boundary

epic: truthful-signals
workstream: WS-01

## Objective

An invariant named for one tree records the sha of a **different** tree, and the drift detector built on
it then reports **a drift that never happened**. A second invariant in the same snapshot fires at
**4 of 4** boundaries and therefore carries no information at all.

⭐ Two failure modes, one snapshot: **a confidently wrong value**, and **a detector that cannot fail
usefully**. Both are consumed by anyone reconciling upstream state.

## OBSERVED — first-party, `PLAN-TRUTH-010`'s own phase-handshake snapshot

### A — `main_sha` holds a commit that was never on `main`

The 5-execute snapshot records `main_sha = de00dca9bbbdfd4b82db746037b8b401af6db842`.

`git branch -a --contains de00dca9b` returns **exactly one ref**:
`remotes/origin/feature/fail-closed-signal-integrity`. That commit is
*"docs(ref-code-quality): fix self-contradicting GOOD examples in error-handling"* — **a commit this
plan authored, on its own branch.** It reached `main` only as part of squash `b713fe4b9`. **It was never
on `main` at the moment of capture.**

⭐⭐ **The same status document simultaneously held the RIGHT value**: `status.metadata.main_sha` records
`5c41364a5`, and the work log at 20:08:05Z shows that value being written. ⇒ **Two fields under the same
name, one correct and one not, in one document** — so this cannot be blamed on the sha being
unobtainable.

**Downstream consequence**, `summarize-invariants` duly reported:

```text
warning, main_sha, "main_sha drift 4-plan -> 5-execute: b5477589cc... -> de00dca9b..."
```

⇒ **A warning describing a drift of `main` that did not occur.** A reader reconciling against it is
reasoning from a fabricated fact. ⚠ The snapshot separately carries a `worktree_sha` invariant — so the
two fields are **recording the same tree under two names**, which is also why the drift looks plausible.

### B — `config_hash` drifted at all four boundaries over a footprint with no config file

`93acf2ec -> d99761ec -> 5c58dcd5 -> e8e8b3ea -> c7935ba6`, while the plan's **29-file merged footprint
contains no configuration file at all.**

⇒ Either something outside the plan mutated config four times in 13 hours, **or the hash is not stable
across the contexts it is computed in.** ⭐ **A drift signal that fires at 4/4 boundaries cannot
discriminate "config changed" from "hash is noisy"** — the definition of a detector that cannot fail
usefully. ⛔ **Do not "fix" it by suppressing the warning**: suppression is indistinguishable in effect
from the signal being absent, which is the epic's own archetype.

## Deliverables

1. **D0 — GATE: confirm the capture mechanism by SYMBOL, both invariants.** ⛔ The filer's stated root
   cause — *phase 5 pins cwd to the worktree (ADR-002, move-based cwd-pinned model), so a capture that
   resolves "main" via cwd-relative `HEAD` resolves to the worktree branch head* — is **explicitly
   labelled a hypothesis by the filer itself.** ⚠ It fits the evidence (phases 1-4 run un-pinned and are
   correct; only 5-execute is wrong) but **fitting is not proving.** Read the capture path.
   ⭐ **Derive the population**: every invariant captured in the handshake, classified by whether it
   resolves against an explicit handle or against cwd. **`main_sha` is unlikely to be the only one.**
2. **D1 — resolve `main_sha` against an explicit main-checkout handle**, never cwd-relative `HEAD`.
   ⭐ **Load-bearing**, and it is the same class as the standing rule *never judge a merge lock stale from
   a worktree-scoped store* — **cite that precedent, do not re-derive it.**
3. **D2 — a capture-time assertion that fails closed.** `main_sha` MUST be an ancestor of `origin/main`.
   A captured value that is not is a **capture bug**, and must be recorded as **`unknown`**, never as a
   confident wrong sha. ⭐ This is clause-for-clause the fail-closed discipline `PLAN-TRUTH-010` shipped
   into `ref-code-quality` — **apply the standard to the machinery that shipped it.**
4. **D3 — settle `config_hash` stability before its warning is trusted OR suppressed.** Determine whether
   the four drifts are real. ⛔ **A determination is the deliverable** — if the hash is context-dependent,
   make it context-independent or rename the field to what it actually measures. ⚠ **Do not suppress an
   unexplained signal.**
5. **D4 — reconcile `main_sha` against `worktree_sha`.** If they can hold the same value, one of them is
   redundant or misnamed. **Decide which and record the rejected option.**
6. **D5 — tests, each verified to FAIL pre-fix.** (a) A capture performed with cwd pinned to a worktree
   records the main checkout's sha. (b) A non-ancestor value yields `unknown`, not a warning.
   (c) `summarize-invariants` does not emit a drift warning for the live 4-plan→5-execute fixture.
   (d) The D0 population is asserted non-empty.

⚠ **Six deliverables — at the scope-bloat threshold.** Split evaluated: **D3/D4 are the split point**
(a separate invariant sharing only the snapshot). Kept together because D0's population sweep serves
both and would otherwise be run twice. ⛔ **If D0 shows the two invariants have different capture paths,
SPLIT before implementation** — this rationale is recorded so the decision is not re-made silently.

## Claim Labels

- **OBSERVED (plan-reported, first-party, with the `git branch --contains` result quoted)**: the
  `de00dca9b` value, its single containing ref, the correct `5c41364a5` in `status.metadata`, the
  20:08:05Z work-log write, the emitted drift warning, the four `config_hash` values, and that the merged
  footprint contains no config file.
- ⚠ **NOT independently re-derived by this orchestrator.** ⭐ **`git branch -a --contains de00dca9b` is
  cheap and still available on main — re-run it at D0 as the very first check.** *A corrective is a
  hypothesis until the named site is read.*
- **HYPOTHESIS, so labelled by the filer**: cwd-pinning is the capture mechanism. ⛔ **Confirm by symbol
  before scoping.**
- **HYPOTHESIS**: the `config_hash` drifts are noise rather than real mutation. ⚠ **Genuinely
  undetermined — both branches are live.** D3 must decide it, not assume it.

## Expected Surface

- **HYPOTHESIS**: `manage-status` — the phase-handshake invariant capture and `summarize-invariants`
- **HYPOTHESIS**: the phase-5 cwd-pinning path (ADR-002)

## Dependencies and Sequencing

- ⚠ **Surface-adjacent to `PLAN-TRUTH-035`** (`manage-metrics`) and **`PLAN-TRUTH-031`** — all three read
  or write the plan status document. ⛔ **SERIALIZE against whichever is running.**
- ⚠ Related in kind (not in surface) to `PLAN-TRUTH-006` (baseline-reconcile persists a merge commit) —
  another *wrong-commit-recorded-confidently* instance. **Cite, do not merge.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-046-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
