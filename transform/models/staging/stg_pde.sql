select
    "DESYNPUF_ID"                                  as beneficiary_id,
    "PDE_ID"                                       as pde_id,
    {{ parse_synpuf_date('SRVC_DT') }}             as fill_date,
    "PROD_SRVC_ID"                                 as product_service_id,
    cast("QTY_DSPNSD_NUM" as double)                as quantity_dispensed,
    cast("DAYS_SUPLY_NUM" as integer)               as days_supply,
    cast("PTNT_PAY_AMT" as double)                  as patient_pay_amount,
    cast("TOT_RX_CST_AMT" as double)                as total_rx_cost_amount

from {{ source('raw', 'pde') }}
