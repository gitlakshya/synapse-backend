from app.dependencies import get_firestore_client
db = get_firestore_client()
print("collections:", [c.id for c in db.collections()])
