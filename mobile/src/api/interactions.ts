import { apiClient } from "./client";

export type SwipeAction = "like" | "pass" | "superlike";

export interface SwipeResult {
  matched: boolean;
  match_id: string | null;
}

export interface SwipeLimit {
  remaining: number;
  limit: number;
  resets_at: string | null;
}

export async function swipe(action: SwipeAction, toUserId: string): Promise<SwipeResult> {
  const resp = await apiClient.post<SwipeResult>(`/interactions/${action}`, { to_user_id: toUserId });
  return resp.data;
}

export async function getSwipeLimit(): Promise<SwipeLimit> {
  const resp = await apiClient.get<SwipeLimit>("/interactions/swipe-limit");
  return resp.data;
}
