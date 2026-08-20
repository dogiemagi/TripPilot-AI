import os
from typing import Literal

from app.inference.confidence import ConfidenceEvaluator
from app.inference.model_registry import MODEL_REGISTRY, get_available_ai_provider
from app.models.agent import ChatResponse
from app.models.travel import TravelerPreference


class InferenceRouter:
    def __init__(self) -> None:
        self._orchestrator = None

    @property
    def orchestrator(self):
        if self._orchestrator is None:
            from app.agents.orchestrator import Orchestrator
            self._orchestrator = Orchestrator()
        return self._orchestrator

    def route_request(
        self,
        text: str,
        modality: Literal["text", "image", "audio", "video"] = "text",
    ) -> dict:
        intent_res = ConfidenceEvaluator.evaluate_intent(text)
        provider = get_available_ai_provider()

        if modality == "image":
            selected_model = "gemini-flash" if provider == "google" else "trippilot-deterministic"
            task_type = "vision_multimodal"
        elif modality == "audio":
            selected_model = "whisper-1" if provider == "openai" else "trippilot-deterministic"
            task_type = "audio_stt"
        elif intent_res.intent == "itinerary_planning":
            selected_model = "gemini-pro" if provider == "google" else "trippilot-deterministic"
            task_type = "reasoning_planning"
        elif intent_res.confidence < 0.65:
            selected_model = "trippilot-deterministic"
            task_type = "clarification"
        else:
            selected_model = "gemini-flash" if provider == "google" else "trippilot-deterministic"
            task_type = "fast_chat"

        return {
            "intent_result": intent_res,
            "selected_model": selected_model,
            "task_type": task_type,
            "provider": provider,
        }

    async def process_chat(
        self,
        user_id: str,
        text: str,
        trip_id: str | None = None,
        profile: TravelerPreference | None = None,
        detected_landmark: str | None = None,
        modality: Literal["text", "image", "audio", "video"] = "text",
    ) -> ChatResponse:
        routing = self.route_request(text, modality=modality)
        intent_res = routing["intent_result"]

        if intent_res.requires_clarification and intent_res.clarification_prompt:
            return ChatResponse(
                trip_id=trip_id,
                answer=intent_res.clarification_prompt,
                intent=intent_res.intent,
                confidence=intent_res.confidence,
                requires_clarification=True,
                clarification_prompt=intent_res.clarification_prompt,
                model_used=routing["selected_model"],
            )

        return await self.orchestrator.run(
            user_id=user_id,
            text=text,
            trip_id=trip_id,
            profile=profile,
            detected_landmark=detected_landmark,
            intent=intent_res.intent,
            confidence=intent_res.confidence,
        )
