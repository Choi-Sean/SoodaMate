import { apiClient } from "./client";
import type { ChatMessage } from "../types";

export async function getMessageHistory(matchId: string, before?: string, limit = 50): Promise<ChatMessage[]> {
  const resp = await apiClient.get<ChatMessage[]>(`/matches/${matchId}/messages`, {
    params: { before, limit },
  });
  return resp.data;
}
