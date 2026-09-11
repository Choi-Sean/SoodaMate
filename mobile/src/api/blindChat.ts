import { apiClient } from "./client";
import type { AiMatchResult, BlindChatFilters, BlindChatLimit, BlindChatQueueStatus } from "../types";

export async function joinBlindChatQueue(
  categories: string[],
  filters?: BlindChatFilters
): Promise<BlindChatQueueStatus> {
  const resp = await apiClient.post<BlindChatQueueStatus>("/blind-chat/queue", { categories, ...filters });
  return resp.data;
}

export async function getBlindChatQueueStatus(): Promise<BlindChatQueueStatus> {
  const resp = await apiClient.get<BlindChatQueueStatus>("/blind-chat/queue");
  return resp.data;
}

export async function leaveBlindChatQueue(): Promise<void> {
  await apiClient.delete("/blind-chat/queue");
}

export async function getBlindChatLimit(): Promise<BlindChatLimit> {
  const resp = await apiClient.get<BlindChatLimit>("/blind-chat/limit");
  return resp.data;
}

export async function requestAiMatch(categories: string[]): Promise<AiMatchResult> {
  const resp = await apiClient.post<AiMatchResult>("/blind-chat/ai-match", { categories });
  return resp.data;
}
