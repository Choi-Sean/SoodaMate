import { apiClient } from "./client";
import { putFileToUrl, type PutFileResult } from "./putFile";
import { reportError } from "../services/errorReporting";

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

/** Voice messages only (always .m4a) — used by the chat composer's
 * record-and-send button. See routers/uploads.py::presign_chat_voice. */
export async function presignChatVoice(contentType: string): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign-chat-voice", { content_type: contentType });
  return resp.data;
}

/** Images only — used by the optional couple-story photo. See
 * routers/uploads.py::presign_story_image. */
export async function presignStoryImage(contentType: string): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign-story-image", { content_type: contentType });
  return resp.data;
}

/** Images only — used by a "요즘 나 / Lately" moment. See
 * routers/uploads.py::presign_moment_image. */
export async function presignMomentImage(contentType: string): Promise<PresignResult> {
  const resp = await apiClient.post<PresignResult>("/uploads/presign-moment-image", { content_type: contentType });
  return resp.data;
}

/** Uploads a photo or video's raw bytes directly to R2 via the presigned
 * URL — never routes through our own backend. */
export async function uploadToPresignedUrl(uploadUrl: string, fileUri: string, contentType: string): Promise<void> {
  const objectPath = uploadUrl.split("?")[0];
  let result: PutFileResult;
  try {
    result = await putFileToUrl(uploadUrl, fileUri, contentType);
  } catch (e) {
    reportError(e, { source: "uploadToPresignedUrl", objectPath, contentType, fileUri });
    throw e;
  }
  if (result.status < 200 || result.status >= 300) {
    // R2/S3 error bodies are small XML explaining *why* (SignatureDoesNotMatch,
    // AccessDenied, expired, ...). Keyed "errorResponse", not "body" —
    // Sentry's default scrubber masks any field named "body" as [Filtered],
    // which is exactly what hid this text the first time it was reported.
    reportError(new Error(`presigned upload failed: ${result.status}`), {
      status: result.status,
      errorResponse: result.body.slice(0, 1000),
      objectPath,
      contentType,
    });
    throw new Error(`upload failed with status ${result.status}${result.body ? `: ${result.body.slice(0, 200)}` : ""}`);
  }
}
