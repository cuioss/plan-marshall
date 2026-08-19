# Finalize-step `order` allocation bands

The phase-6-finalize `order` space is a **banded allocation contract with reserved gaps**, not a flat
integer scale filled by accretion. This document is the contract: it states the bands, what each means,
which ranges are reserved for project-local and third-party steps versus owned by the shared bundle, the
collision rule that keeps two steps from silently sharing an order, and the `reads` / `destroys` declared
facts the ordering key carries beyond a bare slot number.

It is consumed by third-party and project-local step authors deciding where to number a new step, and by
the shared bundle when it reserves a slot. It **layers on top of** the post-run band contract owned by
`code-intelligence-substrate` (the `post_run_review` / `mutates_source` discriminator and their mutual
exclusion, in [`../../phase-6-finalize/standards/source-edit-pushability.md`](../../phase-6-finalize/standards/source-edit-pushability.md)
and [`ext-point-finalize-step.md`](ext-point-finalize-step.md) § "Implementor Frontmatter"); it does
**not** restate or alter that discriminator. Where this contract and the post-run band contract meet — at
and after the merge gate — the post-run band contract governs the `mutates_source` obligation and this
one governs only the numeric allocation.

## Why bands, and why gaps

The `order` key sorts the composed `phase_6.steps` (see
[`../../manage-execution-manifest/scripts/_manifest_validation.py`](../../manage-execution-manifest/scripts/_manifest_validation.py)
`_sort_steps_by_frontmatter_order`). Historically the values were spaced **by convention** — round
anchors for shared steps, odd numbers slotted in between for project-local ones. Sparse-by-convention is
not sparse-by-guarantee: the terminal region accreted to `998 → 999 → 1000` with no integer left between
the last reporting step and `archive-plan`, so there was **no slot** for a terminal emission step, and
two shared steps collided at `order: 9` with nothing to catch it. A band with no reserved gap is the
defect this contract removes.

## The bands

The merge gate (`default:branch-cleanup`) is the pipeline's partition, so the bands are defined relative
to it. Its own order is read **dynamically** by the post-run enforcement (never hard-coded), and the band
boundaries below track it.

| Band | Range | Owner of the range | Meaning |
|------|-------|--------------------|---------|
| **Settle — pre-push** | 1–11 | Shared bundle + project-local / third-party, densely packed | Steps that prepare, gate quality, review and mutate source before the single `push` barrier at 11. **There is NO guaranteed insertion room in this sub-region today** — the integers 1–11 are fully occupied. A new pre-push step's sanctioned remedy is a deliberate re-space of the sub-cluster (see the alternative named below), not a slot in the post-push gaps, which are all numbered above `push` and so cannot hold a pre-push step. |
| **Settle — post-push** | 12–69 | The majors anchor on a coarse grid (`create-pr` 20, `ci-verify` 22, `automatic-review` 30, `sonar-roundtrip` 40, `adr-propose` 62); project-local / third-party insert in the interior gaps | Steps that open the PR, run CI, review and re-settle after the push — everything between the push barrier and the merge gate. The interior gaps (12–19, 23–29, 31–39, 41–61, 63–69) are the band's guaranteed insertion room. |
| **Merge gate** | 70 | Shared bundle (fixed) | `default:branch-cleanup` — the partition. Not a member of any insertable band. |
| **Post-merge operational** | 71–899 | project-local / third-party | Post-merge steps that **act** (deploy, cache-sync) but are not backward-looking reports. They fail the post-run band's P1 predicate, so they are ordered here rather than in the post-run band. The `mutates_source` obligation for a step at or after the merge gate is owned by [`ext-point-finalize-step.md`](ext-point-finalize-step.md) § "Implementor Frontmatter" — read it there. |
| **Post-run review** | 900–999 | Shared bundle + project-local / third-party | `post_run_review: true` backward-looking reports — the band `code-intelligence-substrate` plan 050 owns. Its members' `mutates_source` obligation is owned by that band's contract; this file does not restate it. Existing members cluster at 990–999; **900–989 is reserved insertion room.** |
| **Terminal emission** | 1000–1099 | Shared bundle (reserved) | The single machine-readable terminal emission — the run's landing, emitted after every reporting step and before the archive move. Reserved; occupied by the terminal-emission step. |
| **Terminus** | 1100 | Shared bundle (fixed) | `default:archive-plan` — moves the plan directory out from under every later reader, so nothing may follow it. Numerically the highest order, last by construction. |

**The reserved gaps are the guarantee.** Within each insertable band the shared bundle anchors on round
numbers and leaves the interior free, so a third-party or project-local step always has a slot to claim
without renumbering a neighbour:

- **Settle — pre-push (1–11)** — **no guaranteed insertion room.** Every integer from 3 to 11 is
  occupied (`finalize-step-sync-baseline` 3, `finalize-step-lessons-housekeeping` 4,
  `pre-push-quality-gate` 5, `finalize-step-plugin-doctor` 6, `pre-submission-self-review` 7,
  `finalize-step-simplify` 8, `finalize-step-security-audit` 9, `architecture-refresh` 10, `push` 11),
  leaving only 1–2 free below the whole cluster. The post-push gaps below CANNOT absorb a pre-push step:
  every one of them is numbered above `push`, so a step placed there runs after the branch has already
  shipped. The sanctioned remedy for a new pre-push step is therefore a **deliberate re-space of the
  sub-cluster** — renumbering the existing members to open a slot — which is a change to this contract,
  made once and recorded, not an insertion into reserved room that does not exist.
- **Settle — post-push (12–69)** — the gaps between the majors (12–19, 23–29, 31–39, 41–61, 63–69) are
  open, and this is where the band's guaranteed insertion room lives. `finalize-step-era-stamp-fill` (21)
  already uses it.
- **Post-merge operational (71–899)** — almost entirely open; existing members sit at 81 and 85.
- **Post-run review (900–999)** — 900–989 is open insertion room below the existing 990–999 cluster.
- **Terminal emission (1000–1099)** — reserved for the one terminal emission; 1001–1099 stays open for a
  future co-terminal step rather than being consumed by pushing the terminus up against it.

## The collision rule

**No two steps discovered for the same extension point may share an `order`.** The finalize-step
ext-point is the phase discriminator: `find_implementors(ext-point-finalize-step)` returns finalize
steps only, and the composer sorts that one population. Two orders in **different** ext-points (a phase-5
`ext-point-build-verify-step` order and a phase-6 finalize-step order) are never sorted against each
other, so they may coincide without colliding — that cross-phase coincidence is not a collision and must
not be "fixed".

The rule is enforced as a check that **fails** over the discovered finalize-step population — see
`test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` (it extends the existing
step-discovery test rather than adding a competing checker). A collision is a
defect because the composer's sort resolves it only by an **undeclared tie-break**: the sort is stable,
so two equal-order steps keep their input list position (the `DEFAULT_PHASE_6_STEPS` sequence for
defaults, the on-disk keyed-map order for a configured plan). Relying on that accident is exactly what
the collision rule forbids.

## `reads` and `destroys` — a data dependency the ordering key can express

A slot number states *when* a step runs but not *why that order is correct*. Two optional frontmatter
list fields let the ordering key carry the data dependency as a **declared fact**:

| Field | Type | Meaning |
|-------|------|---------|
| `reads` | list[str] | Named run artifacts the step consumes as input. A step that declares `reads: [X]` is only correctly ordered **after** the step that produces `X`. |
| `destroys` | list[str] | Named run artifacts the step renders unavailable to later steps. A step that declares `destroys: [X]` makes `X` unreadable to every step ordered after it. |

The artifact names are a small shared vocabulary (e.g. `metrics`, `worktree`, `plan-directory`) so a
producer's output and a consumer's `reads` refer to the same token. With both declared, a
read-before-produce or read-after-destroy ordering error is a **checkable fact** rather than a slot-number
accident that only surfaces at runtime — the defect a bare integer cannot express (a step legally
numbered after a `destroys` step still reads a destroyed input). The declaration is the capability; a
step declares only the artifacts it genuinely reads or destroys, and absence means "no declared
dependency", not "obligation unwritten".

The canonical `destroys` declarations anchor the vocabulary, and both sides of it are now live — the
`reads` bullets below name the readers that pair with each:

- `default:archive-plan` declares `destroys: [plan-directory]` — it moves the plan directory, which is
  why it is the terminus and why every plan-file reader must precede it.
- `default:branch-cleanup` declares `destroys: [worktree]` — the merge gate removes the linked worktree,
  so a step that `reads: [worktree]` is mis-ordered if it runs after the gate. Its readers today are
  `default:finalize-step-sync-baseline` (3), `default:pre-push-quality-gate` (5) and
  `project:finalize-step-plugin-doctor` (6) — each inspects the worktree's state as an input to its own
  verdict, and each is ordered well below the gate.
- On the `metrics` side, `default:finalize-step-print-phase-breakdown` (999) and `default:emit-landing`
  (1000) declare `reads: [metrics]` — both consume what `default:record-metrics` (998) produces.

**Declare `reads` where the step INSPECTS the artifact as an input to its own verdict or output — not
merely where it executes.** Every pre-merge step runs *in* the worktree; a blanket declaration would
say nothing. The three above read worktree state and branch on it (a rebase classification, a live
footprint, a worktree-bound executor regeneration), so ordering one after the gate would genuinely
break it. `default:push` executes in the worktree without reading its state for a verdict, and declares
nothing.

**The read-after-destroy direction is checkable; read-before-produce is not.** Pairing a `reads` token
with the matching `destroys` token derives an ordering edge a test asserts
(`test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`). There is no `produces` marker,
so `reads: [metrics]` is paired against `record-metrics` by a human reading this paragraph, not by a
derivation — that half remains a documented convention rather than a checked fact.

## Renumbering is a consequence, not the deliverable

The contract above is the deliverable. Making the existing steps conform to it is a consequence, applied
only where a gap did not already exist: the **terminal slot**. Existing settle, post-merge, and post-run
steps already sit within their bands with free insertion room, so they are left in place; only
`default:archive-plan` moved (to the terminus at 1100) to open the reserved terminal-emission band
(1000–1099). A future step that must land in a band with no interior gap is renumbered into the reserved
room this contract guarantees, never by pushing a neighbour.
