import { useQuery } from '@tanstack/react-query';
import { tracesApi } from '@/api';
import type { TraceQueryParams } from '@/api';

export const useTrace = (traceId: string, params?: TraceQueryParams) => {
  return useQuery({
    queryKey: ['trace', traceId, params],
    queryFn: () => tracesApi.getTrace(traceId, params),
    enabled: !!traceId,
  });
};
