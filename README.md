# claims-retention-platform

Treating medication adherence as a retention problem, on three years of
event-level Medicare claims (CMS DE-SynPUF: 116,352 beneficiaries, about
**11 million** claim and prescription-fill records).

**Status: in active development.** The warehouse and metrics layer are landing
as v0.5; experimentation, causal inference, and modelling follow.

The data is synthetically generated, so instead of only disclaiming that, I
measured it. [`docs/fidelity_audit.md`](docs/fidelity_audit.md) documents what
the synthesis preserves and what it destroys, tested against permutation nulls.
