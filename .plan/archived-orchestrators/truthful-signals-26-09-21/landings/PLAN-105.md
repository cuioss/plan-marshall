# Closure Record: PLAN-105 — CLOSED-SUPERSEDED, never merged

epic: truthful-signals
workstream: WS-01
pr: 1046 — **CLOSED, not merged**

> ⛔ **This is NOT a landing report.** PLAN-105 shipped nothing. The file lives in `landings/` because
> that is where the queue row's `landing` field points; the row status is `superseded`, not `shipped`.

## Disposition

**Closed without merging**, by operator decision, after cross-epic review. Orchestrator-verified:

- PR #1046 **absent from the open-PR list**
- branch `feature/dispatched-leaf-has-no-search-primitive` **gone** (local + remote)
- `origin/main` head is `83a0466d2` (#1049) — **nothing from #1046 reached main**

Superseded by **`code-intelligence-substrate` PLAN-03 `content-search-seam`**, which owns the same
gap and takes the opposite remedy: deliver content search as a **script seam** via
`execute-script.py`, and **eliminate `git grep` as a practice** rather than documenting it.

## Why it was closed — the short version

The finding was right; the remedy was architecturally wrong. #1046 would have installed a shell
primitive as sanctioned practice in a project whose whole idiom is wrap-it-in-a-script, and pinned
that carve-out with a **225-line contract test** across **six non-test surfaces** — so PLAN-03 would
have had to invert or retire the test, and a removal failing CI would read as a regression.
**Test-pins-the-defect, deliberately created.** Verified against the diff before deciding.

## ⛔ MY OWN RECOMMENDATION WAS REFUTED — correction recorded

On 2026-07-29 this epic's ledger recorded that the asymmetry *"argues for D2 option (a) — grant
`Grep` to `execution-context` leaves."*

**That is now refuted by first-party evidence** the plan gathered before standing down, filed as
arch-constraint `2026-07-29-08-001`:

> `Grep`/`Glob` were revoked from **six separate dispatched leaves in one run**, despite the agent
> frontmatter declaring them and `permissions.deny` being `[]`. **Neither project surface withholds
> the tool.**

⇒ **"Grant `Grep` to leaves" is not an available repair.** The revocation happens at harness runtime,
above both the agent declaration and project settings, so no edit in this repository can widen it
back. My recommendation was unimplementable, and PLAN-03's script-seam approach is the only one of
the three canvassed options that actually reaches a dispatched leaf.

⭐ Recorded plainly because this epic's standing rule is that **our own analysis is not exempt** —
a confident orchestrator recommendation was wrong on a checkable fact, and the plan disproved it.

## Evidence carried forward to PLAN-03 D1

1. **Revocation behaviour** — as above. Forwarded.
2. **Where `git grep` does NOT reach**: gitignored paths (`.claude/settings.json` was invisible to
   it; a leaf needed `Read` on a known path), and R1-constrained patterns — one containing `&&`,
   `;`, a backtick or `$(` is denied before it runs. ⭐ **Both are arguments FOR the script seam**,
   since no `git grep` approach covers the first.
3. **Surfaces restating the old contract: four**, and **two were not named in the request**
   (`ref-workflow-architecture/standards/agents.md` and `AGENTS.md` — the latter a hand-maintained
   mirror **no sync step updates**). ⇒ **PLAN-03 must treat any such list as a SAMPLE, not an
   enumeration.**
4. ⚠ **Flagged for REMOVAL from PLAN-03's reasoning**: the `architecture find` argument. It is a path
   glob **working as designed**; faulting it for not being a content search was the weak half of the
   case and must not propagate. ⭐ Self-correction by the plan against its own framing.

## Residue NOT superseded — still owed

- **`-002`** — the authoring rule *"a prohibition's remedy must be reachable by the least-privileged
  bound executor"*. This is the **principle PLAN-03 implements**; it outlives the PR.
- **`-003`** — CodeRabbit returned green `completed: true` with **zero comments across ~32 min and 24
  polls**. ⛔ **A direct hit on this epic's theme, independent of this plan's disposition** — and the
  fourth distinct shape of the green-check lie.
- **`-004` / `-005` / `-006`** — three unfixed tool defects, notably that **`phase-3-outline`
  prescribes a `Task:` dispatch a leaf cannot perform** — ⭐ *the same archetype PLAN-105 was
  chasing*, in a different surface.

## Reconciliation Actions

- [x] row `status` → `superseded`; `pr` = 1046 (closed); `landing` → this record; `plan_marshall_plan_id`
- [x] the refuted orchestrator recommendation corrected in `epic.md`
- [x] PLAN-03 evidence forwarded to `code-intelligence-substrate`
- [x] PLAN-110 unblocked — it was sequenced behind PLAN-105
