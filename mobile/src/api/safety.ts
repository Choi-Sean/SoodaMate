import { apiClient } from "./client";

export async function blockUser(userId: string): Promise<void> {
  await apiClient.post("/safety/block", { user_id: userId });
}

export async function reportUser(userId: string, reason: string, detail?: string): Promise<void> {
  await apiClient.post("/safety/report", { user_id: userId, reason, detail });
}
