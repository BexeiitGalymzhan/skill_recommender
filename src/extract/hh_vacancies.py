import logging
import requests
import time
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from src.storage.s3_client import s3_client
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

RETRY_POLICY = dict(
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@retry(**RETRY_POLICY)
def get_valid_token() -> str:
    logger.info("Fetching access token...")
    response = requests.post(
        "https://hh.ru/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("CLIENT_ID"),
            "client_secret": os.getenv("CLIENT_SECRET"),
        },
    )
    response.raise_for_status()
    token = response.json().get("access_token", "")
    if not token:
        raise ValueError("Empty access_token in response")
    logger.info("Token fetched successfully.")
    return token


@retry(**RETRY_POLICY)
def get_vacancy_details(vacancy_id: str, token: str) -> dict:
    logger.debug("Fetching details for vacancy %s", vacancy_id)
    response = requests.get(
        f"https://api.hh.ru/vacancies/{vacancy_id}",
        headers={
            "User-Agent": "skill-recommender/1.0 (bexeiit1@gmail.com)",
            "Authorization": f"Bearer {token}",
        },
    )
    response.raise_for_status()
    return response.json()


@retry(**RETRY_POLICY)
def fetch_vacancy_page(token: str, query: str, area: int, page: int) -> dict:
    logger.debug(
        "Fetching vacancy list — query=%s area=%s page=%s", query, area, page)
    response = requests.get(
        "https://api.hh.ru/vacancies",
        headers={
            "User-Agent": "skill-recommender/1.0 (bexeiit1@gmail.com)",
            "Authorization": f"Bearer {token}",
        },
        params={"text": query, "area": area, "per_page": 20, "page": page},
    )
    response.raise_for_status()
    return response.json()


def fetch_vacancies_raw(token: str, query: str = "data engineer", area: int = 40) -> list:
    all_vacancies = []
    page = 0

    while page < 5:
        logger.info("Fetching page %d (query=%s, area=%s)", page, query, area)

        data = fetch_vacancy_page(token, query, area, page)
        items = data.get("items", [])

        if not items:
            logger.info("No items on page %d, stopping.", page)
            break

        logger.info("Page %d: %d vacancies found.", page, len(items))

        for item in items:
            vacancy_id = item["id"]
            try:
                details = get_vacancy_details(vacancy_id, token)
                details["_query"] = query
                all_vacancies.append(details)
                logger.debug("Saved raw vacancy %s (%s)",
                             vacancy_id, details.get("name"))
            except Exception as e:
                logger.error(
                    "Failed to fetch vacancy %s after retries: %s", vacancy_id, e)

            time.sleep(0.3)

        page += 1
        if page >= data.get("pages", 1):
            logger.info("Reached last page (%d), stopping.", page)
            break

    logger.info("Done. Total vacancies fetched: %d", len(all_vacancies))
    return all_vacancies


def run_vacancy_ingestion(query: str = "data engineer", area: int = 40, ds=None):
    token = os.getenv("TOKEN") or get_valid_token()

    vacancies = fetch_vacancies_raw(token, query=query, area=area)
    logger.info(f"Fetched {len(vacancies)} vacancies")

    s3_client.upload_file(vacancies, object_name="vacancies", ds=ds)


run_vacancy_ingestion()
