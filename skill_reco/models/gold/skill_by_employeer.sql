with flat as (
    select
        vacancy_id,
        unnest(skills) as skill
    from {{ ref("vacancy_skills") }}
),
company_totals as (
    select employer_name, count(distinct vacancy_id) as total_vacancies
    from {{ ref("hh_vacancies") }}
    group by employer_name
),
agg as (
    select
        v.employer_name,
        vs.skill,
        count(distinct vs.vacancy_id) as vacancy_count
    from flat vs
    join {{ ref("hh_vacancies") }} v using (vacancy_id)
    group by v.employer_name, vs.skill
)
select
    a.employer_name,
    a.skill,
    a.vacancy_count,
    ct.total_vacancies,
    round(a.vacancy_count * 100.0 / ct.total_vacancies, 2) as pct_within_company
from agg a
join company_totals ct using (employer_name)
order by a.employer_name, pct_within_company desc