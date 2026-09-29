select beneficiary_id, month_start, n_fills, is_active
from {{ ref('fct_monthly_active') }}
where (n_fills = 0 and is_active)
   or (n_fills > 0 and not is_active)
