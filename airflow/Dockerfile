FROM apache/airflow:2.10.4-python3.11

# Explicit WORKDIR (inherited from base image, but clearer to state)
WORKDIR /opt/airflow

# Copy requirements first (for Docker cache efficiency)
COPY airflow/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy our source code (chown to airflow user who runs the container)
COPY --chown=airflow:root src/ src/
COPY --chown=airflow:root config/ config/

# Set PYTHONPATH so our modules are importable
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"
