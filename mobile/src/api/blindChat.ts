import { apiClient } from "./client";
import type { AiMatchResult, BlindChatFilters, BlindChatLimit, BlindChatQueueStats, BlindChatQueueStatus } from "../types";

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

/** Live per-category headcount of who's waiting right now, for the picker
 * screen — see routers/blind_chat.py::queue_stats. */
export async function getBlindChatQueueStats(): Promise<BlindChatQueueStats> {
  const resp = await apiClient.get<BlindChatQueueStats>("/blind-chat/queue-stats");
  return resp.data;
}

export async function getBlindChatLimit(): Promise<BlindChatLimit> {
  const resp = await apiClient.get<BlindChatLimit>("/blind-chat/limit");
  return resp.data;
}

export async function requestAiMatch(categories: string[], filters?: BlindChatFilters): Promise<AiMatchResult> {
  const resp = await apiClient.post<AiMatchResult>("/blind-chat/ai-match", { categories, ...filters });
  return resp.data;
}

export async function claimBlindChatAdBonus(): Promise<BlindChatLimit> {
  const resp = await apiClient.post<BlindChatLimit>("/blind-chat/ad-bonus");
  return resp.data;
}
