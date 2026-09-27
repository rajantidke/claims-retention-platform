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
