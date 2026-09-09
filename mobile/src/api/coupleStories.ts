import { apiClient } from "./client";
import type { CoupleStory } from "../types";

export async function createCoupleStory(
  matchId: string,
  storyText: string,
  photoObjectPath?: string | null
): Promise<CoupleStory> {
  const resp = await apiClient.post<CoupleStory>("/couple-stories", {
    match_id: matchId,
    story_text: storyText,
    photo_object_path: photoObjectPath ?? null,
  });
  return resp.data;
}

export async function confirmCoupleStory(storyId: string): Promise<CoupleStory> {
  const resp = await apiClient.post<CoupleStory>(`/couple-stories/${storyId}/confirm`);
  return resp.data;
}

export async function declineCoupleStory(storyId: string): Promise<CoupleStory> {
  const resp = await apiClient.post<CoupleStory>(`/couple-stories/${storyId}/decline`);
  return resp.data;
}

export async function getCoupleStoriesFeed(before?: string): Promise<CoupleStory[]> {
  const resp = await apiClient.get<CoupleStory[]>("/couple-stories/feed", { params: { before } });
  return resp.data;
}

export async function getMyCoupleStories(): Promise<CoupleStory[]> {
  const resp = await apiClient.get<CoupleStory[]>("/couple-stories/mine");
  return resp.data;
}

export async function reportCoupleStory(storyId: string, reason: string): Promise<void> {
  await apiClient.post(`/couple-stories/${storyId}/report`, { reason });
}
