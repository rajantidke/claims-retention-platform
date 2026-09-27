select
    "CLM_ID"                          as claim_id,
    "SEGMENT"                         as claim_segment,
    "DESYNPUF_ID"                     as beneficiary_id,

    {{ parse_synpuf_date('CLM_FROM_DT') }}  as claim_from_date,
    {{ parse_synpuf_date('CLM_THRU_DT') }}  as claim_thru_date,

    cast("CLM_PMT_AMT" as double)     as payment_amount,

    "ADMTNG_ICD9_DGNS_CD"  as admitting_diagnosis_code,
    "ICD9_DGNS_CD_1"       as diagnosis_code_1,
    "ICD9_DGNS_CD_2"       as diagnosis_code_2,
    "ICD9_DGNS_CD_3"       as diagnosis_code_3,
    "ICD9_DGNS_CD_4"       as diagnosis_code_4,
    "ICD9_DGNS_CD_5"       as diagnosis_code_5,
    "ICD9_DGNS_CD_6"       as diagnosis_code_6,
    "ICD9_DGNS_CD_7"       as diagnosis_code_7,
    "ICD9_DGNS_CD_8"       as diagnosis_code_8,
    "ICD9_DGNS_CD_9"       as diagnosis_code_9,
    "ICD9_DGNS_CD_10"      as diagnosis_code_10

from {{ source('raw', 'outpatient') }}
