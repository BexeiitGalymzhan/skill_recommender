with flat as (
	select 
		vacancy_id,
		unnest(skills) as skill
	from {{ ref("vacancy_skills") }} vs 
)
select
    v.experience_name,
    vs.skill,
    count(distinct vs.vacancy_id)   as vacancy_count
from flat vs
join {{ ref("hh_vacancies") }} v using (vacancy_id)
group by v.experience_name, vs.skill
order by v.experience_name, vacancy_count desc