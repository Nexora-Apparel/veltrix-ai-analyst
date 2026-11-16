from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="VELTRIX AI ANALYST API",
    description="Private-use football analysis API.",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse, tags=["operations"])
async def health() -> HealthResponse:
    """Liveness endpoint; does not imply database or provider readiness."""
    return HealthResponse(
        status="ok",
        service="veltrix-ai-analyst-api",
        version=app.version or "unknown",
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": "VELTRIX AI ANALYST API", "docs": "/docs"}
