"""FastAPI server for OTLP trace ingestion and analysis."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from agenttrace_core.config import Settings

from .normalizers import get_normalizer
from .otlp import determine_framework, extract_resource_attributes, parse_otlp_request
from .writers import DatabaseWriter

# Import analysis API
try:
    from agenttrace_analysis import api_router, set_db_pool

    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Analysis module not available, API endpoints will not be mounted")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global writer instance
writer: DatabaseWriter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global writer

    # Startup
    settings = Settings()
    logger.info(f"Starting AgentTrace Service on {settings.otlp_http_port}")

    writer = DatabaseWriter(settings.database_url, batch_size=100)
    await writer.connect()
    logger.info("Database connection pool created")

    # Set database pool for analysis API
    if ANALYSIS_AVAILABLE and writer._pool:
        set_db_pool(writer._pool)
        logger.info("Analysis API initialized")

    yield

    # Shutdown
    if writer:
        await writer.flush()
        await writer.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AgentTrace",
    description="Multi-agent LLM debugging and observability platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount analysis API router if available
if ANALYSIS_AVAILABLE:
    app.include_router(api_router)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns service status without checking dependencies.
    """
    return {"status": "ok", "service": "agenttrace-ingestion"}


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Verifies that the service can connect to the database.
    """
    if not writer or not writer._pool:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "error": "Database not connected"},
        )

    try:
        # Try to acquire a connection
        async with writer._pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

        return {"status": "ready", "service": "agenttrace-ingestion"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "error": str(e)},
        )


@app.post("/v1/traces")
async def receive_traces(request: Request):
    """
    OTLP HTTP endpoint for trace ingestion.

    Accepts:
    - application/x-protobuf (OTLP protobuf format)
    - application/json (OTLP JSON format)

    Returns:
        Success response with ingestion status
    """
    if not writer:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Service not ready"},
        )

    content_type = request.headers.get("content-type", "application/json")
    body = await request.body()

    if not body:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Empty request body"},
        )

    try:
        # Parse OTLP request
        export_request = parse_otlp_request(body, content_type)

        spans_processed = 0

        # Process each resource span
        for resource_spans in export_request.resource_spans:
            resource_attrs = extract_resource_attributes(resource_spans.resource)
            framework = determine_framework(resource_attrs)

            logger.debug(f"Processing spans for framework: {framework}")

            # Get framework-specific normalizer
            normalizer = get_normalizer(framework)

            # Process each scope span
            for scope_spans in resource_spans.scope_spans:
                for span in scope_spans.spans:
                    try:
                        # Normalize span
                        normalized = normalizer.normalize(span, resource_attrs)

                        # Write to database
                        await writer.write(normalized)
                        spans_processed += 1

                    except Exception as e:
                        logger.error(f"Failed to process span {span.name}: {e}")
                        # Continue processing other spans
                        continue

        logger.info(f"Successfully processed {spans_processed} spans")

        return {
            "status": "ok",
            "spans_processed": spans_processed,
        }

    except ValueError as e:
        logger.error(f"Failed to parse OTLP request: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Invalid OTLP request: {str(e)}"},
        )
    except Exception as e:
        logger.error(f"Internal error processing traces: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )


@app.post("/v1/traces/grpc")
async def receive_traces_grpc():
    """
    gRPC endpoint for OTLP trace ingestion.

    Note: This is a stub. Full gRPC implementation will use grpcio.
    For now, clients should use the HTTP endpoint.
    """
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"error": "gRPC endpoint not yet implemented. Use HTTP endpoint instead."},
    )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    endpoints = {
        "health": "/health",
        "ready": "/ready",
        "otlp_http": "/v1/traces",
        "otlp_grpc": "/v1/traces/grpc (not implemented)",
    }

    if ANALYSIS_AVAILABLE:
        endpoints.update(
            {
                "list_traces": "/api/traces",
                "trace_details": "/api/traces/{trace_id}",
                "trace_graph": "/api/traces/{trace_id}/graph",
                "trace_failures": "/api/traces/{trace_id}/failures",
                "trace_metrics": "/api/traces/{trace_id}/metrics",
                "classify_trace": "/api/traces/{trace_id}/classify",
                "list_spans": "/api/traces/{trace_id}/spans",
                "span_details": "/api/spans/{span_id}",
            }
        )

    return {
        "service": "AgentTrace",
        "version": "0.1.0",
        "phase": "Phase 2 - Analysis Engine & Graph Construction",
        "endpoints": endpoints,
    }
