import re
import json
import pandas as pd


def strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text).lower()


def model(dbt, session):
    dbt.config(
        materialized="incremental",
        unique_key="vacancy_id"
    )

    vacancies_df = dbt.ref("hh_vacancies").df()
    skills_df = dbt.ref("skills").df()

    if len(vacancies_df) == 0:
        return pd.DataFrame(columns=["vacancy_id", "skills"])

    known_skills = skills_df["skill_name"].str.lower().tolist()

    def extract_from_description(description: str) -> list[str]:
        clean = strip_html(description)
        found = []
        for skill in known_skills:
            # use word boundary for short skills, substring for multi-word
            if len(skill) <= 2:
                pattern = rf'\b{re.escape(skill)}\b'
            else:
                pattern = re.escape(skill)
            if re.search(pattern, clean):
                found.append(skill)
        return found

    def parse_key_skills(ks: str) -> list[str]:
        if not ks or ks == "[]":
            return []
        try:
            parsed = json.loads(ks)
            return [s["name"].lower() for s in parsed if isinstance(s, dict)]
        except Exception:
            return []

    rows = []
    for _, row in vacancies_df.iterrows():
        vacancy_id = row["vacancy_id"]
        key_skills = parse_key_skills(row.get("key_skills"))
        desc_skills = extract_from_description(row.get("description", ""))
        # dedup, preserve order
        all_skills = list(dict.fromkeys(key_skills + desc_skills))
        rows.append({"vacancy_id": vacancy_id, "skills": all_skills})

    return pd.DataFrame(rows, columns=["vacancy_id", "skills"])
