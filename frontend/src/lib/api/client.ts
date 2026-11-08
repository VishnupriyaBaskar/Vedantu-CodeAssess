import { config } from "@/config";
import { ApiResponse } from "@/types/api";

const DEFAULT_TIMEOUT_MS = 6000;

/**
 * Reusable native fetch API client with timeout, cancellation, and structured error handling
 */
export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit & { timeoutMs?: number }
): Promise<ApiResponse<T>> {
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Link caller signal if provided to support component unmount cancellation
  if (options?.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }

  const baseUrl = config.apiBaseUrl.replace(/\/+$/, "");
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  let url = `${baseUrl}${cleanEndpoint}`;

  // If executing in Node.js server context with a relative path, resolve against internal backend URL
  if (typeof window === "undefined" && url.startsWith("/")) {
    const internalOrigin = (process.env.BACKEND_INTERNAL_URL || "http://backend:8000").replace(/\/+$/, "");
    url = `${internalOrigin}${url}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options?.headers,
      },
      cache: "no-store",
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
      let errorDetails: unknown = undefined;

      try {
        const errorBody = await response.json();
        if (errorBody && typeof errorBody === "object") {
          errorMessage = errorBody.detail || errorBody.message || errorMessage;
          errorDetails = errorBody;
        }
      } catch {
        // Response body was not JSON
      }

      return {
        success: false,
        error: {
          message: errorMessage,
          statusCode: response.status,
          details: errorDetails,
        },
      };
    }

    const data: T = await response.json();
    return {
      success: true,
      data,
    };
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    if (err instanceof Error) {
      if (err.name === "AbortError") {
        if (options?.signal?.aborted) {
          return {
            success: false,
            error: {
              message: "Request was cancelled.",
            },
          };
        }
        return {
          success: false,
          error: {
            message: `Request timed out after ${timeoutMs}ms. Backend server at ${baseUrl} is unreachable or not responding.`,
          },
        };
      }
      return {
        success: false,
        error: {
          message: `Network connection failed: ${err.message}. Ensure the backend service is running on ${baseUrl}.`,
        },
      };
    }

    return {
      success: false,
      error: {
        message: "An unexpected client error occurred while communicating with the backend.",
      },
    };
  }
}

/**
 * Convenience GET helper
 */
export async function apiGet<T>(
  endpoint: string,
  options?: Omit<RequestInit, "method"> & { timeoutMs?: number }
): Promise<ApiResponse<T>> {
  return apiClient<T>(endpoint, {
    ...options,
    method: "GET",
  });
}