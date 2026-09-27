select
    "CLM_ID"                     as claim_id,
    "DESYNPUF_ID"                as beneficiary_id,

    {{ parse_synpuf_date('CLM_FROM_DT') }}  as claim_from_date,
    {{ parse_synpuf_date('CLM_THRU_DT') }}  as claim_thru_date,

    coalesce(cast("LINE_NCH_PMT_AMT_1" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_2" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_3" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_4" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_5" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_6" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_7" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_8" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_9" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_10" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_11" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_12" as double), 0)
    + coalesce(cast("LINE_NCH_PMT_AMT_13" as double), 0)
        as payment_amount

from {{ source('raw', 'carrier') }}
