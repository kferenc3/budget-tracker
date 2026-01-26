{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- set custom = custom_schema_name | trim if custom_schema_name is not none else none -%}

  {%- if target.name == 'prod' -%}
      {# In prod, take folder schema literally #}
      {{ custom if custom is not none else target.schema }}
  {%- else -%}
      {# In dev, isolate by prefixing with target.schema #}
      {{ target.schema if custom is none else target.schema ~ '_' ~ custom }}
  {%- endif -%}
{%- endmacro %}
