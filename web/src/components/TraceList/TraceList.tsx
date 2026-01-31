import { useState } from 'react';
import { useTraces } from '@/hooks';
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/common';
import { TraceRow } from './TraceRow';
import { TraceFilters } from './TraceFilters';
import type { TraceStatus } from '@/api/types';

export const TraceList: React.FC = () => {
  const [status, setStatus] = useState<TraceStatus | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const { data, isLoading, isError, error, refetch } = useTraces({
    limit,
    offset,
    status,
  });

  if (isLoading) {
    return <LoadingSpinner size="lg" message="Loading traces..." />;
  }

  if (isError) {
    return <ErrorState message={error?.message} retry={() => refetch()} />;
  }

  const traces = data?.traces || [];
  const total = data?.total || 0;

  // Filter by search query (client-side for now)
  const filteredTraces = searchQuery
    ? traces.filter(
        (trace) =>
          trace.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          trace.trace_id.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : traces;

  if (filteredTraces.length === 0) {
    return (
      <div>
        <div className="mb-6">
          <TraceFilters
            status={status}
            onStatusChange={setStatus}
            onSearch={setSearchQuery}
          />
        </div>
        <EmptyState
          title="No traces found"
          message={
            searchQuery
              ? 'Try adjusting your search query'
              : 'No traces match the selected filters'
          }
        />
      </div>
    );
  }

  const hasNextPage = offset + limit < total;
  const hasPrevPage = offset > 0;

  return (
    <div>
      <div className="mb-6">
        <TraceFilters
          status={status}
          onStatusChange={setStatus}
          onSearch={setSearchQuery}
        />
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-6 py-3 border-b border-slate-700 bg-slate-800/50">
          <div className="grid grid-cols-6 gap-4 text-xs font-medium text-slate-400 uppercase tracking-wider">
            <div className="col-span-2">Trace</div>
            <div className="text-center">Status</div>
            <div className="text-center">Agents / Spans</div>
            <div className="text-center">Duration / Tokens</div>
            <div className="text-right">Cost / Time</div>
          </div>
        </div>

        <div className="divide-y divide-slate-700">
          {filteredTraces.map((trace) => (
            <TraceRow key={trace.trace_id} trace={trace} />
          ))}
        </div>
      </div>

      {(hasNextPage || hasPrevPage) && (
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} traces
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setOffset((o) => Math.max(0, o - limit))}
              disabled={!hasPrevPage}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setOffset((o) => o + limit)}
              disabled={!hasNextPage}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed border border-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
