# Lemmy Recommendation System

A data engineering project that builds a content recommendation pipeline for [Lemmy](https://join-lemmy.org/) (a federated Reddit alternative). Fetches trending communities and posts, processes them through a medallion architecture (bronze/silver/gold), and will eventually power ML-based recommendations.

## Architecture

```
Lemmy API
    │
    ▼
┌──────────────────────────────────────────┐
│  BRONZE (S3) — Raw JSON, timestamped     │
└─────────────────┬────────────────────────┘
                  │  clean, validate, enrich
                  ▼
┌──────────────────────────────────────────┐
│  SILVER (S3) — Parquet, partitioned      │
│  + enrichment: engagement_ratio,         │
│    age_hours, is_active_community, etc.  │
└─────────────────┬────────────────────────┘
                  │  deduplicate, merge tags
                  ▼
┌──────────────────────────────────────────┐
│  GOLD (S3) — Merged, deduplicated        │
│  One row per community/post with all     │
│  contributing source tags tracked        │
└──────────────────────────────────────────┘
```

**16 independent data streams** (10 post sort types + 6 community sort types), each with its own Airflow DAG. Two gold merge DAGs aggregate across tags using Airflow Dataset triggers.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Data Processing | Polars |
| Storage | AWS S3 (Parquet) |
| Orchestration | Apache Airflow 2.10.4 |
| Infrastructure | Terraform (EC2, VPC, IAM) |
| CI/CD | GitHub Actions |
| Local Dev | LocalStack (S3), Docker Compose |

## Project Structure

```
├── src/
│   ├── __main__.py          # Pipeline entry point
│   ├── config.py            # YAML config loader
│   ├── ingestion/           # Lemmy API fetching
│   ├── transformation/      # Clean, enrich, merge
│   ├── storage/             # S3 read/write operations
│   ├── schemas/             # Schema contracts (silver, gold)
│   ├── models/              # TypedDict API response models
│   └── pipeline/            # RunContext for lineage tracking
├── airflow/
│   ├── dags/pipeline.py     # 18 DAGs (16 source + 2 gold)
│   ├── docker-compose.yaml  # Local Airflow setup
│   └── Dockerfile
├── terraform/               # AWS infrastructure as code
├── tests/
│   ├── integration/         # E2E tests with LocalStack
│   ├── test_schema_contracts.py
│   ├── test_dag_validation.py
│   └── ...                  # Unit tests
├── config/config.yaml       # Data streams, S3 buckets, thresholds
└── .github/workflows/ci.yml # CI pipeline
```

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker & Docker Compose (for Airflow and LocalStack)
- AWS credentials (or LocalStack for local development)

### Install Dependencies

```bash
uv sync --group dev
```

### Configure Environment

Create a `.env` file in the project root:

```env
# For local development with LocalStack
USE_LOCALSTACK=true
LOCALSTACK_ENDPOINT=http://localhost:4566

# For AWS (production)
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_DEFAULT_REGION=us-east-1
```

### Run the Pipeline

```bash
# Run the full pipeline (all sources, all tags)
python -m src

# Or start Airflow for scheduled orchestration
cd airflow && docker compose up -d
# Airflow UI: http://localhost:8080
```

## Testing

```bash
# Unit tests (no external dependencies)
uv run pytest tests/ -m "not integration"

# Schema contract tests (included in unit tests)
uv run pytest tests/test_schema_contracts.py

# DAG validation (requires Airflow installed)
uv run pytest tests/test_dag_validation.py

# Integration tests (requires LocalStack running)
docker compose -f airflow/docker-compose.yaml up localstack -d
uv run pytest tests/integration/ -m integration

# Linting & formatting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run mypy src/
```

## CI Pipeline

GitHub Actions runs on every push and PR to `main`:

| Job | What it checks |
|-----|---------------|
| `lint` | `ruff check` + `ruff format --check` |
| `typecheck` | `mypy src/` (strict mode) |
| `test-unit` | Unit + schema contract tests |
| `test-integration` | E2E pipeline tests against LocalStack |
| `test-dags` | Airflow DAG loading + structure validation |

## Data Streams

The pipeline fetches from the Lemmy API with different sort strategies:

| Source | Tags | Schedule |
|--------|------|----------|
| Posts | hot, active, scaled | Every 3h |
| Posts | new | Every 4h |
| Posts | most_comments | Every 6h |
| Posts | top_day | Every 8h |
| Posts | top_week, top_month, top_year, top_all | Every 12h |
| Communities | hot, active | Every 3h |
| Communities | new | Every 4h |
| Communities | top_day | Every 8h |
| Communities | top_week, top_month | Every 12h |

## Key Features

- **Data Lineage**: Every record tracks its `run_id`, `source_file`, and contributing `sources`
- **Enrichment**: Derived columns like `engagement_ratio`, `comment_density`, `is_active_community`, `age_hours`
- **Schema Contracts**: Silver and gold schemas defined as code with contract tests
- **Deduplication**: Gold layer merges the same entity from multiple tags into one row
- **Data Quality**: Null filtering, required field validation, quality checks during transformation

## Roadmap

### Completed

- **M1** — Lemmy API ingestion to S3 bronze layer
- **M2** — Bronze to silver transformation (Polars + Parquet)
- **M3** — Airflow orchestration (18 DAGs) + EC2 deployment via Terraform
- **MX.1** — Data lineage tracking + silver enrichment columns
- **MX.2** — Infrastructure hardening (health checks, Terraform outputs)
- **MX.3** — Testing & CI/CD (integration tests, schema contracts, GitHub Actions)

### Up Next

- **M4** — User feedback CLI (rate communities/posts, store preferences)
- **M5** — Cold start recommendations (Groq embeddings + pgvector)
- **M6** — Warm start (learn from user ratings over time)

### Future

- **M7** — Post-level recommendations
- **M8** — Validation & analytics dashboard
- **M9** — Scale to PySpark
- **M10** — Web interface (FastAPI + frontend)

See [`design.md`](design.md) for the full roadmap with detailed specifications.
