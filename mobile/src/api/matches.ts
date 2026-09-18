import { apiClient } from "./client";
import type { BlindChatFeedback, BlindChatFeedbackInput, Icebreaker, Match } from "../types";

export async function getMatches(): Promise<Match[]> {
  const resp = await apiClient.get<Match[]>("/matches");
  return resp.data;
}

export async function getIcebreaker(matchId: string): Promise<Icebreaker> {
  const resp = await apiClient.get<Icebreaker>(`/matches/${matchId}/icebreaker`);
  return resp.data;
}

export async function requestBlindReveal(matchId: string): Promise<Match> {
  const resp = await apiClient.post<Match>(`/matches/${matchId}/blind-reveal/request`);
  return resp.data;
}

export async function acceptBlindReveal(matchId: string): Promise<Match> {
  const resp = await apiClient.post<Match>(`/matches/${matchId}/blind-reveal/accept`);
  return resp.data;
}

export async function submitBlindFeedback(
  matchId: string,
  input: BlindChatFeedbackInput
): Promise<BlindChatFeedback> {
  const resp = await apiClient.post<BlindChatFeedback>(`/matches/${matchId}/blind-feedback`, input);
  return resp.data;
}
