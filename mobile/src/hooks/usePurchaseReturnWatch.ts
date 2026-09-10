import { useEffect } from "react";
import { AppState } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../api/profiles";
import { usePurchaseStore } from "../store/purchaseStore";
import { showAlert } from "../utils/alert";

/** Mounted once in the signed-in app. When the app returns to the
 * foreground after a trip to the web shop (usePurchaseStore.watching),
 * refetches the profile and, if credits / premium actually went up, shows
 * a one-time localized success alert. Stays silent when nothing changed —
 * a slow webhook is then picked up by the ordinary focus refetch. */
export function usePurchaseReturnWatch() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  useEffect(() => {
    const sub = AppState.addEventListener("change", async (state) => {
      if (state !== "active") return;
      const { watching, before, stopWatch } = usePurchaseStore.getState();
      if (!watching || !before) return;

      try {
        const fresh = await queryClient.fetchQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
        const gainedSuperlike = fresh.superlike_credits - before.superlikeCredits;
        const gainedBoost = fresh.boost_credits - before.boostCredits;
        const gainedPremium = fresh.is_premium_member && !before.isPremium;

        if (gainedPremium) {
          showAlert(t("profile.purchaseSuccessTitle"), t("profile.purchasePremiumSuccess"));
        } else if (gainedSuperlike > 0) {
          showAlert(t("profile.purchaseSuccessTitle"), t("profile.purchaseSuperlikeSuccess", { count: gainedSuperlike }));
        } else if (gainedBoost > 0) {
          showAlert(t("profile.purchaseSuccessTitle"), t("profile.purchaseBoostSuccess", { count: gainedBoost }));
        }
      } catch {
        // network hiccup — the ordinary focus refetch will catch up.
      } finally {
        stopWatch();
      }
    });
    return () => sub.remove();
  }, [queryClient, t]);
}
