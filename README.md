# TripPilot AI · AI-Native Travel Commerce Platform

TripPilot AI is a production-oriented, AI-native travel planning and recommendation platform inspired by the capabilities of conversational travel assistants like Mondee's Abhi AI.

It combines multi-agent orchestration, live travel data abstraction, deterministic itemized budgeting, task-aware AI inference routing, short/long-term memory, multi-factor recommendation ranking, RAG with hybrid retrieval & reranking, safety guardrails, and conversational commerce.

---

## Key Architecture & Core Capabilities

```text
                         USER (Web UI / API Client)
                                      │
                           Text / Image / Audio
                                      │
                                      ▼
                             Multimodal Gateway
                                      │
                                      ▼
                        Guardrails & Input Validator
                                      │
                                      ▼
                               Context Manager
                        ┌─────────────┼─────────────┐
                        ▼             ▼             ▼
                   Session State  Trip State  Long-Term Memory
                        └─────────────┼─────────────┘
                                      ▼
                             AI Inference Router
                                      │
                        ┌─────────────┼─────────────┐
                        ▼             ▼             ▼
                   Fast/Cheap LLM  Reasoning LLM Vision / Audio
                        └─────────────┼─────────────┘
                                      ▼
                              Agent Orchestrator
                                      │
            ┌───────────────────┬─────┴─────────────┬───────────────────┐
            ▼                   ▼                   ▼                   ▼
       Flight Agent        Hotel Agent        Activity Agent       Budget Agent
            │                   │                   │                   │
            ▼                   ▼                   ▼                   ▼
     Flight Provider     Hotel Provider      Activity Provider    Budget Engine
     (Amadeus / Mock)    (Live / Mock)       (Places / Mock)     (Deterministic)
            └───────────────────┼───────────────────┴───────────────────┘
                                ▼
                      Recommendation Engine
                (Multi-attribute utility + Explanations)
                                │
                                ▼
                     RAG Pipeline + Reranker
                 (Policies, Guides, baggage, visas)
                                │
                                ▼
                         Itinerary Agent
                  (Time-optimized daily scheduling)
                                │
                                ▼
                       Conversational Commerce
                         (Cart & Booking Flow)
```

---

## Highlights & Features

1. **Provider Abstraction Layer**:
   - `FlightProvider`: Realistic catalog + Amadeus Live API integration with credential checking and graceful fallback.
   - `HotelProvider`: Full hotel catalog with star ratings, user ratings, pure vegetarian dining options, and distance calculations.
   - `ActivityProvider`: Cultural sights, crowd density estimates (`low`, `moderate`, `high`), timing, and pure vegetarian / vegan culinary stops.
   - `WeatherProvider`: Open-Meteo live API + deterministic fallback.
   - Distinct metadata labeling (`is_live`, `price_type`: `live` | `cached` | `estimated` | `mock`).

2. **100% Deterministic Itemized Budget Engine**:
   - Item-level arithmetic: `quantity * unit_price = total`.
   - Category subtotals: `Flights`, `Hotels`, `Food`, `Local Transportation`, `Activities`, `Insurance`, `Taxes & Fees`.
   - Daily budgeting breakdowns (`Day 1`, `Day 2`, ..., `Day N`).
   - Budget ceiling enforcement (`ceiling - grand_total = remaining_buffer`).
   - Automated cost reduction suggestions if over budget.

3. **AI Inference Router & Fallback Chain**:
   - Routes between Fast LLM (Flash/GPT-4o-mini), Reasoning LLM (Pro/GPT-4o), Vision/Audio, and deterministic engines.
   - Confidence evaluation with clarification triggers for ambiguous inputs (e.g. *"Find something cheap for tomorrow"* $\to$ asks for clarification).

4. **Multi-Turn Context & Persistent Long-Term Memory**:
   - Separates session conversation, trip state, persistent user preferences (e.g. vegetarian, low crowds), and decision history.
   - Resolves follow-ups: *"Make it cheaper"* or *"Keep the hotel but change the flight"*.

5. **Multi-Attribute Recommendation Engine**:
   - Utility scoring combining Price, User Preference, Rating, Location, Duration, and Crowd Density.
   - Generates transparent natural language explanations citing concrete reasons and price deltas.

6. **RAG Knowledge Retrieval & Reranker**:
   - In-memory TF-IDF vector index + BM25 keyword matching + cross-scoring reranker.
   - Comprehensive knowledge base (`travel_policies.json` & `travel_knowledge.json`) covering airline baggage limits, cancellation rules, and destination guides.

7. **Fine-Tuning Readiness & Evaluation Benchmark**:
   - Curated `training/train.jsonl` and `training/validation.jsonl` across 9 travel intent classes.
   - Standalone automated evaluation suite `evaluation/eval_suite.py` measuring intent accuracy, budget arithmetic, RAG relevance, recommendation grounding, and tool execution.

---

## Local Setup & Quickstart

```bash
# 1. Clone & create virtual environment
python -m venv .venv
.venv\Scripts\activate  # On Windows (or source .venv/bin/activate on Linux/macOS)

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Configure environment variables in .env
cp .env.example .env

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000` in your browser for the web application UI, or `http://127.0.0.1:8000/docs` for interactive OpenAPI documentation.

---

## Running Tests & Evaluation Suite

```bash
# Run unit & integration test suite (21 tests)
pytest

# Run benchmark evaluation suite
python evaluation/eval_suite.py
```

---

## API Endpoints Overview

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/chat` | Main conversational travel copilot endpoint |
| `POST` | `/v1/travel/query` | Backward-compatible query endpoint |
| `POST` | `/v1/search/flights` | Search flights between origin and destination |
| `POST` | `/v1/search/hotels` | Search accommodation options by city & filters |
| `POST` | `/v1/search/activities` | Curated attractions and culinary experiences |
| `POST` | `/v1/trips/{trip_id}/cart` | Add flight/hotel/activity to trip cart |
| `GET` | `/v1/trips/{trip_id}/budget` | Retrieve itemized budget for a trip |
| `GET` | `/v1/memory` | Retrieve persistent user travel preferences |
| `POST` | `/v1/multimodal/{modality}` | Upload image/audio/video for context extraction |
| `POST` | `/v1/plan/pdf` | Export styled travel plan & itemized budget PDF |
| `GET` | `/health` | Service health status |
| `GET` | `/metrics` | Telemetry & request distribution metrics |

---

## Render Deployment Instructions

This repository is optimized for deployment on Render's free or starter web service tiers.

### Deployment

1. Connect the GitHub repository `dogiemagi/TripPilot-AI` to [Render](https://render.com).

2. Select **Web Service** with **Docker Runtime**, or use the included `render.yaml` Blueprint if available.

3. The service uses Python 3.12-slim and starts with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Live Demo
- **Deployed App**: [https://trippilot-ai-nc4g.onrender.com/](https://trippilot-ai-nc4g.onrender.com/)