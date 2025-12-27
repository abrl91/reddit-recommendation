# Reddit Recommendation System

## Key Principles to Remember
1. **MVP First**: Make it work before making it pretty
2. **Validate Early**: Test each milestone before moving forward
3. **Iterate**: Don't perfect anything until you've proven it works
4. **Learn by Doing**: Build real working code, not just documentation
5. **Stay Focused**: One milestone at a time, resist scope creep
6. **Celebrate Wins**: Each green checkmark is progress!

## Project Overview

### What We're Building

A Reddit content recommendation system that learns user preferences without requiring Reddit account connection. Users rate subreddits and posts (like/dislike), and the system suggests personalized content using machine learning embeddings and similarity matching.

### Core Features

- **Data Pipeline**: Automated collection of trending Reddit content
- **User Preference Learning**: CLI-based rating system for subreddits and posts
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
│ Reddit API  │
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

- Fetches trending subreddits from Reddit API
- Pulls hot posts from selected subreddits
- Handles rate limiting and errors
- Saves raw data to S3 bronze layer

**2. Data Processing Service**

- Reads bronze layer JSON
- Cleans and validates data
- Transforms to structured Parquet
- Writes to silver layer with partitioning

**3. Embedding Service**

- Generates embeddings for subreddit descriptions
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
Next Milestone

```

---

## Detailed Roadmap

## PHASE 1: DATA FOUNDATION

### Milestone 1: Get Data Flowing

**Goal:** Fetch trending subreddits from Reddit and save to S3. Prove the pipeline works.

### M1.1 - Ugly MVP

**What to build:**

- Single Python script (`fetch_reddit.py`)
- Hardcode AWS credentials (we'll fix in cleanup)
- Hit Reddit API without authentication (public endpoint)
- Get top 25 trending subreddits
- Save as ONE JSON file to S3 with timestamp in filename
- Example filename: `subreddits_2025-12-20_14-30-00.json`

**Code structure:**

```python
# fetch_reddit.py
import requests
import json
import boto3
from datetime import datetime

# Hardcoded (will fix later)
AWS_ACCESS_KEY = "..."
AWS_SECRET_KEY = "..."
BUCKET_NAME = "reddit-data-bronze"

# Fetch from Reddit
# Save to S3
# Done!

```

**Success Criteria:**

- ✓ Script runs without errors
- ✓ You see the JSON file in S3 console
- ✓ JSON contains subreddit data (name, description, subscribers, etc.)

### M1.2 - Cleanup

**What to improve:**

- Move AWS credentials to environment variables or AWS credentials file
- Add error handling with try/except blocks
- Add proper logging instead of print statements
- Create basic folder structure:
    
    ```
    reddit-recommender/
    ├── src/
    │   └── data_ingestion/
    │       └── fetch_reddit.py
    ├── config/
    │   └── config.yaml
    └── requirements.txt
    
    ```
    
- Add configuration file for API endpoints and S3 paths
- Add basic unit test to verify S3 upload

**Success Criteria:**

- ✓ Script uses environment variables
- ✓ Proper error messages if API fails
- ✓ Clean logs showing what's happening
- ✓ Code is organized in folders

---

### Milestone 2: Bronze → Silver Pipeline

**Goal:** Clean the raw data and create structured silver layer in Parquet format.

### M2.1 - Ugly MVP

**What to build:**

- New script (`transform_reddit.py`)
- Read the JSON from S3 bronze layer
- Use Polars to:
    - Remove null/invalid entries
    - Standardize field names (snake_case)
    - Extract only needed fields (subreddit name, description, subscribers, created_date, url)
    - Add processing timestamp
- Save to S3 silver layer as **Parquet** file
- Example path: `s3://reddit-data-silver/subreddits/2025-12-20.parquet`

**Code structure:**

```python
# transform_reddit.py
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

### M2.2 - Cleanup

**What to improve:**

- Separate bronze and silver logic into different modules
- Add data validation:
    - Schema validation (ensure required fields exist)
    - Data quality checks (no nulls in key fields, valid URLs)
    - Record count validation (bronze count ≈ silver count)
- Implement better file naming with partitioning:
    - `s3://reddit-data-silver/subreddits/year=2025/month=12/day=20/data.parquet`
- Add logging for transformation stats (records processed, dropped, etc.)
- Add data quality report (CSV or JSON summary)

**Success Criteria:**

- ✓ Modular code with clear separation of concerns
- ✓ Validation catches and logs data issues
- ✓ Partitioned file structure in S3
- ✓ Quality report shows transformation metrics

---

### Milestone 3: Airflow Orchestration

**Goal:** Automate the daily pipeline with Airflow.

### M3.1 - Ugly MVP

**What to build:**

- Local Airflow setup using docker-compose
- Single DAG with 2 tasks:
    1. `fetch_reddit_task`: Run M1 script
    2. `transform_reddit_task`: Run M2 script
- Set dependency: transform depends on fetch
- Manual trigger only (no schedule yet)
- DAG runs on-demand when you click "trigger" in UI

**Code structure:**

```python
# airflow/dags/reddit_pipeline.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

dag = DAG('reddit_pipeline', start_date=datetime(2025, 1, 1))

fetch = BashOperator(task_id='fetch', bash_command='python src/data_ingestion/fetch_reddit.py', dag=dag)
transform = BashOperator(task_id='transform', bash_command='python src/transform_reddit.py', dag=dag)

fetch >> transform

```

**Success Criteria:**

- ✓ Airflow UI accessible at localhost:8080
- ✓ DAG appears in UI
- ✓ You can manually trigger the DAG
- ✓ Both tasks complete successfully (green in UI)
- ✓ Data appears in S3 after DAG completes

### M3.2 - Cleanup

**What to improve:**

- Add daily scheduling: `schedule_interval='@daily'` or `'0 9 * * *'` (9 AM daily)
- Add retry logic: `retries=3, retry_delay=timedelta(minutes=5)`
- Add email/Slack alerting on failure
- Separate DAG definition from business logic (use PythonOperator instead of BashOperator)
- Add sensors to check if new data is available before processing
- Add task documentation and default_args
- Improve task dependencies with proper error handling

**Success Criteria:**

- ✓ DAG runs automatically every day at scheduled time
- ✓ Failed tasks retry automatically
- ✓ You get notified if DAG fails after retries
- ✓ Code is clean and maintainable

---

## PHASE 2: USER INTERACTION

### Milestone 4: User Feedback System (CLI)

**Goal:** Let users rate subreddits via CLI and store preferences.

### M4.1 - Ugly MVP

**What to build:**

- CLI script (`rate_subreddits.py`)
- Read 10 random subreddits from S3 silver layer
- Show each subreddit name
- User types 'y' (like) or 'n' (dislike)
- Save ratings to S3 as **Parquet** file
- Structure: `user_id, subreddit_name, rating, timestamp`
- Example path: `s3://reddit-data-gold/ratings/user_ratings.parquet`
- Single user only (hardcoded user_id = 'user1')

**Code structure:**

```python
# rate_subreddits.py
import polars as pl
import boto3

# Load 10 random subreddits from silver
# For each subreddit:
#   print(subreddit_name)
#   rating = input("Like? (y/n): ")
#   save to list
# Write all ratings to Parquet in S3

```

**Success Criteria:**

- ✓ CLI shows 10 subreddits
- ✓ You can rate all 10
- ✓ Parquet file appears in S3 gold layer
- ✓ File contains your ratings with correct structure

### M4.2 - Cleanup

**What to improve:**

- Add progress tracking: "You've rated 23 subreddits. 7 more needed for recommendations."
- Better CLI display:
    
    ```
    [Progress: 23/30 ratings needed]
    
    Subreddit: r/technology
    Description: Tech news and discussions
    Subscribers: 14.2M
    Top post: "New AI breakthrough in quantum computing"
    
    Rate this subreddit:
      [y] Like    [n] Dislike    [s] Skip
    
    Your choice: _
    
    ```
    
- Add category diversity: Don't show 10 tech subreddits in a row
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

**Goal:** Generate embeddings for subreddits and find similar ones based on user preferences.

### M5.1 - Ugly MVP

**What to build:**

- Check if user has 30+ ratings (minimum threshold)
- If less than 30, show message: "Please rate X more subreddits to get recommendations"
- If 30+, proceed:
    - Read subreddit descriptions from silver layer
    - Use **Groq API** to generate embeddings for descriptions
    - Store embeddings in local **ChromaDB**
    - Find user's liked subreddits (from gold layer)
    - Query ChromaDB for 10 most similar subreddits using cosine similarity
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
#   Get user's liked subreddits
#   Query ChromaDB for similar ones
#   Print recommendations

```

**Success Criteria:**

- ✓ System requires 30+ ratings before showing recommendations
- ✓ Embeddings are generated successfully
- ✓ ChromaDB stores embeddings locally
- ✓ CLI shows 10 recommended subreddits
- ✓ Recommendations are actually related to user's likes (manual verification)

### M5.2 - Cleanup

**What to improve:**

- Migrate from ChromaDB to **pgvector on AWS RDS**:
    - Set up PostgreSQL with pgvector extension
    - Create table for embeddings with proper indexes
    - Migrate existing embeddings
- Batch embedding generation (process 100 subreddits at once)
- Add embedding caching:
    - Don't regenerate embeddings for existing subreddits
    - Only generate for new subreddits
- Add confidence scores to recommendations:
    - Based on similarity score and number of user ratings
    - Show: "Recommended with 85% confidence"
- Better error handling for API rate limits

**Success Criteria:**

- ✓ pgvector database running on RDS
- ✓ Embeddings persist across sessions
- ✓ Batch processing speeds up embedding generation
- ✓ Recommendations show confidence scores
- ✓ System handles API errors gracefully

---

### Milestone 6: Warm Start - Learn from User

**Goal:** As user rates more content, improve recommendation quality.

### M6.1 - Ugly MVP

**What to build:**

- After user has rated 50+ subreddits, activate "warm start" mode
- Weight embeddings by user preferences:
    - Liked subreddits: +1 weight
    - Disliked subreddits: -1 weight
- Create user preference vector (average of liked embeddings)
- Find subreddits similar to preference vector
- Filter out already-rated subreddits
- Show 10 new recommendations

**Code structure:**

```python
# warm_recommend.py
# Get all user ratings
# If < 50: use cold start (M5)
# If >= 50:
#   Create preference vector from liked subreddits
#   Query pgvector for similar subreddits
#   Filter out already-rated
#   Return top 10

```

**Success Criteria:**

- ✓ After 50+ ratings, system uses warm start
- ✓ Recommendations change based on recent ratings
- ✓ Already-rated subreddits don't appear in recommendations
- ✓ Recommendations feel more personalized (manual testing)

### M6.2 - Cleanup

**What to improve:**

- Add confidence scoring based on:
    - Number of ratings user has provided
    - Similarity score
    - Consistency of user preferences
- Filter out already-rated subreddits more efficiently (database query)
- Add diversity to recommendations:
    - Not all top-10 most similar
    - Include some "adjacent interest" subreddits
    - Use exploration vs exploitation strategy
- Implement negative filtering:
    - Avoid subreddits similar to disliked ones
    - Weight disliked embeddings negatively in search
- Add explanation for recommendations:
    - "Recommended because you liked r/technology and r/programming"

**Success Criteria:**

- ✓ Recommendations balance similarity and diversity
- ✓ System avoids content similar to dislikes
- ✓ Confidence scores are meaningful
- ✓ Explanations help user understand why subreddit was recommended

---

## PHASE 4: EXPAND CONTENT

### Milestone 7: Add Posts Data

**Goal:** Pull hot posts from subreddits and let users rate them.

### M7.1 - Ugly MVP

**What to build:**

- Extend bronze pipeline (M1):
    - For each trending subreddit, fetch top 10 hot posts
    - Save posts to S3 bronze as JSON
- Extend silver pipeline (M2):
    - Transform posts to Parquet
    - Fields: post_id, subreddit, title, text_snippet, url, score, created_date
- Update CLI (M4):
    - After rating subreddits, show posts
    - Display: title + first 200 chars of text
    - User rates: like/dislike/skip
    - Save post ratings to gold layer (separate from subreddit ratings)

**Code structure:**

```python
# In fetch_reddit.py:
# After fetching subreddits, fetch posts for each

# In rate_subreddits.py:
# Add post rating section after subreddit rating

```

**Success Criteria:**

- ✓ Posts appear in bronze and silver layers
- ✓ CLI shows posts with title and snippet
- ✓ User can rate posts
- ✓ Post ratings saved to S3 separately from subreddit ratings

### M7.2 - Cleanup

**What to improve:**

- Combine subreddit + post signals for better recommendations:
    - If user likes posts from r/technology, boost r/technology recommendation
    - Use post content embeddings for finer-grained matching
- Add post-level embeddings:
    - Generate embeddings for post title + text
    - Store in pgvector alongside subreddit embeddings
    - Recommend specific posts, not just subreddits
- Weight post ratings higher than subreddit ratings:
    - Post rating = 2x weight of subreddit rating
    - More granular signal of user preferences
- Add post preview quality indicators:
    - Image post, text post, link post
    - Show thumbnail if available

**Success Criteria:**

- ✓ Recommendations use both subreddit and post data
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
    - System suggests 10 subreddits/posts it thinks user will LIKE
    - System suggests 10 subreddits/posts it thinks user will NOT like
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

### M8.2 - Cleanup (Analytics)

**What to build:**

- Jupyter notebook with analytics using Polars:
    - **Trending Analysis:**
        - Most featured subreddits over time
        - Subreddits gaining/losing popularity
        - Trending topics by week/month
    - **User Preference Analysis:**
        - Distribution of user ratings (like vs dislike ratio)
        - Most liked categories
        - User preference evolution over time
    - **Recommendation Performance:**
        - Accuracy over time (as user rates more)
        - Precision/recall curves
        - Confusion matrix for recommendations
    - **Data Quality Metrics:**
        - API success rate
        - Data completeness over time
        - Processing pipeline health

**Deliverables:**

- Jupyter notebook: `notebooks/analytics_dashboard.ipynb`
- Visualizations with matplotlib or plotly
- Weekly/monthly summary reports

**Success Criteria:**

- ✓ Analytics notebook runs and generates insights
- ✓ Charts are clear and informative
- ✓ You can identify trends and patterns
- ✓ Recommendation accuracy is tracked over time

---

## PHASE 6: SCALE

### Milestone 9: Scale to PySpark

**Goal:** Handle larger data volumes with PySpark.

### M9.1 - Ugly MVP

**What to build:**

- Replace Polars with PySpark in transform pipeline (M2)
- Keep same bronze → silver logic
- Test with larger dataset:
    - Increase to 100+ subreddits
    - 1000+ posts
    - Multiple days of historical data
- Run PySpark locally (not on EMR yet)
- Keep same Parquet output structure

**Code structure:**

```python
# transform_reddit_spark.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("RedditTransform").getOrCreate()

# Read JSON from bronze
df = spark.read.json("s3://bronze/...")

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
    - Partition by subreddit category
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
    - `POST /rate`: Rate a subreddit or post
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
- Deploy to AWS:
    - Use AWS App Runner, ECS, or EC2
    - Set up load balancer
    - Configure HTTPS
    - Set up domain name
- Add API documentation:
    - Swagger/OpenAPI docs
    - Rate limiting
    - API versioning

**Success Criteria:**

- ✓ Modern, polished web interface
- ✓ Multiple users can have separate accounts
- ✓ Application is deployed and accessible via URL
- ✓ API is documented and secure

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
- **Shared Collections**: Create and share curated subreddit/post collections
- **Community Insights**: Analyze preference patterns across all users

### AI Agents

- **Content Curator Agent**: Autonomous agent that pre-filters low-quality content
- **Discovery Agent**: Finds emerging subreddits and niche communities
- **Summarization Agent**: Creates TL;DR summaries of long posts
- **Sentiment Agent**: Analyzes community sentiment and warns about toxic content

### Infrastructure

- **Real-time Streaming**: Use Kafka/Kinesis for real-time content updates
- **GraphQL API**: More flexible API for frontend
- **Microservices**: Split into smaller services (ingestion, processing, recommendations)
- **Multi-region Deployment**: Global CDN and edge computing

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

---

## Project File Structure (Final)

```
reddit-recommender/
├── README.md
├── requirements.txt
├── docker-compose.yml          # Airflow + Postgres + pgvector
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Environment configs
│   │   └── logging_config.py
│   │
│   ├── data_ingestion/
│   │   ├── __init__.py
│   │   ├── reddit_client.py    # Reddit API wrapper
│   │   ├── fetch_subreddits.py # M1
│   │   └── fetch_posts.py      # M7
│   │
│   ├── data_processing/
│   │   ├── __init__.py
│   │   ├── transform_polars.py # M2 - Polars version
│   │   ├── transform_spark.py  # M9 - PySpark version
│   │   └── validators.py       # Data quality checks
│   │
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── generator.py        # Groq API integration
│   │   ├── vector_store.py     # pgvector operations
│   │   └── cache.py            # Embedding caching
│   │
│   ├── recommendations/
│   │   ├── __init__.py
│   │   ├── cold_start.py       # M5
│   │   ├── warm_start.py       # M6
│   │   ├── hybrid.py           # M7 - posts + subreddits
│   │   └── validator.py        # M8 - accuracy testing
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── s3_client.py        # S3 operations
│   │   └── database.py         # RDS/pgvector client
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── rate_content.py     # M4 - rating interface
│   │   └── recommend.py        # M5/M6 - recommendations
│   │
│   └── api/                    # M10
│       ├── __init__.py
│       ├── main.py             # FastAPI app
│       ├── routers/
│       │   ├── ratings.py
│       │   └── recommendations.py
│       └── models/
│           ├── schemas.py
│           └── database.py
│
├── airflow/                    # M3
│   ├── dags/
│   │   ├── reddit_ingestion_dag.py
│   │   └── embedding_generation_dag.py
│   ├── plugins/
│   └── config/
│
├── notebooks/                  # M8
│   ├── analytics_dashboard.ipynb
│   ├── model_experimentation.ipynb
│   └── data_exploration.ipynb
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── test_data/
│
├── scripts/
│   ├── setup_database.sql      # pgvector setup
│   ├── setup_s3_buckets.sh
│   └── deploy.sh
│
├── frontend/                   # M10.2
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.jsx
│   └── public/
│
└── docs/
    ├── API.md
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    └── ROADMAP.md              # This document!

```

---
