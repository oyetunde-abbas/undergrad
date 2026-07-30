from fastapi import FastAPI
from routes.jobs import router as jobs_router

app = FastAPI(
    title="Undergrad API",
    version="1.0"
)

app.include_router(
    jobs_router,
    prefix="/jobs",
    tags=["Jobs"]
)


@app.get("/")
def home():
    return {
        "message": "Undergrad API running"
    }