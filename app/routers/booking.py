from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/booking/redirect")
async def booking_redirect(request: Request):
    """
    Mock booking redirect - just returns a demo URL.
    """
    params = dict(request.query_params)
    destination = params.get("destination", "Unknown")
    return {
        "status": "ok",
        "redirectUrl": f"https://example-booking-site.com/search?place={destination}"
    }
