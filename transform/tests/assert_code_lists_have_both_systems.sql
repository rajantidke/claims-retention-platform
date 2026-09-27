select concept
from {{ ref('seed_code_lists') }}
group by concept
having count(distinct code_system) < 2
