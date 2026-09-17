import { apiClient } from "./client";

export async function createInquiry(subject: string, message: string): Promise<void> {
  await apiClient.post("/inquiries", { subject, message });
}
