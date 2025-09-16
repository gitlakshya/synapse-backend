import os, sys, datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.dependencies import get_firestore_client
db = get_firestore_client()

db.collection("sessions").add({
    "expiresAt": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=30)  # for test
})

