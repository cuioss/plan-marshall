envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:43:39Z

## Our corpus is procedural memory managed by a declarative lifecycle

Source: *Context Engineering: Sessions, Memory* (Milam, Gulli, Nawalgaria; Google/Kaggle, updated May 2026) —
Day 3 of the course series, read from a local PDF. Note: this is the **2025 paper refreshed**, and it carries
no Skills section, despite Day 1 cross-referencing it as "Sessions, Skills & Memory". Most of it concerns
conversational agent products — user personalization, CRM bootstrapping, session compaction — and does not
apply here. Two sections do. This is one.

### The distinction it draws

The paper separates **declarative** memory (the "what" — facts, history, user data) from **procedural**
memory (the "how" — workflows and reasoning), and states plainly that the industry builds only the first:

> "Most memory management platforms are also architected for this declarative approach... these systems are
> not designed to manage procedural memories... Storing the 'how' is not an information retrieval problem; it
> is a reasoning augmentation problem. Managing this 'knowing how' requires a completely separate and
> specialized algorithmic lifecycle."

It gives that lifecycle three stages that differ from their declarative twins in kind, not degree:

1. **Extraction** distils a reusable *playbook* from a successful interaction, not a fact.
2. **Consolidation** "curates the workflow itself" — integrating new successful methods with existing best
   practices, **patching flawed steps in a known plan**, and pruning outdated or ineffective procedures.
3. **Retrieval** returns *a plan that guides execution*, not data that answers a question — and so
   "may have a different data schema than declarative memories."

### Why it matters here

Essentially everything this epic is chartered to measure is procedural memory. Skills are playbooks. Workflow
docs are plans. Lessons are distilled procedures. Yet the lifecycle we manage them with is the declarative
one: `manage-lessons` stores a lesson body, marks it stalled, retires it. There is no primitive for *patching
a flawed step inside a plan that otherwise holds* — the closest thing we have is a human promoting "reusable
residue into the governing skill before retiring the lesson", which is procedural consolidation performed by
hand, one lesson at a time, with no schema behind it.

That is a naming, and namings are cheap. What makes it worth filing is the schema claim: if procedural
retrieval genuinely wants a different shape than declarative retrieval, then the lesson body format inherited
from a fact-shaped store may be the wrong container for the thing it holds, and the hand-promotion step is a
symptom of the mismatch rather than a workflow choice.

### Bounds

- The paper supplies **no data** for any of this, and cites one endnote for the whole section.
- It is describing a gap in commercial memory platforms, not prescribing a design.
- Routing: this touches the lessons corpus, so the orchestrator may judge it to belong with the
  lessons-handling epics rather than here. Filed to `next-level` because the substrate it describes is the
  one this epic exists to measure; the routing call is not mine.

### Status

A conceptual reframe with no measurement behind it. It changes how a future spec might be worded; it is not
evidence for writing one.
