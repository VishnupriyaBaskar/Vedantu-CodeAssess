"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  LoginPayload,
  RegisterPayload,
  UserProfile,
} from "@/types/auth";
import {
  getCurrentUserApi,
  loginApi,
  logoutApi,
  refreshTokensApi,
  registerApi,
} from "@/lib/api/auth";
import { tokenStorage } from "@/lib/auth/tokenStorage";

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginPayload) => Promise<{ success: boolean; error?: string }>;
  register: (payload: RegisterPayload) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
  hasRole: (role: string) => boolean;
  isAdmin: boolean;
  isInstructor: boolean;
  isStudent: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadCurrentUser = useCallback(async (): Promise<boolean> => {
    const token = tokenStorage.getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return false;
    }

    const res = await getCurrentUserApi();
    if (res.success && res.data) {
      setUser(res.data);
      setIsLoading(false);
      return true;
    }

    // Try token refresh if access token expired
    const refreshToken = tokenStorage.getRefreshToken();
    if (refreshToken) {
      const refreshRes = await refreshTokensApi(refreshToken);
      if (refreshRes.success) {
        const retryRes = await getCurrentUserApi();
        if (retryRes.success && retryRes.data) {
          setUser(retryRes.data);
          setIsLoading(false);
          return true;
        }
      }
    }

    tokenStorage.clearTokens();
    setUser(null);
    setIsLoading(false);
    return false;
  }, []);

  useEffect(() => {
    let ignore = false;
    async function initAuth() {
      if (!ignore) {
        await loadCurrentUser();
      }
    }
    initAuth();
    return () => {
      ignore = true;
    };
  }, [loadCurrentUser]);

  const login = async (credentials: LoginPayload) => {
    setIsLoading(true);
    const res = await loginApi(credentials);
    if (res.success && res.data) {
      setUser(res.data.user);
      setIsLoading(false);
      return { success: true };
    }
    setIsLoading(false);
    return {
      success: false,
      error: res.error?.message || "Login failed. Please check credentials.",
    };
  };

  const register = async (payload: RegisterPayload) => {
    setIsLoading(true);
    const res = await registerApi(payload);
    if (res.success && res.data) {
      setUser(res.data.user);
      setIsLoading(false);
      return { success: true };
    }
    setIsLoading(false);
    return {
      success: false,
      error: res.error?.message || "Registration failed.",
    };
  };

  const logout = async () => {
    setIsLoading(true);
    await logoutApi();
    setUser(null);
    setIsLoading(false);
  };

  const hasRole = (role: string) => {
    if (!user) return false;
    return user.roles.includes(role);
  };

  const isAdmin = hasRole("ADMIN");
  const isInstructor = hasRole("INSTRUCTOR") || isAdmin;
  const isStudent = hasRole("STUDENT");

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshSession: loadCurrentUser,
        hasRole,
        isAdmin,
        isInstructor,
        isStudent,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
