{% set checks = [
    ('fct_engagement_rate_monthly', 'month_start'),
    ('fct_cohort_retention',        'calendar_month'),
    ('fct_utilization_monthly',     'month_start'),
    ('fct_pdc_monthly',             'month_start')
] %}

{% for model, col in checks %}
    {% if not loop.first %}union all{% endif %}
    select '{{ model }}' as model_name, {{ col }} as bad_date
    from {{ ref(model) }}
    where {{ col }} > date '{{ var("clean_window_end") }}'
{% endfor %}
