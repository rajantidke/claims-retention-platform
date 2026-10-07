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
),

pdc_by_beneficiary_month as (
    select
        beneficiary_id,
        month_start,
        covered_days,
        extract(day from (month_start + interval 1 month - interval 1 day)::date) as days_in_month,
        least(1.0, covered_days::double
            / extract(day from (month_start + interval 1 month - interval 1 day)::date)) as pdc

    from covered_days_by_beneficiary_month
)

select
    month_start,
    count(*) as n_with_spell,
    avg(pdc) as avg_pdc,
    max(pdc) as max_pdc

from pdc_by_beneficiary_month
where {{ in_analysis_window('month_start') }}
group by 1
order by 1
