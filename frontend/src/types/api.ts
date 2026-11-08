/**
 * API Error Model
 */
export interface ApiError {
  message: string;
  statusCode?: number;
  details?: unknown;
}

/**
 * Backend Health Check Response Structure
 * Matches FastAPI GET /api/v1/health response
 */
export interface BackendHealthResponse {
  status: "healthy" | string;
  app_name: string;
  environment: string;
  version: string;
  api_version: string;
}

/**
 * Strongly-typed API Response Union
 */
export type ApiResponse<T> =
  | { success: true; data: T; error?: never }
  | { success: false; data?: never; error: ApiError };
