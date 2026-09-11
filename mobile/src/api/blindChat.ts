import { apiClient } from "./client";
import type { BlindChatQueueStatus } from "../types";

export async function joinBlindChatQueue(categories: string[]): Promise<BlindChatQueueStatus> {
  const resp = await apiClient.post<BlindChatQueueStatus>("/blind-chat/queue", { categories });
  return resp.data;
}

export async function getBlindChatQueueStatus(): Promise<BlindChatQueueStatus> {
  const resp = await apiClient.get<BlindChatQueueStatus>("/blind-chat/queue");
  return resp.data;
}

export async function leaveBlindChatQueue(): Promise<void> {
  await apiClient.delete("/blind-chat/queue");
}
