import { apiClient } from './client';
import type { Span, SpansResponse, SpansQueryParams } from './types';

export const spansApi = {
  // List spans for a trace
  listSpans: async (traceId: string, params?: SpansQueryParams): Promise<SpansResponse> => {
    const response = await apiClient.get<SpansResponse>(`/traces/${traceId}/spans`, { params });
    return response.data;
  },

  // Get single span
  getSpan: async (spanId: string): Promise<Span> => {
    const response = await apiClient.get<Span>(`/spans/${spanId}`);
    return response.data;
  },
};
