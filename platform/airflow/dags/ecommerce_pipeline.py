from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "data-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}

with DAG(
    dag_id="ecommerce_pipeline",
    description="Bootstrap raw ecommerce data, build dbt models, and test them",
    default_args=default_args,
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    tags=["ecommerce", "dataops"],
) as dag:
    bootstrap = BashOperator(task_id="bootstrap_raw_data", bash_command="python /opt/open-dataops/platform/jobs/bootstrap_raw_data.py")
    run_dbt = BashOperator(task_id="run_dbt", bash_command="python /opt/open-dataops/platform/jobs/run_dbt.py")
    test_dbt = BashOperator(task_id="test_dbt", bash_command="python /opt/open-dataops/platform/jobs/test_dbt.py")

    bootstrap >> run_dbt >> test_dbt
