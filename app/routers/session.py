from fastapi import APIRouter, Depends
from app.services.firestore_service import FirestoreService
from app.dependencies import get_firestore_service
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/session")
async def create_session(fs: FirestoreService = Depends(get_firestore_service)):
    """
    Create a guest session, valid for 4 hours.
    """
    sid = fs.create_session()
    expires_at = (datetime.utcnow() + timedelta(hours=4)).isoformat()
    return {"sessionId": sid, "expiresAt": expires_at}
