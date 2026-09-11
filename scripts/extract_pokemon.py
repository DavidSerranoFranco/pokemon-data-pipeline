# -*- coding: utf-8 -*-
from datetime import datetime
import os
import requests
import polars as pl
import fsspec


now = datetime.now()
print(f"Starting extraction at: {now.strftime('%Y-%m-%d %H:%M:%S')}")


def get_config():
    """Determines the configuration for storage based on the environment."""
    is_cloud = os.getenv('ENVIRONMENT') == 'production'

    if is_cloud:
        bucket = os.getenv('GCS_BUCKET', 'pokemon-data-lake')
        return {
            'storage_type': 'gcs',
            'base_path': f"gs://{bucket}/raw",
        }
    else:
        # Local configuration
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        return {
            'storage_type': 'local',
            'base_path': os.path.join(project_root, 'data', 'raw'),
        }


def get_partitioned_path(base_path, filename, timestamp=None):
    """
    Generates a partitioned path based on the current
    date for storing the extracted data.

    Example:
    base_path = 'data/raw'
    filename = 'pokemon.parquet'
    → 'data/raw/year=2024/month=06/day=13/pokemon.parquet'
    """

    if timestamp is None:
        now_partition = datetime.now()
    else:
        now_partition = timestamp

    # Extract date components
    year = now_partition.strftime('%Y')
    month = now_partition.strftime('%m')
    day = now_partition.strftime('%d')

    # Build the partitioned path
    if base_path.startswith('gs://'):
        partitioned_path = f"{base_path}/year={year}/month={month}/day={day}/{filename}"
    else:
        partitioned_path = os.path.join(
            base_path,
            f'year={year}',
            f'month={month}',
            f'day={day}',
            filename   
        )

    return partitioned_path


def extract_pokemon(limit, extraction_timestamp):
    """Extracts Pokemon data from the PokeAPI for a given Pokemon ID."""

    list_pokemon = []

    for i in range(1, limit + 1):
        try:
            url = f'https://pokeapi.co/api/v2/pokemon/{i}'
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors

            data = response.json()

            pokemon_data = {
                'id': data['id'],
                'name': data['name'],
                'height': data['height'],
                'weight': data['weight'],
                'types':
                    [t['type']['name'] for t in data['types']],
                'abilities':
                    [a['ability']['name'] for a in data['abilities']],
                'extracted_at':
                    extraction_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }

            list_pokemon.append(pokemon_data)

        except requests.exceptions.Timeout:
            print(f"Timeout error for Pokemon ID: {i}")
            continue  # Skip to the next iteration
        except Exception as e:
            print(f"Error occurred while retrieving data for Pokemon ID: {i}")
            print(f"Error details: {e}")
            continue  # Skip to the next iteration

    print(f"Finished extracting. Pokemon found: {len(list_pokemon)}")
    return list_pokemon


def transform_pokemon(pokemon_data):
    """Transforms the extracted Pokemon data into a Polars DataFrame."""
    df = pl.from_records(pokemon_data)
    return df


def load_pokemon(pokemon_df, filename, config, extraction_timestamp):
    """Loads the transformed Pokemon data into a parquet format."""
    filepath = get_partitioned_path(
        config['base_path'], filename, extraction_timestamp
        )

    if config['storage_type'] == 'local':
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with fsspec.open(filepath, 'wb') as buffer:
        pokemon_df.write_parquet(buffer)

    print(f"Data loaded successfully into '{filepath}'.")


if __name__ == "__main__":
    config = get_config()
    print(f"Using storage type: {config['storage_type']}")

    LIMIT = 151
    extraction_timestamp = datetime.now()

    print("Extracting data from PokeAPI...")
    pokemon_data = extract_pokemon(LIMIT, extraction_timestamp)

    print("Transforming to Polars DataFrame...")
    pokemon_df = transform_pokemon(pokemon_data)

    print("Loading to Storage...")

    load_pokemon(pokemon_df, 'pokemon.parquet', config, extraction_timestamp)

    print("Extraction, transformation, and loading completed successfully.")

    # Solo imprimimos esto si estamos en local para debug
    if config['storage_type'] == 'local':
        print(pokemon_df.head(5))
