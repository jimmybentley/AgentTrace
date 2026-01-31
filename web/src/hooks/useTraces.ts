import { useQuery } from '@tanstack/react-query';
import { tracesApi } from '@/api';
import type { TracesQueryParams } from '@/api';

export const useTraces = (params?: TracesQueryParams) => {
  return useQuery({
    queryKey: ['traces', params],
    queryFn: () => tracesApi.listTraces(params),
    staleTime: 10000, // 10 seconds
  });
};
