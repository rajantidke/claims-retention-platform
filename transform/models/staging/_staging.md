{% docs staging_conventions %}

**Staging conventions (all `stg_*` models).**
Staging renames and types. It does not filter, join, or aggregate.

- `*_id` identifiers, `*_date` dates, `*_amount` money, `*_code` coded values,
  `has_*` / `is_*` booleans. (`*_code` rather than the runbook's `*_cd`.
  A deliberate spelling choice, applied consistently.)
- `DESYNPUF_ID` becomes `beneficiary_id` everywhere.
- Chronic flags use `yn_flag()` (1 = Yes, 2 = No, anything else null so
  `not_null` tests catch it). ESRD uses Y / 0 per codebook BEN-6.
- Fields the fidelity audit found unreliable (`product_service_id`,
  `labeler_cd`, `days_supply`, `claim_segment`) are carried through and
  caveated in their model descriptions, never silently cleaned.

{% enddocs %}
