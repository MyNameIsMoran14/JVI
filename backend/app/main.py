from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.all_models  # noqa: F401
from app.auth.router import router as auth_router
from app.documents.router import router as documents_router
from app.labs.router import router as labs_router
from app.patient.router import router as patient_router
from app.treatment.router import router as treatment_router
from app.visits.router import router as visits_router

app = FastAPI(title="med-helper API", version="0.1.0")

# JWT bearer auth (no cookies), so a permissive CORS policy carries no CSRF risk — the Mini
# App is served from a tunnel/CDN origin that differs from the API's, by design.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(patient_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(labs_router, prefix="/api/v1")
app.include_router(visits_router, prefix="/api/v1")
app.include_router(treatment_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
