{% macro yn_flag(col) %}
    {# DE-SynPUF chronic flags: 1 = Yes, 2 = No. NOT 1/0. Anything else -> null, so tests can catch it. #}
    case when {{ col }} = '1' then true
         when {{ col }} = '2' then false
    end
{% endmacro %}
