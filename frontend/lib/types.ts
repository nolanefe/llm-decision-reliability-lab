// Types mirror the FastAPI Pydantic schemas in backend/app/schemas exactly.
// Keep in sync by hand -- there is no shared codegen in v0.1.

export type TicketCategory =
  | "billing"
  | "account_access"
  | "bug"
  | "feature_request"
  | "other";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export type ExperimentStatus =
  | "draft"
  | "pending"
  | "running"
  | "completed"
  | "failed";

export type RunStatus = "pending" | "running" | "completed" | "failed";

export type FailureCategory =
  | "invalid_json"
  | "schema_error"
  | "provider_error"
  | "timeout"
  | "content_mismatch"
  | "other";

export const SUPPORTED_MODELS = ["gpt-5-mini", "gpt-5-nano"] as const;
export type SupportedModel = (typeof SUPPORTED_MODELS)[number];

export interface DatasetItem {
  id: number;
  name: string;
  input_text: string;
  expected_category: TicketCategory;
  expected_priority: TicketPriority;
  reference_summary: string | null;
  reference_action: string | null;
  created_at: string;
}

export interface PromptVersion {
  id: number;
  name: string;
  version: number;
  description: string | null;
  template_text: string;
  created_at: string;
}

export interface Experiment {
  id: number;
  name: string;
  status: ExperimentStatus;
  repeat_count: number;
  dataset_item_ids: number[];
  prompt_version_ids: number[];
  model_names: string[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ExperimentCreatePayload {
  name: string;
  dataset_item_ids: number[];
  prompt_version_ids: number[];
  model_names: string[];
  repeat_count: number;
}

export interface ExecutionSummary {
  experiment_id: number;
  status: ExperimentStatus;
  planned_runs: number;
  completed_runs: number;
  failed_runs: number;
  schema_valid_runs: number;
  schema_invalid_runs: number;
  started_at: string | null;
  completed_at: string | null;
  average_reliability_score: number | null;
  recommended_prompt_version_id: number | null;
  recommended_model_name: string | null;
}

export interface Evaluation {
  id: number;
  run_id: number;
  schema_valid: boolean;
  category_correct: boolean | null;
  priority_correct: boolean | null;
  quality_score: number | null;
  consistency_score: number | null;
  failure_category: FailureCategory | null;
  reliability_score: number | null;
  notes: string | null;
  created_at: string;
}

export interface Run {
  id: number;
  experiment_id: number;
  dataset_item_id: number;
  prompt_version_id: number;
  model_name: string;
  repetition_index: number;
  status: RunStatus;
  raw_response: string | null;
  parsed_output: Record<string, unknown> | null;
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  estimated_cost_usd: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  evaluation: Evaluation | null;
}

export interface VariantMetrics {
  prompt_version_id: number;
  prompt_version_name: string;
  prompt_version_version: number;
  model_name: string;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  schema_valid_runs: number;
  schema_validity_rate: number;
  category_accuracy: number | null;
  priority_accuracy: number | null;
  average_quality_score: number | null;
  average_consistency_score: number | null;
  average_reliability_score: number | null;
  average_latency_ms: number | null;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  failure_count: number;
}

export interface Recommendation {
  recommended_prompt_version_id: number;
  recommended_model_name: string;
  reason: string;
  reliability_score: number;
  estimated_cost_usd: number;
  average_latency_ms: number | null;
}

export interface ExperimentMetrics {
  experiment_id: number;
  experiment_name: string;
  status: ExperimentStatus;
  total_runs: number;
  variant_metrics: VariantMetrics[];
  recommendation: Recommendation | null;
}

export interface FailureEntry {
  run_id: number;
  dataset_item_id: number;
  dataset_item_name: string;
  prompt_version_id: number;
  prompt_version_name: string;
  model_name: string;
  repetition_index: number;
  run_status: RunStatus;
  failure_category: FailureCategory;
  schema_valid: boolean;
  category_correct: boolean | null;
  priority_correct: boolean | null;
  sanitized_error_message: string | null;
  raw_response_preview: string | null;
}
