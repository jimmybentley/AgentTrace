import { useState } from 'react';

type TabId = 'graph' | 'timeline' | 'failures' | 'spans';

interface TraceTabsProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  failureCount?: number;
  spanCount?: number;
}

export const TraceTabs: React.FC<TraceTabsProps> = ({
  activeTab,
  onTabChange,
  failureCount = 0,
  spanCount = 0,
}) => {
  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: 'graph', label: 'Agent Graph' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'failures', label: 'Failures', count: failureCount },
    { id: 'spans', label: 'Spans', count: spanCount },
  ];

  return (
    <div className="border-b border-slate-700">
      <div className="flex gap-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.id
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-slate-400 hover:text-slate-300'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span
                className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-slate-700 text-slate-400'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

export type { TabId };
