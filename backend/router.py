# router.py – FastAPI routes for the Bureaucracy Autopilot

"""All API endpoints for the final beuro AI agent.

Endpoints:
- GET  /health                     – returns currently active LLM provider
- POST /chat   (json)               – processes a user message, returns reply and updated data
- GET  /links?topic=...            – fetches official .gov.in links for the given topic
- GET  /download?topic=...&session= – returns a filled PDF for the session
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List

from .llm_client import ask_llm, active_provider
from .link_fetcher import get_official_links
from .form_downloader import get_official_form
from .storage import load_session, save_session
from .workflow_engine import process_user_message

router = APIRouter()

@router.get("/health")
async def health() -> Dict[str, str]:
    provider = await active_provider()
    return {"active_provider": provider}

@router.post("/chat")
async def chat_endpoint(payload: Dict):
    topic      = payload.get("topic")
    message    = payload.get("message")
    session_id = payload.get("session_id")
    language   = payload.get("language", "en")
    # Runtime API keys (user-supplied via UI — never stored on disk)
    gemini_key = payload.get("gemini_key", "").strip()
    groq_key   = payload.get("groq_key",   "").strip()

    if not all([topic, message, session_id]):
        raise HTTPException(status_code=400, detail="Missing required fields: topic, message, session_id")

    current_data = load_session(session_id)
    reply, updated_data, steps = await process_user_message(
        topic, message, current_data,
        language=language,
        gemini_key=gemini_key,
        groq_key=groq_key,
    )
    save_session(session_id, updated_data)
    return {"reply": reply, "updated_data": updated_data, "steps": steps}

@router.get("/links")
async def links_endpoint(topic: str = Query(...)) -> List[Dict[str, str]]:
    return get_official_links(topic)

@router.get("/download")
async def download_endpoint(topic: str = Query(...), session: str = Query(...)):
    user_data = load_session(session)
    if not user_data:
        raise HTTPException(status_code=404, detail="No data for session")
    try:
        pdf_bytes = get_official_form(topic, user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # Return raw PDF bytes – FastAPI will auto‑detect binary response
    return pdf_bytes
