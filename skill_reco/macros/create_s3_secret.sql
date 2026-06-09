{% macro create_s3_secret() %}
  {% set sql %}
    CREATE OR REPLACE SECRET s3_secret (
      TYPE S3,
      KEY_ID '{{ env_var("AWS_ACCESS_KEY_ID") }}',
      SECRET '{{ env_var("AWS_SECRET_ACCESS_KEY") }}',
      REGION '{{ env_var("AWS_REGION") }}',
      ENDPOINT 's3.{{ env_var("AWS_REGION") }}.amazonaws.com',
      USE_SSL true
    );
  {% endset %}
  {% do run_query(sql) %}
{% endmacro %}