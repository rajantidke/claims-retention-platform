with inpatient_by_month as (
    select
        date_trunc('month', claim_from_date)::date as month_start,
        sum(payment_amount) as inpatient_amount
    from {{ ref('stg_inpatient') }}
    where {{ in_analysis_window('claim_from_date') }}
    group by 1
),

outpatient_by_month as (
    select
        date_trunc('month', claim_from_date)::date as month_start,
        sum(payment_amount) as outpatient_amount
    from {{ ref('stg_outpatient') }}
    where {{ in_analysis_window('claim_from_date') }}
    group by 1
),

carrier_by_month as (
    select
        date_trunc('month', claim_from_date)::date as month_start,
        sum(payment_amount) as carrier_amount
    from {{ ref('stg_carrier') }}
    where {{ in_analysis_window('claim_from_date') }}
    group by 1
),

denominators as (
    select
        month_start,
        count(*) as n_enrolled_all,
        sum(case when has_full_year_part_ab then 1 else 0 end) as n_enrolled_strict
    from {{ ref('fct_monthly_active') }}
    where {{ in_analysis_window('month_start') }}
        and is_alive
    group by 1
)

select
    d.month_start,
    d.n_enrolled_all,
    d.n_enrolled_strict,

    coalesce(ip.inpatient_amount, 0)   as inpatient_amount,
    coalesce(op.outpatient_amount, 0)  as outpatient_amount,
    coalesce(car.carrier_amount, 0)    as carrier_amount,

    coalesce(ip.inpatient_amount, 0)
        + coalesce(op.outpatient_amount, 0)
        + coalesce(car.carrier_amount, 0)  as total_amount,

    (coalesce(ip.inpatient_amount, 0)
        + coalesce(op.outpatient_amount, 0)
        + coalesce(car.carrier_amount, 0))
        / nullif(d.n_enrolled_strict, 0)   as pmpm_strict

from denominators d
left join inpatient_by_month ip on d.month_start = ip.month_start
left join outpatient_by_month op on d.month_start = op.month_start
left join carrier_by_month car on d.month_start = car.month_start

order by d.month_start
