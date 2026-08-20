import os
from datetime import datetime, timezone
import httpx

from app.models.budget import PriceMetadata
from app.models.travel import FlightOption
from .base import FlightProvider


MOCK_FLIGHT_CATALOG = [
    # Chennai -> Hyderabad
    {
        "id": "fl-maa-hyd-6e512",
        "airline": "IndiGo",
        "flight_number": "6E-512",
        "origin": "Chennai",
        "destination": "Hyderabad",
        "departure_time": "06:15",
        "arrival_time": "07:30",
        "duration": "1h 15m",
        "stops": 0,
        "base_price": 4200.0,
        "cabin_class": "Economy",
        "baggage": "15kg check-in, 7kg cabin",
    },
    {
        "id": "fl-maa-hyd-ai840",
        "airline": "Air India",
        "flight_number": "AI-840",
        "origin": "Chennai",
        "destination": "Hyderabad",
        "departure_time": "09:45",
        "arrival_time": "11:05",
        "duration": "1h 20m",
        "stops": 0,
        "base_price": 5100.0,
        "cabin_class": "Economy",
        "baggage": "25kg check-in, 7kg cabin, meal included",
    },
    {
        "id": "fl-maa-hyd-sg304",
        "airline": "SpiceJet",
        "flight_number": "SG-304",
        "origin": "Chennai",
        "destination": "Hyderabad",
        "departure_time": "18:20",
        "arrival_time": "19:40",
        "duration": "1h 20m",
        "stops": 0,
        "base_price": 3800.0,
        "cabin_class": "Economy",
        "baggage": "15kg check-in, 7kg cabin",
    },
    # Delhi -> Goa
    {
        "id": "fl-del-goa-6e214",
        "airline": "IndiGo",
        "flight_number": "6E-214",
        "origin": "Delhi",
        "destination": "Goa",
        "departure_time": "08:10",
        "arrival_time": "10:45",
        "duration": "2h 35m",
        "stops": 0,
        "base_price": 5600.0,
        "cabin_class": "Economy",
        "baggage": "15kg check-in, 7kg cabin",
    },
    # Delhi / Mumbai -> Paris
    {
        "id": "fl-del-cdg-af225",
        "airline": "Air France",
        "flight_number": "AF-225",
        "origin": "Delhi",
        "destination": "Paris",
        "departure_time": "01:30",
        "arrival_time": "06:45",
        "duration": "8h 45m",
        "stops": 0,
        "base_price": 48500.0,
        "cabin_class": "Economy",
        "baggage": "23kg check-in, 8kg cabin",
    },
    # Mumbai -> Dubai
    {
        "id": "fl-bom-dxb-ek501",
        "airline": "Emirates",
        "flight_number": "EK-501",
        "origin": "Mumbai",
        "destination": "Dubai",
        "departure_time": "04:30",
        "arrival_time": "06:15",
        "duration": "3h 15m",
        "stops": 0,
        "base_price": 19200.0,
        "cabin_class": "Economy",
        "baggage": "30kg check-in, 7kg cabin",
    },
]


class MockFlightProvider(FlightProvider):
    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: str | None = None,
        travelers: int = 1,
        cabin_class: str = "Economy",
    ) -> list[FlightOption]:
        norm_orig = origin.strip().lower()
        norm_dest = destination.strip().lower()

        matched = [
            f for f in MOCK_FLIGHT_CATALOG
            if norm_orig in f["origin"].lower() and norm_dest in f["destination"].lower()
        ]

        if not matched:
            # Generate deterministic fallback flights for any city pair
            matched = [
                {
                    "id": f"fl-{norm_orig[:3]}-{norm_dest[:3]}-eco1",
                    "airline": "IndiGo",
                    "flight_number": "6E-711",
                    "origin": origin.title(),
                    "destination": destination.title(),
                    "departure_time": "07:00",
                    "arrival_time": "08:45",
                    "duration": "1h 45m",
                    "stops": 0,
                    "base_price": 4500.0,
                    "cabin_class": cabin_class,
                    "baggage": "15kg check-in, 7kg cabin",
                },
                {
                    "id": f"fl-{norm_orig[:3]}-{norm_dest[:3]}-eco2",
                    "airline": "Air India",
                    "flight_number": "AI-602",
                    "origin": origin.title(),
                    "destination": destination.title(),
                    "departure_time": "14:15",
                    "arrival_time": "16:05",
                    "duration": "1h 50m",
                    "stops": 0,
                    "base_price": 5200.0,
                    "cabin_class": cabin_class,
                    "baggage": "25kg check-in, meal included",
                },
            ]

        results = []
        for item in matched:
            unit_price = item["base_price"]
            total_price = unit_price * travelers
            results.append(
                FlightOption(
                    id=item["id"],
                    airline=item["airline"],
                    flight_number=item["flight_number"],
                    origin=item["origin"],
                    destination=item["destination"],
                    departure_time=item["departure_time"],
                    arrival_time=item["arrival_time"],
                    duration=item["duration"],
                    stops=item["stops"],
                    cabin_class=item["cabin_class"],
                    baggage=item["baggage"],
                    price=PriceMetadata(
                        amount=total_price,
                        currency="INR",
                        source="mock_flight_provider",
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        is_live=False,
                        price_type="mock",
                    ),
                )
            )
        return results


class AmadeusFlightProvider(FlightProvider):
    def __init__(self) -> None:
        self.client_id = os.getenv("AMADEUS_CLIENT_ID", "")
        self.client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "")
        self.token: str | None = None
        self.token_expiry: float = 0.0

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _authenticate(self) -> str | None:
        if not self.is_configured():
            return None
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, data=data)
                if res.status_code == 200:
                    payload = res.json()
                    self.token = payload.get("access_token")
                    return self.token
        except Exception:
            return None
        return None

    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: str | None = None,
        travelers: int = 1,
        cabin_class: str = "Economy",
    ) -> list[FlightOption]:
        if not self.is_configured():
            return []
        token = await self._authenticate()
        if not token:
            return []

        # Amadeus uses IATA codes (e.g. MAA, HYD)
        city_iata_map = {
            "chennai": "MAA",
            "hyderabad": "HYD",
            "delhi": "DEL",
            "mumbai": "BOM",
            "bangalore": "BLR",
            "goa": "GOI",
            "paris": "CDG",
            "dubai": "DXB",
        }
        orig_code = city_iata_map.get(origin.lower(), origin.upper()[:3])
        dest_code = city_iata_map.get(destination.lower(), destination.upper()[:3])
        travel_date = date or "2026-09-01"

        url = f"https://test.api.amadeus.com/v2/shopping/flight-offers?originLocationCode={orig_code}&destinationLocationCode={dest_code}&departureDate={travel_date}&adults={travelers}&max=5"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    options = []
                    for idx, offer in enumerate(data):
                        price_eur = float(offer.get("price", {}).get("total", 0))
                        price_inr = round(price_eur * 90.0, 2)  # approximate conversion
                        itineraries = offer.get("itineraries", [{}])[0]
                        segments = itineraries.get("segments", [{}])
                        carrier = segments[0].get("carrierCode", "Carrier")
                        flight_num = f"{carrier}-{segments[0].get('number', '101')}"
                        dep_time = segments[0].get("departure", {}).get("at", "08:00")[11:16]
                        arr_time = segments[-1].get("arrival", {}).get("at", "10:00")[11:16]
                        duration = itineraries.get("duration", "PT2H").replace("PT", "").lower()

                        options.append(
                            FlightOption(
                                id=f"amadeus-{offer.get('id', idx)}",
                                airline=carrier,
                                flight_number=flight_num,
                                origin=origin.title(),
                                destination=destination.title(),
                                departure_time=dep_time,
                                arrival_time=arr_time,
                                duration=duration,
                                stops=len(segments) - 1,
                                cabin_class=cabin_class,
                                baggage="Included per airline rules",
                                price=PriceMetadata(
                                    amount=price_inr,
                                    currency="INR",
                                    source="amadeus_live_api",
                                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                                    is_live=True,
                                    price_type="live",
                                ),
                            )
                        )
                    if options:
                        return options
        except Exception:
            pass
        return []


class FlightProviderAggregator(FlightProvider):
    def __init__(self) -> None:
        self.live_provider = AmadeusFlightProvider()
        self.mock_provider = MockFlightProvider()

    async def search_flights(
        self,
        origin: str,
        destination: str,
        date: str | None = None,
        travelers: int = 1,
        cabin_class: str = "Economy",
    ) -> list[FlightOption]:
        if self.live_provider.is_configured():
            try:
                live_results = await self.live_provider.search_flights(
                    origin, destination, date, travelers, cabin_class
                )
                if live_results:
                    return live_results
            except Exception:
                pass
        return await self.mock_provider.search_flights(
            origin, destination, date, travelers, cabin_class
        )
