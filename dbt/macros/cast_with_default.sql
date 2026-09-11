{#

  Macro: cast_with_default
  Description: Converts a column to a specific data type, 
               replacing NULLs with a default value.
  
  Parameters:
    - column_name: Name of the column to convert
    - data_type: Target data type (FLOAT64, INT64, STRING, etc.)
    - default_value: Value to use if the column is NULL

#}

{% macro cast_with_default(column_name, data_type, default_value) %}
    COALESCE(CAST({{ column_name }} AS {{ data_type }}), {{ default_value }})
{% endmacro %}