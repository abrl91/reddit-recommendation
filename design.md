# Lemmy Recommendation System

## Key Principles to Remember
1. **MVP First**: Make it work before making it pretty
2. **Validate Early**: Test each milestone before moving forward
3. **Iterate**: Don't perfect anything until you've proven it works
4. **Learn by Doing**: Build real working code, not just documentation
5. **Stay Focused**: One milestone at a time, resist scope creep
6. **Celebrate Wins**: Each green checkmark is progress!

## Project Overview

### What We're Building

A Lemmy content recommendation system that learns user preferences. Users rate communities and posts (like/dislike), and the system suggests personalized content using machine learning embeddings and similarity matching.

### Core Features

- **Data Pipeline**: Automated collection of trending Lemmy content
- **User Preference Learning**: CLI-based rating system for communities and posts
- **Smart Recommendations**: ML-powered suggestions based on user preferences
- **Cold Start Solution**: Begin with popular content, no account required
- **Validation System**: Test and measure recommendation accuracy
- **Analytics Dashboard**: Insights on trends and user preferences

### Why This Project?

- **Learning Focus**: Covers data engineering, ML, orchestration, and cloud services
- **Real-world Application**: Solves actual content discovery problem
- **Scalable Design**: Starts simple, grows to handle production workloads
- **AWS Native**: Full AWS stack experience (S3, RDS, Airflow, potentially EMR)

---

## Technical Architecture

### Tech Stack

**Data Processing:**

- **Python**: Primary programming language
- **Polars**: Initial data processing (lightweight, fast)
- **PySpark**: Scale-up for larger datasets (M9+)

**Orchestration:**

- **Apache Airflow**: Workflow management and scheduling
- **Docker**: Local development environment

**Storage:**

- **AWS S3**: Data lake with bronze/silver/gold layers
- **AWS RDS (PostgreSQL + pgvector)**: Vector database for embeddings
- **Parquet**: Columnar storage format for processed data

**Machine Learning:**

- **Groq API**: Fast embedding generation
- **ChromaDB → pgvector**: Vector similarity search
- **Cosine Similarity**: Recommendation algorithm (start simple)

**Interface:**

- **CLI**: Initial user interface (M4-M9)
- **FastAPI**: Web backend (M10+)
- **React/Vue**: Web frontend (M10+ cleanup)

### Data Architecture

```
┌─────────────┐
│ Lemmy API   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  BRONZE LAYER (S3)                  │
│  - Raw JSON from API                │
│  - Timestamped files                │
│  - No transformations               │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  SILVER LAYER (S3)                  │
│  - Cleaned & validated Parquet      │
│  - Standardized schema              │
│  - Partitioned by date              │
└──────────┬──────────────────────────┘
           │
           ├──────────────────┬────────────────┐
           ▼                  ▼                ▼
    ┌──────────┐      ┌──────────┐    ┌──────────┐
    │  GOLD    │      │ pgvector │    │Analytics │
    │ (Ratings)│      │(Embeddings)    │ Layer    │
    └──────────┘      └──────────┘    └──────────┘
           │                  │
           └────────┬─────────┘
                    ▼
         ┌─────────────────────┐
         │ Recommendation       │
         │ Engine               │
         └─────────────────────┘

```

### System Components

**1. Data Ingestion Service**

- Fetches trending communities and posts from Lemmy API
- Handles rate limiting and errors
- Saves raw data to S3 bronze layer

**Lemmy API Endpoints:**

| Source Type | Sort Tags | Count |
|-------------|-----------|-------|
| Posts | hot, active, scaled, new, most_comments, top_day, top_week, top_month, top_year, top_all | 10 tags |
| Communities | hot, active, new, top_day, top_week, top_month | 6 tags |

**Strategy:** 16 independent source streams (10 posts + 6 communities), each with its own DAG:
- **Every 3h**: hot, active, scaled
- **Every 4h**: new
- **Every 6h**: most_comments
- **Every 8h**: top_day
- **Every 12h**: top_week, top_month, top_year, top_all

**Architecture:** Each source/tag combo saved separately in bronze layer → transformation creates silver layer output → gold DAGs merge by source type. This enables independent scheduling and fault isolation.

**2. Data Processing Service**

- Reads bronze layer JSON
- Cleans and validates data
- Transforms to structured Parquet
- Writes to silver layer with partitioning

**3. Embedding Service**

- Generates embeddings for community descriptions
- Generates embeddings for post content
- Stores vectors in pgvector database
- Handles batching and caching

**4. User Feedback Service**

- CLI interface for rating content
- Stores user preferences in S3 gold layer
- Tracks rating progress and history
- Supports multiple users

**5. Recommendation Engine**

- Queries pgvector for similar content
- Filters based on user ratings
- Weights recommendations by confidence
- Handles cold start (few ratings) and warm start (many ratings)

**6. Orchestration Service**

- Airflow DAGs for scheduling
- Daily data collection
- On-demand processing
- Monitoring and alerting

---

## Development Philosophy

### MVP-First Approach

Every milestone follows this pattern:

1. **Build the ugliest thing that works**: One script, hardcoded values, no error handling
2. **Validate it works**: See output, confirm correctness
3. **Clean it up**: Best practices, error handling, modularity
4. **Move forward**: Don't over-optimize, progress to next milestone

### Goals Over Time

- Milestones are defined by **what works**, not when it's done
- Each milestone has a clear **success criterion**
- No moving to next milestone until current one **demonstrably works**

### Iteration Strategy

```
Milestone X.1 (Ugly MVP)
    ↓
Validate + Test
    ↓
Milestone X.2 (Cleanup)
    ↓
Validate + Test
    ↓
Milestone X.3 (Deploy) ← Optional, for milestones with infra
    ↓
Validate + Test
    ↓
Next Milestone
```

> **Note:** X.3 deployment steps are optional and only exist for milestones that introduce new infrastructure (M3: Airflow→EC2, M5: pgvector→RDS, M10: Web→Cloud).

---

## Detailed Roadmap

## PHASE 1: DATA FOUNDATION

### Milestone 1: Get Data Flowing ✅

**Goal:** Fetch trending communities from Lemmy and save to S3. Prove the pipeline works.

### M1.1 - Ugly MVP ✅

**What to build:**

- ~~Single Python script for Lemmy API ingestion~~
- ~~Hardcode AWS credentials (we'll fix in cleanup)~~
- ~~Hit Lemmy API (public endpoint)~~
- ~~Fetch communities and posts with various sort tags~~
- ~~Save each source/tag combo as separate JSON file to S3~~

**Code structure:**

```python
# fetch_lemmy.py
import httpx
import json
import boto3
from datetime import datetime

# Hardcoded (will fix later)
BUCKET_NAME = "lemmy-bronze-data"

# Fetch from Lemmy API
# Save to S3
# Done!

```

**Success Criteria:**

- ✓ Script runs without errors
- ✓ You see the JSON file in S3 console
- ✓ JSON contains community/post data (name, description, subscribers, etc.)

### M1.2 - Cleanup ✅

**What to improve:**

- ~~Move AWS credentials to environment variables or AWS credentials file~~
- ~~Add error handling with try/except blocks~~
- ~~Add proper logging instead of print statements~~
- ~~Create basic folder structure:~~

    ```
    lemmy-recommender/
    ├── src/
    │   ├── __main__.py
    │   ├── config.py
    │   ├── ingestion/
    │   │   └── fetch_lemmy.py
    │   ├── storage/
    │   │   ├── read.py
    │   │   └── write.py
    │   ├── transformation/
    │   │   └── transform.py
    │   └── models/
    │       └── lemmy.py
    ├── config/
    │   └── config.yaml
    ├── airflow/
    │   └── dags/
    │       └── pipeline.py
    └── pyproject.toml

    ```

- ~~Add configuration file for API endpoints and S3 paths~~
- ~~Add basic unit test to verify S3 upload~~

**Success Criteria:**

- ✓ Script uses environment variables
- ✓ Proper error messages if API fails
- ✓ Clean logs showing what's happening
- ✓ Code is organized in folders

---

### Milestone 2: Bronze → Silver Pipeline ✅

**Goal:** Clean the raw data and create structured silver layer in Parquet format.

### M2.1 - Ugly MVP ✅

**What to build:**

- ~~New script for transformation~~
- ~~Read the JSON from S3 bronze layer~~
- ~~Use Polars to:~~
    - ~~Remove null/invalid entries~~
    - ~~Standardize field names (snake_case)~~
    - ~~Extract only needed fields (community name, description, subscribers, created_date, url)~~
    - ~~Add processing timestamp~~
- ~~Save to S3 silver layer as **Parquet** file~~
- ~~Example path: `s3://lemmy-silver-data/communities/hot/2025-12-20.parquet`~~

**Code structure:**

```python
# transform_lemmy.py
import polars as pl
import boto3

# Read JSON from bronze
# Transform with Polars
# Save as Parquet to silver

```

**Success Criteria:**

- ✓ Script reads bronze JSON successfully
- ✓ Parquet file appears in silver layer
- ✓ Parquet file is smaller than JSON (compression works)
- ✓ You can read the Parquet file and see clean data

### M2.2 - Cleanup ✅

**What to improve:**

- ~~Separate bronze and silver logic into different modules~~
- ~~Add defensive data handling:~~
    - ~~Filter records missing required fields (e.g., community_name)~~
    - ~~Fill nulls with sensible defaults~~
    - ~~Log null statistics before filling (visibility into data quality)~~
- ~~Implement better file naming with partitioning:~~
    - ~~`s3://lemmy-silver-data/communities/hot/year=2025/month=12/day=20/data.parquet`~~
- ~~Add logging for transformation stats (records processed, dropped, etc.)~~

**Success Criteria:**

- ✓ Modular code with clear separation of concerns
- ✓ Transformation handles missing/null data gracefully
- ✓ Partitioned file structure in S3
- ✓ Logs show transformation metrics (input/output counts, dropped records)

> **Note:** Advanced data quality features (persistent reports, record count assertions, comprehensive validation rules) are deferred to M8 (Validation & Analytics) where they fit naturally with the analytics dashboard.

---

### Milestone 3: Airflow Orchestration ✅

**Goal:** Automate the daily pipeline with Airflow.

### M3.1 - Ugly MVP ✅

**What to build:**

- ~~Local Airflow setup using docker-compose~~
- ~~18 DAGs using TaskFlow API and Dataset triggers:~~
    - ~~16 Source DAGs (10 posts + 6 communities): `bronze()` → `silver()` tasks~~
    - ~~2 Gold DAGs: One per source type, triggered when ANY respective silver dataset updates~~
- ~~Per-tag scheduling:~~
    - ~~Every 3h: hot, active, scaled~~
    - ~~Every 4h: new~~
    - ~~Every 6h: most_comments~~
    - ~~Every 8h: top_day~~
    - ~~Every 12h: top_week, top_month, top_year, top_all~~
- ~~Event-driven Gold merge via Airflow Datasets (no polling)~~

**Architecture:**

```
    posts_hot_dag ────────► silver_posts_hot ────────┐
    posts_new_dag ────────► silver_posts_new ────────┼──► posts_gold_dag
    ...                                              │
    posts_top_all_dag ────► silver_posts_top_all ───┘

    communities_hot_dag ──► silver_communities_hot ──┐
    ...                                              ├──► communities_gold_dag
    communities_top_all ──► silver_communities_top_all
```

**Code structure:**

```python
# airflow/dags/pipeline.py
from airflow.datasets import Dataset
from airflow.decorators import dag, task
from src import create_bronze_source, create_gold, create_silver_source
from src.config import get_all_streams, get_gold_tags, get_s3_bucket, SOURCES

# Schedule mapping by tag (actual intervals)
TAG_SCHEDULES = {
    "hot": timedelta(hours=3),
    "active": timedelta(hours=3),
    "scaled": timedelta(hours=3),
    "new": timedelta(hours=4),
    "most_comments": timedelta(hours=6),
    "top_day": timedelta(hours=8),
    "top_week": timedelta(hours=12),
    "top_month": timedelta(hours=12),
    "top_year": timedelta(hours=12),
    "top_all": timedelta(hours=12),
}

# Build datasets from config
SILVER_DATASETS = {
    (source, tag): Dataset(f"s3://{get_s3_bucket('silver')}/{source}/{tag}")
    for source, tag, _ in get_all_streams()
}

def create_source_dag(source, tag, schedule, outlet_dataset):
    @dag(dag_id=f"lemmy_{source}_{tag}_pipeline", schedule=schedule, ...)
    def source_pipeline():
        @task
        def bronze():
            create_bronze_source(source, tag)

        @task(outlets=[outlet_dataset])
        def silver():
            create_silver_source(source, tag)

        bronze() >> silver()
    return source_pipeline()

# Instantiate all 16 source DAGs dynamically
for source, tag, _ in get_all_streams():
    create_source_dag(source, tag, ...)

# Two gold DAGs - trigger when ANY silver dataset for that source updates
@dag(schedule=[SILVER_DATASETS[("posts", tag)] for tag in get_gold_tags("posts")])
def lemmy_posts_gold_pipeline():
    @task
    def merge_to_gold():
        create_gold("posts")
    merge_to_gold()

@dag(schedule=[SILVER_DATASETS[("communities", tag)] for tag in get_gold_tags("communities")])
def lemmy_communities_gold_pipeline():
    @task
    def merge_to_gold():
        create_gold("communities")
    merge_to_gold()
```

**Success Criteria:**

- ✓ Airflow UI accessible at localhost:8080
- ✓ All 18 DAGs appear in UI
- ✓ Source DAGs can be triggered manually or run on schedule
- ✓ Gold DAGs trigger automatically when respective Silver datasets complete
- ✓ Data appears in S3 after DAGs complete

### M3.2 - Cleanup ✅

**What to improve:**

- ~~Add scheduling~~ ✓ (done in M3.1 - per-source schedules)
- ~~Add retry logic~~ ✓ (done: `retries=2, retry_delay=5min`)
- ~~Separate DAG definition from business logic~~ ✓ (done: TaskFlow API + src functions)
- ~~Add sensors~~ → Replaced with Dataset triggers (better approach)
- ~~Add task documentation and default_args~~ ✓ (done: DEFAULT_ARGS with owner, retries, retry_delay)
- ~~Add email/Slack alerting on failure~~ → Moved to M8.2 (with monitoring)
- ~~Add monitoring dashboard (Airflow metrics)~~ → Moved to M8.2

**Success Criteria:**

- ✓ DAGs run automatically at scheduled times
- ✓ Failed tasks retry automatically
- ✓ Code is clean and maintainable

### M3.3 - EC2 Deployment ✅

**Goal:** Deploy Airflow to AWS EC2 using Terraform for IaC learning.

**What to build:**

- Terraform infrastructure:
    - VPC with public subnet
    - EC2 instance (t3.medium) running Docker
    - Security groups (SSH + HTTP 8080, restricted to your IP)
    - IAM role with S3 access for bronze/silver/gold buckets
    - Elastic IP for stable address across stop/start
- Production docker-compose override (`docker-compose.prod.yaml`)
- Deployment script for git pull + rebuild

**Architecture:**
```
EC2 (t3.medium) + Elastic IP
├── Docker Compose
│   ├── Airflow Webserver (:8080)
│   ├── Airflow Scheduler
│   └── PostgreSQL
└── IAM Role → S3 Access
```

**Success Criteria:**

- Terraform provisions all resources successfully
- Airflow UI accessible at `http://<elastic-ip>:8080`
- DAGs can be triggered and write to S3
- Instance can be stopped/started without losing IP

---

### Milestone X: Engineering Excellence

**Goal:** Harden the data pipeline with production-grade practices before adding new features. This milestone ensures the foundation is solid for the remaining work.

### MX.1 - Data Lineage & Enrichment ✅

**What was built:**

- **Data lineage tracking:**
    - ✅ Add `source_file` column in silver layer (tracks which bronze file produced each record)
    - ✅ Add `sources` array column in gold layer (tracks which silver tags contributed to each record)
    - ✅ Add `run_id` to all layers (UUID for each pipeline execution, enables debugging)
    - ✅ Created `RunContext` dataclass for pipeline execution tracking
    - ✅ Created `BronzeResult` dataclass for source file lineage

- **Silver layer enrichment (derived columns):**
    - **Posts:**
        - ✅ `engagement_ratio`: `upvotes / (upvotes + downvotes)` - quality signal (0.0-1.0)
        - ✅ `comment_density`: `num_comments / max(score, 1)` - discussion activity
        - ✅ `content_type`: 'text', 'link', or 'image' based on URL pattern
        - ✅ `body_length`: character count for embeddings
        - ✅ `age_hours`: hours since publication
    - **Communities:**
        - ✅ `description_length`: character count for embeddings
        - ✅ `is_active_community`: `users_active_week > threshold` (configurable in config.yaml)
        - ✅ `age_hours`: hours since creation

**Files created/modified:**

| File | Purpose |
|------|---------|
| `src/pipeline/run_context.py` | `RunContext` dataclass for pipeline execution tracking |
| `src/transformation/enrich.py` | `enrich_posts()` and `enrich_communities()` functions |
| `src/transformation/utils.py` | `is_post_response()` and `is_listing_response()` TypeGuards |
| `src/storage/read.py` | `BronzeResult` dataclass for source file lineage |
| `src/transformation/transform.py` | `add_lineage()` function, enrichment integration |
| `src/transformation/merge_datasources.py` | Added `run_id` to gold layer |
| `config/config.yaml` | Added `enrichment.active_community_threshold` |
| `tests/test_enrich.py` | 17 unit tests for enrichment functions |

**Success Criteria:**

- ✅ Every silver record has `source_file` and `run_id` columns
- ✅ Every gold record has `sources` array showing contributing sources
- ✅ Posts have enrichment columns: `engagement_ratio`, `comment_density`, `content_type`, `body_length`, `age_hours`
- ✅ Communities have enrichment columns: `description_length`, `is_active_community`, `age_hours`
- ✅ Unit tests for all enrichment functions (17 tests)
- ✅ `active_community_threshold` configurable in `config.yaml`

### MX.2 - Infrastructure Hardening ✅

**What was built:**

- **Terraform outputs:**
    - Added `bucket_bronze`, `bucket_silver`, `bucket_gold` outputs
    - Makes it easy to get bucket names after `terraform apply`
- **Docker Compose improvements:**
    - Added health check for LocalStack (curl to `/_localstack/health`)
    - Added `restart: unless-stopped` for resilience

**Removed from scope:**
- Task groups - minimal value for 2-task linear DAGs (bronze → silver)

> **Interview Note:** Remote state management (S3 + DynamoDB locking) and SLA monitoring are important for team/production environments, but overkill for a solo learning project. Be ready to explain *why* they matter: remote state prevents conflicts when multiple people run terraform; SLAs alert on-call when pipelines are late.

**Success Criteria:**

- ✅ `terraform output` shows bucket names (`bucket_bronze`, `bucket_silver`, `bucket_gold`)
- ✅ Docker LocalStack has health check (curl to `/_localstack/health`)
- ✅ LocalStack restarts on failure (`restart: unless-stopped`)

---

### MX.3 - Testing & CI/CD

**What to build:**

- **Integration tests with LocalStack:**
    - End-to-end test: bronze → silver → gold with real S3 operations
    - Verify Parquet schema matches expected (use `polars.testing`)
    - Test deduplication logic with known inputs/outputs
- **DAG validation tests:**
    - Pytest tests that load all DAGs and verify no import errors
    - Validate DAG structure (tasks exist, dependencies correct)
- **Schema contract tests:**
    - Define expected schemas in code
    - Test that silver/gold outputs match contract
- **GitHub Actions CI pipeline:**
    - Run on every push and PR to main
    - Jobs: `ruff check`, `ruff format --check`, `mypy`, `pytest`
    - Fail PR if any check fails
    - Free for public repos, 2000 min/month for private

**Code structure:**

```python
# tests/integration/test_pipeline_e2e.py
@pytest.fixture
def localstack_s3():
    # Setup LocalStack S3 client
    yield s3_client
    # Cleanup buckets

def test_bronze_to_gold_pipeline(localstack_s3):
    # 1. Write mock bronze JSON
    # 2. Run silver transformation
    # 3. Run gold merge
    # 4. Assert output schema and content

# tests/test_airflow_dags.py
def test_all_dags_load_without_errors():
    from airflow.models import DagBag
    dag_bag = DagBag(dag_folder="airflow/dags", include_examples=False)
    assert len(dag_bag.import_errors) == 0
    assert len(dag_bag.dags) == 18  # 16 source + 2 gold

def test_dag_dependencies():
    # Verify gold DAGs depend on correct silver datasets
```

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check src/
      - run: ruff format --check src/

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      localstack:
        image: localstack/localstack
        ports:
          - 4566:4566
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest tests/
        env:
          USE_LOCALSTACK: "true"
```

**Success Criteria:**

- ✓ Integration tests pass against LocalStack
- ✓ DAG validation tests catch import errors
- ✓ Schema contract tests verify output structure
- ✓ GitHub Actions runs on every push/PR
- ✓ PRs blocked if ruff, mypy, or pytest fails

### MX.4 - Schema Versioning

**What to build:**

- **Pipeline version tracking:**
    - Add `pipeline_version` column to all layers (bronze, silver, gold)
    - Use semantic versioning (e.g., `"1.0.0"`)
    - Bump version when schema changes (new columns, type changes, removed columns)

- **Versioning strategy:**
    - Define version in single source of truth (`src/pipeline/version.py`)
    - Include version in all transformations automatically
    - Document schema changes in a changelog

**Code structure:**

```python
# src/pipeline/version.py
PIPELINE_VERSION = "1.0.0"

# Version history:
# 1.0.0 - Initial schema with lineage + enrichment (MX.1)
```

```python
# src/transformation/transform.py
from src.pipeline.version import PIPELINE_VERSION

def add_lineage(df: pl.DataFrame, source_file: str, run_id: str) -> pl.DataFrame:
    return df.with_columns([
        pl.lit(source_file).alias("source_file"),
        pl.lit(run_id).alias("run_id"),
        pl.lit(PIPELINE_VERSION).alias("pipeline_version"),
    ])
```

**When to bump versions:**

| Change Type | Version Bump | Example |
|-------------|--------------|---------|
| New column added | Minor (1.0 → 1.1) | Adding `sentiment_score` |
| Column type changed | Major (1.x → 2.0) | `score: int → float` |
| Column removed | Major (1.x → 2.0) | Removing deprecated field |
| Bug fix (no schema change) | Patch (1.0.0 → 1.0.1) | Fix null handling |

**Success Criteria:**

- ✓ Every record has `pipeline_version` column
- ✓ Version is defined in single location
- ✓ Schema changes are documented with version bumps

> **Note:** MX can be done incrementally—MX.1 (Data Lineage) is highest priority as it affects data contracts. MX.2 (Infrastructure Hardening) improves Docker health checks before integration tests. MX.3 (Testing & CI/CD) and MX.4 (Schema Versioning) can be deferred if eager to start M4.

---

## PHASE 2: USER INTERACTION

### Milestone 4: User Feedback System (CLI)

**Goal:** Let users rate communities via CLI and store preferences.

### M4.1 - Ugly MVP

**What to build:**

- CLI script (`rate_communities.py`)
- Read 10 random communities from S3 silver layer
- Show each community name
- User types 'y' (like) or 'n' (dislike)
- Save ratings to S3 as **Parquet** file
- Structure: `user_id, community_name, rating, timestamp`
- Example path: `s3://lemmy-gold-data/ratings/user_ratings.parquet`
- Single user only (hardcoded user_id = 'user1')
- maybe ask user what he likes, like in content websites

**Code structure:**

```python
# rate_communities.py
import polars as pl
import boto3

# Load 10 random communities from silver
# For each community:
#   print(community_name)
#   rating = input("Like? (y/n): ")
#   save to list
# Write all ratings to Parquet in S3

```

**Success Criteria:**

- ✓ CLI shows 10 communities
- ✓ You can rate all 10
- ✓ Parquet file appears in S3 gold layer
- ✓ File contains your ratings with correct structure

### M4.2 - Cleanup

**What to improve:**

- Add progress tracking: "You've rated 23 communities. 7 more needed for recommendations."
- Better CLI display:

    ```
    [Progress: 23/30 ratings needed]

    Community: technology@lemmy.world
    Description: Tech news and discussions
    Subscribers: 14.2K
    Top post: "New AI breakthrough in quantum computing"

    Rate this community:
      [y] Like    [n] Dislike    [s] Skip

    Your choice: _

    ```

- Add category diversity: Don't show 10 tech communities in a row
- Add user_id support: Prompt for username, support multiple users
- Add skip option: User can skip without rating
- Append to existing ratings file (don't overwrite)
- Add ability to rate in batches (user can exit and resume later)

**Success Criteria:**

- ✓ Clean, informative CLI interface
- ✓ Shows progress toward 30-rating threshold
- ✓ Multiple users can use the system
- ✓ Ratings accumulate over multiple sessions

---

## PHASE 3: RECOMMENDATIONS

### Milestone 5: Cold Start with Embeddings

**Goal:** Generate embeddings for communities and find similar ones based on user preferences.

### M5.1 - Ugly MVP

**What to build:**

- Check if user has 30+ ratings (minimum threshold)
- If less than 30, show message: "Please rate X more communities to get recommendations"
- If 30+, proceed:
    - Read community descriptions from silver layer
    - Use **Groq API** to generate embeddings for descriptions
    - Store embeddings in local **ChromaDB**
    - Find user's liked communities (from gold layer)
    - Query ChromaDB for 10 most similar communities using cosine similarity
    - Show recommendations in CLI

**Code structure:**

```python
# recommend.py
import chromadb
from groq import Groq

# Check rating count
# If < 30: exit with message
# If >= 30:
#   Generate embeddings with Groq
#   Store in ChromaDB
#   Get user's liked communities
#   Query ChromaDB for similar ones
#   Print recommendations

```

**Success Criteria:**

- ✓ System requires 30+ ratings before showing recommendations
- ✓ Embeddings are generated successfully
- ✓ ChromaDB stores embeddings locally
- ✓ CLI shows 10 recommended communities
- ✓ Recommendations are actually related to user's likes (manual verification)

### M5.2 - Cleanup

**What to improve:**

- Migrate from ChromaDB to **pgvector** (local PostgreSQL first):
    - Set up local PostgreSQL with pgvector extension (Docker)
    - Create table for embeddings with proper indexes
    - Migrate existing embeddings from ChromaDB
- Batch embedding generation (process 100 communities at once)
- Add embedding caching:
    - Don't regenerate embeddings for existing communities
    - Only generate for new communities
- Add confidence scores to recommendations:
    - Based on similarity score and number of user ratings
    - Show: "Recommended with 85% confidence"
- Better error handling for API rate limits

**Success Criteria:**

- pgvector running locally in Docker
- Embeddings persist across sessions
- Batch processing speeds up embedding generation
- Recommendations show confidence scores
- System handles API errors gracefully

### M5.3 - RDS Deployment (Optional)

**Goal:** Deploy pgvector database to AWS RDS for production use.

**What to build:**

- Terraform module for RDS PostgreSQL:
    - RDS instance with pgvector extension
    - Security group for EC2 → RDS access (if M3.3 done)
    - Subnet group in existing VPC
    - Parameter group with pgvector enabled
- Database migration script (local → RDS)
- Connection string management (environment variables)

**Architecture:**
```
EC2 (Airflow) ──────► RDS PostgreSQL
                      └── pgvector extension
                      └── embeddings table
```

**Cost:**
- db.t3.micro: ~$15/month
- db.t3.small: ~$30/month

**Success Criteria:**

- RDS instance provisioned via Terraform
- Embeddings stored in RDS pgvector
- Airflow tasks can read/write embeddings
- Local development still works (fallback to local postgres)

---

### Milestone 6: Warm Start - Learn from User

**Goal:** As user rates more content, improve recommendation quality.

### M6.1 - Ugly MVP

**What to build:**

- After user has rated 50+ communities, activate "warm start" mode
- Weight embeddings by user preferences:
    - Liked communities: +1 weight
    - Disliked communities: -1 weight
- Create user preference vector (average of liked embeddings)
- Find communities similar to preference vector
- Filter out already-rated communities
- Show 10 new recommendations

**Code structure:**

```python
# warm_recommend.py
# Get all user ratings
# If < 50: use cold start (M5)
# If >= 50:
#   Create preference vector from liked communities
#   Query pgvector for similar communities
#   Filter out already-rated
#   Return top 10

```

**Success Criteria:**

- ✓ After 50+ ratings, system uses warm start
- ✓ Recommendations change based on recent ratings
- ✓ Already-rated communities don't appear in recommendations
- ✓ Recommendations feel more personalized (manual testing)

### M6.2 - Cleanup

**What to improve:**

- Add confidence scoring based on:
    - Number of ratings user has provided
    - Similarity score
    - Consistency of user preferences
- Filter out already-rated communities more efficiently (database query)
- Add diversity to recommendations:
    - Not all top-10 most similar
    - Include some "adjacent interest" communities
    - Use exploration vs exploitation strategy
- Implement negative filtering:
    - Avoid communities similar to disliked ones
    - Weight disliked embeddings negatively in search
- Add explanation for recommendations:
    - "Recommended because you liked technology@lemmy.world and programming@lemmy.ml"

**Success Criteria:**

- ✓ Recommendations balance similarity and diversity
- ✓ System avoids content similar to dislikes
- ✓ Confidence scores are meaningful
- ✓ Explanations help user understand why community was recommended

---

## PHASE 4: EXPAND CONTENT

### Milestone 7: Add Posts Data

**Goal:** Pull posts from communities and let users rate them.

### M7.1 - Ugly MVP

**What to build:**

- Extend bronze pipeline (M1):
    - Fetch posts with various sort tags (hot, new, top, etc.)
    - Save posts to S3 bronze as JSON
- Extend silver pipeline (M2):
    - Transform posts to Parquet
    - Fields: id, name, body, url, community_id, community_name, creator_id, creator_name, published, score, num_comments, upvotes, downvotes, nsfw, featured_community, featured_local, source, created_date, processed_at
- Update CLI (M4):
    - After rating communities, show posts
    - Display: title + first 200 chars of text
    - User rates: like/dislike/skip
    - Save post ratings to gold layer (separate from community ratings)

**Code structure:**

```python
# In fetch_lemmy.py:
# Fetch posts with various sort tags

# In rate_communities.py:
# Add post rating section after community rating

```

**Success Criteria:**

- ✓ Posts appear in bronze and silver layers
- ✓ CLI shows posts with title and snippet
- ✓ User can rate posts
- ✓ Post ratings saved to S3 separately from community ratings

### M7.2 - Cleanup

**What to improve:**

- Combine community + post signals for better recommendations:
    - If user likes posts from technology@lemmy.world, boost that community's recommendation
    - Use post content embeddings for finer-grained matching
- Add post-level embeddings:
    - Generate embeddings for post title + text
    - Store in pgvector alongside community embeddings
    - Recommend specific posts, not just communities
- Weight post ratings higher than community ratings:
    - Post rating = 2x weight of community rating
    - More granular signal of user preferences
- Add post preview quality indicators:
    - Image post, text post, link post
    - Show thumbnail if available

**Success Criteria:**

- ✓ Recommendations use both community and post data
- ✓ Post embeddings stored in pgvector
- ✓ System recommends specific posts user will likely enjoy
- ✓ Post previews are informative

---

## PHASE 5: VALIDATION

### Milestone 8: Validation & Analytics

**Goal:** Test if the recommendation system actually works + build basic analytics.

### M8.1 - Ugly MVP (Validation)

**What to build:**

- Validation script that tests recommendation accuracy:
    - System suggests 10 communities/posts it thinks user will LIKE
    - System suggests 10 communities/posts it thinks user will NOT like
    - User rates all 20 items
    - Calculate accuracy:
        - Precision: % of "will like" that user actually liked
        - Recall: % of "won't like" that user actually disliked
    - Print accuracy score: "7/10 likes correct, 8/10 dislikes correct"

**Code structure:**

```python
# validate_recommendations.py
# Get 10 predicted likes
# Get 10 predicted dislikes
# User rates all 20
# Calculate and print accuracy

```

**Success Criteria:**

- ✓ Validation script runs successfully
- ✓ You see accuracy metrics
- ✓ Accuracy is better than random (>50%)
- ✓ System learns from validation ratings (adds to dataset)

### M8.2 - Cleanup (Analytics & Monitoring)

**What to build:**

- **Airflow Alerting & Monitoring (moved from M3.2):**
    - Email/Slack alerting on DAG failure
    - Airflow metrics dashboard (task duration, success rate, etc.)
    - CloudWatch integration (if deployed to AWS)

- Jupyter notebook with analytics using Polars:
    - **Trending Analysis:**
        - Most featured communities over time
        - Communities gaining/losing popularity
        - Trending topics by week/month
    - **User Preference Analysis:**
        - Distribution of user ratings (like vs dislike ratio)
        - Most liked categories
        - User preference evolution over time
    - **Recommendation Performance:**
        - Accuracy over time (as user rates more)
        - Precision/recall curves
        - Confusion matrix for recommendations
    - **Data Quality Metrics Persistence:**
        - Write quality metrics to S3 during transformation (null counts, dropped records, schema validation)
        - Path: `s3://lemmy-gold-data/data_quality/year=YYYY/month=MM/day=DD/{run_id}_{source}_{tag}.json`
        - Create `QualityMetrics` dataclass to capture: input/output records, null stats, business rule drops
        - Integrate metric collection into `clean_source_data()` transformation
    - **Data Quality Analytics Dashboard:**
        - API success rate
        - Data completeness over time (null rates, missing fields)
        - Processing pipeline health
        - Record count validation (bronze vs silver layer counts)
        - Trending dashboard from `data_quality/` metrics
        - Anomaly detection: Alert when source returns unusual data volumes (e.g., 2 communities instead of ~25)
        - Cross-source validation: Stats about overlap between sources (e.g., "15% of communities appear in 3+ sources")
    - **Data Lineage Visualization (uses MX.1 lineage):**
        - Trace any gold record back through silver → bronze files
        - Query by `run_id` to see all records from a specific pipeline execution
        - Visualize source tag contributions to gold layer
    - **Cost Monitoring (if deployed to AWS):**
        - S3 storage costs by layer (bronze/silver/gold)
        - EC2 runtime costs
        - Airflow task duration trends (identify slow tasks)

**Deliverables:**

- Jupyter notebook: `notebooks/analytics_dashboard.ipynb`
- Visualizations with matplotlib or plotly
- Weekly/monthly summary reports

**Success Criteria:**

- ✓ Analytics notebook runs and generates insights
- ✓ Charts are clear and informative
- ✓ You can identify trends and patterns
- ✓ Recommendation accuracy is tracked over time
- You get notified if DAG fails after retries (alerting)
- Airflow metrics visible in dashboard

---

## PHASE 6: SCALE

### Milestone 9: Scale to PySpark

**Goal:** Handle larger data volumes with PySpark.

### M9.1 - Ugly MVP

**What to build:**

- Replace Polars with PySpark in transform pipeline (M2)
- Keep same bronze → silver logic
- Test with larger dataset:
    - Increase to 100+ communities
    - 1000+ posts
    - Multiple days of historical data
- Run PySpark locally (not on EMR yet)
- Keep same Parquet output structure

**Code structure:**

```python
# transform_lemmy_spark.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("LemmyTransform").getOrCreate()

# Read JSON from bronze
df = spark.read.json("s3://lemmy-bronze-data/...")

# Transform with Spark
# Write Parquet to silver

```

**Success Criteria:**

- ✓ PySpark pipeline processes data successfully
- ✓ Handles 10x more data than Polars version
- ✓ Output Parquet files are identical in structure
- ✓ Processing time is reasonable for dataset size

### M9.2 - Cleanup

**What to improve:**

- Optimize Spark jobs:
    - Proper partitioning strategy
    - Broadcast joins where appropriate
    - Caching intermediate results
- Add advanced partitioning:
    - Partition by year/month/day/hour
    - Partition by community category
- Move to AWS EMR or Glue:
    - Set up EMR cluster (or use Glue)
    - Deploy Spark jobs to AWS
    - Configure auto-scaling
- Add comprehensive monitoring:
    - Spark UI metrics
    - Job duration tracking
    - Data volume metrics
    - Cost monitoring

**Success Criteria:**

- ✓ Spark jobs run efficiently on large datasets
- ✓ Running on AWS infrastructure (EMR/Glue)
- ✓ Monitoring dashboard shows job health
- ✓ Cost per data processed is reasonable

---

## PHASE 7: WEB INTERFACE

### Milestone 10: Web Interface (FastAPI)

**Goal:** Move from CLI to web application.

### M10.1 - Ugly MVP

**What to build:**

- Simple FastAPI backend with endpoints:
    - `POST /rate`: Rate a community or post
    - `GET /recommendations`: Get personalized recommendations
    - `GET /content`: Get random content to rate
    - `GET /stats`: Get user rating stats
- Basic HTML frontend:
    - Form to rate content (radio buttons: like/dislike)
    - Button to get recommendations
    - Display recommendations in a list
- No authentication yet (single user)
- Run locally: `uvicorn main:app --reload`

**Code structure:**

```python
# api/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.post("/rate")
async def rate_content(content_id: str, rating: str):
    # Save rating to S3
    return {"status": "success"}

@app.get("/recommendations")
async def get_recommendations():
    # Query pgvector, return recommendations
    return {"recommendations": [...]}

# Simple HTML form
@app.get("/", response_class=HTMLResponse)
async def home():
    return "<html>...</html>"

```

**Success Criteria:**

- ✓ FastAPI server runs locally
- ✓ You can rate content via web browser
- ✓ Recommendations appear on the page
- ✓ Ratings are saved to S3

### M10.2 - Cleanup

**What to improve:**

- Add React or Vue frontend:
    - Clean, modern UI
    - Card-based content display
    - Smooth animations
    - Mobile-responsive
- Add user authentication:
    - Login/signup system
    - JWT tokens
    - User profiles
- Add session management:
    - Remember user preferences
    - Rating history
    - Recommendation history
- Add API documentation:
    - Swagger/OpenAPI docs
    - Rate limiting
    - API versioning

**Success Criteria:**

- Modern, polished web interface
- Multiple users can have separate accounts
- API is documented and secure
- Application runs locally with full features

### M10.3 - Web App Deployment (Optional)

**Goal:** Deploy the web application to AWS for public access.

**What to build:**

- Terraform module for web hosting:
    - AWS App Runner or ECS Fargate (containerized)
    - Application Load Balancer
    - ACM certificate for HTTPS
    - Route 53 for domain (optional)
- CI/CD pipeline:
    - GitHub Actions for build + deploy
    - Docker image push to ECR
    - Automatic deployment on merge to main
- Environment configuration:
    - Production secrets management (AWS Secrets Manager)
    - Environment-specific configs (dev/staging/prod)

**Architecture:**
```
Internet ──► ALB (HTTPS) ──► App Runner/ECS
                              └── FastAPI container
                              └── Connects to RDS (M5.3)
                              └── Connects to S3 buckets
```

**Cost:**
- App Runner: ~$5-25/month (scales to zero)
- ECS Fargate: ~$10-30/month
- ALB: ~$16/month
- Domain + SSL: ~$12/year + free (ACM)

**Success Criteria:**

- Application accessible via HTTPS URL
- Auto-scaling handles traffic spikes
- CI/CD deploys on git push
- Monitoring and logging in CloudWatch

---

## Future Enhancements (Post-MVP)

### Content Features

- **Weekly/Monthly Summaries**: Personalized email digests of recommended content
- **Trending Topics**: AI-powered topic extraction and trending analysis
- **Content Scheduling**: Suggest best times to browse based on new content arrival
- **Multi-modal Recommendations**: Include images, videos, and rich media in recommendations

### Advanced ML

- **A/B Testing**: Test different recommendation algorithms
- **Reinforcement Learning**: Improve recommendations based on user engagement (clicks, time spent)
- **Deep Learning Models**: Experiment with transformers for better embeddings
- **Collaborative Filtering**: Add user-to-user similarity for social recommendations

### Social Features

- **Compare Preferences**: See how your interests align with friends
- **Shared Collections**: Create and share curated community/post collections
- **Community Insights**: Analyze preference patterns across all users

### AI Agents

> **Orchestration Note:** These agents are a strong candidate for **Temporal** instead of Airflow. Temporal's durable execution model (workflow-as-code, automatic retries, state persistence across crashes) is purpose-built for long-running, stateful agent workflows — unlike Airflow which is designed for scheduled DAGs. Airflow stays for the data pipeline (M1-M3); Temporal gets introduced here.

- **Content Curator Agent**: Autonomous agent that pre-filters low-quality content
- **Discovery Agent**: Finds emerging communities and niche topics
- **Summarization Agent**: Creates TL;DR summaries of long posts
- **Sentiment Agent**: Analyzes community sentiment and warns about toxic content

### Infrastructure

- **Real-time Streaming**: Use Kafka/Kinesis for real-time content updates
- **GraphQL API**: More flexible API for frontend
- **Microservices**: Split into smaller services (ingestion, processing, recommendations)
- **Multi-region Deployment**: Global CDN and edge computing

### Production/Team Readiness

- **Terraform Remote State**: S3 backend + DynamoDB locking for team collaboration and state conflict prevention
- **Airflow SLA Monitoring**: `sla=timedelta()` on tasks with alerts when pipelines run late
- **Secrets Management**: AWS Secrets Manager or HashiCorp Vault instead of environment variables
- **CD Pipeline**: Automated deployment to EC2/ECS on merge to main (CI for tests/linting already in MX.2)
- **Atomic Writes**: Write to temp file → copy to final → delete temp; prevents partial/corrupt files on S3 write failures
- **Content-Hash Deduplication**: Hash API responses before writing to bronze; skip write if content unchanged from previous pull. Reduces redundant storage and processing when ingestion frequency > API refresh rate. More reliable than ETag/Last-Modified which many APIs don't support.
- **Observability Stack**: Prometheus metrics, Grafana dashboards, distributed tracing

---

## Success Metrics

### Technical Metrics

- **Data Pipeline:**
    - API success rate > 99%
    - Bronze → Silver processing < 5 minutes
    - Data quality score > 95%
    - Zero data loss
- **Recommendations:**
    - Cold start accuracy > 60%
    - Warm start accuracy > 75%
    - Recommendation latency < 500ms
    - Diversity score > 0.7 (not all recommendations from same category)
- **System Performance:**
    - API response time < 200ms (p95)
    - Embedding generation < 10s for 100 items
    - Database query time < 50ms
    - Uptime > 99.5%

### User Experience Metrics

- **Engagement:**
    - User rates > 30 items in first session
    - Returns to rate more content > 3 times
    - Clicks on recommendations > 40% of time
    - Time spent on recommended content > average
- **Satisfaction:**
    - Recommendation accuracy (user validation) > 70%
    - User reports recommendations are "relevant" > 80% of time
    - User continues using system after first week

### Learning Outcomes (Personal Goals)

- ✓ Understand data lake architecture (bronze/silver/gold)
- ✓ Experience with orchestration (Airflow)
- ✓ Hands-on with vector databases and embeddings
- ✓ Build and validate an ML recommendation system
- ✓ Deploy full-stack application to AWS
- ✓ Practice moving from Polars to PySpark for scale
- ✓ Experience with iterative, MVP-driven development
