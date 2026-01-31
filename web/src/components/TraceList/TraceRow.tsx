import { Link } from 'react-router-dom';
import type { Trace } from '@/api/types';
import { StatusBadge } from '@/components/common';
import { formatDuration, formatCost, formatTokens, formatRelativeTime } from '@/utils';

interface TraceRowProps {
  trace: Trace;
}

export const TraceRow: React.FC<TraceRowProps> = ({ trace }) => {
  const duration = trace.end_time
    ? new Date(trace.end_time).getTime() - new Date(trace.start_time).getTime()
    : undefined;

  return (
    <Link
      to={`/traces/${trace.trace_id}`}
      className="block hover:bg-slate-800/50 transition-colors border-b border-slate-700 last:border-b-0"
    >
      <div className="px-6 py-4 grid grid-cols-6 gap-4 items-center">
        <div className="col-span-2">
          <div className="font-medium text-slate-200 truncate">{trace.name || 'Untitled'}</div>
          <div className="text-xs text-slate-500 truncate">{trace.trace_id}</div>
        </div>
        <div className="text-center">
          <StatusBadge status={trace.status} />
        </div>
        <div className="text-center">
          <div className="text-sm text-slate-300">{trace.agent_count} agents</div>
          <div className="text-xs text-slate-500">{trace.span_count} spans</div>
        </div>
        <div className="text-center">
          <div className="text-sm text-slate-300">{formatDuration(duration)}</div>
          <div className="text-xs text-slate-500">{formatTokens(trace.total_tokens)}</div>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-300">{formatCost(trace.total_cost_usd)}</div>
          <div className="text-xs text-slate-500">{formatRelativeTime(trace.start_time)}</div>
        </div>
      </div>
    </Link>
  );
};
