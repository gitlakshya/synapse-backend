import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import trip, chat, itineraries, booking, session
from app.config import settings, cloud_config

# Initialize FastAPI app
app = FastAPI(
    title="AI Trip Planner API", 
    version="0.01",
    description="AI-powered trip planning and itinerary management API"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if not cloud_config.IS_CLOUD_RUN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trip.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(itineraries.router, prefix="/api/v1")
app.include_router(booking.router, prefix="/api/v1", tags=["booking"])
app.include_router(session.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run and monitoring"""
    return {
        "status": "ok", 
        "message": "AI Trip Planner API is running",
        "environment": "cloud-run" if cloud_config.IS_CLOUD_RUN else "local",
        "project_id": cloud_config.PROJECT_ID if cloud_config.IS_CLOUD_RUN else "local"
    }

@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": "AI Trip Planner API",
        "version": "0.01",
        "docs_url": "/docs",
        "health_url": "/health"
    }

# For Cloud Run, the port is set via environment variable
if __name__ == "__main__":
    import uvicorn
    port = cloud_config.PORT if cloud_config.IS_CLOUD_RUN else 8080
    uvicorn.run(app, host="0.0.0.0", port=port)
