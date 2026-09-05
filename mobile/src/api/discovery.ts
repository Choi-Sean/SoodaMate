import { apiClient } from "./client";
import type { Candidate } from "../types";

export async function getCandidates(limit = 20): Promise<Candidate[]> {
  const resp = await apiClient.get<Candidate[]>("/discovery/candidates", { params: { limit } });
  return resp.data;
}
