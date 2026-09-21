envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:13:00Z

# Plugin-cache and registry-pin staleness is a correctness hazard, not a version delta

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 3 lessons. **Suggested fold target:** `PLAN-TRUTH-059` held the registry-parity
surface at the last drain.

## The claim that sharpens the class

⛔⛔ **`2026-08-25-09-001`: the pin gap is a CORRECTNESS hazard producing duplicate landings,
not just a version delta.** The served 0.1.1240 `lessons-capture` body says Branch B4 emits a
landing **unconditionally**; main-source says it emits **none**. Two agents on the same repo
at the same moment follow contradictory instructions, and the observable is a duplicate
landing record — not a stale doc.

That reframing is the cluster's whole point. Treating the gap as "we are N versions behind"
invites a judgement call about whether N is large enough to matter. Treating it as
"two contradictory contracts are simultaneously live" does not.

## The three instances

| Lesson | Instance |
|--------|----------|
| `2026-08-25-09-001` | Served 0.1.1240 vs main-source: Branch B4 emits a landing unconditionally vs emits none. (Title-only stub.) |
| `2026-08-25-06-002` | Dispatched agents load `automatic-review/SKILL.md` from the **0.1.1240 registered-marketplace path** while scripts resolve **0.1.1541**. The served body prescribes an `--enabled-bots` flag **neither script declares**, and defaults the roster to a list **excluding the required bot**. (Title-only stub.) |
| `2026-08-25-15-002` | ⭐ **The worktree analogue, with a full body and a clean diagnosis.** `finalize-step-plugin-doctor` reported 8 `ARGUMENT_NAMING_NOTATION_INVALID` findings against a skill that arrived from upstream **during** `finalize-step-sync-baseline`'s rebase. The worktree's generated executor predated it. **Regenerating cleared all 8 with zero source edits.** |

## What `2026-08-25-15-002` adds that the other two do not

⭐⭐ **The failure mode is not a false positive — it is an UNFALSIFIABLE verdict.** The
finding can be neither confirmed nor refuted against source, because the substrate it was
computed over no longer matches the tree. ⛔ Triaging it as a defect wastes the round;
triaging it as a false positive **records a refutation that was never established**.

⭐ **The diagnostic tell is cheap and reliable**: the findings name a component the plan's own
diff never touches. That asymmetry — findings on untouched, newly-arrived files —
distinguishes this class from a real regression the plan introduced.

⇒ **Regenerate the derived state after any rebase, BEFORE reading a single finding.** The
general shape: a rebase moves SOURCE into the tree but does not move the DERIVED state built
from it, and every gate reading the derived state attributes the mismatch to the source file
it is inspecting.

⚠ Its stated impact: *"applies to every plan whose finalize rebases in upstream commits,
which is most of them under a busy main."*

## Read-coverage caveat

⛔ Two of three rows — `2026-08-25-09-001` and `2026-08-25-06-002` — are **title-only stubs**:
`add` allocated them, `set-body` never ran, no body exists. Both titles name specific version
numbers and a specific contradiction, which is what makes them usable at all. Neither was
re-verified against the live cache by this router.

## Claim labels

- **OBSERVED** — `2026-08-25-15-002` in full: the 8 findings, the rebase provenance, and
  that regeneration cleared them with zero source edits.
- **HYPOTHESIS** — the two version-gap contradictions (`0.1.1240` vs `0.1.1541`, Branch B4's
  two contracts). Title-derived only. Confirm/refute by reading both paths' bodies at the
  named versions — `automatic-review/SKILL.md` § Producer: FIND for the `--enabled-bots`
  claim, and `phase-6-finalize/standards/lessons-capture.md` § Branch B4 for the landing
  claim. ⚠ These are **version-pinned claims about a mutable cache**; whether they still
  hold depends on what has been synced since. Verify-at-outline against the pin state at that
  moment, not against these version numbers.
- **HYPOTHESIS** — that the served-path gap and the worktree-executor gap share a remedy.
  This router's inference from co-location; the two have different mechanisms (a registry pin
  vs a per-worktree derived artifact) and may not. Confirm/refute at outline.
