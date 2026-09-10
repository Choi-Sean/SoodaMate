import { create } from "zustand";

/** Tracks a trip out to the web shop so that, when the app comes back to
 * the foreground, we can tell whether an actual purchase landed (credits /
 * premium went up) and show a one-time success alert — rather than a blind
 * "did you buy something? refresh" popup that would also fire when the user
 * just browsed the shop and came back. */
export interface EntitlementSnapshot {
  superlikeCredits: number;
  boostCredits: number;
  isPremium: boolean;
}

interface PurchaseState {
  /** True between opening the shop and the first foreground check after. */
  watching: boolean;
  /** Entitlements captured the moment the shop was opened. */
  before: EntitlementSnapshot | null;
  beginWatch: (snapshot: EntitlementSnapshot) => void;
  stopWatch: () => void;
}

export const usePurchaseStore = create<PurchaseState>((set) => ({
  watching: false,
  before: null,
  beginWatch: (snapshot) => set({ watching: true, before: snapshot }),
  stopWatch: () => set({ watching: false, before: null }),
}));
