with spell_total as (
    select sum(n_fills) as total from {{ ref('int_coverage_spells') }}
),
fill_event_total as (
    select count(*) as total
    from {{ ref('int_fill_events') }}
    where not is_zero_days_supply
)

select spell_total.total as spell_fills, fill_event_total.total as event_fills
from spell_total, fill_event_total
where spell_total.total != fill_event_total.total
