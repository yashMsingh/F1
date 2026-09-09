# Phase 2B.8 — F1 Race Intelligence Dashboard & API Layer

## Overview

The F1 Race Intelligence Dashboard is a polished, resume-quality analytics web application built with **FastAPI** (Python backend) and **React + TypeScript + Vite** (frontend).

The dashboard visualizes the full F1 intelligence pipeline:
```text
Raw F1 Data (PostgreSQL)
       ↓
Computed Analytical SQL Layer
       ↓
Statistical Evidence Layer
       ↓
Deterministic Insight Engine (16 Rules)
       ↓
Grounded AI Narrative Layer (Groq / OpenRouter)
       ↓
FastAPI Backend Boundary
       ↓
React / TypeScript UI
```

---

## Architectural Principles

1. **Database as Single Source of Truth**: The frontend never computes rankings, point totals, or deltas. All analytical values originate deterministically from backend queries.
2. **Deterministic Rules Before AI Narration**: Insights are detected using deterministic statistical rules. The LLM acts solely as a grounded narrator and never invents metrics.
3. **Fault-Tolerant AI Isolation**: If an LLM provider times out, hits rate limits, or is unconfigured, the dashboard continues to function with 100% operational integrity for all deterministic analytics.
4. **Zero Client-Side Secrets**: All database URLs and AI API keys (`GROQ_API_KEY`, `OPENROUTER_API_KEY`) remain strictly backend-side. The frontend only communicates with `/api/*` endpoints.

---

## Backend API Specification

The backend API is implemented with FastAPI in `app/api/`.

### Base URL
Default: `http://127.0.0.1:8000/api`

### Endpoints

| Method | Endpoint | Description | Response Schema |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health check and API version | `HealthResponse` |
| `GET` | `/races` | Available championship races for selector | `list[RaceListItem]` |
| `GET` | `/races/{season}/{round}` | Grand Prix overview & winner information | `RaceOverviewResponse` |
| `GET` | `/races/{season}/{round}/results` | Full classification and Grid-to-Finish changes | `RaceResultsResponse` |
| `GET` | `/races/{season}/{round}/qualifying`| Qualifying order and teammate deltas | `QualifyingResponse` |
| `GET` | `/races/{season}/{round}/pit-stops` | Driver & constructor pit stop aggregations | `PitStopsResponse` |
| `GET` | `/races/{season}/{round}/laps` | Driver lap time summaries | `LapTimesResponse` |
| `GET` | `/races/{season}/{round}/standings` | Official persisted driver & constructor standings | `StandingsResponse` |
| `GET` | `/races/{season}/{round}/insights` | Deterministic insights with traceability trail | `InsightsResponse` |
| `GET` | `/races/{season}/{round}/narrative`| Grounded natural-language explanation | `NarrativeResponse` |

### Narrative Failure Handling
When AI narrative generation fails or is unconfigured, the endpoint returns HTTP 200 with:
```json
{
  "status": "unavailable",
  "provider": null,
  "model": null,
  "narrative": null,
  "limitations": [],
  "evidence_references": [],
  "error": "AI Provider credentials unconfigured."
}
```
The frontend gracefully displays an informative fallback notice while leaving all analytical charts and tables interactive.

---

## Frontend Architecture

The frontend is structured in `frontend/`:

```text
frontend/
├── src/
│   ├── api/
│   │   └── client.ts            # Centralized typed HTTP client
│   ├── components/
│   │   ├── Navbar.tsx           # Brand, live API indicator, race selector slot
│   │   ├── RaceSelector.tsx     # Season & round dropdown picker
│   │   ├── HeroHeader.tsx       # Race title, circuit, date, winner card
│   │   ├── RaceResultsTable.tsx # Full classification with position change badges
│   │   ├── GridVsFinishChart.tsx# Visual position change grid (Grid → Finish)
│   │   ├── QualifyingSection.tsx# Q1/Q2/Q3 order & teammate delta comparisons
│   │   ├── PitStopSection.tsx   # Driver & team pit stop duration analytics
│   │   ├── LapTimeSection.tsx   # Driver lap records with telemetry note
│   │   ├── StandingsSection.tsx # Official driver and constructor standings
│   │   ├── InsightsSection.tsx  # Deterministic insight cards with audit trail
│   │   ├── NarrativeSection.tsx # Grounded AI narrative container
│   │   └── LoadingSkeleton.tsx  # Loading skeletons & ErrorBoundary
│   ├── types/
│   │   └── api.ts               # Complete TypeScript API contracts
│   ├── utils/
│   │   └── formatters.ts        # Presentation formatting (time, deltas, positions)
│   ├── App.tsx                  # Root state orchestration & tab navigation
│   ├── index.css                # Motorsport dark theme styling
│   └── main.tsx                 # React DOM mount point
```

### Visual Direction
- **Dark Motorsport Palette**: Pitch-black carbon backdrop (`#0e1015`), surface cards (`#161822`), elevated layers (`#1f2230`), and border styling (`#2a2e40`).
- **F1 Racing Red**: `#e10600` accent for brand badges, active tabs, and primary action indicators.
- **Accessible Indicators**: Position changes use both textual arrows and signs (`▲ +3`, `▼ -2`, `▬ 0`) in addition to green/red colors to ensure readability across all displays and contrast needs.

---

## Local Development & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ (tested on Node.js v24.11.1)
- npm 9+ (tested on npm 11.13.0)

### 1. Backend Server
```bash
# From project root:
uvicorn app.api.app:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger documentation: `http://127.0.0.1:8000/docs`
- Redoc documentation: `http://127.0.0.1:8000/redoc`

### 2. Frontend Development Server
```bash
# From frontend directory:
cd frontend
npm run dev
```
- Local dashboard URL: `http://localhost:5173`

### 3. Production Build
```bash
cd frontend
npm run build
```

---

## Testing & Verification

### Backend Tests
Run the entire backend test suite (277 tests):
```bash
pytest tests/ -v
```

Run API endpoint tests specifically:
```bash
pytest tests/api/ -v
```

### Frontend Tests
Run Vitest component tests:
```bash
cd frontend
npm test
```

---

## Security & Isolation Guarantees

1. **No Frontend Secrets**: Browser network inspection confirms zero exposure of `DATABASE_URL`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY`.
2. **Restricted CORS**: Backend restricts allowed origins to explicit local development URLs (`http://localhost:5173`, `http://127.0.0.1:5173`).
3. **No Direct External API Calls**: The frontend never connects to Jolpica API, Groq, or OpenRouter.
4. **Parameter Validation**: All season and round parameters are validated as strict integers via FastAPI route definitions.

---

## Known Limitations & Future Work

- **Sprint Weekend Sessions**: Sprint qualifying and sprint race analytics will be added once sprint session rules are integrated in the analytics spec.
- **Tyre Compound Visualizations**: Stint tyre degradation requires FastF1 session telemetry ingestion planned for Phase 3.
- **Historical Comparison Graphs**: Multi-race rolling form charts will be implemented when full multi-season data is persisted.
