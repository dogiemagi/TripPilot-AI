# TripPilot AI

Lightweight, confidence-aware multimodal travel-agent MVP designed for a small Render deployment. Heavyweight vision, speech, video, maps, weather, and booking inference remain provider adapters rather than deployment artifacts.

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Included capabilities

- Text request router with travel-intent confidence
- JSON knowledge retrieval and SQLite session memory
- Landmark context passed into response fusion
- Image/audio/video upload endpoints with file validation and ephemeral processing
- Explainable hotel/activity decision engine
- Docker and Render configuration

## API examples

```bash
curl -X POST http://127.0.0.1:8000/v1/travel/query -H "Content-Type: application/json" -d "{\"user_id\":\"demo\",\"text\":\"Plan a 3 day Paris itinerary\",\"detected_landmark\":\"Eiffel Tower\"}"
```

```bash
pytest
```

## Production adapters

Add a provider module for a vision, speech-to-text, video-frame, LLM, weather, or places API. Pass only extracted text/entities into the orchestration flow and keep uploads in memory or temporary storage. The current answer composer is deliberately deterministic, so the service can run without API keys.
