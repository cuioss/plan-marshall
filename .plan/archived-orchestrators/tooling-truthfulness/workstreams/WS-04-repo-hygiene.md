# WS-04: Two verified repo-hygiene residues

epic: tooling-truthfulness

## Charter

Own the two small, independently verified residues that need no design work: a stray inventory
document tracked at the repository root, and a `format` alias whose tree set disagrees with both
`lint` and the quality gate.

⭐ **This workstream exists to be DISJOINT.** Every other member of this epic touches an overlapping
orchestrator surface, so at `parallelization_scope: 2` this is the work that can fill the second
slot. Keeping it separate is the point; folding it into a larger plan would remove the only
pairing the epic can make.

The workstream closes when both are gone and the format/lint/gate tree sets agree.
