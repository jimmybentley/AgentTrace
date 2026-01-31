import { useState } from 'react';
import type { FailureAnnotation, FailureCategory } from '@/api/types';
import { FailureCard } from './FailureCard';
import { FAILURE_CATEGORIES } from '@/utils';

interface FailurePanelProps {
  annotations: FailureAnnotation[];
  onAnnotationClick?: (annotation: FailureAnnotation) => void;
}

export const FailurePanel: React.FC<FailurePanelProps> = ({
  annotations,
  onAnnotationClick,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<FailureCategory | 'all'>('all');

  const filteredAnnotations =
    selectedCategory === 'all'
      ? annotations
      : annotations.filter((a) => a.category === selectedCategory);

  // Count by category
  const categoryCounts = annotations.reduce((acc, a) => {
    acc[a.category] = (acc[a.category] || 0) + 1;
    return acc;
  }, {} as Record<FailureCategory, number>);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-slate-200">
          Failure Annotations ({annotations.length})
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            All ({annotations.length})
          </button>
          {FAILURE_CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedCategory === cat.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {cat.label} ({categoryCounts[cat.value] || 0})
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        {filteredAnnotations.length > 0 ? (
          filteredAnnotations.map((annotation) => (
            <FailureCard
              key={annotation.annotation_id}
              annotation={annotation}
              onClick={() => onAnnotationClick?.(annotation)}
            />
          ))
        ) : (
          <div className="text-center text-slate-400 py-8">
            No failures in this category
          </div>
        )}
      </div>
    </div>
  );
};
