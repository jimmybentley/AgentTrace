import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTrace, useGraph, useFailures, useSpans } from '@/hooks';
import { LoadingSpinner, ErrorState } from '@/components/common';
import { AgentGraph, GraphLegend } from '@/components/AgentGraph';
import { FailurePanel } from '@/components/FailurePanel';
import { SpanTimeline } from '@/components/SpanTimeline';
import { TraceHeader } from './TraceHeader';
import { TraceTabs, type TabId } from './TraceTabs';

export const TraceDetail: React.FC = () => {
  const { traceId } = useParams<{ traceId: string }>();
  const [activeTab, setActiveTab] = useState<TabId>('graph');
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>(undefined);

  const { data: trace, isLoading: isLoadingTrace, isError: isErrorTrace } = useTrace(traceId!);
  const { data: graph, isLoading: isLoadingGraph } = useGraph(traceId!);
  const { data: failures } = useFailures(traceId!);
  const { data: spansData } = useSpans(traceId!, { limit: 1000 });

  if (isLoadingTrace) {
    return <LoadingSpinner size="lg" message="Loading trace..." />;
  }

  if (isErrorTrace || !trace) {
    return <ErrorState message="Failed to load trace" />;
  }

  const spans = spansData?.spans || [];
  const failureCount = failures?.annotations.length || 0;

  return (
    <div className="space-y-6">
      <TraceHeader trace={trace} />

      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <TraceTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          failureCount={failureCount}
          spanCount={trace.span_count}
        />

        <div className="p-6">
          {activeTab === 'graph' && (
            <div className="relative">
              {isLoadingGraph ? (
                <LoadingSpinner message="Loading graph..." />
              ) : graph && graph.nodes.length > 0 ? (
                <div style={{ height: '600px' }} className="relative">
                  <AgentGraph
                    nodes={graph.nodes}
                    edges={graph.edges}
                    onNodeClick={(node) => setSelectedAgent(node.id)}
                    highlightedAgent={selectedAgent}
                    failedAgents={graph.nodes
                      .filter((n) => n.error_count > 0)
                      .map((n) => n.id)}
                  />
                  <GraphLegend />
                </div>
              ) : (
                <div className="text-center text-slate-400 py-12">
                  No agent graph data available
                </div>
              )}
            </div>
          )}

          {activeTab === 'timeline' && (
            <div>
              {spans.length > 0 ? (
                <SpanTimeline spans={spans} />
              ) : (
                <div className="text-center text-slate-400 py-12">No spans to display</div>
              )}
            </div>
          )}

          {activeTab === 'failures' && (
            <div>
              {failures && failures.annotations.length > 0 ? (
                <FailurePanel
                  annotations={failures.annotations}
                  onAnnotationClick={(ann) => setSelectedAgent(ann.agent_id)}
                />
              ) : (
                <div className="text-center text-slate-400 py-12">
                  No failures detected
                </div>
              )}
            </div>
          )}

          {activeTab === 'spans' && (
            <div>
              {spans.length > 0 ? (
                <div className="space-y-2">
                  {spans.map((span) => (
                    <div
                      key={span.span_id}
                      className="p-4 bg-slate-900 border border-slate-700 rounded-lg"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-slate-200">{span.name}</div>
                          <div className="text-xs text-slate-500">{span.kind}</div>
                        </div>
                        <div className="text-xs text-slate-400">{span.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-slate-400 py-12">No spans to display</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
