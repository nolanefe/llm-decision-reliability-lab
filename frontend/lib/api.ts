import type {
  DatasetItem,
  ExecutionSummary,
  Experiment,
  ExperimentCreatePayload,
  ExperimentMetrics,
  FailureEntry,
  PromptVersion,
  Run,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Shape FastAPI uses for its default 422 request-validation errors. */
interface FastApiValidationDetail {
  loc: Array<string | number>;
  msg: string;
  type: string;
}

function isValidationDetailList(
  value: unknown,
): value is FastApiValidationDetail[] {
  return (
    Array.isArray(value) &&
    value.every(
      (entry) =>
        typeof entry === "object" &&
        entry !== null &&
        "msg" in entry &&
        typeof (entry as { msg: unknown }).msg === "string",
    )
  );
}

async function extractErrorMessage(response: Response): Promise<string> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return `Request failed with status ${response.status}`;
  }

  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (isValidationDetailList(detail)) {
      return detail
        .map((entry) => {
          const field = entry.loc.filter((part) => part !== "body").join(".");
          return field ? `${field}: ${entry.msg}` : entry.msg;
        })
        .join("; ");
    }
  }

  return `Request failed with status ${response.status}`;
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  cache?: RequestCache;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: options.cache ?? "no-store",
    });
  } catch {
    throw new ApiError(
      "Could not reach the API server. Confirm the backend is running and NEXT_PUBLIC_API_BASE_URL is correct.",
      0,
    );
  }

  if (!response.ok) {
    const message = await extractErrorMessage(response);
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function listDatasetItems(): Promise<DatasetItem[]> {
  return request<DatasetItem[]>("/api/v1/dataset-items");
}

export function listPromptVersions(): Promise<PromptVersion[]> {
  return request<PromptVersion[]>("/api/v1/prompt-versions");
}

export function listExperiments(): Promise<Experiment[]> {
  return request<Experiment[]>("/api/v1/experiments");
}

export function getExperiment(experimentId: number): Promise<Experiment> {
  return request<Experiment>(`/api/v1/experiments/${experimentId}`);
}

export function createExperiment(
  payload: ExperimentCreatePayload,
): Promise<Experiment> {
  return request<Experiment>("/api/v1/experiments", {
    method: "POST",
    body: payload,
  });
}

export function executeExperiment(
  experimentId: number,
): Promise<ExecutionSummary> {
  return request<ExecutionSummary>(
    `/api/v1/experiments/${experimentId}/execute`,
    { method: "POST" },
  );
}

export function listExperimentRuns(experimentId: number): Promise<Run[]> {
  return request<Run[]>(`/api/v1/experiments/${experimentId}/runs`);
}

export function getExperimentMetrics(
  experimentId: number,
): Promise<ExperimentMetrics> {
  return request<ExperimentMetrics>(
    `/api/v1/experiments/${experimentId}/metrics`,
  );
}

export function getExperimentFailures(
  experimentId: number,
): Promise<FailureEntry[]> {
  return request<FailureEntry[]>(
    `/api/v1/experiments/${experimentId}/failures`,
  );
}
