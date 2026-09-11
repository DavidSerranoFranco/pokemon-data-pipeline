"""
DAG: Pokemon Full Pipeline (ELT)
Architecture: Python (GCS Bronze) -> dbt (BigQuery Silver/Gold)
"""

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Allow Airflow to find our scripts in the /opt/airflow/scripts directory
SCRIPTS_DIR = '/opt/airflow/scripts'
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)

from extract_pokemon import get_config, extract_pokemon, transform_pokemon, load_pokemon

def task_extract_and_load_to_gcs(**context):
    """
    Extracts Pokemon data from the API, transforms it into a DataFrame,
    and loads it to Google Cloud Storage in Parquet format.
    This function is designed to be used as a PythonOperator in an Airflow DAG.
    """
    print("Starting extraction and loading to GCS...")

    config = get_config()
    extraction_timestamp = datetime.now()

    # 1. Extract
    pokemon_data = extract_pokemon(
        limit=151,
        extraction_timestamp=extraction_timestamp
    )

    # 2. Transform to DataFrame (lightweight, only for formatting)
    pokemon_df = transform_pokemon(pokemon_data)

    # 3. Load to GCS (Parquet)
    load_pokemon(pokemon_df, 'pokemon.parquet', config, extraction_timestamp)

    print(f"Loaded Records: {len(pokemon_data)}")


default_args = {
    'owner': 'david_serrano_franco',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
}

with DAG(
    dag_id='pokemon_elt_pipeline',
    default_args=default_args,
    description='Pipeline ELT: Python (GCS) -> dbt (BigQuery)',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['pokemon', 'elt', 'gcs', 'bigquery', 'dbt'],
    max_active_runs=1,
) as dag:

    # Task 1: PythonOperator to extract and load data to GCS
    extract_and_load = PythonOperator(
        task_id='extract_and_load_to_gcs',
        python_callable=task_extract_and_load_to_gcs,
    )

    # Task 2: dbt transforma los datos en BigQuery (Lee de GCS)
    # We use BashOperator because
    # it's the most native and clean way to run dbt in Airflow
    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/dbt && dbt run --profiles-dir .'
    )

    # Task 3: dbt valida la calidad de los datos
    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt && dbt test --profiles-dir .'
    )

    # The >> operator defines that the task
    # the left must complete successfully before the task on the right starts.
    extract_and_load >> dbt_run >> dbt_test
