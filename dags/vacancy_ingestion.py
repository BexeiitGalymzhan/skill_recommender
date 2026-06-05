from airflow.sdk import dag, task
from pendulum import datetime
from datetime import timedelta

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


@dag(
    dag_id="vacancy_ingestion_dag",
    schedule="@daily",
    start_date=datetime(2026, 6, 4, tz="Asia/Almaty"),
    is_paused_upon_creation=False,
    catchup=False,
    default_args=default_args,
)
def vacancy_ingestion_dag():
    @task.python(retries=0)
    def run_vacancy_ingestion_task(**context):
        from src.extract.hh_vacancies import run_vacancy_ingestion
        ti = context["ti"]
        ds = context["data_interval_start"]

        key = run_vacancy_ingestion(ds=ds)
        ti.xcom_push(key="s3_key", value=key)

    @task.python
    def run_bronze_load_task(**context):
        from src.load.bronze_vacancies import run_bronze_load
        ti = context["ti"]
        s3_key = ti.xcom_pull(
            key="s3_key", task_ids="run_vacancy_ingestion_task")

        run_bronze_load(s3_key)

    first = run_vacancy_ingestion_task()
    second = run_bronze_load_task()

    first >> second


vacancy_ingestion_dag()
