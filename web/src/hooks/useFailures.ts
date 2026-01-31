import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tracesApi } from '@/api';

export const useFailures = (traceId: string) => {
  return useQuery({
    queryKey: ['failures', traceId],
    queryFn: () => tracesApi.getFailures(traceId),
    enabled: !!traceId,
  });
};

export const useClassifyTrace = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (traceId: string) => tracesApi.classify(traceId),
    onSuccess: (data, traceId) => {
      queryClient.invalidateQueries({ queryKey: ['failures', traceId] });
    },
  });
};
