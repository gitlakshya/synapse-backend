from fastapi import APIRouter, Depends
from app.dependencies import get_firestore_client, verify_id_token_dependency, get_current_uid
from app.services.firestore_service import FirestoreService

router = APIRouter()
db = get_firestore_client()
fs = FirestoreService(db)

@router.post("/saveItinerary")
def save_itinerary(payload: dict, decoded_token=Depends(verify_id_token_dependency)):
    uid = get_current_uid(decoded_token)
    itinerary_id = fs.save_itinerary_for_user(uid, payload["itinerary"])
    return {"ok": True, "itineraryId": itinerary_id}
