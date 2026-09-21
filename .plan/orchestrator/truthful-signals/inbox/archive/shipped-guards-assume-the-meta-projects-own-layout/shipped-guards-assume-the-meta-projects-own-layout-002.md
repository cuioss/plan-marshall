envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=finding
created=2026-09-04T14:24:14Z

# cb3735 is UNDER-SCOPED: the degradation reaches scoped runs and a second rule

Supplements `shipped-guards-assume-the-meta-projects-own-layout-001.md`. Two
corrections to that report, both discovered by re-running the gate rather than
by re-reading it.

## 1. It is not whole-tree-only

The first report characterised the defect from whole-tree runs. A **scoped**
run (9 skill dirs, `--paths`) at HEAD `91de82309` returned **49
`manage-invocation-invalid` findings**, same tell: the reported `registered` set
is the router-level `['audit-plan-id', 'help', 'plan-id', 'project-dir']`.

The scoped control settles it — same 9 `--paths`, same 37-rule roster, only the
root swapped:

| Root | `scan_manage_invocation` |
|---|---|
| `<worktree>/marketplace` | 49 |
| `<main>/marketplace` | 0 |

**The source delta cannot explain it.** Iteration 4 gated the *same 9 dirs* at
`96cd4890a` with 0 issues. The only commit since (`d12c79def`) touches two files
under `test/` and no marketplace file at all. So the blast radius grew on its
own between two runs over an unchanged marketplace tree — which makes the defect
non-stationary, and means a single clean scoped run is not evidence the next one
will be.

Sampled anchors are byte-identical to main and outside `affected_files`:
`manage-tasks/SKILL.md` 815/826/1057, `phase-6-finalize/standards/branch-cleanup.md`
758/884/1403/1425. Live `--help` again confirms the flags exist (`manage-tasks
batch-add --tasks-json/--tasks-file`, `github_pr fetch_findings
--required-bots/--optional-bots`), and both probes ran through the freshly
regenerated **worktree** executor — so the executor resolves correctly and only
the analyzer's derivation is degraded.

## 2. A second rule is affected, quietly

`analyze_argument_naming` reports **`blind_spots: 518`** under the worktree root
against **308** under main — same run, same rule, +210 unresolvable sites. It
reports `0` findings either way, so it never fails a build and never appears in
a findings list.

That is the more dangerous half. `manage-invocation-invalid` at least fails
loudly; this one returns a **quieter zero over a materially smaller examined
population**, and nothing in the payload distinguishes "0 because nothing is
wrong" from "0 because 210 more sites could not be resolved". The published
`blind_spots` count is the only thing that reveals it, and only to a reader who
compares two runs.

So cb3735 is under-scoped in two directions: it is not one rule, and it is not
one mode.

## What this costs a consumer of the gate

`scan_manage_invocation`'s verdict for the branch is not clean and not dirty —
it is **unavailable**. The one rule that fired is the broken one, so the gate
cannot say whether a genuine violation exists in the gated skills. For files the
branch did not modify the main-root control is conclusive; for the files it
*did* modify it is not, because main does not carry those edits. That gap is
real and is recorded rather than closed.

## Disposition

The dispatched step **refused to mark itself** rather than choose between
`--outcome failed` (aborting finalize on 49 accepted-false findings) and
`--outcome done` with a `clean` detail (a false green off a `status: fail`
gate). That refusal was correct and is worth preserving as the expected
behaviour for a leaf facing a known-defect exemption it cannot adjudicate.

The orchestrator recorded `--outcome done` with
`display_detail: "9 skills gated, 36/37 rules clean, manage-invocation DEGRADED (cb3735)"`
— naming the un-gated rule instead of claiming a pass, on the strength of the
main-root control.

## Suggested shape of a fix, for whoever picks this up

Publish, per rule, whether the accept-set was **derived** or **fallen back to**.
The `registered` list is already in the payload; what is missing is its
provenance. A rule that cannot derive a surface should report *unavailable*
rather than emitting a violation against a router fallback — the same
un-run-versus-clean distinction this epic keeps arriving at.
