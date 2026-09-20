export interface PutFileResult {
  status: number;
  body: string;
}

// Browsers set Content-Type from the explicit header as-is (the RN-specific
// Blob/Content-Type problem described in putFile.native.ts doesn't exist
// here), and expo-file-system's upload API has no web implementation.
export async function putFileToUrl(uploadUrl: string, fileUri: string, contentType: string): Promise<PutFileResult> {
  const fileResp = await fetch(fileUri);
  const blob = await fileResp.blob();
  const resp = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: blob,
  });
  return { status: resp.status, body: await resp.text().catch(() => "") };
}
