#!/bin/bash
set -e

cd "$(dirname "$0")/.."  # Go to project root

echo "Exporting dependencies from pyproject.toml..."
uv export --no-dev --no-hashes -o airflow/requirements.txt

echo "Building Airflow image..."
docker compose -f airflow/docker-compose.yaml build

echo "Starting Airflow services..."
docker compose -f airflow/docker-compose.yaml up -d

echo ""
echo "Airflow is starting up..."
echo "  - Web UI: http://localhost:8080"
echo "  - Username: admin"
echo "  - Password: admin"
echo ""
echo "Wait ~30 seconds for services to be ready."
echo "Run 'docker compose -f airflow/docker-compose.yaml logs -f' to watch startup."
