import { useQuery } from '@tanstack/react-query';
import { spansApi } from '@/api';
import type { SpansQueryParams } from '@/api';

export const useSpans = (traceId: string, params?: SpansQueryParams) => {
  return useQuery({
    queryKey: ['spans', traceId, params],
    queryFn: () => spansApi.listSpans(traceId, params),
    enabled: !!traceId,
  });
};

export const useSpan = (spanId: string) => {
  return useQuery({
    queryKey: ['span', spanId],
    queryFn: () => spansApi.getSpan(spanId),
    enabled: !!spanId,
  });
};
