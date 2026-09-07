import { apiClient } from "./client";

export async function startVerification(kind: "work" | "school", email: string): Promise<void> {
  await apiClient.post("/verification/start", { kind, email });
}

export async function confirmVerification(kind: "work" | "school", code: string): Promise<void> {
  await apiClient.post("/verification/confirm", { kind, code });
}

export interface FacePresignResult {
  upload_url: string;
  gcs_object_path: string;
}

export async function presignFacePhoto(
  contentType: string,
  kind: "selfie" | "id_photo" = "selfie"
): Promise<FacePresignResult> {
  const resp = await apiClient.post<FacePresignResult>("/verification/face/presign", {
    content_type: contentType,
    kind,
  });
  return resp.data;
}

export interface FaceVerificationStatus {
  status: "unsubmitted" | "pending" | "approved" | "rejected";
  submitted_at?: string | null;
  rejection_reason?: string | null;
  rejection_reason_key?: string | null;
}

export async function submitFaceVerification(
  selfieObjectPath: string,
  idPhotoObjectPath: string
): Promise<FaceVerificationStatus> {
  const resp = await apiClient.post<FaceVerificationStatus>("/verification/face/submit", {
    selfie_object_path: selfieObjectPath,
    id_photo_object_path: idPhotoObjectPath,
  });
  return resp.data;
}

export async function getFaceVerificationStatus(): Promise<FaceVerificationStatus> {
  const resp = await apiClient.get<FaceVerificationStatus>("/verification/face/status");
  return resp.data;
}
