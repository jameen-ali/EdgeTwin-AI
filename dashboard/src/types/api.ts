/**
 * API client and RFC 7807 Problem Details type definitions.
 */

export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: Record<string, string[]> | Array<{ loc: string[]; msg: string; type: string }>;
  [key: string]: unknown;
}

export class ApiError extends Error {
  public status: number;
  public problem?: ProblemDetails;

  constructor(message: string, status: number, problem?: ProblemDetails) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export interface HealthResponse {
  status: string;
  environment: string;
  version: string;
  timestamp: string;
  database?: string;
  mqtt?: string;
}
