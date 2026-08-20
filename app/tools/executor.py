import time
from typing import Any

from app.models.agent import ToolCallRecord
from app.providers.activity_provider import ActivityProviderAggregator
from app.providers.flight_provider import FlightProviderAggregator
from app.providers.hotel_provider import HotelProviderAggregator
from app.providers.weather_provider import OpenMeteoWeatherProvider
from app.services.rag_service import RAGPipeline
from .registry import (
    GetWeatherArgs,
    SearchActivitiesArgs,
    SearchFlightsArgs,
    SearchHotelsArgs,
    SearchKnowledgeArgs,
)


class ToolExecutor:
    def __init__(self) -> None:
        self.flight_provider = FlightProviderAggregator()
        self.hotel_provider = HotelProviderAggregator()
        self.activity_provider = ActivityProviderAggregator()
        self.weather_provider = OpenMeteoWeatherProvider()

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        start_time = time.perf_counter()
        status = "success"
        error_msg = None
        result: Any = None

        try:
            if tool_name == "search_flights":
                args = SearchFlightsArgs.model_validate(arguments)
                flights = await self.flight_provider.search_flights(
                    origin=args.origin,
                    destination=args.destination,
                    date=args.date,
                    travelers=args.travelers,
                    cabin_class=args.cabin_class,
                )
                result = {"count": len(flights), "flights": [f.model_dump() for f in flights]}

            elif tool_name == "search_hotels":
                args = SearchHotelsArgs.model_validate(arguments)
                hotels = await self.hotel_provider.search_hotels(
                    city=args.city,
                    nights=args.nights,
                    guests=args.guests,
                    min_rating=args.min_rating,
                    max_price_per_night=args.max_price_per_night,
                    dietary_preference=args.dietary_preference,
                )
                result = {"count": len(hotels), "hotels": [h.model_dump() for h in hotels]}

            elif tool_name == "search_activities":
                args = SearchActivitiesArgs.model_validate(arguments)
                activities = await self.activity_provider.search_activities(
                    city=args.city,
                    category=args.category,
                    dietary_tags=args.dietary_tags,
                    crowd_preference=args.crowd_preference,
                )
                result = {"count": len(activities), "activities": [a.model_dump() for a in activities]}

            elif tool_name == "get_weather":
                args = GetWeatherArgs.model_validate(arguments)
                weather = await self.weather_provider.get_forecast(city=args.city, date=args.date)
                result = weather

            elif tool_name == "search_knowledge":
                args = SearchKnowledgeArgs.model_validate(arguments)
                docs = RAGPipeline.retrieve(query=args.query, limit=args.limit)
                result = {"count": len(docs), "documents": docs}

            else:
                status = "error"
                error_msg = f"Unknown tool '{tool_name}'"
        except Exception as e:
            status = "error"
            error_msg = str(e)

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return ToolCallRecord(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            status=status,
            latency_ms=latency,
            error_message=error_msg,
        )
