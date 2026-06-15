from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .router import router

app = FastAPI(title="Final Beuro AI Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Serve static assets
static_dir = Path(__file__).parent.parent / "frontend" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve the main HTML UI
@app.get("/")
async def serve_ui():
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return FileResponse(str(html_path))
