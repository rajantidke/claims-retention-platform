with months as (
    select unnest(generate_series(
        date '{{ var("study_start") }}',
        date '2010-12-01',
        interval 1 month
    ))::date as month_start
),

beneficiaries as (
    select distinct beneficiary_id
    from {{ ref('stg_beneficiary') }}
),

spine as (
    select
        b.beneficiary_id,
        m.month_start,
        extract(year from m.month_start)::integer as month_year
    from beneficiaries b
    cross join months m
)

select
    s.beneficiary_id,
    s.month_start,
    s.month_year                                                   as source_year,

    (bene.death_date is null or bene.death_date >= s.month_start)  as is_alive,
    (bene.part_d_coverage_months = 12)                             as has_full_year_part_d,
    {{ in_clean_window('s.month_start') }}                         as in_clean_window

from spine s
left join {{ ref('stg_beneficiary') }} bene
    on s.beneficiary_id = bene.beneficiary_id
    and s.month_year = bene.source_year
