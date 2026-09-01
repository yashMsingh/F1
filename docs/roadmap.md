# F1 Race Intelligence — Roadmap

> Last updated: 2026-09-01

This document defines the implementation phases for the F1 Race Intelligence platform. Each phase has clear objectives, inputs, outputs, dependencies, and completion criteria.

---

## Phase 1: Product & Architecture ✅

**Objective**: Define the project vision, architecture, data sources, database schema, analytics specification, and roadmap.

**Inputs**:
- Project requirements document
- Verified API endpoint responses
- FastF1 documentation

**Outputs**:
- `docs/product-spec.md`
- `docs/architecture.md`
- `docs/data-sources.md`
- `docs/database-schema.md`
- `docs/data-dictionary.md`
- `docs/analytics-spec.md`
- `docs/roadmap.md`
- `AGENTS.md`
- `.gitignore`
- Initialized Git repository

**Dependencies**: None

**Completion Criteria**:
- [x] All documentation files created
- [x] Data sources verified against live API
- [x] Database schema based on actual API response structures
- [x] Analytics metrics formally defined with edge cases
- [x] Repository initialized with Git

---

## Phase 2: Data Sources & Database Setup

**Objective**: Set up PostgreSQL database, implement schema migrations, and create the initial project structure.

**Inputs**:
- `docs/database-schema.md`
- PostgreSQL installation

**Outputs**:
- Python project structure (`src/` directory with packages)
- `pyproject.toml` or `requirements.txt` with pinned dependencies
- SQLAlchemy models matching the documented schema
- Alembic migrations for all tables
- Database connection configuration (environment variables)
- Docker Compose file for PostgreSQL (optional but recommended)
- Basic test infrastructure (pytest)

**Dependencies**: Phase 1 complete

**Completion Criteria**:
- [ ] `alembic upgrade head` creates all 12 tables + etl_log
- [ ] SQLAlchemy models match the schema document
- [ ] Foreign keys and indexes verified
- [ ] Database can be stood up from scratch reproducibly
- [ ] Environment variables documented in `.env.example`
- [ ] Basic smoke test passes

---

## Phase 3: Data Ingestion / ETL

**Objective**: Build the ETL pipeline to ingest F1 data from the Jolpica API into PostgreSQL.

**Inputs**:
- Jolpica API (verified endpoints)
- SQLAlchemy models
- `docs/data-dictionary.md` (parsing rules)

**Outputs**:
- API client module with rate limiting, pagination, retry/backoff, caching
- ETL modules for each entity type:
  - Seasons
  - Circuits
  - Constructors
  - Drivers
  - Races (schedule)
  - Race Results
  - Qualifying Results
  - Sprint Results
  - Pit Stops
  - Lap Times
  - Driver Standings
  - Constructor Standings
- Time-string parser (handles all formats)
- Data validation layer
- ETL orchestrator (can ingest a full season or specific race)
- ETL logging to `etl_log` table
- CLI interface for running ingestion

**Dependencies**: Phase 2 complete

**Completion Criteria**:
- [ ] Can ingest a complete recent season (e.g., 2024 or 2025)
- [ ] All tables populated with correct data
- [ ] Idempotent: re-running ingestion doesn't create duplicates
- [ ] Pagination works for large datasets (laps, pit stops)
- [ ] Edge cases handled: DNF, DNS, DSQ, missing qualifying sessions, empty sprint rounds
- [ ] ETL log records all operations
- [ ] Time strings correctly parsed to milliseconds
- [ ] Unit tests for parser and validation logic
- [ ] Rate limiting verified (courteous API usage)

---

## Phase 4: SQL Analytics

**Objective**: Implement the core SQL-based analytical metrics defined in `analytics-spec.md`.

**Inputs**:
- Populated database (from Phase 3)
- `docs/analytics-spec.md` (P0 and P1 metrics)

**Outputs**:
- SQL views or materialized views for:
  - Driver season summary (avg position, points, wins, podiums, DNF rate)
  - Constructor season summary
  - Race summary (winner, podium, fastest lap, positions gained)
  - Qualifying vs race delta
  - Teammate head-to-head comparison
  - Championship progression (cumulative points by round)
  - Pit stop statistics per race/constructor
- Python query functions wrapping SQL analytics
- Analytics test suite validating calculations against known data
- FastAPI endpoints (initial) serving analytics results

**Dependencies**: Phase 3 complete (database populated)

**Completion Criteria**:
- [ ] All P0 metrics implemented and tested
- [ ] All P1 metrics implemented and tested
- [ ] Results verified against official F1 standings for at least one season
- [ ] Analytics queries perform within acceptable time (<2s for single-season queries)
- [ ] FastAPI serves at least: `/api/races/{season}`, `/api/drivers/{id}/stats`, `/api/constructors/{id}/stats`

---

## Phase 5: Statistical Analytics

**Objective**: Add statistical analysis layer on top of SQL analytics.

**Inputs**:
- SQL analytics (from Phase 4)
- `docs/analytics-spec.md` (P2 and P3 metrics, statistical methods)

**Outputs**:
- Python statistics module using SciPy/NumPy:
  - Rolling averages (N-race moving average)
  - Z-score computation for outlier detection
  - Pearson correlation analysis
  - OLS linear regression for trend detection
  - Confidence intervals on key averages
- Race pace analysis (median lap time with outlier filtering)
- Performance trend analysis per driver/constructor
- Statistical results API endpoints

**Dependencies**: Phase 4 complete

**Completion Criteria**:
- [ ] Rolling averages computed and serving via API
- [ ] Z-score outlier detection working on finishing positions, lap times, pit stops
- [ ] At least one correlation analysis demonstrated (e.g., qualifying → finishing position)
- [ ] Linear regression trend for at least one driver's season performance
- [ ] Confidence intervals reported on key averages
- [ ] Statistical methods documented with purpose and assumptions
- [ ] Tests verify statistical calculations against known results

---

## Phase 6: Automated Insight Detection

**Objective**: Build the deterministic insight detection engine that identifies noteworthy patterns and anomalies.

**Inputs**:
- SQL analytics + statistical analytics
- Insight triggers from `docs/analytics-spec.md`

**Outputs**:
- Insight detection engine (Python):
  - Scans analytics results against defined triggers
  - Generates candidate findings with evidence packages
  - Each finding includes: metrics, baselines, statistical significance, methodology
- Evidence package data structure (typed Python dataclass/Pydantic model)
- Insight storage (database table or JSON output)
- API endpoints for retrieving insights

**Dependencies**: Phase 5 complete

**Completion Criteria**:
- [ ] At least 5 insight triggers implemented
- [ ] Evidence packages contain all required fields
- [ ] Insights generated for a real season produce plausible findings
- [ ] No AI involvement in the detection phase
- [ ] False positive rate acceptable (subjective review of ~20 generated insights)
- [ ] Insights ranked by severity

---

## Phase 7: AI Insight Generation

**Objective**: Add the AI explanation layer that transforms evidence packages into natural-language insights.

**Inputs**:
- Evidence packages (from Phase 6)
- `docs/product-spec.md` (AI rules)

**Outputs**:
- LLM integration module (provider-agnostic interface):
  - Support for at least one provider (OpenAI, Anthropic, or Gemini)
  - Structured output format: title, summary, severity, evidence, explanation, methodology, confidence
- Prompt engineering:
  - System prompt enforcing grounding rules
  - Evidence injection into prompts
  - Epistemic classification (fact vs. finding vs. prediction vs. interpretation)
- AI output validation (reject if references non-existent data)
- API endpoints serving AI-enhanced insights
- `docs/ai-insight-spec.md` documenting the prompt design and rules

**Dependencies**: Phase 6 complete

**Completion Criteria**:
- [ ] AI generates explanations grounded in evidence
- [ ] AI does NOT invent statistics
- [ ] AI distinguishes fact from interpretation
- [ ] Structured output matches defined schema
- [ ] Provider can be swapped via configuration
- [ ] At least 10 insights generated and manually reviewed for quality
- [ ] Prompt and grounding rules documented

---

## Phase 8: Visualization / Frontend Dashboard

**Objective**: Build the React frontend dashboard to visualize analytics and insights.

**Inputs**:
- FastAPI backend with all analytics and insight endpoints
- Chart data from analytics engine (NOT from AI)

**Outputs**:
- React + TypeScript + Vite project
- Dashboard pages:
  - Race Overview (results, positions gained, fastest laps, pit stops)
  - Driver Profile (season stats, performance trends, teammate comparison)
  - Constructor Profile (season stats, reliability, driver contribution)
  - Championship Standings (interactive progression chart)
  - Insights Feed (AI-generated insights with evidence cards)
- Charting library integration (Recharts or equivalent)
- Responsive design with dark mode
- Season/race selector components

**Dependencies**: Phase 7 complete (or Phase 4 for analytics-only dashboard)

**Completion Criteria**:
- [ ] Dashboard renders real data from API
- [ ] Charts driven by analytical data (not AI-generated numbers)
- [ ] At least 4 pages functional
- [ ] Responsive on desktop and tablet
- [ ] Dark mode implemented
- [ ] Insights displayed with evidence and methodology visible
- [ ] No hardcoded data in frontend

---

## Phase 9: ML / Predictive Analytics

**Objective**: Add machine learning models for predictive analysis.

**Inputs**:
- Historical data (multiple seasons)
- Statistical analytics

**Outputs**:
- Predictive models (scikit-learn):
  - Race result prediction (classification or regression)
  - Qualifying position prediction
  - Championship outcome probability
- Feature engineering pipeline
- Model evaluation (cross-validation, accuracy metrics)
- Prediction confidence reporting
- Integration with insight engine (predictions as a finding type)

**Dependencies**: Phase 5 complete (statistical analytics), multiple seasons of data

**Completion Criteria**:
- [ ] At least one predictive model trained and evaluated
- [ ] Model performance documented with appropriate metrics
- [ ] Predictions clearly labeled as "model predictions" (not facts)
- [ ] Confidence/uncertainty reported alongside predictions
- [ ] Model versioning and reproducibility

---

## Phase 10: Ask the Data + Productionization

**Objective**: Add natural-language query interface and production hardening.

**Inputs**:
- Full platform (Phases 1-9)

**Outputs**:
- Natural-language-to-SQL interface:
  - LLM generates SQL from user questions
  - SQL validation/whitelist (SELECT only; block all mutating operations)
  - Read-only database user for query execution
  - Result formatting and AI explanation
- Production infrastructure:
  - Docker Compose for full stack
  - CI/CD pipeline (GitHub Actions)
  - Monitoring and alerting
  - Automated ingestion scheduler
  - Error tracking
  - Performance optimization (query caching, connection pooling)

**Dependencies**: All prior phases

**Completion Criteria**:
- [ ] Users can ask questions in natural language and receive data-backed answers
- [ ] SQL injection fully prevented (whitelist + read-only user)
- [ ] Full stack deployable via Docker Compose
- [ ] CI/CD runs tests on every PR
- [ ] Documentation complete and up-to-date

---

## Phase Summary

| Phase | Name | Status | Estimated Effort |
|-------|------|--------|-----------------|
| 1 | Product & Architecture | ✅ Complete | — |
| 2 | Database Setup | 🔲 Not started | 1-2 sessions |
| 3 | Data Ingestion / ETL | 🔲 Not started | 2-3 sessions |
| 4 | SQL Analytics | 🔲 Not started | 2-3 sessions |
| 5 | Statistical Analytics | 🔲 Not started | 1-2 sessions |
| 6 | Insight Detection | 🔲 Not started | 1-2 sessions |
| 7 | AI Insight Generation | 🔲 Not started | 1-2 sessions |
| 8 | Frontend Dashboard | 🔲 Not started | 3-4 sessions |
| 9 | ML / Predictive | 🔲 Not started | 2-3 sessions |
| 10 | Ask the Data | 🔲 Not started | 2-3 sessions |

> **Recommended next step**: Phase 2 — Set up the Python project structure, SQLAlchemy models, Alembic migrations, and database infrastructure.
