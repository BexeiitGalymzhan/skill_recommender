with flat as (
    select
        vacancy_id,
        unnest(skills) as skill
    from {{ ref("vacancy_skills") }}
)
select
    a.skill as skill_a,
    b.skill as skill_b,
    count(distinct a.vacancy_id) as co_occurrence_count
from flat a
join flat b using (vacancy_id)
where a.skill < b.skill  -- avoid duplicates
group by a.skill, b.skill
order by co_occurrence_count desc