import type { FailureCategory } from '@/api/types';

export const FAILURE_CATEGORIES: { value: FailureCategory; label: string }[] = [
  { value: 'specification', label: 'Specification' },
  { value: 'coordination', label: 'Coordination' },
  { value: 'verification', label: 'Verification' },
];

export const FAILURE_MODE_LABELS: Record<string, string> = {
  role_ambiguity: 'Role Ambiguity',
  incomplete_spec: 'Incomplete Specification',
  conflicting_instructions: 'Conflicting Instructions',
  handoff_failure: 'Handoff Failure',
  resource_contention: 'Resource Contention',
  deadlock: 'Deadlock',
  infinite_loop: 'Infinite Loop',
  output_validation: 'Output Validation',
  hallucination: 'Hallucination',
  format_error: 'Format Error',
};

export const SPAN_KIND_LABELS: Record<string, string> = {
  llm_call: 'LLM Call',
  tool_call: 'Tool Call',
  agent_message: 'Agent Message',
  checkpoint: 'Checkpoint',
  handoff: 'Handoff',
};
