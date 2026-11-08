import { apiClient } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/tokenStorage";
import {
  LoginPayload,
  RegisterPayload,
  TokenRefreshResponse,
  TokenResponse,
  UserProfile,
} from "@/types/auth";
import { ApiResponse } from "@/types/api";

export async function loginApi(payload: LoginPayload): Promise<ApiResponse<TokenResponse>> {
  const result = await apiClient<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.success && result.data) {
    tokenStorage.setTokens({
      accessToken: result.data.access_token,
      refreshToken: result.data.refresh_token,
    });
  }

  return result;
}

export async function registerApi(payload: RegisterPayload): Promise<ApiResponse<TokenResponse>> {
  const result = await apiClient<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (result.success && result.data) {
    tokenStorage.setTokens({
      accessToken: result.data.access_token,
      refreshToken: result.data.refresh_token,
    });
  }

  return result;
}

export async function refreshTokensApi(refreshToken: string): Promise<ApiResponse<TokenRefreshResponse>> {
  const result = await apiClient<TokenRefreshResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (result.success && result.data) {
    tokenStorage.setTokens({
      accessToken: result.data.access_token,
      refreshToken: result.data.refresh_token,
    });
  } else {
    tokenStorage.clearTokens();
  }

  return result;
}

export async function logoutApi(): Promise<ApiResponse<{ message: string; detail?: string }>> {
  const tokens = tokenStorage.getTokens();
  const headers: Record<string, string> = {};

  if (tokens?.accessToken) {
    headers["Authorization"] = `Bearer ${tokens.accessToken}`;
  }

  try {
    return await apiClient<{ message: string; detail?: string }>("/auth/logout", {
      method: "POST",
      headers,
      body: JSON.stringify({ refresh_token: tokens?.refreshToken || null }),
    });
  } finally {
    tokenStorage.clearTokens();
  }
}

export async function getCurrentUserApi(): Promise<ApiResponse<UserProfile>> {
  const token = tokenStorage.getAccessToken();
  if (!token) {
    return {
      success: false,
      error: {
        message: "No authentication token present.",
      },
    };
  }

  return await apiClient<UserProfile>("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
