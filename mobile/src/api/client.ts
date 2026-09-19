import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { env } from "../config/env";
import { reportError } from "../services/errorReporting";
import { useAuthStore } from "../store/authStore";

// 402 (payment required, e.g. no AI Match credits) and 429 (rate limited,
// e.g. daily blind-chat match cap) are deliberately-thrown, expected,
// high-frequency business responses in this backend — still worth having
// in Sentry (a *sudden spike* in either is real signal), just not at
// "error" severity, or they'd bury genuine bugs in the same list.
const EXPECTED_STATUS_LEVEL: Record<number, "warning"> = { 402: "warning", 429: "warning" };

function reportApiError(error: AxiosError) {
  const status = error.response?.status;
  reportError(
    error,
    {
      method: error.config?.method,
      url: error.config?.url,
      status: status ?? "no response",
      responseData: error.response?.data,
    },
    (status && EXPECTED_STATUS_LEVEL[status]) || "error"
  );
}

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

    // The very first 401 on a request is routine (access tokens expire
    // constantly) and, if the refresh below succeeds, never actually
    // reaches the caller as an error at all — reporting it would just be
    // noise. Every other rejection (this 401 after a failed/already-tried
    // refresh, or any other status, or no response at all) is real.
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
    reportApiError(error);
    return Promise.reject(error);
  }
);
