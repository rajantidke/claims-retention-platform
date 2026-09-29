with fills_by_month as (
    select
        beneficiary_id,
        date_trunc('month', fill_date)::date as month_start,
        count(*) as n_fills,
        sum(coalesce(days_supply, 0)) as days_supplied_in_month
    from {{ ref('int_fill_events') }}
    group by 1, 2
)

select
    mm.beneficiary_id,
    mm.month_start,
    mm.source_year,
    mm.is_alive,
    mm.has_full_year_part_d,
    mm.has_full_year_part_ab,
    mm.in_clean_window,
    coalesce(f.n_fills, 0)                 as n_fills,
    coalesce(f.n_fills, 0) > 0             as is_active,
    coalesce(f.days_supplied_in_month, 0)  as days_supplied_in_month

from {{ ref('int_member_months') }} mm
left join fills_by_month f
    on mm.beneficiary_id = f.beneficiary_id
    and mm.month_start = f.month_start
