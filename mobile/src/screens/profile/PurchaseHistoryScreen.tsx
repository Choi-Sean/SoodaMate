import { useState } from "react";
import { ActivityIndicator, FlatList, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getPurchaseHistory } from "../../api/payments";
import type { PurchaseHistoryItem } from "../../types";
import { colors } from "../../theme";

const ICON_BY_KIND: Record<string, keyof typeof Ionicons.glyphMap> = {
  ai_match: "sparkles",
  unlimited_matching_days: "infinite",
  membership: "star",
  superlike: "star",
  boost: "rocket",
};

/** Every completed Stripe purchase, newest first — lets a user confirm a
 * payment actually applied (credits/premium) without digging through their
 * bank statement, and gives a "did it work?" answer independent of whatever
 * the current balance happens to be (spent credits still show up here). See
 * MyProfileScreen's purchaseHistoryLink and the refresh button beside it —
 * together they're this app's answer to "restore purchases" (there's no
 * native IAP here, every purchase is a Stripe web checkout — see
 * utils/openShop.ts). */
export default function PurchaseHistoryScreen() {
  const { t, i18n } = useTranslation();
  const { data: items, isLoading, refetch } = useQuery({
    queryKey: ["purchaseHistory"],
    queryFn: getPurchaseHistory,
  });
  // Not react-query's own `isRefetching` — see MyProfileScreen's identical
  // fix for why (it stays true through any background refetch, including
  // ones this screen didn't ask for, and their default retries, which made
  // the pull-to-refresh spinner look stuck). Tracks only our own manual pull.
  const [manualRefreshing, setManualRefreshing] = useState(false);

  async function handleManualRefresh() {
    setManualRefreshing(true);
    try {
      await refetch();
    } finally {
      setManualRefreshing(false);
    }
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(i18n.language, { year: "numeric", month: "long", day: "numeric" });
  }

  function subtitle(item: PurchaseHistoryItem): string {
    if (item.credit_kind === "membership") return t("purchaseHistory.membershipSubtitle");
    if (item.credit_kind === "unlimited_matching_days") return t("purchaseHistory.unlimitedMatchingSubtitle");
    return t("purchaseHistory.creditsSubtitle", { count: item.credits_granted });
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(item, i) => `${item.product_id}-${item.created_at}-${i}`}
      contentContainerStyle={styles.list}
      onRefresh={handleManualRefresh}
      refreshing={manualRefreshing}
      ListEmptyComponent={
        <View style={styles.centered}>
          <Ionicons name="receipt-outline" size={40} color={colors.muted} />
          <Text style={styles.emptyText}>{t("purchaseHistory.empty")}</Text>
        </View>
      }
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.iconBubble}>
            <Ionicons name={ICON_BY_KIND[item.credit_kind] ?? "cart"} size={18} color={colors.accentDark} />
          </View>
          <View style={styles.textWrap}>
            <Text style={styles.name}>{item.name}</Text>
            <Text style={styles.subtitle}>{subtitle(item)}</Text>
            <Text style={styles.date}>{formatDate(item.created_at)}</Text>
          </View>
          <Ionicons name="checkmark-circle" size={18} color={colors.sage} />
        </View>
      )}
    />
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 60, paddingHorizontal: 30, gap: 10 },
  emptyText: { color: colors.muted, textAlign: "center", fontSize: 14, lineHeight: 20 },
  list: { padding: 16, gap: 12, flexGrow: 1 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  iconBubble: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
  },
  textWrap: { flex: 1, gap: 2 },
  name: { fontSize: 14.5, fontWeight: "800", color: colors.navy },
  subtitle: { fontSize: 12.5, color: colors.muted },
  date: { fontSize: 11.5, color: colors.muted, marginTop: 2 },
});
