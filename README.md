# Skill Recommender

Data pipeline and LangGraph-powered Telegram bot that ingests job vacancy data from hh.ru and produces skill demand analytics for data engineering roles in Kazakhstan.

---

## 🚀 Tech Stack

### Core Components

- **Apache Airflow** — pipeline orchestration via scheduled DAGs (every 3 days)
- **Amazon S3** — raw layer storage for unmodified API responses with Hive-style partitioning
- **Delta Lake** — bronze layer on S3 using append-only Delta tables
- **dbt-duckdb** — silver and gold layer transformations with incremental models
- **DuckDB** — local serving layer for the recommender app
- **hh.ru API** — vacancy data extraction with token management
- **LangGraph** — ReAct agent with custom tools + MCP server for ad-hoc SQL
- **aiogram** — Telegram bot interface for the skill recommender
- **Docker** — containerization of Airflow and pipeline components

---

## 📁 Project Structure

```
skill_reco/
├── dags/
│   └── vacancy_ingestion.py        # Airflow DAG: extract → bronze → dbt → sync
├── src/
│   ├── extract/
│   │   └── hh_vacancies.py         # hh.ru API extraction with retry logic
│   ├── load/
│   │   ├── bronze_vacancies.py     # Raw JSON → Delta Lake bronze on S3
│   │
│   ├── storage/
│   │   └── s3_client.py            # S3 client with partitioned upload/download
│   │
│   └── recommender.py              # LangGraph agent + Telegram bot
├── skill_reco/                     # dbt project
│   ├── models/
│   │   ├── silver/
│   │   │   ├── hh_vacancies.sql        # Incremental, deduped, flattened vacancies
│   │   │   └── vacancy_skills.py       # Skill extraction from key_skills + description
│   │   └── gold/
│   │       ├── skill_frequency.sql     # Overall skill demand with % of vacancies
│   │       ├── skill_by_experience.sql # Skill demand by experience level
│   │       ├── skill_by_employer.sql   # Skill demand by employer
│   │       └── skill_combinations.sql  # Co-occurring skill pairs
│   ├── seeds/
│   │   └── skills.csv              # Known skill dictionary for description extraction
│   ├── macros/
│   │   └── create_s3_secret.sql    # DuckDB S3 credential macro
│   ├── profiles.yml
│   └── dbt_project.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## 🛠 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourname/skill-reco.git
cd skill-reco
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# hh.ru API
HH_TOKEN=your_hh_token
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=eu-north-1
AWS_DEFAULT_REGION=eu-north-1
S3_BUCKET_NAME=your_bucket_name

# DuckDB
DUCKDB_PATH=/absolute/path/to/skill_reco.duckdb

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-nano

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Airflow
AIRFLOW_UID=50000
```

### 3. Build and Start Airflow

```bash
docker compose build
docker compose up -d
```

### 4. Initialize dbt

```bash
cd skill_reco
dbt deps
dbt seed      # load skills.csv
dbt run       # build silver and mart models
```

### 5. Start the Telegram Bot

```bash
uv run python -m src.recommender
```

---

## 🔧 Configuration

### Ports & Access

| Service    | URL                   | Credentials       |
| ---------- | --------------------- | ----------------- |
| Airflow UI | http://localhost:8080 | airflow / airflow |

---

## 📊 Pipeline Flow

```
vacancy_ingestion_dag  (every 3 days)
  ├── extract          ──► s3://bucket/vacancies/year=/month=/day=/HHMM.json
  ├── load_bronze      ──► s3://bucket/bronze/hh_vacancies/  (Delta table)
  ├── run_dbt
  │   ├── silver.hh_vacancies       (incremental, deduped, flattened)
  │   ├── silver.vacancy_skills     (key_skills + description extraction)
  │   ├── gold.skill_frequency
  │   ├── gold.skill_by_experience
  │   ├── gold.skill_by_employer
  │   └── gold.skill_combinations
  └── sync_duckdb      ──► skill_reco.duckdb  (local serving layer)
```

---

## 🗄 Data Layers

| Layer  | Location                                         | Description                                            |
| ------ | ------------------------------------------------ | ------------------------------------------------------ |
| Raw    | `s3://bucket/vacancies/`                         | Unmodified hh.ru API responses as JSON batches         |
| Bronze | `s3://bucket/bronze/hh_vacancies/`               | Append-only Delta table, nested fields as JSON strings |
| Silver | `skill_reco.duckdb` → `silver.hh_vacancies`      | Deduplicated, flattened vacancies                      |
| Silver | `skill_reco.duckdb` → `silver.vacancy_skills`    | One row per vacancy with extracted skills list         |
| Gold   | `skill_reco.duckdb` → `gold.skill_frequency`     | Skill demand with vacancy count and % of vacancies     |
| Gold   | `skill_reco.duckdb` → `gold.skill_by_experience` | Skill demand by experience level with rank             |
| Gold   | `skill_reco.duckdb` → `gold.skill_by_employer`   | Normalized skill demand per employer                   |
| Gold   | `skill_reco.duckdb` → `gold.skill_combinations`  | Co-occurring skill pairs by frequency                  |

---

## 🤖 Skill Recommender Agent

The LangGraph ReAct agent serves skill recommendations via Telegram. It combines:

**Custom tools (fast, pre-optimized):**

- `get_skill_frequency` — overall market demand
- `get_skill_by_experience` — demand by experience level
- `get_skill_combinations` — related skills to learn next
- `get_skills_by_employer` — employer-specific skill demand

**MCP server (ad-hoc SQL):**

- `mcp-server-duckdb` — lets the LLM write arbitrary SQL for complex queries

The agent uses `MemorySaver` checkpointer with `thread_id` per Telegram user, maintaining conversation history within each session.

**Example interaction:**

```
User: I know Python and SQL. What should I learn next?
Bot:  Based on market data, your next priorities should be:
      1. Airflow (67% of vacancies) — you likely already have SQL, Airflow is the next gap
      2. Docker (61% of vacancies) — essential for any DE role
      3. dbt (45% of vacancies) — pairs strongly with SQL in 38% of vacancies
```

---

## 🌱 Skill Extraction

Skills are extracted from two sources per vacancy:

1. **`key_skills` field** — structured list from hh.ru API
2. **`description` field** — HTML job description, parsed with regex word-boundary matching against `seeds/skills.csv`

Both sources are combined and deduplicated per vacancy, with `key_skills` taking priority.

---

## ♻️ Retry Strategy

| Layer       | Tenacity Retries          | Airflow Retries | Notes                     |
| ----------- | ------------------------- | --------------- | ------------------------- |
| Extract     | 5× exponential (2–10 sec) | 0               | Internal retry handles it |
| Bronze load | —                         | 1× / 5 min      | Handles S3 write failures |
| dbt run     | —                         | 1× / 5 min      | dbt handles model errors  |
| DuckDB sync | —                         | 1× / 5 min      | Handles lock conflicts    |

---

## 📝 Documentation

- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [dbt Docs](https://docs.getdbt.com/)
- [Delta Lake Python](https://delta-io.github.io/delta-rs/)
- [dbt-duckdb](https://github.com/duckdb/dbt-duckdb)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [hh.ru API](https://api.hh.ru/openapi/en/redoc)
- [aiogram Docs](https://docs.aiogram.dev/)
- [mcp-server-duckdb](https://github.com/ktanaka101/mcp-server-duckdb)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 Contact

If you have questions or suggestions, open an Issue in the repository or reach me through Telegram: @bexeiit.
