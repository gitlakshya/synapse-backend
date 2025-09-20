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
    session_id = fs.create_session()
    session_data = fs.get_session(session_id)
    return {
        "sessionId": session_id,
        "expiresAt": session_data["expiresAt"].isoformat()
    }
