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
)

select * from person_month_grid
