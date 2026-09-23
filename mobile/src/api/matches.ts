import { apiClient } from "./client";
import type { BlindChatFeedback, BlindChatFeedbackInput, Candidate, Icebreaker, Match } from "../types";

export async function getMatches(): Promise<Match[]> {
  const resp = await apiClient.get<Match[]>("/matches");
  return resp.data;
}

/** Deletes the match and everything in it (messages, calls, ...). Unless
 * either side has reported or blocked the other, this also clears the swipe
 * history between the two — that's what actually lets them match again
 * later; a report/block keeps this pair permanently excluded from each
 * other's Discover deck instead (see backend match_service.delete_match). */
export async function deleteMatch(matchId: string): Promise<void> {
  await apiClient.delete(`/matches/${matchId}`);
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

/** Spends 1 stealth_peek_credit (shop product blind_peek_1) so *I* alone can
 * see the other side's real profile in a still-anonymous blind match — the
 * other side is never told. Throws a 402 (axios error, response.status)
 * when there are no credits left; the caller sends the buyer to the shop.
 * Named spendBlindPeek, not useBlindPeek — it's a plain API call fired from
 * an event handler, and a "use..." name would make eslint's rules-of-hooks
 * (wrongly) treat it as a hook. */
export async function spendBlindPeek(matchId: string): Promise<Match> {
  const resp = await apiClient.post<Match>(`/matches/${matchId}/blind-peek`);
  return resp.data;
}

export async function submitBlindFeedback(
  matchId: string,
  input: BlindChatFeedbackInput
): Promise<BlindChatFeedback> {
  const resp = await apiClient.post<BlindChatFeedback>(`/matches/${matchId}/blind-feedback`, input);
  return resp.data;
}
