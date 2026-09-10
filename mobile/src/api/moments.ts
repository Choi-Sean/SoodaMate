import { apiClient } from "./client";
import type { Moment } from "../types";

export async function getMyMoments(): Promise<Moment[]> {
  const resp = await apiClient.get<Moment[]>("/moments/me");
  return resp.data;
}

export async function createMoment(imageObjectPath: string, caption?: string | null): Promise<Moment> {
  const resp = await apiClient.post<Moment>("/moments", {
    image_object_path: imageObjectPath,
    caption: caption?.trim() || null,
  });
  return resp.data;
}

export async function deleteMoment(momentId: string): Promise<void> {
  await apiClient.delete(`/moments/${momentId}`);
}
