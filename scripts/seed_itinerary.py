import os, sys
from datetime import timezone, datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.dependencies import get_firestore_client

db = get_firestore_client()

def seed_itinerary(uid: str):
    itinerary = {
        "title": "Goa Long Weekend",
        "input": {
            "destination": {"placeId": "ChIJxx", "name": "Goa", "country": "IN"},
            "startDate": "2025-10-01",
            "endDate": "2025-10-04",
            "numDays": 3,
            "budget": 20000,
            "sliders": {"nightlife": 0.7, "nature": 0.6}
        },
        "days": [
            {
                "dayIndex": 0,
                "activities": [
                    {
                        "poiId": "poi123",
                        "title": "Beach Walk",
                        "durationMins": 120,
                        "category": "nature",
                        "dayIndex": 0,
                        "poiSnapshot": {
                            "name": "Calangute Beach",
                            "lat": 15.543,
                            "lng": 73.762,
                            "imageUrl": "gs://your-bucket/poi123.jpg"
                        }
                    }
                ]
            }
        ],
        "estimatedCost": 18000,
        "meta": {"generatedByLLM": True},
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }

    ref = db.collection("sessions").document(uid).collection("itineraries").document()
    itinerary["itineraryId"] = ref.id
    ref.set(itinerary)
    print(f"Seeded itinerary {ref.id} for user {uid}")

if __name__ == "__main__":
    seed_itinerary("sess_demo")
