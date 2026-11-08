/**
 * Centralized Application Configuration
 */
export interface AppConfig {
  apiBaseUrl: string;
  appName: string;
  isProduction: boolean;
  isDevelopment: boolean;
}

const DEFAULT_API_BASE_URL = "/api/v1";

export const config: AppConfig = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL,
  appName: "Vedantu Coding Assessment Platform",
  isProduction: process.env.NODE_ENV === "production",
  isDevelopment: process.env.NODE_ENV === "development",
};
