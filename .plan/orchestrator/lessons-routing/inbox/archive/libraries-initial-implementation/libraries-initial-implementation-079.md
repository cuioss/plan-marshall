envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=finding
created=2026-11-24T12:17:19Z
revision=1
amended=2026-11-24T12:17:32Z

# CHANGE REQUEST — priority: HIGH — plan-orchestrator: route the leftovers of a landing analysis by a standing rule instead of asking for every finding

Requested by the operator of epic `libraries-initial-implementation` (repository git-document-repository), 2026-11-24, plugin 0.1.2184.
Class: change request for the `plan-orchestrator` skill (verbs `analyze`, `handle-open`, `lessons`, `next`) and its standards. Priority: high.

## Problem

After every landing the three-layer analysis produces leftovers (layer-3 defects, layer-2 test gaps, layer-1 spec flaws) of the landed plan. Today each batch stops at the operator:
`analyze.md` says a layer-3 defect "becomes a staged fix-plan spec only on the operator's word", and the Step 5b Fold disposition only applies to a message, with the orchestrator
left to choose the target spec. In this epic that produced twelve Open Defect entries (PLAN-03, 04, 06, 07, 08, 09, 10, 11, 12, 19, 20, 23), each reported to the operator and each routed only after the question was
answered, with the same answer every time: put it into the plan that fits. Three of them (PLAN-10, PLAN-23 and, until the rule, PLAN-20 and PLAN-11) stood as "NOT YET ROUTED" across at least
one session break while staged specs that edit the same files existed.

## The rule the operator set (applied by hand in this epic since 2026-11-24, `epic.md` Decisions "STANDING ROUTING RULE")

1. A leftover goes, without asking, into the **staged plan that fits by content** (same module or same surface, not launched; a launched or running plan's spec is frozen and
   takes no fold) as a NEW DELIVERABLE of that plan, in the same edit as its `Expected Surface`, with its claims stamped through `corpus set-verdict`.
2. Only when no staged plan fits, or the fitting plan already holds **more than 10 deliverables**, it goes into a **follow-up container plan for the module or modules**: one container per
   module (or module group), staged with `queue --add-row`, held back from `next` until the operator releases it; later leftovers of that module fold into it until it is launched.
3. The operator is asked only at a real fork: a fix that changes a documented behaviour, an owner decision, a finding that touches two modules. Staging a fix plan never launches or
   emits it.
4. The routing is recorded as an Open Defect that names the plan and the deliverable, and as one decision-log line per finding group.

Applied on 2026-11-24 to: PLAN-10 and PLAN-11 findings into PLAN-22 (deliverable 4), PLAN-23's into PLAN-14 (deliverable 5), PLAN-20's into the new container PLAN-24.

## Requested change

1. **Fit predicate.** A verb (suggested: `orchestrator corpus route --slug S --paths ... [--module M]`) that returns, for a set of repository paths or a module, the staged specs of the epic whose
   declared surface covers them (`corpus surfaces` already knows `derivation_status`, `admits_disjointness_check` and the claimed paths), each with its queue status, its
   `deliverables_total` (which `corpus spec-skills` already reports), whether it is frozen (`launched`, `running`, `parked` with a worktree) and whether it is held back. The rule's choice (a staged,
   not frozen, fitting plan with at most 10 deliverables; otherwise the container for the module) is then a read, not a judgement.
2. **A deliverable-append write** (suggested: `orchestrator corpus fold --slug S --plan PLAN-NN --deliverable-file F --surface path...`) that appends the numbered deliverable with its `Skills:`
   and `Persona:` lines, adds the named paths to `## Expected Surface` in the same write (the same-act obligation of the Fold disposition), refuses a frozen plan, and returns the new
   `claimed_count` and `deliverables_total`. Today both are direct edits of the spec file, and nothing refused a hand-written verdict line in a spec (it was caught by the author).
3. **A container-plan template and a held-back marker.** `templates/plan-spec.md` gets a container variant (objective naming the module group, "later leftovers fold in until launch", the
   hold-back line), and the held-back state is a field of the queue row, not prose in the spec, so `next` can refuse it mechanically (`corpus cross-check`, `next` Step 4 read it).
   A configured limit for the deliverable bound (default 10; the scope-bloat guard of about six for an emitted plan stays a separate, recorded decision).
4. **Verb text.** `analyze.md` Step 4 "Routing what the three-layer analysis finds" replaces "staged only on the operator's word" with the rule above where an epic carries it (an epic-level
   standing decision, `routing_rule: fold-by-content`, in `status.json` metadata or `epic.md`), and keeps the question for a real fork. `handle-open` applies the same rule to Open
   Defects marked "not yet routed". `lessons` and `next` read the held-back marker.
5. **Claims.** A folded deliverable's `OBSERVED` claims are stamped through `corpus set-verdict` by the same verb call when the folding run has re-read them (verdict, sha, evidence), never
   by an edit of the spec text.

## Acceptance

- A landing analysis whose layer-3 findings all lie in `git-forms/` while PLAN-14 (staged, five deliverables) is the only staged `git-forms` plan appends a deliverable to PLAN-14, extends
  its Expected Surface when the paths were not declared, stamps the claims, writes the Open Defect entry and asks nothing.
- The same findings with the staged plan at 11 deliverables stage or extend the `git-forms` container instead.
- A finding whose only fitting plan is `running` goes to the container, not into the running spec.
- A finding that changes a documented behaviour or needs an owner decision still produces the operator question, once, naming the item.
- `next` never emits a held-back container; `corpus cross-check` reports it as held back, not as indeterminate.

## Evidence

This epic, 2026-11-24: `epic.md` Decisions ("STANDING ROUTING RULE"), `plans/PLAN-22-store-hardening.md` deliverable 4, `plans/PLAN-14-forms-deadlines-links-numbers.md` deliverable 5,
`plans/PLAN-24-git-core-hardening.md`, and the ledger's twelve Open Defect entries of PLAN-03 to PLAN-23. Related change request: `libraries-initial-implementation-078`
(forwarding of framework-owned lessons).
