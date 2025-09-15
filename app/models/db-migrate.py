import os
from dotenv import load_dotenv
from google.cloud import firestore
load_dotenv()


"""
seed_firestore_full.py
Seed Firestore with mock data for AI Trip Planner MVP.
Creates collections: users, sessions, places, pois, search_logs, llm_responses
Each includes subcollections where applicable (itineraries).
"""


def seed_places(db):
    places = [
        {"placeId": "place_goa", "name": "Goa", "type": "city", "lat": 15.49, "lng": 73.82, "country": "IN"},
        {"placeId": "place_jaipur", "name": "Jaipur", "type": "city", "lat": 26.91, "lng": 75.78, "country": "IN"},
    ]
    for p in places:
        db.collection("places").document(p["placeId"]).set({**p, "updatedAt": firestore.SERVER_TIMESTAMP})
        print(f"Created place: {p['placeId']}")

# ---------- Seed POIs ----------
def seed_pois(db):
    pois = [
        {
            "poiId": "poi_anjuna",
            "externalPlaceId": "ChIJ_ANJUNA",
            "name": "Anjuna Beach",
            "placeId": "place_goa",
            "lat": 15.58,
            "lng": 73.75,
            "categories": ["beach", "nature"],
            "shortDesc": "Popular beach with sunset views",
            "popularityScore": 0.9,
            "avgDurationMins": 90
        },
        {
            "poiId": "poi_hawa_mahal",
            "externalPlaceId": "ChIJ_HAWA",
            "name": "Hawa Mahal",
            "placeId": "place_jaipur",
            "lat": 26.9239,
            "lng": 75.8267,
            "categories": ["heritage", "landmark"],
            "shortDesc": "Iconic pink-hued palace",
            "popularityScore": 0.88,
            "avgDurationMins": 60
        }
    ]
    for poi in pois:
        db.collection("pois").document(poi["poiId"]).set({**poi, "updatedAt": firestore.SERVER_TIMESTAMP})
        print(f"Created POI: {poi['poiId']}")

# ---------- Seed Users + Itineraries ----------
def seed_users(db):
    uid = "user_demo"
    user_ref = db.collection("users").document(uid)
    user_ref.set({
        "uid": uid,
        "displayName": "Demo User",
        "email": "demo@example.com",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "lastActiveAt": firestore.SERVER_TIMESTAMP,
        "preferences": {
            "currency": "INR",
            "dietary": "vegetarian",
            "slidersDefault": {"nature": 60, "food": 70}
        }
    })
    print(f"Created user: {uid}")

    # Subcollection: itineraries
    itin_ref = user_ref.collection("itineraries").document("it_demo")
    itin_ref.set({
        "itineraryId": "it_demo",
        "title": "Goa 3-day Adventure",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "input": {
            "destination": {"placeId": "place_goa", "name": "Goa", "lat": 15.49, "lng": 73.82},
            "dates": {"start": "2025-11-14", "end": "2025-11-16"},
            "budget": 250,
            "sliders": {"nature": 70, "food": 60, "adventure": 40}
        },
        "days": [
            {
                "day": 1,
                "date": "2025-11-14",
                "activities": [
                    {"title": "Anjuna Beach Walk", "poiId": "poi_anjuna", "category": "nature", "durationMins": 120},
                    {"title": "Dinner at Fisherman’s Wharf", "poiId": "poi_anjuna", "category": "food", "durationMins": 90}
                ]
            }
        ],
        "estimatedCost": {"total": 240, "breakdownByDay": [90, 80, 70]},
        "meta": {"llmResponseId": "llm_001", "createdBy": uid}
    })
    print(f"Created itinerary: users/{uid}/itineraries/it_demo")

# ---------- Seed Guest Session + Itinerary ----------
def seed_sessions(db):
    sess_id = "sess_demo"
    sess_ref = db.collection("sessions").document(sess_id)
    sess_ref.set({
        "sessionId": sess_id,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "lastSeen": firestore.SERVER_TIMESTAMP,
        "geoHint": "IN",
        "preferences": {
            "currency": "INR",
            "dietary": "none",
            "slidersDefault": {"heritage": 80, "food": 50}
        }
    })
    print(f"Created session: {sess_id}")

    # Subcollection: itineraries
    guest_itin_ref = sess_ref.collection("itineraries").document("it_guest")
    guest_itin_ref.set({
        "itineraryId": "it_guest",
        "title": "Jaipur Heritage Weekend",
        "createdAt": firestore.SERVER_TIMESTAMP,
        "input": {
            "destination": {"placeId": "place_jaipur", "name": "Jaipur", "lat": 26.91, "lng": 75.78},
            "dates": {"start": "2025-10-10", "end": "2025-10-11"},
            "budget": 150,
            "sliders": {"heritage": 80, "food": 50}
        },
        "days": [
            {
                "day": 1,
                "date": "2025-10-10",
                "activities": [
                    {"title": "Visit Hawa Mahal", "poiId": "poi_hawa_mahal", "category": "heritage", "durationMins": 60}
                ]
            }
        ],
        "meta": {"llmResponseId": "llm_002"}
    })
    print(f"Created guest itinerary: sessions/{sess_id}/itineraries/it_guest")

# ---------- Seed Search Logs ----------
def seed_search_logs(db):
    log_ref = db.collection("search_logs").document("log_001")
    log_ref.set({
        "logId": "log_001",
        "sessionId": "sess_demo",
        "type": "plan_request",
        "input": {"destination": "Goa", "budget": 250},
        "llmResponseId": "llm_001",
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    print("Created search_log: log_001")

# ---------- Seed LLM Responses ----------
def seed_llm_responses(db):
    llm_ref = db.collection("llm_responses").document("llm_001")
    llm_ref.set({
        "llmId": "llm_001",
        "model": "gemini-2.5",
        "promptHash": "sha256:abc123",
        "inputSummary": "3-day Goa trip with food & nature prefs",
        "outputSummary": "3-day itinerary, 6 activities",
        "outputRef": "gs://bucket/llm/llm_001.json",
        "functionsCalled": [
            {"name": "search_pois", "args": {"types": ["nature", "food"]}}
        ],
        "tokensUsed": 1340,
        "createdAt": firestore.SERVER_TIMESTAMP
    })
    print("Created llm_response: llm_001")

# ---------- Main ----------
def main():
    db = firestore.Client(project='calcium-ratio-472014-r9', database='synapse-stage')
    seed_places(db)
    seed_pois(db)
    seed_users(db)
    seed_sessions(db)
    seed_search_logs(db)
    seed_llm_responses(db)
    print("🔥 Firestore seeding complete.")

if __name__ == "__main__":
    main()
