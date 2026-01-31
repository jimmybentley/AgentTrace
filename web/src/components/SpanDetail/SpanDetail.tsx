import { JsonView, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import type { Span } from '@/api/types';
import { StatusBadge, CopyButton } from '@/components/common';
import { formatDuration, formatTokens, formatCost, formatDateTime } from '@/utils';

interface SpanDetailProps {
  span: Span;
  onClose?: () => void;
}

export const SpanDetail: React.FC<SpanDetailProps> = ({ span, onClose }) => {
  const duration = span.duration_ms || (span.end_time
    ? new Date(span.end_time).getTime() - new Date(span.start_time).getTime()
    : undefined);

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg">
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex-1">
          <h3 className="text-lg font-medium text-slate-200">{span.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-slate-500 font-mono">{span.span_id}</span>
            <CopyButton text={span.span_id} />
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <svg
              className="w-5 h-5 text-slate-400"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="p-4 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-slate-500 mb-1">Status</div>
            <StatusBadge status={span.status} />
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Kind</div>
            <div className="text-sm text-slate-300">{span.kind}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Duration</div>
            <div className="text-sm text-slate-300">{formatDuration(duration)}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Model</div>
            <div className="text-sm text-slate-300">{span.model || '-'}</div>
          </div>
          {span.input_tokens !== undefined && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Input Tokens</div>
              <div className="text-sm text-slate-300">{formatTokens(span.input_tokens)}</div>
            </div>
          )}
          {span.output_tokens !== undefined && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Output Tokens</div>
              <div className="text-sm text-slate-300">{formatTokens(span.output_tokens)}</div>
            </div>
          )}
          {span.cost_usd !== undefined && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Cost</div>
              <div className="text-sm text-slate-300">{formatCost(span.cost_usd)}</div>
            </div>
          )}
          <div>
            <div className="text-xs text-slate-500 mb-1">Started</div>
            <div className="text-sm text-slate-300">{formatDateTime(span.start_time)}</div>
          </div>
        </div>

        {span.input && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-slate-300">Input</div>
              <CopyButton text={JSON.stringify(span.input, null, 2)} />
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 max-h-64 overflow-auto">
              <JsonView
                data={span.input}
                shouldExpandNode={() => false}
                style={{
                  ...defaultStyles,
                  container: 'json-container',
                  basicChildStyle: 'json-basic-child',
                  label: 'json-label',
                  nullValue: 'json-null',
                  undefinedValue: 'json-undefined',
                  numberValue: 'json-number',
                  stringValue: 'json-string',
                  booleanValue: 'json-boolean',
                  otherValue: 'json-other',
                  punctuation: 'json-punctuation',
                }}
              />
            </div>
          </div>
        )}

        {span.output && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-slate-300">Output</div>
              <CopyButton text={JSON.stringify(span.output, null, 2)} />
            </div>
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 max-h-64 overflow-auto">
              <JsonView
                data={span.output}
                shouldExpandNode={() => false}
                style={{
                  ...defaultStyles,
                  container: 'json-container',
                  basicChildStyle: 'json-basic-child',
                  label: 'json-label',
                  nullValue: 'json-null',
                  undefinedValue: 'json-undefined',
                  numberValue: 'json-number',
                  stringValue: 'json-string',
                  booleanValue: 'json-boolean',
                  otherValue: 'json-other',
                  punctuation: 'json-punctuation',
                }}
              />
            </div>
          </div>
        )}

        {span.error && (
          <div>
            <div className="text-sm font-medium text-red-400 mb-2">Error</div>
            <div className="bg-red-900/20 border border-red-700 rounded-lg p-3">
              <pre className="text-sm text-red-300 whitespace-pre-wrap">
                {JSON.stringify(span.error, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
