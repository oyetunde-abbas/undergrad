from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routes.jobs import router as jobs_router
from routes.saved import router as saved_router
from routes.applications import router as applications_router
from routes.profile import router as profile_router
from routes.auth import router as auth_router

app = FastAPI(
    title="Undergrad API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    jobs_router,
    prefix="/jobs",
    tags=["Jobs"]
)

app.include_router(
    saved_router,
    prefix="/saved",
    tags=["Saved"]
)

app.include_router(
    applications_router,
    prefix="/applications",
    tags=["Applications"]
)

app.include_router(
    profile_router,
    prefix="/profile",
    tags=["Profile"]
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"]
)


@app.get("/")
def home():
    return {
        "message": "Undergrad API running"
    }