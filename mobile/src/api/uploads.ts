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

/** Uploads raw image bytes directly to GCS via the presigned URL — never
 * routes through our own backend. */
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
