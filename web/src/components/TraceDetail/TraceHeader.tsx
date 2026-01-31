import type { TraceDetail } from '@/api/types';
import { StatusBadge, CopyButton } from '@/components/common';
import {
  formatDuration,
  formatCost,
  formatTokens,
  formatDateTime,
  formatNumber,
} from '@/utils';

interface TraceHeaderProps {
  trace: TraceDetail;
}

export const TraceHeader: React.FC<TraceHeaderProps> = ({ trace }) => {
  const duration = trace.end_time
    ? new Date(trace.end_time).getTime() - new Date(trace.start_time).getTime()
    : undefined;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-100 mb-2">
            {trace.name || 'Untitled Trace'}
          </h1>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="font-mono">{trace.trace_id}</span>
            <CopyButton text={trace.trace_id} />
          </div>
        </div>
        <StatusBadge status={trace.status} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-1">Duration</div>
          <div className="text-lg font-semibold text-slate-200">
            {formatDuration(duration)}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Total Tokens</div>
          <div className="text-lg font-semibold text-slate-200">
            {formatTokens(trace.total_tokens)}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Total Cost</div>
          <div className="text-lg font-semibold text-slate-200">
            {formatCost(trace.total_cost_usd)}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500 mb-1">Agents</div>
          <div className="text-lg font-semibold text-slate-200">
            {formatNumber(trace.agent_count)}
          </div>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">Started {formatDateTime(trace.start_time)}</div>
        {trace.end_time && (
          <div className="text-xs text-slate-500">Ended {formatDateTime(trace.end_time)}</div>
        )}
      </div>
    </div>
  );
};
