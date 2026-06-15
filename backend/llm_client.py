# llm_client.py – Smart multi-model rotation with 429 fallback
import os
import json
import time
import warnings
from pathlib import Path
from typing import Optional, List, Tuple

import httpx

warnings.filterwarnings("ignore")

# ─── Load .env automatically ─────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "").strip()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── Model priority list (best → fallback) ───────────────────
# Models ordered by quality. Skipped automatically on 429.
GEMINI_MODELS: List[str] = [
    "gemini-2.5-flash",       # Best, 5 RPM available
    "gemini-3.5-flash",       # Fallback, 1 RPM
    "gemini-2.5-flash-lite",  # Last resort, 1 RPM
]

# Track per-model cooldown (unix timestamp when it's usable again)
_model_cooldown: dict = {}
COOLDOWN_SECONDS = 65  # 1 minute cooldown after a 429


def _gemini_url(model: str, key: str) -> str:
    return (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )


def _pick_gemini_model() -> Optional[str]:
    """Return the first model not in cooldown."""
    now = time.time()
    for m in GEMINI_MODELS:
        if _model_cooldown.get(m, 0) < now:
            return m
    return None  # All in cooldown


async def _call_gemini_model(model: str, prompt: str, system: str = "", key: str = "") -> Tuple[Optional[str], int]:
    """Returns (response_text_or_None, http_status_code)."""
    active_key = key or GEMINI_API_KEY
    if not active_key:
        return None, 0
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1500,
            "responseMimeType": "text/plain",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_gemini_url(model, active_key), json=payload)
            if resp.status_code == 200:
                text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                return text, 200
            elif resp.status_code == 429:
                print(f"[LLM] {model} → 429 rate limited, cooling down for {COOLDOWN_SECONDS}s")
                _model_cooldown[model] = time.time() + COOLDOWN_SECONDS
                return None, 429
            else:
                print(f"[LLM] {model} → {resp.status_code}: {resp.text[:200]}")
                return None, resp.status_code
    except Exception as e:
        print(f"[LLM] {model} → exception: {e}")
        return None, 0


async def _call_groq(prompt: str, system: str = "", key: str = "") -> Optional[str]:
    active_key = key or GROQ_API_KEY
    if not active_key:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {active_key}"},
                json={"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.3},
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM] Groq exception: {e}")
    return None


# ─── Main public function ────────────────────────────────────
async def ask_llm(prompt: str, system: str = "", gemini_key: str = "", groq_key: str = "") -> str:
    """Try all Gemini models in priority order, then Groq, then graceful stub.
    Accepts optional runtime keys that override the .env values.
    """
    if gemini_key or GEMINI_API_KEY:
        for model in GEMINI_MODELS:
            now = time.time()
            if _model_cooldown.get(model, 0) > now:
                remaining = int(_model_cooldown[model] - now)
                print(f"[LLM] Skipping {model} — {remaining}s cooldown remaining")
                continue
            result, status = await _call_gemini_model(model, prompt, system, key=gemini_key)
            if result:
                print(f"[LLM] ✅ Used {model}")
                return result

    # Try Groq
    result = await _call_groq(prompt, system, key=groq_key)
    if result:
        print("[LLM] ✅ Used Groq")
        return result

    # All providers exhausted — valid JSON stub so UI never crashes
    fallback = {
        "reply": (
            "⏳ No AI provider is connected.\n\n"
            "Please click the **⚙️ Settings** button in the top-right corner "
            "and enter your Gemini API key.\n\n"
            "Get a FREE key at: https://aistudio.google.com/app/apikey"
        ),
        "updated_data": {},
    }
    return json.dumps(fallback)


# ─── Health check ────────────────────────────────────────────
async def active_provider() -> str:
    if not GEMINI_API_KEY and not GROQ_API_KEY:
        return "No provider — set GEMINI_API_KEY in .env file"

    statuses = []
    now = time.time()
    for m in GEMINI_MODELS:
        if _model_cooldown.get(m, 0) > now:
            remaining = int(_model_cooldown[m] - now)
            statuses.append(f"{m} (cooling {remaining}s)")
        else:
            statuses.append(f"{m} ✅")

    active = _pick_gemini_model()
    if active:
        return f"Gemini ✅ (active: {active})"
    if GROQ_API_KEY:
        return "Groq ✅ (Gemini rate-limited)"
    return "⏳ Rate limited — retry in 1 min"
