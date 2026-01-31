import { TraceList } from '@/components/TraceList';

export const TracesPage: React.FC = () => {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-100">Traces</h2>
        <p className="text-slate-400 mt-1">
          View and analyze multi-agent execution traces
        </p>
      </div>
      <TraceList />
    </div>
  );
};
