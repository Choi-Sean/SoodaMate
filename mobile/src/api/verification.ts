import { apiClient } from "./client";

export async function startVerification(kind: "work" | "school", email: string): Promise<void> {
  await apiClient.post("/verification/start", { kind, email });
}

export async function confirmVerification(kind: "work" | "school", code: string): Promise<void> {
  await apiClient.post("/verification/confirm", { kind, code });
}
