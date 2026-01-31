import { Link } from 'react-router-dom';
import { TraceDetail } from '@/components/TraceDetail';

export const TraceDetailPage: React.FC = () => {
  return (
    <div>
      <div className="mb-6">
        <Link
          to="/traces"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-300 transition-colors mb-4"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M15 19l-7-7 7-7" />
          </svg>
          Back to Traces
        </Link>
      </div>
      <TraceDetail />
    </div>
  );
};
