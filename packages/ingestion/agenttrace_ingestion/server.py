"""FastAPI server for OTLP trace ingestion."""

from fastapi import FastAPI

app = FastAPI(
    title="AgentTrace Ingestion",
    description="OTLP trace ingestion service for multi-agent LLM systems",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "agenttrace-ingestion"}


@app.post("/v1/traces")
async def receive_traces():
    """
    OTLP HTTP endpoint for trace ingestion.

    Accepts: application/x-protobuf or application/json
    """
    # Stub implementation - will be implemented in Phase 1
    return {"status": "ok", "message": "Trace ingestion endpoint (stub)"}
