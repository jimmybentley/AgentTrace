import { useState } from 'react';
import type { TraceStatus } from '@/api/types';

interface TraceFiltersProps {
  status?: TraceStatus;
  onStatusChange: (status?: TraceStatus) => void;
  onSearch: (query: string) => void;
}

export const TraceFilters: React.FC<TraceFiltersProps> = ({
  status,
  onStatusChange,
  onSearch,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  return (
    <div className="flex gap-4 items-center">
      <form onSubmit={handleSearch} className="flex-1">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by trace name or ID..."
            className="w-full px-4 py-2 pl-10 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <svg
            className="absolute left-3 top-2.5 w-5 h-5 text-slate-500"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </form>

      <select
        value={status || ''}
        onChange={(e) => onStatusChange((e.target.value as TraceStatus) || undefined)}
        className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Status</option>
        <option value="running">Running</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="timeout">Timeout</option>
      </select>
    </div>
  );
};
