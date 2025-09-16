from pydantic import BaseModel
from typing import Optional, Dict, Any, List


# ---------------------------
# Core Models
# ---------------------------

class ItineraryInput(BaseModel):
    destination: Dict[str, Any]  
    startDate: Optional[str] = None   
    endDate: Optional[str] = None     
    numDays: Optional[int] = None     
    budget: Optional[float] = None
    sliders: Optional[Dict[str, float]] = {}  # flexible weights, e.g. {"nightlife": 0.7, "nature": 0.5}


class Activity(BaseModel):
    poiId: str
    title: str
    durationMins: Optional[int] = None
    category: Optional[str] = None
    dayIndex: Optional[int] = None                
    poiSnapshot: Optional[Dict[str, Any]] = None  # minimal optional info {name, lat?, lng?, imageUrl?}


class DayPlan(BaseModel):
    dayIndex: Optional[int] = None
    activities: List[Activity] = []


class Itinerary(BaseModel):
    title: str
    input: ItineraryInput
    days: List[DayPlan] = []
    estimatedCost: Optional[float] = None
    meta: Optional[Dict[str, Any]] = {}  # flexible: {"generatedByLLM": True, "sourcePrompt": "..."}


# ---------------------------
# Request/Response Models
# ---------------------------

class SaveItineraryRequest(BaseModel):
    sessionId: Optional[str] = None
    itinerary: Itinerary


class SaveItineraryResponse(BaseModel):
    ok: bool = True
    itineraryId: str
    migrated: Optional[Dict[str, Any]] = None


class ItineraryResponse(Itinerary):
    itineraryId: str
    createdAt: Optional[Any] = None
    updatedAt: Optional[Any] = None


class ListItinerariesResponse(BaseModel):
    ok: bool = True
    itineraries: List[ItineraryResponse]
