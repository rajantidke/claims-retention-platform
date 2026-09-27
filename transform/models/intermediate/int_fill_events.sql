select
    beneficiary_id,
    pde_id,
    fill_date,
    product_service_id,
    labeler_cd,
    quantity_dispensed,
    days_supply,
    patient_pay_amount,
    total_rx_cost_amount,

    fill_date <= cast('{{ var("clean_window_end") }}' as date)  as in_clean_window,
    days_supply = 0                                             as is_zero_days_supply,

    fill_date                                                   as coverage_start,
    case
        when days_supply = 0 then null
        else fill_date + (days_supply - 1)
    end                                                         as coverage_end

from {{ ref('stg_pde') }}
