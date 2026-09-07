import { apiClient } from "./client";

export async function deleteAccount(): Promise<void> {
  await apiClient.delete("/account/me");
}

/** Kept in sync with the client's own i18n language purely so push_service
 * (backend) can send FCM notification text in the language the user reads
 * the app in — it has no effect on in-app text. Best-effort: callers should
 * swallow errors (e.g. not logged in yet, offline) rather than surface them,
 * since this is a background sync, not a user-initiated action. */
export async function updateLanguagePreference(language: string): Promise<void> {
  await apiClient.put("/account/language", { language });
}

export interface CancelSubscriptionResult {
  premium_until: string;
}

export async function cancelSubscription(): Promise<CancelSubscriptionResult> {
  const resp = await apiClient.post<CancelSubscriptionResult>("/account/subscription/cancel");
  return resp.data;
}
