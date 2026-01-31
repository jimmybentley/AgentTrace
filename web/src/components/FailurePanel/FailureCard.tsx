import type { FailureAnnotation } from '@/api/types';
import { getCategoryColor } from '@/utils';
import { formatPercentage } from '@/utils';
import { FAILURE_MODE_LABELS } from '@/utils';

interface FailureCardProps {
  annotation: FailureAnnotation;
  onClick?: () => void;
}

export const FailureCard: React.FC<FailureCardProps> = ({ annotation, onClick }) => {
  const categoryColor = getCategoryColor(annotation.category);
  const modeLabel = FAILURE_MODE_LABELS[annotation.failure_mode] || annotation.failure_mode;

  return (
    <div
      className="p-4 bg-slate-900 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className="px-2.5 py-0.5 rounded-full text-xs font-medium"
            style={{
              backgroundColor: `${categoryColor}20`,
              color: categoryColor,
              border: `1px solid ${categoryColor}40`,
            }}
          >
            {annotation.category}
          </span>
          <span className="text-sm font-medium text-slate-200">{modeLabel}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <span>Confidence:</span>
          <span className="font-semibold text-slate-300">
            {formatPercentage(annotation.confidence)}
          </span>
        </div>
      </div>

      <p className="text-sm text-slate-400 mb-3">{annotation.reasoning}</p>

      <div className="flex items-center gap-4 text-xs text-slate-500">
        {annotation.span_id && (
          <div className="flex items-center gap-1">
            <span>Span:</span>
            <span className="font-mono">{annotation.span_id.slice(0, 8)}...</span>
          </div>
        )}
        {annotation.agent_id && (
          <div className="flex items-center gap-1">
            <span>Agent:</span>
            <span className="font-mono">{annotation.agent_id.slice(0, 8)}...</span>
          </div>
        )}
      </div>
    </div>
  );
};
