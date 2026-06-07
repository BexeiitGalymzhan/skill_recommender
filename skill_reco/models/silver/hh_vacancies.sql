{{
  config(
    materialized = 'incremental',
    unique_key = 'vacancy_id'
    )
}}

with bronze as (
    select * from {{ source('bronze', 'hh_vacancies') }}

    {% if is_incremental() %}
        where fetched_at > (select max(fetched_at) from {{ this }})
    {% endif %}
),
deduped as (
    select *
    from bronze
    qualify row_number() over (
        partition by id
        order by fetched_at desc
    ) = 1
)
select
    id                                                      as vacancy_id,
    name                                                    as title,

    -- employer
    json_extract_string(employer, '$.name')                 as employer_name,
    json_extract_string(employer, '$.url')                  as employer_url,

    -- salary
    cast(json_extract(salary, '$.from') as integer)         as salary_from,
    cast(json_extract(salary, '$.to') as integer)           as salary_to,
    json_extract_string(salary, '$.currency')               as currency,
    cast(json_extract(salary, '$.gross') as boolean)        as salary_is_gross,

    -- experience & employment
    json_extract_string(experience, '$.id')                 as experience_id,
    json_extract_string(experience, '$.name')               as experience_name,
    json_extract_string(employment_form, '$.id')            as employment_id,
    json_extract_string(employment_form, '$.name')          as employment_name,

    -- area
    json_extract_string(area, '$.name')                     as area_name,
    json_extract_string(area, '$.id')                       as area_id,

    -- keep these as JSON strings for further processing in gold
    key_skills,
    description,

    published_at,
    fetched_at,
    _query,
    alternate_url                                     as vacancy_url,
    archived
from deduped
where archived = 'false'