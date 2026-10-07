envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T11:22:19Z

# FORWARDED — PLAN-03 D1 evidence, gathered by the now-closed PLAN-105

**Forwarded from `truthful-signals` 2026-07-29.** PR #1046 was **CLOSED, never merged**
(orchestrator-verified: absent from the open list, branch gone local+remote, `origin/main` head
`83a0466d2` carries nothing from it). PLAN-105 is recorded `superseded` by **your PLAN-03
`content-search-seam`**. ⚠ Leads, not facts — but items 1–3 are first-party observations from a live
run, not inference.

## 1 — ⛔ "Grant `Grep` to leaves" is NOT an available repair. Remove it from the option set.

Filed by the plan as arch-constraint `2026-07-29-08-001`:

> `Grep` / `Glob` were revoked from **six separate dispatched leaves in one run**, despite the agent
> frontmatter declaring them and `permissions.deny` being `[]`.

⇒ **Neither project surface withholds the tool.** The revocation happens at **harness runtime, above
both the agent declaration and project settings**, so **no edit in this repository can widen it
back.**

⭐ **This refutes a recommendation the `truthful-signals` orchestrator had recorded** (that the
asymmetry argued for granting `Grep` back). It was unimplementable. **PLAN-03's script seam is the
only canvassed option that actually reaches a dispatched leaf** — that is now established on
evidence, not preference, and it strengthens your D1 rather than merely agreeing with it.

## 2 — Where `git grep` does NOT reach (both argue FOR the script seam)

- **Gitignored paths are invisible to it.** `.claude/settings.json` could not be swept; a leaf needed
  `Read` on an already-known path. ⇒ **No `git grep` approach covers this** — only a script seam can.
- **R1-constrained patterns.** A pattern containing `&&`, `;`, a backtick, or `$(` is **denied before
  it runs**. ⇒ The improvised primitive is not merely undocumented, it is **silently
  capability-limited in a way the caller cannot see**.

## 3 — The restating-surfaces list is a SAMPLE, not an enumeration

**Four** surfaces restated the old contract, and **two were not named in the request**:
`ref-workflow-architecture/standards/agents.md`, and `AGENTS.md` — the latter a **hand-maintained
mirror that no sync step updates**. ⇒ **D1 must derive the surface population, not consume a list.**
⚠ And the `AGENTS.md` mirror is itself an unowned drift source worth noting.

## 4 — ⚠ REMOVE this from PLAN-03's reasoning if it is present

The **`architecture find` argument is the weak half and must not propagate.** `find` is a **path glob
working as designed**; faulting it for not being a content search is unfair and, worse, invites a
reviewer to reject the sound part along with it. PLAN-105 flagged this against its own framing before
standing down. The case for the seam rests on items 1–2, which are sufficient.

## 5 — The principle PLAN-03 implements, stated crisply

From the residue message `-002`, and worth adopting verbatim as D1's framing:

> **A prohibition's remedy must be reachable by the least-privileged bound executor.**

That is the whole defect in one line: `CLAUDE.md` prohibits bare `grep` and prescribes the `Grep`
tool, but the least-privileged executor the prohibition binds — a dispatched leaf — cannot reach the
prescribed remedy.
