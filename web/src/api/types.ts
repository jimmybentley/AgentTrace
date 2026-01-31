// Core types matching the backend API

export type TraceStatus = 'running' | 'completed' | 'failed' | 'timeout';
export type SpanStatus = 'ok' | 'error' | 'timeout';
export type SpanKind = 'llm_call' | 'tool_call' | 'agent_message' | 'checkpoint' | 'handoff';
export type MessageType = 'request' | 'response' | 'broadcast' | 'handoff';
export type FailureCategory = 'specification' | 'coordination' | 'verification';

export interface Trace {
  trace_id: string;
  name: string;
  status: TraceStatus;
  start_time: string;
  end_time?: string;
  agent_count: number;
  span_count: number;
  total_tokens: number;
  total_cost_usd: number;
  metadata?: Record<string, any>;
}

export interface TraceDetail extends Trace {
  graph?: AgentGraph;
}

export interface TracesResponse {
  traces: Trace[];
  total: number;
  limit: number;
  offset: number;
}

export interface Span {
  span_id: string;
  trace_id: string;
  parent_span_id?: string;
  agent_id?: string;
  name: string;
  kind: SpanKind;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  status: SpanStatus;
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
  input?: Record<string, any>;
  output?: Record<string, any>;
  error?: Record<string, any>;
  attributes?: Record<string, any>;
}

export interface SpansResponse {
  spans: Span[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentNode {
  id: string;
  name: string;
  role: string;
  model?: string;
  span_count: number;
  total_tokens: number;
  total_cost_usd: number;
  error_count: number;
  avg_latency_ms: number;
}

export interface CommunicationEdge {
  source: string;
  target: string;
  message_count: number;
  message_types: string[];
  avg_latency_ms: number;
}

export interface GraphMetrics {
  node_count: number;
  edge_count: number;
  density: number;
  has_cycles: boolean;
}

export interface AgentGraph {
  trace_id: string;
  nodes: AgentNode[];
  edges: CommunicationEdge[];
  metrics: GraphMetrics;
  bottlenecks?: string[];
  isolated_agents?: string[];
}

export interface FailureAnnotation {
  annotation_id: string;
  failure_mode: string;
  category: FailureCategory;
  confidence: number;
  reasoning: string;
  span_id?: string;
  agent_id?: string;
}

export interface FailuresResponse {
  trace_id: string;
  annotations: FailureAnnotation[];
}

export interface TraceMetrics {
  trace_id: string;
  total_duration_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  agent_count: number;
  span_count: number;
  error_count: number;
  tokens_by_agent: Record<string, number>;
  latency_by_agent: Record<string, number>;
  cost_by_agent: Record<string, number>;
}

export interface ClassifyResponse {
  trace_id: string;
  annotations: FailureAnnotation[];
  created_count: number;
}

// Query parameters
export interface TracesQueryParams {
  limit?: number;
  offset?: number;
  status?: TraceStatus;
  start_time?: string;
  end_time?: string;
}

export interface SpansQueryParams {
  limit?: number;
  offset?: number;
}

export interface TraceQueryParams {
  include_graph?: boolean;
}
