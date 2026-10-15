-- Asserts the per-beneficiary-month proportion-of-days-covered ratio
-- never exceeds 1.0. Until 2026-10, a least(1.0, ...) cap silently
-- absorbed violations caused by the int_coverage_spells tiebreak bug
-- (9 beneficiary-months, found 2026-10-07). That bug is now fixed and
-- the cap is dead code, removed in favor of this loud check: dbt
-- singular tests pass on zero returned rows.

with months as (
    select unnest(generate_series(
        date '{{ var("study_start") }}',
        date '2010-12-01',
        interval 1 month
    ))::date as month_start
),

spell_month_overlap as (
    select
        s.beneficiary_id,
        m.month_start,
        least(s.spell_end, (m.month_start + interval 1 month - interval 1 day)::date)
            - greatest(s.spell_start, m.month_start)
            + 1 as covered_days
    from {{ ref('int_coverage_spells') }} s
    inner join months m
        on s.spell_start <= (m.month_start + interval 1 month - interval 1 day)::date
        and s.spell_end >= m.month_start
),

covered_days_by_beneficiary_month as (
    select
        beneficiary_id,
        month_start,
        sum(covered_days) as covered_days
    from spell_month_overlap
    group by 1, 2
)

select
    beneficiary_id,
    month_start,
    covered_days,
    extract(day from (month_start + interval 1 month - interval 1 day)::date) as days_in_month,
    covered_days::double
        / extract(day from (month_start + interval 1 month - interval 1 day)::date) as raw_pdc
from covered_days_by_beneficiary_month
where covered_days::double
    / extract(day from (month_start + interval 1 month - interval 1 day)::date) > 1.0
