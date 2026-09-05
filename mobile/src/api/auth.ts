import { apiClient } from "./client";
import type { AuthTokens } from "../types";

export async function signup(email: string, password: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/signup", { email, password });
  return resp.data;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/login", { email, password });
  return resp.data;
}

export async function loginWithGoogle(idToken: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/google", { id_token: idToken });
  return resp.data;
}

export async function loginWithKakao(accessToken: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/kakao", { access_token: accessToken });
  return resp.data;
}

export async function loginWithApple(identityToken: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/apple", { identity_token: identityToken });
  return resp.data;
}
