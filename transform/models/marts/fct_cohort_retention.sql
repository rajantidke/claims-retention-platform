with fill_gaps as (
    select
        beneficiary_id,
        fill_date,
        fill_date - lag(fill_date) over (
            partition by beneficiary_id order by fill_date
        ) as days_since_prev_fill
    from {{ ref('int_fill_events') }}
    where not is_zero_days_supply
),

entry_candidates as (
    select
        beneficiary_id,
        fill_date as entry_date
    from fill_gaps
    where days_since_prev_fill is null
       or days_since_prev_fill >= {{ var("washout_days") }}
),

entry_window as (
    select *
    from entry_candidates
    where entry_date between
        date '{{ var("analysis_start") }}' + interval '{{ var("washout_days") }}' day
        and date '2009-07-31'
),

first_entry as (
    select
        beneficiary_id,
        date_trunc('month', min(entry_date))::date as entry_month
    from entry_window
    group by 1
),

months_available as (
    select
        beneficiary_id,
        entry_month,
        generate_series(
            0,
            datediff('month', entry_month, date '{{ var("clean_window_end") }}')
        ) as months_list
    from first_entry
),

person_month_grid as (
    select
        beneficiary_id,
        entry_month,
        unnest(months_list) as months_since_entry
    from months_available
),

grid_with_activity as (
    select
        pmg.beneficiary_id,
        pmg.entry_month,
        pmg.months_since_entry,
        (pmg.entry_month + interval (pmg.months_since_entry) month)::date as calendar_month,
        coalesce(ma.is_active, false) as is_active

    from person_month_grid pmg
    left join {{ ref('fct_monthly_active') }} ma
        on pmg.beneficiary_id = ma.beneficiary_id
        and ma.month_start = (pmg.entry_month + interval (pmg.months_since_entry) month)::date
)

select
    entry_month,
    months_since_entry,
    calendar_month,
    count(*)                                         as cohort_size,
    sum(case when is_active then 1 else 0 end)       as n_active,
    100.0 * sum(case when is_active then 1 else 0 end)
        / count(*)                                   as retention_rate

from grid_with_activity
group by 1, 2, 3
order by 1, 2
