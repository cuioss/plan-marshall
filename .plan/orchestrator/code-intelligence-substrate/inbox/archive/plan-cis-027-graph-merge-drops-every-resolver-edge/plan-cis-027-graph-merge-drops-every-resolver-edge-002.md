envelope_version=1
sender_type=plan
sender_id=plan-cis-027-graph-merge-drops-every-resolver-edge
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T13:58:52Z

component=plan-marshall:manage-architecture
category=bug
created=2026-08-02
bundle=plan-marshall

# A seeded empty container is not a declaration — test the value, not the key

`_declared_dependencies` in `_cmd_client_query.py` answered *"is this module declared?"* with
a **key-membership** test against `enriched.json`. But `architecture init` seeds an **empty**
`internal_dependencies` stub into **every** module's `enriched.json`. Under a key-membership
test, every module in the project therefore read as *"declared, with zero dependencies"* — a
population of 12/12 where the intended population was 0/12.

The declared-wins precedence branch then did exactly what it was written to do: it replaced
each module's resolver-derived edge set with the declared list. The declared list was empty,
so the merged graph shipped `edge_count: 0` with all 12 modules listed as both roots **and**
leaves, while all three resolvers reported `status: ok` with 29 edges between them.

The defect is not in the precedence rule and not in the resolvers. It is in the predicate that
decides which population the precedence rule applies to.

## Solution

Treat only a **non-empty** value as a declaration, at **every** precedence source — here both
the `enriched.json` overlay and `derived.json`. Keep the predicate as a single shared authority
(one function consumed by both `_build_deps_and_producers` and `_derive_edges`) so the
"skip enrichment" population and the "discard derived edges" population cannot drift apart.

## Impact

Applies to any consumer that reads a store whose **scaffolder seeds empty defaults**. The
scaffolder's job is to make the key always present; that is precisely what makes key-presence
worthless as an is-this-populated signal. Whenever a writer guarantees a key exists, the reader
MUST discriminate on the value.

Recognition signature: a producer reports a healthy non-zero count and `ok`, the consumer
reports zero, and the two never contradict each other because nothing compares them. Before
suspecting the producer, check whether the consumer's *presence predicate* is matching a
scaffolded stub.
