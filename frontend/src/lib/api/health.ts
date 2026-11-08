import { apiGet } from "./client";
import { BackendHealthResponse, ApiResponse } from "@/types/api";

/**
 * Checks connectivity to FastAPI backend GET /api/v1/health
 */
export async function checkBackendHealth(
  options?: { signal?: AbortSignal; timeoutMs?: number }
): Promise<ApiResponse<BackendHealthResponse>> {
  return apiGet<BackendHealthResponse>("/health", options);
}