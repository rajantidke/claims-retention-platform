with ordered as (
    select
        beneficiary_id,
        coverage_start,
        coverage_end,
        max(coverage_end) over (
            partition by beneficiary_id order by coverage_start
            rows between unbounded preceding and 1 preceding
        ) as prev_max_end
    from {{ ref('int_fill_events') }}
    where not is_zero_days_supply
),

flagged as (
    select
        *,
        case
            when prev_max_end is null
                or coverage_start > prev_max_end + interval 1 day
            then 1
            else 0
        end as is_new_spell
    from ordered
),

numbered as (
    select
        *,
        sum(is_new_spell) over (
            partition by beneficiary_id order by coverage_start
            rows between unbounded preceding and current row
        ) as spell_seq
    from flagged
)

select
    beneficiary_id,
    spell_seq,
    min(coverage_start) as spell_start,
    max(coverage_end)   as spell_end,
    count(*)            as n_fills

from numbered
group by 1, 2
