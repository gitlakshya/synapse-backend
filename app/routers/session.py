from fastapi import APIRouter
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
from app.dependencies import get_firestore_client
from app.services.firestore_service import FirestoreService

load_dotenv()
router = APIRouter(tags=["session"])

db = get_firestore_client()
fs = FirestoreService(db)

SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "4"))

@router.post("/session")
def create_session():
    """
    Create a guest session with TTL (4h).
    Returns sessionId and expiry timestamp.
    """
    session_id = fs.create_session()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    return {
        "sessionId": session_id,
        "expiresAt": expires_at.isoformat()
    }
