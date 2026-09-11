# Dockerfile to the Airflow image with Polars and other dependencies installed

FROM apache/airflow:2.9.2-python3.11

# Change to root user to install system dependencies
USER root

# Install system dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Change back to the airflow user
USER airflow

# Copy and install your Python dependencies
COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt

# Verify installation
RUN python -c "import polars; print(f'Polars version: {polars.__version__}')"
RUN python -c "import fsspec; print(f'fsspec version: {fsspec.__version__}')"
RUN python -c "import gcsfs; print(f'gcsfs version: {gcsfs.__version__}')"
RUN python -c "import google.cloud.storage; print(f'google-cloud-storage version: {google.cloud.storage.__version__}')"