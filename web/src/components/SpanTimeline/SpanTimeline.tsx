import type { Span } from '@/api/types';
import { getKindColor } from '@/utils';
import { formatDuration } from '@/utils';

interface SpanTimelineProps {
  spans: Span[];
  onSpanClick?: (span: Span) => void;
}

export const SpanTimeline: React.FC<SpanTimelineProps> = ({ spans, onSpanClick }) => {
  if (spans.length === 0) return null;

  // Calculate timeline bounds
  const times = spans.map((s) => new Date(s.start_time).getTime());
  const minTime = Math.min(...times);
  const maxTime = Math.max(
    ...spans.map((s) => (s.end_time ? new Date(s.end_time).getTime() : new Date(s.start_time).getTime()))
  );
  const totalDuration = maxTime - minTime;

  // Group spans by agent
  const spansByAgent = spans.reduce((acc, span) => {
    const agentId = span.agent_id || 'unknown';
    if (!acc[agentId]) acc[agentId] = [];
    acc[agentId].push(span);
    return acc;
  }, {} as Record<string, Span[]>);

  const agents = Object.keys(spansByAgent);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-slate-200">Span Timeline</h3>
        <div className="text-sm text-slate-400">
          Total Duration: {formatDuration(totalDuration)}
        </div>
      </div>

      <div className="space-y-3">
        {agents.map((agentId) => (
          <div key={agentId} className="border border-slate-700 rounded-lg p-4">
            <div className="text-sm font-medium text-slate-300 mb-3">
              Agent: {agentId.slice(0, 8)}...
            </div>
            <div className="relative h-12 bg-slate-900 rounded">
              {spansByAgent[agentId].map((span) => {
                const startTime = new Date(span.start_time).getTime();
                const endTime = span.end_time
                  ? new Date(span.end_time).getTime()
                  : startTime + 1000; // Default 1s if no end time
                const left = ((startTime - minTime) / totalDuration) * 100;
                const width = ((endTime - startTime) / totalDuration) * 100;

                return (
                  <div
                    key={span.span_id}
                    className="absolute top-1 h-10 rounded cursor-pointer hover:opacity-80 transition-opacity"
                    style={{
                      left: `${left}%`,
                      width: `${Math.max(width, 0.5)}%`,
                      backgroundColor: getKindColor(span.kind),
                    }}
                    onClick={() => onSpanClick?.(span)}
                    title={`${span.name} - ${span.kind}`}
                  >
                    <div className="px-2 py-1 text-xs text-white truncate">
                      {span.name}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-4 pt-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">Legend:</div>
        {[
          { kind: 'llm_call', label: 'LLM Call' },
          { kind: 'tool_call', label: 'Tool Call' },
          { kind: 'agent_message', label: 'Agent Message' },
          { kind: 'handoff', label: 'Handoff' },
          { kind: 'checkpoint', label: 'Checkpoint' },
        ].map(({ kind, label }) => (
          <div key={kind} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded"
              style={{ backgroundColor: getKindColor(kind as any) }}
            />
            <span className="text-xs text-slate-400">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
