import { apiClient } from './client';
import type {
  Trace,
  TraceDetail,
  TracesResponse,
  TracesQueryParams,
  TraceQueryParams,
  AgentGraph,
  FailuresResponse,
  TraceMetrics,
  ClassifyResponse,
} from './types';

export const tracesApi = {
  // List traces with optional filters
  listTraces: async (params?: TracesQueryParams): Promise<TracesResponse> => {
    const response = await apiClient.get<TracesResponse>('/traces', { params });
    return response.data;
  },

  // Get single trace
  getTrace: async (traceId: string, params?: TraceQueryParams): Promise<TraceDetail> => {
    const response = await apiClient.get<TraceDetail>(`/traces/${traceId}`, { params });
    return response.data;
  },

  // Get agent communication graph
  getGraph: async (traceId: string): Promise<AgentGraph> => {
    const response = await apiClient.get<AgentGraph>(`/traces/${traceId}/graph`);
    return response.data;
  },

  // Get failure annotations
  getFailures: async (traceId: string): Promise<FailuresResponse> => {
    const response = await apiClient.get<FailuresResponse>(`/traces/${traceId}/failures`);
    return response.data;
  },

  // Get metrics
  getMetrics: async (traceId: string): Promise<TraceMetrics> => {
    const response = await apiClient.get<TraceMetrics>(`/traces/${traceId}/metrics`);
    return response.data;
  },

  // Trigger failure classification
  classify: async (traceId: string): Promise<ClassifyResponse> => {
    const response = await apiClient.post<ClassifyResponse>(`/traces/${traceId}/classify`);
    return response.data;
  },
};
