# Metrics Reference

A lookup table, not an explanation. If a number here disagrees with
`docs/fidelity_audit.md` or the notebook, they win, not this file.

| Metric | Value | Computed in | Explained in |
|---|---|---|---|
| Gate 4: 2009 plateau (fills/enrolled/30d) | 1.554 | `audit/fidelity.py` | `fidelity_audit.md` Part B, Gate 4 |
| Gate 4: 90% threshold | 1.399 | `audit/fidelity.py` | `fidelity_audit.md` Part B, Gate 4 |
| Gate 4: analysis_start (first 2008 month at/above threshold) | 2008-04-01 | `audit/fidelity.py` | `fidelity_audit.md` Part B, Gate 4 |
| Gate 4: first 2010 month below threshold | 2010-03-01 (89.9% of plateau) | `audit/fidelity.py` | `fidelity_audit.md` Part B, Gate 4 |
| Gate 4: Dec 2010 % of plateau | 24.2% | `audit/fidelity.py` | `fidelity_audit.md` Part B, Gate 4 |
| Segment payment check: inpatient, 2-segment claims | seg 1 avg $17,823.53, seg 2 avg $18,789.71 — different, not duplicated | ad hoc query, 2026-09-28 | progress log, `fct_utilization_monthly` entry (pending) |
| Segment payment check: outpatient, 2-segment claims | seg 1 avg $1,368.95, seg 2 avg $1,352.17 — different, not duplicated | ad hoc query, 2026-09-28 | progress log, `fct_utilization_monthly` entry (pending) |
| fct_monthly_active: active share, clean window, full-year Part D members | 72.4% (1,297,519 / 1,792,334) | ad hoc query, 2026-09-29 | progress log, `fct_monthly_active` entry (pending) |
| int_member_months: beneficiaries with has_full_year_part_d at least once | 94,564 | ad hoc query, 2026-09-29 | matches the earlier 94,564 in `int_member_months` entry, 2026-09-27 |
| fct_engagement_rate_monthly: Jun 2009, n_enrolled_strict | 79,938 | `transform/models/marts/fct_engagement_rate_monthly.sql` | progress log, `fct_engagement_rate_monthly` entry, 2026-09-29 |
| fct_engagement_rate_monthly: Jun 2009, rate_strict | 70.6% | `transform/models/marts/fct_engagement_rate_monthly.sql` | progress log, `fct_engagement_rate_monthly` entry, 2026-09-29 |
| fct_engagement_rate_monthly: Jun 2009, n_enrolled_all / rate_all | 115,580 / 51.3% | `transform/models/marts/fct_engagement_rate_monthly.sql` | progress log, `fct_engagement_rate_monthly` entry, 2026-09-29 |
| fct_cohort_retention: cohort size (new-user entries, Sep 2008 - Jul 2009) | 20,260 beneficiaries | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: entry window, earliest/latest entry_month | 2008-09-01 to 2009-07-01 | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: person-month grid, max months_since_entry | 16 (earliest cohort, Sep 2008, to clean_window_end) | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: month-0 retention (all cohorts, by construction) | 100.0% | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: Sep 2008 cohort size (partial month, 3 eligible entry days) | 163 | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: cohort sizes, Oct 2008 - Jul 2009 | 1,656 to 2,305 per month | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
| fct_cohort_retention: Sep 2008 cohort, retention at month 1 / month 6 | 36.2% / 30.1% | `transform/models/marts/fct_cohort_retention.sql` | progress log, `fct_cohort_retention` entry, 2026-09-30 |
