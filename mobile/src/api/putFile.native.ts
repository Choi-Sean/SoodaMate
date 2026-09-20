import * as FileSystem from "expo-file-system/legacy";

export interface PutFileResult {
  status: number;
  body: string;
}

/** PUTs a local file's raw bytes to a presigned URL using the OS's own
 * upload task (NSURLSession / OkHttp via expo-file-system) rather than
 * React Native's fetch + Blob. RN's Blob path derives what it sends from
 * the Blob's own metadata (blob.type comes back empty for a file:// read),
 * and a presigned R2/S3 PUT signs Content-Type into the signature — any
 * difference from what was signed is a 403 with no useful client-side
 * signal (this is exactly what production showed: every image/video upload
 * 403'd on iOS while the same presigned URL succeeded from a plain HTTP
 * client). A native upload task sends the file bytes as-is with exactly the
 * headers given.
 *
 * FOREGROUND session (not the default BACKGROUND one): a background session
 * retries forever on failure instead of returning the HTTP status, which
 * would leave a user staring at a spinner — this is an interactive upload
 * the caller awaits and reports on. */
export async function putFileToUrl(uploadUrl: string, fileUri: string, contentType: string): Promise<PutFileResult> {
  const result = await FileSystem.uploadAsync(uploadUrl, fileUri, {
    httpMethod: "PUT",
    uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
    sessionType: FileSystem.FileSystemSessionType.FOREGROUND,
    headers: { "Content-Type": contentType },
  });
  return { status: result.status, body: result.body };
}
