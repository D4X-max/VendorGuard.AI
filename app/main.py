from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging

# Old v1 routers (assessments, findings — not yet migrated to clean arch)
from app.api.v1 import assessments, findings

# New clean architecture routers
from app.api.routers import auth, vendors, evidence, risk







# ─────────────────────────────────────────────
# Lifespan — runs on startup/shutdown
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


# ─────────────────────────────────────────────
# App Initialization
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise Vendor Risk Management Platform with AI-powered assessment engine.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# CORS Middleware
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Global Exception Handler
# ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ─────────────────────────────────────────────
# API Routers
# ─────────────────────────────────────────────
API_PREFIX = "/api/v1"

# Clean architecture routers (Phase 4 spec)
app.include_router(auth.router,        prefix=API_PREFIX)
app.include_router(vendors.router,     prefix=API_PREFIX)
app.include_router(evidence.router, prefix=API_PREFIX)
# Legacy v1 routers — to be migrated to service layer in later phases
app.include_router(assessments.router, prefix=API_PREFIX)
app.include_router(findings.router,    prefix=API_PREFIX)
app.include_router(risk.router, prefix=API_PREFIX)



# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["System"])
async def root():
    return {"message": f"Welcome to {settings.APP_NAME} API. Docs at /api/docs"}