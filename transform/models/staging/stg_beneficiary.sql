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


    -- ESRD uses Y / 0 (codebook BEN-6), not 1/2
    case when "BENE_ESRD_IND" = 'Y' then true
         when "BENE_ESRD_IND" = '0' then false

    end                           as has_esrd,

    -- Chronic condition flags: 1 = Yes, 2 = No, via the yn_flag macro
    {{ yn_flag('SP_ALZHDMTA') }}  as has_alzheimers,
    {{ yn_flag('SP_CHF') }}       as has_heart_failure,
    {{ yn_flag('SP_CHRNKIDN') }}  as has_chronic_kidney_disease,
    {{ yn_flag('SP_CNCR') }}      as has_cancer,
    {{ yn_flag('SP_COPD') }}      as has_copd,
    {{ yn_flag('SP_DEPRESSN') }}  as has_depression,
    {{ yn_flag('SP_DIABETES') }}  as has_diabetes,
    {{ yn_flag('SP_ISCHMCHT') }}  as has_ischemic_heart_disease,
    {{ yn_flag('SP_OSTEOPRS') }}  as has_osteoporosis,
    {{ yn_flag('SP_RA_OA') }}     as has_ra_oa,
    {{ yn_flag('SP_STRKETIA') }}  as has_stroke_tia,

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
