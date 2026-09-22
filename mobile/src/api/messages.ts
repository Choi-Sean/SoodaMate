import { apiClient } from "./client";
import type { ChatMessage } from "../types";

export async function getMessageHistory(matchId: string, before?: string, limit = 50): Promise<ChatMessage[]> {
  const resp = await apiClient.get<ChatMessage[]>(`/matches/${matchId}/messages`, {
    params: { before, limit },
  });
  return resp.data;
}

/** On-demand, user-picked-language translation — distinct from the automatic
 * one already attached to `translated_content` at send time (which only ever
 * targets the recipient's saved preferred_language). */
export async function translateMessage(
  matchId: string,
  messageId: string,
  targetLanguage: string
): Promise<{ translated_content: string; target_language: string }> {
  const resp = await apiClient.post(`/matches/${matchId}/messages/${messageId}/translate`, {
    target_language: targetLanguage,
  });
  return resp.data;
}
