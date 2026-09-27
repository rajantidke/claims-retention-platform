select mm.beneficiary_id, mm.month_start, bene.death_date
from {{ ref('int_member_months') }} mm
inner join {{ ref('stg_beneficiary') }} bene
    on mm.beneficiary_id = bene.beneficiary_id
    and mm.source_year = bene.source_year
where mm.is_alive
    and bene.death_date is not null
    and mm.month_start > bene.death_date
