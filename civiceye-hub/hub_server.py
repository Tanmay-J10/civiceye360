from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CivicEye Central Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

@app.get("/")
def serve_dashboard():
    return FileResponse(BASE_DIR / "civiceye_dashboard.html")

@app.get("/api/health")
def health_check():
    return {"status": "online", "role": "central-hub"}