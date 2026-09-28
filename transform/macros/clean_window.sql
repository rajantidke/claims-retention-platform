{# The data window: everything from the earliest data through the clean-window end. #}
{% macro in_clean_window(date_col) %}
    {{ date_col }} between date '{{ var("study_start") }}'
                       and date '{{ var("clean_window_end") }}'
{% endmacro %}

{# The analysis window: only months with trustworthy volume (Gate 4). #}
{% macro in_analysis_window(date_col) %}
    {{ date_col }} between date '{{ var("analysis_start") }}'
                       and date '{{ var("clean_window_end") }}'
{% endmacro %}

{# Cap a date at the end of the clean window. #}
{% macro clip_to_clean_window(date_col) %}
    least({{ date_col }}, date '{{ var("clean_window_end") }}')
{% endmacro %}
