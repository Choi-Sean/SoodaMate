import { apiClient } from "./client";
import type { PurchaseHistoryItem } from "../types";

export async function getPurchaseHistory(): Promise<PurchaseHistoryItem[]> {
  const resp = await apiClient.get<{ items: PurchaseHistoryItem[] }>("/payments/history");
  return resp.data.items;
}
