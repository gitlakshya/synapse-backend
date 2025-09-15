"""
Firestore Service Layer for AI Trip Planner MVP.

This service wraps all read/write operations for:
- Users & itineraries
- Guest sessions & itineraries
- POIs & Places
- Logs (search, LLM responses)

Assumptions (per MVP):
- Only the latest itinerary version is stored (no versions subcollection).
- Session TTL = 4 hours (handled via expiresAt + Firestore TTL policy).
- POI IDs = Google place_id.
- Images stored in a public Cloud Storage bucket (URLs referenced here).
- Server-only writes for search_logs & llm_responses (via Admin SDK).
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from firebase_admin import firestore


class FirestoreService:
    def __init__(self, db: firestore.Client):
        self.db = db

    # -------------------------
    # Utility
    # -------------------------
    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def _now(self):
        return datetime.utcnow()

    # -------------------------
    # User Helpers
    # -------------------------
    def create_user(self, uid: str, display_name: str, email: str, preferences: Optional[Dict[str, Any]] = None):
        ref = self.db.collection("users").document(uid)
        ref.set({
            "uid": uid,
            "displayName": display_name,
            "email": email,
            "preferences": preferences or {},
            "createdAt": firestore.SERVER_TIMESTAMP,
            "lastActiveAt": firestore.SERVER_TIMESTAMP,
        })

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("users").document(uid).get()
        return snap.to_dict() if snap.exists else None

    def update_user_preferences(self, uid: str, preferences: Dict[str, Any]):
        ref = self.db.collection("users").document(uid)
        ref.set({"preferences": preferences, "lastActiveAt": firestore.SERVER_TIMESTAMP}, merge=True)

    # -------------------------
    # Session Helpers
    # -------------------------
    def create_session(self, geo_hint: Optional[str] = None, preferences: Optional[Dict[str, Any]] = None) -> str:
        sid = self._new_id("sess")
        expires_at = self._now() + timedelta(hours=4)
        self.db.collection("sessions").document(sid).set({
            "sessionId": sid,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "lastSeen": firestore.SERVER_TIMESTAMP,
            "expiresAt": expires_at,
            "geoHint": geo_hint,
            "preferences": preferences or {},
            "migratedTo": None,
        })
        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("sessions").document(session_id).get()
        return snap.to_dict() if snap.exists else None

    def touch_session(self, session_id: str):
        self.db.collection("sessions").document(session_id).update({"lastSeen": firestore.SERVER_TIMESTAMP})

    # -------------------------
    # Itinerary Helpers
    # -------------------------
    def save_itinerary_for_user(self, uid: str, itinerary: Dict[str, Any]) -> str:
        itin_id = self._new_id("it")
        itinerary["itineraryId"] = itin_id
        itinerary["createdAt"] = firestore.SERVER_TIMESTAMP
        itinerary["updatedAt"] = firestore.SERVER_TIMESTAMP
        ref = self.db.collection("users").document(uid).collection("itineraries").document(itin_id)
        ref.set(itinerary)
        return itin_id

    def list_itineraries_for_user(self, uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        col = self.db.collection("users").document(uid).collection("itineraries")
        snaps = col.order_by("updatedAt", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [s.to_dict() for s in snaps]

    def save_itinerary_for_session(self, session_id: str, itinerary: Dict[str, Any]) -> str:
        itin_id = self._new_id("it")
        itinerary["itineraryId"] = itin_id
        itinerary["createdAt"] = firestore.SERVER_TIMESTAMP
        itinerary["updatedAt"] = firestore.SERVER_TIMESTAMP
        ref = self.db.collection("sessions").document(session_id).collection("itineraries").document(itin_id)
        ref.set(itinerary)
        return itin_id

    def list_itineraries_for_session(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        col = self.db.collection("sessions").document(session_id).collection("itineraries")
        snaps = col.order_by("updatedAt", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [s.to_dict() for s in snaps]

    # -------------------------
    # Migration: Session → User
    # -------------------------
    def migrate_session_to_user(self, session_id: str, uid: str) -> Dict[str, Any]:
        session_ref = self.db.collection("sessions").document(session_id)
        session_snap = session_ref.get()
        if not session_snap.exists:
            return {"migrated": False, "reason": "session not found"}

        session_data = session_snap.to_dict()
        user_ref = self.db.collection("users").document(uid)
        itineraries = session_ref.collection("itineraries").stream()

        migrated_ids = []
        for itin in itineraries:
            data = itin.to_dict()
            new_id = self._new_id("it")
            data["itineraryId"] = new_id
            data["migratedFromSession"] = session_id
            data["migratedAt"] = firestore.SERVER_TIMESTAMP
            user_ref.collection("itineraries").document(new_id).set(data)
            migrated_ids.append(new_id)

        session_ref.set({"migratedTo": uid, "migratedAt": firestore.SERVER_TIMESTAMP}, merge=True)

        return {"migrated": True, "itineraryCount": len(migrated_ids)}

    # -------------------------
    # POIs & Places
    # -------------------------
    def upsert_poi(self, poi_id: str, data: Dict[str, Any]):
        data["updatedAt"] = firestore.SERVER_TIMESTAMP
        self.db.collection("pois").document(poi_id).set(data, merge=True)

    def get_poi(self, poi_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("pois").document(poi_id).get()
        return snap.to_dict() if snap.exists else None

    def upsert_place(self, place_id: str, data: Dict[str, Any]):
        data["updatedAt"] = firestore.SERVER_TIMESTAMP
        self.db.collection("places").document(place_id).set(data, merge=True)

    def get_place(self, place_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("places").document(place_id).get()
        return snap.to_dict() if snap.exists else None

    # -------------------------
    # Logs (server-only)
    # -------------------------
    def log_search(self, payload: Dict[str, Any]) -> str:
        ref = self.db.collection("search_logs").document()
        payload["logId"] = ref.id
        payload["createdAt"] = firestore.SERVER_TIMESTAMP
        ref.set(payload)
        return ref.id

    def save_llm_response(self, record: Dict[str, Any]) -> str:
        ref = self.db.collection("llm_responses").document()
        record["llmId"] = ref.id
        record["createdAt"] = firestore.SERVER_TIMESTAMP
        ref.set(record)
        return ref.id
