import type { TraceStatus, SpanStatus, SpanKind } from '@/api/types';

export const roleColors: Record<string, string> = {
  planner: '#8b5cf6',
  executor: '#10b981',
  reviewer: '#f59e0b',
  coder: '#3b82f6',
  researcher: '#ec4899',
  default: '#6b7280',
};

export const getRoleColor = (role: string): string => {
  return roleColors[role.toLowerCase()] || roleColors.default;
};

export const statusColors: Record<TraceStatus | SpanStatus, string> = {
  running: '#eab308',
  completed: '#22c55e',
  failed: '#ef4444',
  timeout: '#f97316',
  ok: '#22c55e',
  error: '#ef4444',
};

export const getStatusColor = (status: TraceStatus | SpanStatus): string => {
  return statusColors[status] || statusColors.error;
};

export const kindColors: Record<SpanKind, string> = {
  llm_call: '#3b82f6',
  tool_call: '#10b981',
  agent_message: '#8b5cf6',
  checkpoint: '#f59e0b',
  handoff: '#ec4899',
};

export const getKindColor = (kind: SpanKind): string => {
  return kindColors[kind] || '#6b7280';
};

export const categoryColors: Record<string, string> = {
  specification: '#ef4444',
  coordination: '#f59e0b',
  verification: '#3b82f6',
};

export const getCategoryColor = (category: string): string => {
  return categoryColors[category] || '#6b7280';
};
