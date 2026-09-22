import { apiClient } from "./client";
import type { BlindChatFeedback, BlindChatFeedbackInput, Candidate, Icebreaker, Match } from "../types";

export async function getMatches(): Promise<Match[]> {
  const resp = await apiClient.get<Match[]>("/matches");
  return resp.data;
}

/** The other side's full profile (every photo, age, gender, interests, MBTI, ...) —
 * same shape a discovery card uses. 403s until a blind match is revealed; the
 * caller (ChatRoomScreen's header) only offers this once there's something to show. */
export async function getMatchedProfile(matchId: string): Promise<Candidate> {
  const resp = await apiClient.get<Candidate>(`/matches/${matchId}/profile`);
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
