import { useQuery } from '@tanstack/react-query';
import { tracesApi } from '@/api';

export const useGraph = (traceId: string) => {
  return useQuery({
    queryKey: ['graph', traceId],
    queryFn: () => tracesApi.getGraph(traceId),
    enabled: !!traceId,
  });
};
