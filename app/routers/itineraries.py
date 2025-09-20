from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional
from app.dependencies import get_firestore_client, verify_id_token, verify_id_token_dependency, optional_verify_id_token_dependency, get_current_uid
from app.services.firestore_service import FirestoreService
from app.models.itinerary import Itinerary, SaveItineraryRequest, SaveItineraryResponse, ListItinerariesResponse

router = APIRouter(tags=["itineraries"])

db = get_firestore_client()
fs = FirestoreService(db)


@router.post("/saveItinerary", response_model=SaveItineraryResponse)
def save_itinerary(
    body: SaveItineraryRequest,
    decoded_token=Depends(verify_id_token_dependency)
):
    uid = get_current_uid(decoded_token)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid UID in token")

    migration_result = None
    if body.sessionId:
        migration_result = fs.migrate_session_to_user(body.sessionId, uid)

    itinerary_id = fs.save_itinerary_for_user(uid, body.itinerary.dict())

    return SaveItineraryResponse(
        ok=True,
        itineraryId=itinerary_id,
        migrated=migration_result
    )


@router.get("/itineraries", response_model=ListItinerariesResponse)
def list_itineraries(
    sessionId: Optional[str] = Query(None),
    decoded_token: Optional[str] = Depends(optional_verify_id_token_dependency)
):
    """
    List itineraries for either:
    - Guest session (if sessionId query param provided, no auth needed)
    - Authenticated user (requires Authorization header)
    """
    # Guest mode → no auth required
    if sessionId:
        return ListItinerariesResponse(ok=True, itineraries=fs.list_itineraries_for_session(sessionId))
    
    # Authenticated mode
    if not decoded_token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    uid = decoded_token.get("uid")
    return ListItinerariesResponse(ok=True, itineraries=fs.list_itineraries_for_user(uid))

@router.put("/itinerary/{itineraryId}", response_model=SaveItineraryResponse)
def update_itinerary(
    itineraryId: str,
    itinerary: Itinerary,
    sessionId: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """
    Replace an existing itinerary with a new version.
    - Guest mode: requires sessionId, no auth
    - User mode: requires Authorization header
    """
    if sessionId:
        updated_id = fs.replace_itinerary_for_session(sessionId, itineraryId, itinerary.model_dump())
        return SaveItineraryResponse(ok=True, itineraryId=updated_id)

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ")[1] if " " in authorization else authorization
    decoded_token = verify_id_token(token)
    uid = get_current_uid(decoded_token)

    if not uid:
        raise HTTPException(status_code=401, detail="Invalid UID in token")

    updated_id = fs.replace_itinerary_for_user(uid, itineraryId, itinerary.model_dump())
    return SaveItineraryResponse(ok=True, itineraryId=updated_id)