import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { env } from "../config/env";
import { useAuthStore } from "../store/authStore";

export const apiClient = axios.create({ baseURL: env.apiBaseUrl });

apiClient.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, setAccessToken, logout } = useAuthStore.getState();
  if (!refreshToken) return null;

  try {
    const resp = await axios.post(`${env.apiBaseUrl}/auth/refresh`, { refresh_token: refreshToken });
    const newAccessToken: string = resp.data.access_token;
    await setAccessToken(newAccessToken);
    return newAccessToken;
  } catch {
    await logout();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;

    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      refreshInFlight ??= refreshAccessToken().finally(() => {
        refreshInFlight = null;
      });
      const newAccessToken = await refreshInFlight;
      if (newAccessToken) {
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newAccessToken}`;
        return apiClient(original);
      }
    }
    return Promise.reject(error);
  }
);
