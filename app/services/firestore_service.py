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
from datetime import datetime, timedelta, timezone
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
        return datetime.now(timezone.utc)

    def is_session_valid(self, session_id: str) -> tuple[bool, str]:
        """
        Check if a session exists and is not expired.
        
        Returns:
            tuple[bool, str]: (is_valid, reason_if_invalid)
        """
        try:
            session_doc = self.db.collection("sessions").document(session_id).get()
            
            if not session_doc.exists:
                return False, "Session does not exist"
            
            session_data = session_doc.to_dict()
            expires_at = session_data.get("expiresAt")
            
            if not expires_at:
                return False, "Session has no expiration date"
            
            if expires_at < self._now():
                return False, "Session has expired"
            
            return True, "Session is valid"
            
        except Exception as e:
            return False, f"Error checking session: {str(e)}"

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

    def create_user_profile(self, uid: str, profile_data: Dict[str, Any]):
        """Create a new user profile with Google Sign-In data"""
        ref = self.db.collection("users").document(uid)
        profile_data["createdAt"] = firestore.SERVER_TIMESTAMP
        profile_data["lastActiveAt"] = firestore.SERVER_TIMESTAMP
        ref.set(profile_data)

    def update_user_profile(self, uid: str, profile_data: Dict[str, Any]):
        """Update existing user profile"""
        ref = self.db.collection("users").document(uid)
        profile_data["lastActiveAt"] = firestore.SERVER_TIMESTAMP
        ref.set(profile_data, merge=True)

    def get_user_profile(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get user profile (alias for get_user for consistency)"""
        return self.get_user(uid)

    def _get_server_timestamp(self):
        """Get Firestore server timestamp"""
        return firestore.SERVER_TIMESTAMP

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

    def touch_session(self, session_id: str, extend_expiry: bool = True):
        """
        Update session's lastSeen timestamp and optionally extend expiry.
        
        Args:
            session_id: The session ID to touch
            extend_expiry: Whether to extend the session expiry by 4 hours
        """
        is_valid, reason = self.is_session_valid(session_id)
        if not is_valid:
            raise ValueError(f"Cannot touch session: {reason}")
        
        update_data = {"lastSeen": firestore.SERVER_TIMESTAMP}
        
        if extend_expiry:
            new_expiry = self._now() + timedelta(hours=4)
            update_data["expiresAt"] = new_expiry
        
        self.db.collection("sessions").document(session_id).update(update_data)

    # -------------------------
    # Itinerary Helpers
    # -------------------------
    def save_itinerary_for_user(self, uid: str, itinerary: Dict[str, Any]) -> str:
        itin_id = self._new_id("it")
        
        itinerary_to_save = itinerary.copy()
        itinerary_to_save["itineraryId"] = itin_id
        itinerary_to_save["createdAt"] = firestore.SERVER_TIMESTAMP
        itinerary_to_save["updatedAt"] = firestore.SERVER_TIMESTAMP
        
        ref = self.db.collection("users").document(uid).collection("itineraries").document(itin_id)
        ref.set(itinerary_to_save)
        return itin_id

    def list_itineraries_for_user(self, uid: str, limit: int = 20) -> List[Dict[str, Any]]:
        col = self.db.collection("users").document(uid).collection("itineraries")
        snaps = col.order_by("updatedAt", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [s.to_dict() for s in snaps]

    def save_itinerary_for_session(self, session_id: str, itinerary: Dict[str, Any]) -> str:
        itin_id = self._new_id("it")
        
        itinerary_to_save = itinerary.copy()
        itinerary_to_save["itineraryId"] = itin_id
        itinerary_to_save["createdAt"] = firestore.SERVER_TIMESTAMP
        itinerary_to_save["updatedAt"] = firestore.SERVER_TIMESTAMP

        # Check if session exists and is not expired before saving itinerary
        is_valid, reason = self.is_session_valid(session_id)
        if not is_valid:
            raise ValueError(f"Cannot save itinerary: {reason}")
        
        ref = self.db.collection("sessions").document(session_id).collection("itineraries").document(itin_id)
        ref.set(itinerary_to_save)
        return itin_id

    def list_itineraries_for_session(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        col = self.db.collection("sessions").document(session_id).collection("itineraries")
        snaps = col.limit(limit).stream()
        return [s.to_dict() for s in snaps if s.to_dict()]
    
    def replace_itinerary_for_user(self, uid: str, itinerary_id: str, itinerary_data: Dict[str, Any]) -> str:
        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("itineraries")
            .document(itinerary_id)
        )
        snapshot = doc_ref.get()
        created_at = snapshot.to_dict().get("createdAt") if snapshot.exists else firestore.SERVER_TIMESTAMP

        doc_ref.set(
            {
                **itinerary_data,
                "itineraryId": itinerary_id,
                "createdAt": created_at,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )
        return itinerary_id


    def replace_itinerary_for_session(self, session_id: str, itinerary_id: str, itinerary_data: Dict[str, Any]) -> str:
        doc_ref = (
            self.db.collection("sessions")
            .document(session_id)
            .collection("itineraries")
            .document(itinerary_id)
        )
        snapshot = doc_ref.get()
        created_at = snapshot.to_dict().get("createdAt") if snapshot.exists else firestore.SERVER_TIMESTAMP

        doc_ref.set(
            {
                **itinerary_data,
                "itineraryId": itinerary_id,
                "createdAt": created_at,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )
        return itinerary_id


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
