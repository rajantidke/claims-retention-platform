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
| Segment payment check: inpatient, 2-segment claims | seg 1 avg $17,823.53, seg 2 avg $18,789.71 — different, not duplicated | ad hoc query, 2026-09-28; reconfirmed at staging layer | progress log, fct_utilization_monthly entry, 2026-10-06 |
| Segment payment check: outpatient, 2-segment claims | seg 1 avg $1,368.95, seg 2 avg $1,352.17 — different, not duplicated | ad hoc query, 2026-09-28; reconfirmed at staging layer | progress log, fct_utilization_monthly entry, 2026-10-06 |
| fct_monthly_active: active share, clean window, full-year Part D members | 72.4% (1,297,519 / 1,792,334) | `transform/models/marts/fct_monthly_active.sql` | progress log, fct_monthly_active entry, 2026-09-29 |
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
| retention_null.py: cohort size, cross-implementation check (Python vs. dbt) | 20,260 (exact match), Sep 2008 - Jul 2009 | `audit/retention_null.py` | progress log, `retention_null.py` entry, 2026-09-30 |
| retention_null.py: pooled month-6 retention, real data | 23.1% (4,690 / 20,260) | `audit/retention_null.py` | progress log, `retention_null.py` entry, 2026-09-30 |
| retention_null.py: beneficiaries with <3 fills, whole population (unchanged by Null A') | 12,362 / 93,588 (13.2%) | `audit/retention_null.py` | progress log, `retention_null.py` entry, 2026-09-30 |
| retention_null.py: real vs. Null A' month-6, 20 redraws, decision | real 23.15%, null median 23.36% (range 22.99-23.90%), T=3.50pp, D=0.21pp, "arithmetic" | `audit/retention_null.py`, `reports/audit_results.json` | progress log, `retention_null.py` entry, 2026-10-01 |
| fct_utilization_monthly: Jun 2009, n_enrolled_strict (Part A/B) / pmpm_strict | 103,361 / $401.80 | `transform/models/marts/fct_utilization_monthly.sql` | progress log, `fct_utilization_monthly` entry, 2026-10-01 |
| fct_pdc_monthly: Jun 2009, n_with_spell / avg_pdc / max_pdc | 70,124 / 0.87906 / 1.0 (uncapped, never exceeded post-tiebreak-fix) | `transform/models/marts/fct_pdc_monthly.sql` | progress log, fct_pdc_monthly entry, 2026-10-01; cap retired 2026-10-14, see assert_pdc_never_exceeds_one.sql |
| gate7_terminal_stop.py: population (alive at clean_window_end, full-year Part D 2008+2009, >=1 fill) | 59,216 beneficiaries | `audit/gate7_terminal_stop.py` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14 |
| gate7_terminal_stop.py: real trailing gap >= 180 days | 2.21% of population (1,311 / 59,216) | `audit/gate7_terminal_stop.py` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14 |
| gate7_terminal_stop.py: Null A median, 20 redraws, trailing gap >= 180 days | 1.28% (band 1.22-1.32%) | `audit/gate7_terminal_stop.py`, `reports/audit_results.json` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14 |
| gate7_terminal_stop.py: Null B median, 20 redraws, trailing gap >= 180 days | 1.26% (band 1.18-1.35%) | `audit/gate7_terminal_stop.py`, `reports/audit_results.json` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14 |
| gate7_terminal_stop.py: decision (relative bar 1.25x, absolute bar 2.0pp) | relative 1.74x (cleared), absolute 0.94pp (not cleared), "detectable_but_too_rare" | `audit/gate7_terminal_stop.py`, `reports/audit_results.json` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14; `fidelity_audit.md` Gate 7 |
| gate7_terminal_stop.py: sensitivity sweep, real share / null A median, by gap threshold | 90d: 5.50%/3.49%; 120d: 3.88%/2.31%; 180d: 2.21%/1.28%; 270d: 1.16%/0.64% | `audit/gate7_terminal_stop.py`, `reports/audit_results.json` | progress log, `gate7_terminal_stop.py` entry, 2026-10-14 |
| experiments/simulation/baseline.py: eligible population, pre/post active-month params | 60,725 beneficiaries; post mean 4.976 (SD 1.556); baseline <=2-month rate 8.92%; pre/post Pearson rho 0.760 | `experiments/simulation/baseline.py`, `reports/harness_validation.json` | progress log, `baseline.py` entry, 2026-10-15 |
| experiments/simulation/power.py: MDE/N spine, full population and plausible-effect scenarios | full-pop MDE: 0.035mo (continuous) / 0.65pp (binary); N for 0.25mo lift: 609/arm; N for 2pp reduction: 3,189/arm | `experiments/simulation/power.py` | progress log, `power.py` entry, 2026-10-15 |
