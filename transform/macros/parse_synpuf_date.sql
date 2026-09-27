{% macro parse_synpuf_date(column_name) %}
    CAST(STRPTIME({{ column_name }}, '%Y%m%d') AS DATE)
{% endmacro %}
