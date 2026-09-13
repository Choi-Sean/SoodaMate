import { apiClient } from "./client";

export async function deleteAccount(): Promise<void> {
  await apiClient.delete("/account/me");
}

export interface Me {
  id: string;
  email: string | null;
  phone_verified: boolean;
  preferred_language: string;
}

/** Unlike getMyProfile, this never 404s on a brand-new account that hasn't
 * completed ProfileSetupScreen yet — RootNavigator calls it first to decide
 * the phone-verification gate, which now sits before profile setup. */
export async function getMe(): Promise<Me> {
  const resp = await apiClient.get<Me>("/account/me");
  return resp.data;
}

/** Kept in sync with the client's own i18n language purely so push_service
 * (backend) can send FCM notification text in the language the user reads
 * the app in — it has no effect on in-app text. Best-effort: callers should
 * swallow errors (e.g. not logged in yet, offline) rather than surface them,
 * since this is a background sync, not a user-initiated action. */
export async function updateLanguagePreference(language: string): Promise<void> {
  await apiClient.put("/account/language", { language });
}

/** Collected once at signup (ProfileSetupScreen) for marketing outreach only
 * — phone number is the sole login credential now, so this is never
 * verified. The backend still enforces uniqueness and 409s on a collision. */
export async function updateEmail(email: string): Promise<void> {
  await apiClient.put("/account/email", { email });
}

export interface CancelSubscriptionResult {
  premium_until: string;
}

export async function cancelSubscription(): Promise<CancelSubscriptionResult> {
  const resp = await apiClient.post<CancelSubscriptionResult>("/account/subscription/cancel");
  return resp.data;
}
