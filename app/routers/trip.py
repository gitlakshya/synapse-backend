from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.firestore_service import FirestoreService
from app.dependencies import get_firestore_client, verify_id_token_dependency
import uuid
from datetime import datetime, timezone

router = APIRouter(tags=["trip"])
db = get_firestore_client()
fs = FirestoreService(db)

class PlanTripRequest(BaseModel):
    sessionId: Optional[str] = None
    destination: str
    days: Optional[int] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    budget: float
    preferences: Optional[dict] = {}

def getFirestoreService():
    return FirestoreService(get_firestore_client())

@router.post("/plantrip")
async def plan_trip(
    body: PlanTripRequest,
    fs: FirestoreService = Depends(getFirestoreService),
    decoded: Optional[str] = Depends(verify_id_token_dependency)
):
    """
    Mock itinerary generator: returns a dummy itinerary and saves to Firestore.
    Requires either authentication token OR session ID.
    """
    # Validate that either auth token or session ID is present
    if not decoded and not body.sessionId:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required: provide either auth token or sessionId"
        )
    
    uid = decoded["uid"] if decoded else None
    session_id = body.sessionId

    itinerary = {
        "itineraryId": f"it_{uuid.uuid4().hex[:8]}",
        "title": f"Trip to {body.destination}",
        "input": body.model_dump(),
        "days": body.days,
        "budget": body.budget,
        "plan": [
            {"day": i+1, "activities": [f"Activity {i+1} in {body.destination}"]}
            for i in range(body.days if body.days is not None else 1)
        ],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    
    response_itinerary = itinerary.copy()
    
    if uid:
        itin_id = fs.save_itinerary_for_user(uid, itinerary)
    else:
        itin_id = fs.save_itinerary_for_session(session_id, itinerary)

    return {"status": "ok", "itineraryId": itin_id, "itinerary": response_itinerary}

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
