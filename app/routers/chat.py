from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/chat")
async def chat(request: Request):
    """
    Mock chatbot: echoes user query with canned response.
    """
    body = await request.json()
    query = body.get("query", "")
    return {
        "status": "ok",
        "query": query,
        "response": f"This is a mock response to '{query}'. Real LLM coming soon!"
    }
