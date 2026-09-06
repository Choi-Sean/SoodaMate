import { apiClient } from "./client";
import type { Candidate } from "../types";

export async function getCandidates(limit = 20): Promise<Candidate[]> {
  const resp = await apiClient.get<Candidate[]>("/discovery/candidates", { params: { limit } });
  return resp.data;
}

/** People recommended nearby matching the viewer's preferences — same pool
 * as getCandidates, just fetched in a bigger batch for a browsable grid
 * (the Discover tab) instead of the one-at-a-time Swipe deck. */
export async function getRecommended(limit = 30): Promise<Candidate[]> {
  const resp = await apiClient.get<Candidate[]>("/discovery/candidates", { params: { limit } });
  return resp.data;
}

export async function getLikedMe(limit = 50): Promise<Candidate[]> {
  const resp = await apiClient.get<Candidate[]>("/discovery/liked-me", { params: { limit } });
  return resp.data;
}
