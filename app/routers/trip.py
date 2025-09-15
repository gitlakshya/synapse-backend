from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.firestore_service import FirestoreService
from app.dependencies import get_firestore_service, verify_id_token_optional
import uuid
from datetime import datetime

router = APIRouter()

class PlanTripRequest(BaseModel):
    sessionId: Optional[str] = None
    destination: str
    days: int
    budget: float
    preferences: Optional[dict] = {}

@router.post("/planTrip")
async def plan_trip(
    body: PlanTripRequest,
    fs: FirestoreService = Depends(get_firestore_service),
    decoded=Depends(verify_id_token_optional)
):
    """
    Mock itinerary generator: returns a dummy itinerary and saves to Firestore.
    """
    uid = decoded["uid"] if decoded else None
    session_id = body.sessionId or fs.create_session()

    itinerary = {
        "itineraryId": f"it_{uuid.uuid4().hex[:8]}",
        "title": f"Trip to {body.destination}",
        "input": body.dict(),
        "days": body.days,
        "budget": body.budget,
        "plan": [
            {"day": i+1, "activities": [f"Activity {i+1} in {body.destination}"]}
            for i in range(body.days)
        ],
        "createdAt": datetime.utcnow().isoformat(),
    }

    if uid:
        itin_id = fs.save_itinerary_for_user(uid, itinerary)
    else:
        itin_id = fs.save_itinerary_for_session(session_id, itinerary)

    return {"status": "ok", "itineraryId": itin_id, "itinerary": itinerary}

@router.post("/adjustItinerary")
async def adjust_itinerary(request: Request):
    """
    Mock adjust itinerary - returns modified mock plan.
    """
    body = await request.json()
    itinerary = body.get("itinerary", {})
    # Pretend to adjust plan based on preferences
    itinerary["adjusted"] = True
    return {"status": "ok", "adjustedItinerary": itinerary}
