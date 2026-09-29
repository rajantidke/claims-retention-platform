# Future Work

Ideas and known limitations that were deliberately deferred rather than
built, with the reasoning for why. Not a backlog, rather a record of considered
tradeoffs.

## Clustering as a supplementary EDA technique

During Week 2's fidelity work, unsupervised clustering (e.g., k-means on
beneficiary/claims data, compared against condition flags or ICD codes as
ground truth) was considered as an additional exploratory technique across
the beneficiary, carrier, inpatient, outpatient, and PDE tables.

Decided against for v1.0: the six fidelity gates already answer the
relevant "does this property hold" questions with sharper, hypothesis-
driven, statistically decisive tests (shuffle nulls, KS tests, Spearman
correlations) than clustering would provide. Clustering is exploratory,
it shows groupings and you eyeball whether they align with something you
care about, which is a weaker standard of evidence than what the gates
already deliver, and it can't establish causal/temporal precedence at all
(that's what Module C's plasmode design and Module D's snapshots are for).

Worth revisiting only as a supplementary sanity-check tool in a future EDA
phase, not as primary evidence for a data-fidelity claim.


## int_coverage_spells: non-recursive approximation (no stockpiling)

`int_coverage_spells` (Week 4) merges overlapping and adjacent prescription
fill coverage into continuous spells, but does not model stockpiling: an
early refill's coverage does not push the next fill's *effective* start
date forward to the end of the previous supply. A patient who refills 10
days early is treated as if their new coverage starts immediately, rather
than after their existing supply would have run out.

True stockpiling logic requires a recursive CTE (each fill's effective
start depends on the previous fill's effective end, which itself may have
been pushed forward by the fill before it). Decided against for v1.0:
Gate 6 (docs/fidelity_audit.md) already established that `days_supply`
does not reliably predict actual refill timing in this dataset, and PDC
(the metric stockpiling logic exists to support) was demoted from primary
metric to a documented limitation as a direct result. Spending ~3 hours
building the more precise version would sharpen a number already
established as unreliable on this data.

Revisit if: (a) a future dataset with trustworthy days-supply/timing
behavior replaces DE-SynPUF, or (b) PDC is ever promoted back to a primary
metric for a specific sub-analysis with its own validation.


## Washout-period sensitivity comparison (180 vs. 365 days)

`washout_days` is already a project var (`transform/dbt_project.yml`), not
hardcoded, so the new-user cohort definition can be rebuilt with a
different washout period (e.g. 365 days instead of 180) by changing one
line and rerunning `make build` — no SQL changes needed. What doesn't
exist is a way to run both side by side and compare cohort composition or
retention shape between them.

Decided against building this now: it's a real sensitivity analysis, not
a configuration option, and would mean a second cohort definition, more
marts, and more to reconcile and explain, which is more scope than a v0.5
warehouse-and-metrics milestone needs. `fct_cohort_retention`'s
description notes the var is swappable; the actual side-by-side
comparison is deferred here.

Revisit if: a reviewer or later module specifically asks "how sensitive
is the retention shape to the washout definition," since that's exactly
the question this comparison would answer.
