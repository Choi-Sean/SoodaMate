import { apiClient } from "./client";

export async function deleteAccount(): Promise<void> {
  await apiClient.delete("/account/me");
}
