import { getStatusColor } from '@/utils';
import type { TraceStatus, SpanStatus } from '@/api/types';

interface StatusBadgeProps {
  status: TraceStatus | SpanStatus;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const color = getStatusColor(status);

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className}`}
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {status}
    </span>
  );
};
