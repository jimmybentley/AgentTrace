import { useQuery } from '@tanstack/react-query';
import { tracesApi } from '@/api';

export const useMetrics = (traceId: string) => {
  return useQuery({
    queryKey: ['metrics', traceId],
    queryFn: () => tracesApi.getMetrics(traceId),
    enabled: !!traceId,
  });
};
