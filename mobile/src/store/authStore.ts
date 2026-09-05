import { create } from "zustand";

import * as secureStorage from "../services/secureStorage";
import type { AuthTokens } from "../types";

const ACCESS_TOKEN_KEY = "sooda_access_token";
const REFRESH_TOKEN_KEY = "sooda_refresh_token";
const USER_ID_KEY = "sooda_user_id";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  hydrated: boolean;
  isAuthenticated: boolean;
  hydrate: () => Promise<void>;
  login: (tokens: AuthTokens) => Promise<void>;
  setAccessToken: (accessToken: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  userId: null,
  hydrated: false,
  isAuthenticated: false,

  hydrate: async () => {
    const [accessToken, refreshToken, userId] = await Promise.all([
      secureStorage.getItem(ACCESS_TOKEN_KEY),
      secureStorage.getItem(REFRESH_TOKEN_KEY),
      secureStorage.getItem(USER_ID_KEY),
    ]);
    set({
      accessToken,
      refreshToken,
      userId,
      isAuthenticated: Boolean(accessToken && refreshToken),
      hydrated: true,
    });
  },

  login: async (tokens: AuthTokens) => {
    await Promise.all([
      secureStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token),
      secureStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token),
      secureStorage.setItem(USER_ID_KEY, tokens.user_id),
    ]);
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      userId: tokens.user_id,
      isAuthenticated: true,
    });
  },

  setAccessToken: async (accessToken: string) => {
    await secureStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    set({ accessToken });
  },

  logout: async () => {
    await Promise.all([
      secureStorage.deleteItem(ACCESS_TOKEN_KEY),
      secureStorage.deleteItem(REFRESH_TOKEN_KEY),
      secureStorage.deleteItem(USER_ID_KEY),
    ]);
    set({ accessToken: null, refreshToken: null, userId: null, isAuthenticated: false });
  },
}));

export function getRefreshToken(): string | null {
  return useAuthStore.getState().refreshToken;
}
