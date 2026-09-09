import { apiClient } from "./client";

export interface PresignResult {
  upload_url: string;
  gcs_object_path: string;
}

export async function presignUpload(contentType: string, position: number): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign", {
    content_type: contentType,
    position,
  });
  return resp.data;
}

/** Images only (jpeg/png/webp) — used by the chat composer's image-send
 * button. See routers/uploads.py::presign_chat_image. */
export async function presignChatImage(contentType: string): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign-chat-image", { content_type: contentType });
  return resp.data;
}

/** Images only — used by the optional couple-story photo. See
 * routers/uploads.py::presign_story_image. */
export async function presignStoryImage(contentType: string): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign-story-image", { content_type: contentType });
  return resp.data;
}

/** Uploads a photo or video's raw bytes directly to R2 via the presigned
 * URL — never routes through our own backend. */
export async function uploadToPresignedUrl(uploadUrl: string, fileUri: string, contentType: string): Promise<void> {
  const fileResp = await fetch(fileUri);
  const blob = await fileResp.blob();
  const putResp = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: blob,
  });
  if (!putResp.ok) {
    throw new Error(`upload failed with status ${putResp.status}`);
  }
}
