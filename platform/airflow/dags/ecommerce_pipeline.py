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
    description="Build and test ecommerce data, then measure health and detect incidents",
    default_args=default_args,
    start_date=days_ago(1),
    schedule=None,
    catchup=False,
    tags=["ecommerce", "dataops"],
) as dag:
    bootstrap = BashOperator(task_id="bootstrap_raw_data", bash_command="python /opt/open-dataops/platform/jobs/bootstrap_raw_data.py")
    run_dbt = BashOperator(task_id="run_dbt", bash_command="python /opt/open-dataops/platform/jobs/run_dbt.py")
    test_dbt = BashOperator(task_id="test_dbt", bash_command="python /opt/open-dataops/platform/jobs/test_dbt.py")
    collect_dbt_metadata = BashOperator(
        task_id="collect_dbt_metadata",
        bash_command=(
            'python /opt/open-dataops/platform/jobs/collect_dbt_metadata.py '
            '--dag-id "$PIPELINE_DAG_ID" --airflow-run-id "$PIPELINE_RUN_ID" '
            '--started-at "$PIPELINE_STARTED_AT" --run-status success'
        ),
        env={
            "PIPELINE_DAG_ID": "{{ dag.dag_id }}",
            "PIPELINE_RUN_ID": "{{ run_id }}",
            "PIPELINE_STARTED_AT": "{{ dag_run.start_date.isoformat() }}",
        },
        append_env=True,
    )
    collect_data_health_metrics = BashOperator(
        task_id="collect_data_health_metrics",
        bash_command=(
            'python /opt/open-dataops/platform/jobs/collect_data_health_metrics.py '
            '--dag-id "$PIPELINE_DAG_ID" --airflow-run-id "$PIPELINE_RUN_ID"'
        ),
        env={
            "PIPELINE_DAG_ID": "{{ dag.dag_id }}",
            "PIPELINE_RUN_ID": "{{ run_id }}",
        },
        append_env=True,
    )
    detect_data_incidents = BashOperator(
        task_id="detect_data_incidents",
        bash_command=(
            'python /opt/open-dataops/platform/jobs/detect_data_incidents.py '
            '--dag-id "$PIPELINE_DAG_ID" --airflow-run-id "$PIPELINE_RUN_ID"'
        ),
        env={
            "PIPELINE_DAG_ID": "{{ dag.dag_id }}",
            "PIPELINE_RUN_ID": "{{ run_id }}",
        },
        append_env=True,
    )

    (
        bootstrap
        >> run_dbt
        >> test_dbt
        >> collect_dbt_metadata
        >> collect_data_health_metrics
        >> detect_data_incidents
    )
