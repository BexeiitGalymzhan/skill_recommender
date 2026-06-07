with flat as (
    select
        vs.vacancy_id,
        unnest(vs.skills) as skill
    from {{ ref("vacancy_skills") }} vs
),
agg as (
    select
        skill,
        count(distinct vacancy_id) as vacancy_count
    from flat
    group by skill
),
total as (
    select count(distinct vacancy_id) as total_vacancies
    from {{ ref("vacancy_skills") }} vs 
)
select
    skill,
    vacancy_count,
    round(vacancy_count * 100.0 / total_vacancies, 2) as pct_of_vacancies
from agg
cross join total
order by vacancy_count desc


