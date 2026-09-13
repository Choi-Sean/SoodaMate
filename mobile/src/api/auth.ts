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

export async function loginWithApple(identityToken: string): Promise<AuthTokens> {
  const resp = await apiClient.post<AuthTokens>("/auth/apple", { identity_token: identityToken });
  return resp.data;
}

export async function startPhoneAuth(phoneNumber: string): Promise<void> {
  await apiClient.post("/auth/phone/start", { phone_number: phoneNumber });
}

export interface PhoneAuthResult extends AuthTokens {
  is_new_user: boolean;
}

export async function confirmPhoneAuth(phoneNumber: string, code: string): Promise<PhoneAuthResult> {
  const resp = await apiClient.post<PhoneAuthResult>("/auth/phone/confirm", {
    phone_number: phoneNumber,
    code,
  });
  return resp.data;
}
