from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.inference.router import InferenceRouter
from app.models.agent import ChatRequest, ChatResponse
from app.models.budget import ItemizedBudget
from app.models.travel import (
    ActivityOption,
    FlightOption,
    HotelOption,
    TravelerPreference,
    TripState,
)
from app.models import Candidate, PlanPdfRequest, RankRequest, SessionEndRequest, TravelRequest
from app.providers.activity_provider import ActivityProviderAggregator
from app.providers.flight_provider import FlightProviderAggregator
from app.providers.hotel_provider import HotelProviderAggregator
from app.services.budget_engine import BudgetEngine
from app.services.commerce_service import CommerceService
from app.services.context_manager import ContextManager
from app.services.guardrails import Guardrails
from app.services.memory_service import MemoryService
from app.services.multimodal_service import MultimodalGateway
from app.services.observability import ObservabilityService
from app.services.recommendation_engine import RecommendationEngine

ALLOWED_MEDIA = {
    "image": {"image/jpeg", "image/png", "image/webp"},
    "audio": {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a"},
    "video": {"video/mp4", "video/webm"},
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TripPilot AI",
    description="Production-oriented AI-Native Travel Commerce Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

router_service = InferenceRouter()
flight_provider = FlightProviderAggregator()
hotel_provider = HotelProviderAggregator()
activity_provider = ActivityProviderAggregator()


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "TripPilot AI", "version": "1.0.0"}


@app.get("/metrics")
def metrics():
    return ObservabilityService.get_metrics_summary()


@app.post("/v1/chat", response_model=ChatResponse)
@app.post("/v1/travel/query", response_model=ChatResponse)
async def chat_query(request: TravelRequest | ChatRequest):
    # 1. Guardrails & input validation
    valid, err_msg = Guardrails.validate_input(request.text)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg)

    # 2. Extract profile preferences if provided
    profile_pref = None
    if request.profile:
        if isinstance(request.profile, TravelerPreference):
            profile_pref = request.profile
        else:
            profile_pref = TravelerPreference(
                dietary_requirements=request.profile.dietary_requirements,
                travel_style=request.profile.travel_style,
            )

    # 3. Route and process request
    response = await router_service.process_chat(
        user_id=request.user_id,
        text=request.text,
        trip_id=getattr(request, "trip_id", None),
        profile=profile_pref,
        detected_landmark=request.detected_landmark,
        modality=getattr(request, "modality", "text"),
    )

    # 4. Telemetry logging
    ObservabilityService.log_event(
        event_name="chat_interaction",
        request_id=f"req-{request.user_id[:8]}",
        user_id=request.user_id,
        intent=response.intent,
        confidence=response.confidence,
        model_used=response.model_used,
        status="success",
    )

    return response


@app.post("/v1/search/flights", response_model=list[FlightOption])
async def search_flights(
    origin: str = Body(default="Chennai"),
    destination: str = Body(default="Hyderabad"),
    date: str | None = Body(default=None),
    travelers: int = Body(default=1),
    cabin_class: str = Body(default="Economy"),
):
    return await flight_provider.search_flights(origin, destination, date, travelers, cabin_class)


@app.post("/v1/search/hotels", response_model=list[HotelOption])
async def search_hotels(
    city: str = Body(default="Hyderabad"),
    nights: int = Body(default=3),
    guests: int = Body(default=1),
    min_rating: float = Body(default=0.0),
    max_price_per_night: float | None = Body(default=None),
    dietary_preference: str | None = Body(default=None),
):
    return await hotel_provider.search_hotels(city, nights, guests, min_rating, max_price_per_night, dietary_preference)


@app.post("/v1/search/activities", response_model=list[ActivityOption])
async def search_activities(
    city: str = Body(default="Hyderabad"),
    category: str | None = Body(default=None),
    dietary_tags: list[str] | None = Body(default=None),
    crowd_preference: str | None = Body(default=None),
):
    return await activity_provider.search_activities(city, category, dietary_tags, crowd_preference)


@app.post("/v1/decision/rank")
def rank_options(request: RankRequest):
    weights = {"price": 0.30, "location": 0.25, "rating": 0.20, "preference": 0.15, "duration": 0.10}
    ranked = []
    for c in request.candidates:
        score = (
            c.price_score * 0.30
            + c.location_score * 0.25
            + c.rating_score * 0.20
            + c.preference_score * 0.15
            + c.amenities_score * 0.10
        )
        ranked.append({"name": c.name, "score": round(score * 100, 1)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {
        "recommendation": ranked[0],
        "ranked_options": ranked,
        "formula": "30% price + 25% location + 20% rating + 15% preference + 10% amenities",
    }


@app.post("/v1/trips/{trip_id}/cart")
def add_cart_item(trip_id: str, item: dict = Body(...)):
    cart_item = CommerceService.add_to_cart(
        trip_id=trip_id,
        item_type=item.get("type", "custom"),
        item_id=item.get("item_id", "custom-1"),
        name=item.get("name", "Custom Item"),
        unit_price=float(item.get("unit_price", 0.0)),
        quantity=int(item.get("quantity", 1)),
        currency=item.get("currency", "INR"),
        details=item.get("details", {}),
    )
    return {"status": "added", "cart_item": cart_item}


@app.get("/v1/trips/{trip_id}/budget", response_model=ItemizedBudget)
def get_trip_budget(trip_id: str, budget_ceiling: float | None = Query(default=None)):
    return CommerceService.calculate_cart_budget(trip_id, budget_ceiling=budget_ceiling)


@app.get("/v1/memory")
def get_user_memories(user_id: str = Query(...)):
    memories = MemoryService.retrieve_memories(user_id)
    profile = MemoryService.get_user_preference_profile(user_id)
    return {"user_id": user_id, "memories": memories, "profile": profile}


@app.post("/v1/memory")
def store_user_memory(
    user_id: str = Body(...),
    category: str = Body(default="preference"),
    key: str = Body(...),
    value: str = Body(...),
    confidence: float = Body(default=0.9),
):
    MemoryService.store_memory(user_id, category, key, value, confidence)
    return {"status": "stored", "key": key, "value": value}


@app.delete("/v1/memory/{user_id}")
@app.post("/v1/session/end", status_code=204)
def clear_user_memories(user_id: str | None = None, request: SessionEndRequest | None = None):
    target = user_id or (request.session_id if request else None)
    if target:
        MemoryService.delete_memory(target)


@app.post("/v1/multimodal/{modality}")
async def upload_media(modality: str, file: Annotated[UploadFile, File(...)]):
    if modality not in ALLOWED_MEDIA:
        raise HTTPException(status_code=404, detail="Supported modalities: image, audio, video")
    if file.content_type not in ALLOWED_MEDIA[modality]:
        raise HTTPException(status_code=415, detail=f"Unsupported {modality} file type")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 25 MB")

    return await MultimodalGateway.process_media(
        modality=modality,
        filename=file.filename or f"upload.{modality}",
        content=content,
        content_type=file.content_type,
    )


@app.post("/v1/plan/pdf")
def download_plan(request: PlanPdfRequest):
    """Create a styled, printable travel brief with itemized budget table."""
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TripPilotTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=HexColor("#0f172a"),
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "TripPilotBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#1e293b"),
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "TripPilotLabel",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=HexColor("#0284c7"),
        spaceBefore=10,
        spaceAfter=5,
    )

    escape = lambda text: text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

    story = [
        Paragraph("TripPilot AI · Multimodal Travel Brief", ParagraphStyle("Brand", parent=label_style, textColor=HexColor("#2563eb"))),
        Paragraph(escape(request.title.title()), title_style),
        Paragraph("TRAVEL BRIEF & ITINERARY", label_style),
        Paragraph(escape(request.answer), body_style),
    ]

    # Add itemized budget table if available
    if request.budget and request.budget.categories:
        story.extend([Spacer(1, 8), Paragraph("ITEMIZED BUDGET BREAKDOWN", label_style)])
        table_data = [["Category", "Allocated Line Items", "Subtotal (INR)"]]
        for cat in request.budget.categories:
            items_str = ", ".join([f"{it.name} (x{it.quantity})" for it in cat.items[:2]])
            table_data.append([cat.category.replace("_", " ").title(), items_str, f"₹{cat.subtotal:,.0f}"])
        table_data.append(["GRAND TOTAL", "All travel, stay, dining & transit items", f"₹{request.budget.grand_total:,.0f}"])

        t = Table(table_data, colWidths=[1.8 * inch, 3.8 * inch, 1.4 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, -1), (-1, -1), HexColor("#f1f5f9")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(t)

    if request.context:
        story.extend([Spacer(1, 8), Paragraph("POLICY & TRAVEL CONTEXT", label_style)])
        story.extend(Paragraph(f"• {escape(item)}", body_style) for item in request.context[:4])

    story.extend(
        [
            Spacer(1, 12),
            Paragraph(
                "Generated by TripPilot AI. Prices and availability are verified against travel providers. Verify bookings before travel.",
                ParagraphStyle("Footer", parent=body_style, fontSize=7.5, leading=10, textColor=HexColor("#64748b")),
            ),
        ]
    )

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=trippilot-travel-plan.pdf"},
    )
