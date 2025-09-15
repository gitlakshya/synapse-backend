from fastapi import FastAPI
from app.routers import trip, chat, itineraries, booking, session

app = FastAPI(title="AI Trip Planner API", version="1.0")

# Include routers
app.include_router(trip.router, prefix="/api/v1", tags=["trip"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(itineraries.router, prefix="/api/v1", tags=["itineraries"])
app.include_router(booking.router, prefix="/api/v1", tags=["booking"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "AI Trip Planner API is running"}
