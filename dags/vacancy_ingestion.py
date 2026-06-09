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

    @task(retries=1)
    def run_dbt(**context):
        import subprocess
        import shutil

        dbt_path = shutil.which("dbt")
        if not dbt_path:
            raise RuntimeError("dbt not found in PATH")

        result = subprocess.run(
            [
                dbt_path, "run",
                "--project-dir", "/opt/airflow/dbt",
                "--profiles-dir", "/opt/airflow/dbt",
                "--target", "prod",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"dbt run failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    first = run_vacancy_ingestion_task()
    second = run_bronze_load_task()
    third = run_dbt()

    first >> second >> third


vacancy_ingestion_dag()
