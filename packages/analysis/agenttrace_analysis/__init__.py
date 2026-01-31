"""AgentTrace Analysis - Agent communication graph analysis and failure classification."""

from .api import router as api_router
from .api import set_db_pool
from .graph import AgentGraph, AgentNode, CommunicationEdge
from .jobs import classify_failed_traces, classify_trace, periodic_classification_job
from .mast import (
    FAILURE_MODES,
    ClassificationResult,
    FailureCategory,
    FailureMode,
    RuleBasedClassifier,
)
from .metrics import TraceMetrics, compute_trace_metrics

__version__ = "0.1.0"

__all__ = [
    # Graph
    "AgentGraph",
    "AgentNode",
    "CommunicationEdge",
    # MAST
    "FailureCategory",
    "FailureMode",
    "FAILURE_MODES",
    "ClassificationResult",
    "RuleBasedClassifier",
    # Metrics
    "TraceMetrics",
    "compute_trace_metrics",
    # API
    "api_router",
    "set_db_pool",
    # Jobs
    "classify_failed_traces",
    "classify_trace",
    "periodic_classification_job",
]
