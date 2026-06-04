import requests
import time
from dotenv import load_dotenv
import os

load_dotenv()


def get_valid_token() -> str:
    try:
        token_response = requests.post(
            "https://hh.ru/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": os.getenv("CLIENT_ID"),
                "client_secret": os.getenv("CLIENT_SECRET"),
            }
        )

        token_data = token_response.json()
        # Debug: print the entire response
        print("Token response:", token_data)
        return token_data.get("access_token", "")
    except Exception as e:
        print("Error fetching token:", e)
        raise


def get_vacancy_details(vacancy_id: str, token: str) -> dict:
    headers = {
        "User-Agent": "skill-recommender/1.0 (bexeiit1@gmail.com)",
        "Authorization": f"Bearer {token}",
    }
    response = requests.get(
        f"https://api.hh.ru/vacancies/{vacancy_id}",
        headers=headers,
    )
    return response.json()


def fetch_vacancies_with_skills(token: str, query: str = "data engineer", area: int = 40) -> list:
    headers = {
        "User-Agent": "skill-recommender/1.0 (bexeiit1@gmail.com)",
        "Authorization": f"Bearer {token}",
    }

    all_vacancies = []
    page = 0

    while page < 1:
        # Step 1 — get vacancy list
        response = requests.get(
            "https://api.hh.ru/vacancies",
            headers=headers,
            params={
                "text": query,
                "area": area,
                "per_page": 20,
                "page": page,
            },
        )
        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        # Step 2 — fetch full details for each vacancy
        for item in items:
            vacancy_id = item["id"]
            details = get_vacancy_details(vacancy_id, token)

            all_vacancies.append(details)
            time.sleep(0.3)

        page += 1
        if page >= data.get("pages", 1):
            break

    return all_vacancies


# Usage

token = os.getenv("TOKEN") if os.getenv("TOKEN") else get_valid_token()

vacancies = fetch_vacancies_with_skills(token, query="data", area=40)
print(f"Fetched {len(vacancies)} vacancies with skills:")
print(vacancies[:1])  # Print first 1 vacancy for brevity
