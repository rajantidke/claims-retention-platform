select
    "DESYNPUF_ID"                       as beneficiary_id,
    source_year,

    {{ parse_synpuf_date('BENE_BIRTH_DT') }}   as birth_date,
    {{ parse_synpuf_date('BENE_DEATH_DT') }}   as death_date,

    "BENE_SEX_IDENT_CD"                 as sex_code,
    "BENE_RACE_CD"                      as race_code,
    "SP_STATE_CODE"                     as state_code,
    "BENE_COUNTY_CD"                    as county_code,


    cast("BENE_HI_CVRAGE_TOT_MONS" as integer)   as part_a_coverage_months,
    cast("BENE_SMI_CVRAGE_TOT_MONS" as integer)  as part_b_coverage_months,
    cast("BENE_HMO_CVRAGE_TOT_MONS" as integer)  as hmo_coverage_months,
    cast("PLAN_CVRG_MOS_NUM" as integer)         as part_d_coverage_months,


    ("BENE_ESRD_IND" = 'Y') as has_esrd,
    -- Chronic condition flags: source uses 1=Yes, 2=No (NOT 0/1, see fidelity_audit.md)
    ("SP_ALZHDMTA" = '1')  as has_alzheimers,
    ("SP_CHF" = '1')       as has_heart_failure,
    ("SP_CHRNKIDN" = '1')  as has_chronic_kidney_disease,
    ("SP_CNCR" = '1')      as has_cancer,
    ("SP_COPD" = '1')      as has_copd,
    ("SP_DEPRESSN" = '1')  as has_depression,
    ("SP_DIABETES" = '1')  as has_diabetes,
    ("SP_ISCHMCHT" = '1')  as has_ischemic_heart_disease,
    ("SP_OSTEOPRS" = '1')  as has_osteoporosis,
    ("SP_RA_OA" = '1')     as has_ra_oa,
    ("SP_STRKETIA" = '1')  as has_stroke_tia,

    cast("MEDREIMB_IP" as double)   as ip_medicare_reimb_amount,
    cast("BENRES_IP" as double)     as ip_beneficiary_resp_amount,
    cast("PPPYMT_IP" as double)     as ip_primary_payer_amount,
    cast("MEDREIMB_OP" as double)   as op_medicare_reimb_amount,
    cast("BENRES_OP" as double)     as op_beneficiary_resp_amount,
    cast("PPPYMT_OP" as double)     as op_primary_payer_amount,
    cast("MEDREIMB_CAR" as double)  as car_medicare_reimb_amount,
    cast("BENRES_CAR" as double)    as car_beneficiary_resp_amount,
    cast("PPPYMT_CAR" as double)    as car_primary_payer_amount

from {{ source('raw', 'beneficiary') }}
