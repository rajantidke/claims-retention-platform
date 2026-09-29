select
    month_start,

    count(*)                                                    as n_enrolled_all,
    sum(case when is_active then 1 else 0 end)                  as n_active_all,
    100.0 * sum(case when is_active then 1 else 0 end)
        / count(*)                                              as rate_all,

    sum(case when has_full_year_part_d then 1 else 0 end)       as n_enrolled_strict,
    sum(case when has_full_year_part_d and is_active
             then 1 else 0 end)                                 as n_active_strict,
    100.0 * sum(case when has_full_year_part_d and is_active
                      then 1 else 0 end)
        / nullif(sum(case when has_full_year_part_d then 1 else 0 end), 0)
                                                                as rate_strict,

    100.0 * sum(case when has_full_year_part_d then 1 else 0 end)
        / count(*)                                              as strict_share

from {{ ref('fct_monthly_active') }}
where {{ in_analysis_window('month_start') }}
    and is_alive
group by 1
order by 1
