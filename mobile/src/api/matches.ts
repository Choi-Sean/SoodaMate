import { apiClient } from "./client";
import type { Icebreaker, Match } from "../types";

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
