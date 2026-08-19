from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import RankRequest, TravelRequest
from .services import compose_answer, detect_intent, get_memories, initialize_db, retrieve, score_candidate, store_memory

ALLOWED_MEDIA = {"image": {"image/jpeg", "image/png", "image/webp"}, "audio": {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4"}, "video": {"video/mp4", "video/webm"}}


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_db()
    yield


app = FastAPI(title="TripPilot AI", version="0.1.0", lifespan=lifespan)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "TripPilot AI"}


@app.post("/v1/travel/query")
def travel_query(request: TravelRequest):
    intent, intent_confidence = detect_intent(request.text)
    context = retrieve(f"{request.text} {request.detected_landmark or ''}")
    memories = get_memories(request.user_id)
    answer = compose_answer(request.text, intent, request.detected_landmark, context, memories, request.profile)
    confidence = round(min(.95, (.65 * intent_confidence) + (.10 * bool(context)) + (.15 * bool(request.detected_landmark)) + (.10 * bool(request.text))), 2)
    store_memory(request.user_id, "session", request.text)
    store_memory(request.user_id, "response", answer)
    return {"answer": answer, "intent": intent, "confidence": confidence, "requires_clarification": confidence < .60, "retrieved_context": context, "memory_used": len(memories)}


@app.post("/v1/decision/rank")
def rank_options(request: RankRequest):
    ranked = sorted((score_candidate(candidate) for candidate in request.candidates), key=lambda item: item["score"], reverse=True)
    return {"recommendation": ranked[0], "ranked_options": ranked, "formula": "30% price + 25% location + 20% rating + 15% preference + 10% amenities"}


@app.post("/v1/multimodal/{modality}")
async def upload_media(modality: str, file: Annotated[UploadFile, File(...)]):
    if modality not in ALLOWED_MEDIA:
        raise HTTPException(status_code=404, detail="Supported modalities: image, audio, video")
    if file.content_type not in ALLOWED_MEDIA[modality]:
        raise HTTPException(status_code=415, detail=f"Unsupported {modality} file type")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 25 MB")
    # Production adapters should send the in-memory bytes to a vision/STT/video API,
    # then discard them. This MVP intentionally never persists uploaded media.
    return {"modality": modality, "filename": file.filename, "bytes_processed": len(content), "status": "accepted", "next_step": f"Configure a {modality} provider adapter to analyze this upload."}
