import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from rate_limit import limiter

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from routes.jobs import router as jobs_router
from routes.saved import router as saved_router
from routes.applications import router as applications_router
from routes.profile import router as profile_router
from routes.auth import router as auth_router
from routes.submit import router as submit_router
from routes.feedback import router as feedback_router
from routes.track import router as track_router
from routes.tailor import router as tailor_router
from routes.draft import router as draft_router
from routes.admin import router as admin_router
from db import log_error
from notify import send_error_alert_email

logger = logging.getLogger("main")

app = FastAPI(
    title="Undergrad API",
    version="1.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,  # required for the browser to send/receive the httpOnly auth cookie
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Standard security headers — cheap to add, block a handful of common
    attack classes (clickjacking, MIME-sniffing, referrer leakage). HSTS is
    only meaningful once this is actually served over HTTPS in production,
    but it's harmless to send now — a real deployment behind SSL will
    benefit from it immediately with no further change needed here.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches ANY exception that isn't already handled by a route (i.e. isn't
    a deliberate HTTPException) — so a bug anywhere in the app gets logged
    with full context automatically, instead of only surfacing if someone
    happened to wrap that specific code in a try/except.
    """
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{tb}")

    try:
        log_error(
            source="backend",
            message=str(exc) or exc.__class__.__name__,
            detail=tb,
            path=str(request.url.path),
        )
    except Exception:
        pass  # logging the error should never itself crash the error handler

    # Alert email runs AFTER the response is sent (via BackgroundTask), same
    # reasoning as the feedback notification fix — a slow/broken SMTP
    # connection should never make an already-broken request take even
    # longer to fail.
    error_path, error_msg = str(request.url.path), str(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our end. It's been logged."},
        background=BackgroundTask(send_error_alert_email, error_path, error_msg, tb),
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

app.include_router(
    submit_router,
    prefix="/submit",
    tags=["Submit"]
)

app.include_router(
    feedback_router,
    prefix="/feedback",
    tags=["Feedback"]
)

app.include_router(
    track_router,
    prefix="/track",
    tags=["Tracking"]
)

app.include_router(
    tailor_router,
    prefix="/jobs",
    tags=["Resume Tailoring"]
)

app.include_router(
    draft_router,
    prefix="/jobs",
    tags=["Resume Tailoring"]
)

app.include_router(
    admin_router,
    prefix="/admin",
    tags=["Admin"]
)




@app.get("/")
def home():
    return {
        "message": "Undergrad API running"
    }