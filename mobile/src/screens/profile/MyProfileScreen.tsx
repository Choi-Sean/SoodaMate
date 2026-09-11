import { useState } from "react";
import { Image, Pressable, RefreshControl, ScrollView, Text, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../../api/profiles";
import { cancelSubscription } from "../../api/account";
import VerifiedBadge from "../../components/VerifiedBadge";
import ScreenHeader from "../../components/ScreenHeader";
import { showAlert } from "../../utils/alert";
import { openShop } from "../../utils/openShop";
import { calculateProfileCompleteness } from "../../utils/profileCompleteness";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "MyProfile">;

function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

/** Bumble/Hinge-style profile home: a framed hero avatar (accent ring +
 * edit-pencil badge + completeness badge), name/bio, a 2-up grid of feature
 * cards, and a premium banner — all in the brand's cream/orange/navy look
 * rather than either app's literal colors. Every number and card state
 * comes from the real profile (credits, completeness %, premium status) —
 * nothing here is a static mock. */
export default function MyProfileScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, refetch, isRefetching } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const [canceling, setCanceling] = useState(false);

  const photo = profile?.photos[0];
  const completeness = profile ? calculateProfileCompleteness(profile) : null;
  const isPremium = profile?.is_premium_member ?? false;
  // Only a real recurring Stripe Subscription has these set (see
  // models/profile.py) - premium granted any other way (a one-time top-up,
  // a manual comp) has nothing to show a billing date/amount for or cancel.
  const hasSubscription = isPremium && !!profile?.billing_cycle;

  // The web shop has no login of its own — it reads the JWT straight out of
  // the URL (see web/shop.html). openShop() also snapshots the user's
  // credits so a completed purchase can be confirmed on return
  // (usePurchaseReturnWatch).
  const handleOpenShop = () => openShop(queryClient);

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(i18n.language, { year: "numeric", month: "long", day: "numeric" });
  }

  async function doCancel() {
    setCanceling(true);
    try {
      const result = await cancelSubscription();
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      showAlert(t("profile.cancelSuccessTitle"), t("profile.cancelSuccessBody", { date: formatDate(result.premium_until) }));
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    } finally {
      setCanceling(false);
    }
  }

  function confirmCancel() {
    if (!profile?.premium_until) return;
    showAlert(t("profile.cancelConfirmTitle"), t("profile.cancelConfirmBody", { date: formatDate(profile.premium_until) }), [
      { text: t("profile.keepMembership"), style: "cancel" },
      { text: t("profile.cancelConfirmButton"), style: "destructive", onPress: doCancel },
    ]);
  }

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.accent} />}
    >
      <ScreenHeader
        title={t("tabs.profile")}
        right={
          <Pressable style={styles.gearButton} onPress={() => navigation.navigate("Settings")} hitSlop={8}>
            <Ionicons name="settings-outline" size={22} color={colors.navy} />
          </Pressable>
        }
      />

      <View style={styles.body}>
      <View style={styles.avatarWrap}>
        <View style={styles.avatarRing}>
          {photo ? (
            <Image source={{ uri: photo.url }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarPlaceholder]} />
          )}
        </View>
        <Pressable style={styles.editBadge} onPress={() => navigation.navigate("EditProfile")} hitSlop={6}>
          <Ionicons name="pencil" size={13} color="#fff" />
        </Pressable>
        {completeness != null && completeness < 100 && (
          <View style={styles.completenessBadge}>
            <Text style={styles.completenessBadgeText}>{completeness}%</Text>
          </View>
        )}
      </View>

      <View style={styles.nameRow}>
        <Text style={styles.name}>{profile?.display_name ?? "..."}</Text>
        {profile?.verified_badge && <Text style={styles.badge}>🏅</Text>}
        {profile?.face_verified && <VerifiedBadge size={20} />}
      </View>
      {profile?.bio && <Text style={styles.bio}>{profile.bio}</Text>}

      {completeness != null && completeness < 100 && (
        <Pressable style={styles.completeCta} onPress={() => navigation.navigate("EditProfile")}>
          <Text style={styles.completeCtaText}>{t("profile.completeProfileCta")}</Text>
          <Ionicons name="chevron-forward" size={15} color={colors.accentDark} />
        </Pressable>
      )}

      {profile && (
        <View style={styles.cardGrid}>
          <View style={styles.featureCard}>
            <View style={[styles.featureIconBubble, { backgroundColor: colors.navy }]}>
              <Ionicons name="star" size={18} color="#fff" />
            </View>
            <Text style={styles.featureCardText}>{t("profile.superlikeCredits", { count: profile.superlike_credits })}</Text>
          </View>
          <View style={styles.featureCard}>
            <View style={[styles.featureIconBubble, { backgroundColor: colors.accentDark }]}>
              <Ionicons name="flash" size={18} color="#fff" />
            </View>
            <Text style={styles.featureCardText}>{t("profile.boostCredits", { count: profile.boost_credits })}</Text>
          </View>
        </View>
      )}

      <View style={styles.explainerCard}>
        <Text style={styles.explainerTitle}>{t("profile.explainerTitle")}</Text>
        {[
          { label: t("profile.explainerPremiumTitle"), body: t("profile.explainerPremiumBody") },
          { label: t("profile.explainerSuperlikeTitle"), body: t("profile.explainerSuperlikeBody") },
          { label: t("profile.explainerBoostTitle"), body: t("profile.explainerBoostBody") },
          { label: t("profile.explainerAiMatchTitle"), body: t("profile.explainerAiMatchBody") },
          { label: t("profile.explainerUnlimitedMatchingTitle"), body: t("profile.explainerUnlimitedMatchingBody") },
        ].map((row, i) => (
          <View key={i} style={styles.explainerRow}>
            <View style={styles.explainerDot} />
            <View style={styles.explainerTextWrap}>
              <Text style={styles.explainerLabel}>{row.label}</Text>
              <Text style={styles.explainerBody}>{row.body}</Text>
            </View>
          </View>
        ))}
      </View>

      <Pressable style={styles.coupleStoryCard} onPress={() => navigation.navigate("ClassicSwipe")}>
        <View style={[styles.coupleStoryIconBubble, { backgroundColor: colors.navy }]}>
          <Ionicons name="compass" size={18} color="#fff" />
        </View>
        <View style={styles.coupleStoryTextWrap}>
          <Text style={styles.coupleStoryTitle}>{t("profile.classicMatchingCardTitle")}</Text>
          <Text style={styles.coupleStorySubtitle}>{t("profile.classicMatchingCardSubtitle")}</Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color={colors.accentDark} />
      </Pressable>

      <Pressable style={styles.coupleStoryCard} onPress={() => navigation.navigate("CoupleStoriesFeed")}>
        <View style={styles.coupleStoryIconBubble}>
          <Ionicons name="heart" size={18} color="#fff" />
        </View>
        <View style={styles.coupleStoryTextWrap}>
          <Text style={styles.coupleStoryTitle}>{t("profile.coupleStoryCardTitle")}</Text>
          <Text style={styles.coupleStorySubtitle}>{t("profile.coupleStoryCardSubtitle")}</Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color={colors.accentDark} />
      </Pressable>

      <Pressable style={[styles.promoBanner, isPremium && styles.promoBannerActive]} onPress={handleOpenShop}>
        <Ionicons name="sparkles" size={22} color={isPremium ? colors.navy : "#fff"} />
        <Text style={[styles.promoTitle, isPremium && styles.promoTitleActive]}>
          {isPremium ? t("profile.premiumActiveTitle") : t("profile.premiumBannerTitle")}
        </Text>
        <Text style={[styles.promoBody, isPremium && styles.promoBodyActive]}>
          {isPremium ? t("profile.premiumActiveBody") : t("profile.premiumBannerBody")}
        </Text>
        {!isPremium && (
          <View style={styles.promoCta}>
            <Text style={styles.promoCtaText}>{t("profile.premiumBannerCta")}</Text>
          </View>
        )}
      </Pressable>

      {hasSubscription && profile?.premium_until && (
        <View style={styles.billingCard}>
          <View style={styles.billingRow}>
            <Text style={styles.billingPlan}>
              {profile.billing_cycle === "yearly" ? t("profile.billingCycleYearly") : t("profile.billingCycleMonthly")}
            </Text>
          </View>
          {profile.cancel_at_period_end ? (
            <Text style={styles.billingCancelledText}>{t("profile.cancelledBanner", { date: formatDate(profile.premium_until) })}</Text>
          ) : (
            <>
              <Text style={styles.billingLabel}>{t("profile.nextBillingLabel")}</Text>
              <Text style={styles.billingAmount}>
                {t("profile.nextBillingBody", {
                  amount: formatPrice(profile.subscription_price_cents ?? 0),
                  date: formatDate(profile.premium_until),
                })}
              </Text>
              <Pressable style={styles.cancelButton} onPress={confirmCancel} disabled={canceling}>
                <Text style={styles.cancelButtonText}>{t("profile.cancelMembership")}</Text>
              </Pressable>
              <Text style={styles.noRefundText}>{t("profile.noRefundNotice")}</Text>
            </>
          )}
        </View>
      )}

      <View style={styles.perksCard}>
        <Text style={styles.perksTitle}>{t("profile.perksTitle")}</Text>
        {[
          { icon: "infinite" as const, label: t("profile.perkUnlimitedSwipes") },
          { icon: "eye" as const, label: t("profile.perkSeeWhoLikedYou") },
          { icon: "options" as const, label: t("profile.perkAdvancedFilters") },
        ].map((perk, i) => (
          <View key={i} style={styles.perkRow}>
            <View style={styles.perkIconBubble}>
              <Ionicons name={perk.icon} size={15} color={colors.accentDark} />
            </View>
            <Text style={styles.perkText}>{perk.label}</Text>
            <Ionicons name="checkmark" size={16} color={colors.sage} />
          </View>
        ))}
      </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { paddingBottom: 20, backgroundColor: colors.cream, flexGrow: 1 },
  body: { paddingHorizontal: 20, gap: 4 },
  gearButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  avatarWrap: { alignSelf: "center", marginTop: 8 },
  avatarRing: {
    width: 128,
    height: 128,
    borderRadius: 64,
    borderWidth: 3,
    borderColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  avatar: { width: 116, height: 116, borderRadius: 58, backgroundColor: colors.creamDeep },
  avatarPlaceholder: {},
  editBadge: {
    position: "absolute",
    bottom: 2,
    right: 2,
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: colors.navy,
    borderWidth: 2,
    borderColor: colors.cream,
    alignItems: "center",
    justifyContent: "center",
  },
  completenessBadge: {
    position: "absolute",
    bottom: 2,
    left: -4,
    backgroundColor: colors.navyDeep,
    borderRadius: 12,
    paddingVertical: 3,
    paddingHorizontal: 9,
    borderWidth: 2,
    borderColor: colors.cream,
  },
  completenessBadgeText: { color: "#fff", fontSize: 11, fontWeight: "800" },
  nameRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: 14 },
  name: { fontSize: 22, fontWeight: "800", color: colors.navy },
  badge: { fontSize: 18 },
  bio: { color: colors.muted, textAlign: "center", marginTop: 4, marginBottom: 4, paddingHorizontal: 12 },
  completeCta: {
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.creamDeep,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginTop: 6,
    marginBottom: 4,
  },
  completeCtaText: { color: colors.accentDark, fontWeight: "700", fontSize: 13 },
  cardGrid: { flexDirection: "row", gap: 12, marginTop: 18 },
  featureCard: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 16,
    gap: 10,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  featureIconBubble: { width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center" },
  featureCardText: { color: colors.ink, fontWeight: "700", fontSize: 14 },
  explainerCard: {
    marginTop: 16,
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: colors.border,
  },
  explainerTitle: { fontSize: 14, fontWeight: "800", color: colors.navy, marginBottom: 2 },
  explainerRow: { flexDirection: "row", gap: 10, alignItems: "flex-start" },
  explainerDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.accent, marginTop: 6 },
  explainerTextWrap: { flex: 1 },
  explainerLabel: { fontSize: 13.5, fontWeight: "700", color: colors.navy },
  explainerBody: { fontSize: 12.5, color: colors.muted, marginTop: 2, lineHeight: 17 },
  coupleStoryCard: {
    marginTop: 16,
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  coupleStoryIconBubble: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.heart,
    alignItems: "center",
    justifyContent: "center",
  },
  coupleStoryTextWrap: { flex: 1 },
  coupleStoryTitle: { fontSize: 14.5, fontWeight: "800", color: colors.navy },
  coupleStorySubtitle: { fontSize: 12, color: colors.muted, marginTop: 2, lineHeight: 16 },
  promoBanner: {
    marginTop: 16,
    backgroundColor: colors.navy,
    borderRadius: 22,
    padding: 20,
    gap: 4,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  promoBannerActive: { backgroundColor: colors.creamDeep, shadowOpacity: 0.05 },
  promoTitle: { fontSize: 17, fontWeight: "800", color: "#fff", marginTop: 4 },
  promoTitleActive: { color: colors.navy },
  promoBody: { fontSize: 13, color: "rgba(255,255,255,0.85)", lineHeight: 19 },
  promoBodyActive: { color: colors.ink },
  promoCta: { alignSelf: "flex-start", backgroundColor: colors.accent, borderRadius: 999, paddingVertical: 10, paddingHorizontal: 18, marginTop: 8 },
  promoCtaText: { color: "#fff", fontWeight: "700", fontSize: 13.5 },
  billingCard: {
    marginTop: 12,
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 18,
    gap: 4,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  billingRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  billingPlan: { fontSize: 13, fontWeight: "800", color: colors.navy, textTransform: "uppercase", letterSpacing: 0.3 },
  billingLabel: { fontSize: 12.5, color: colors.muted, marginTop: 6 },
  billingAmount: { fontSize: 17, fontWeight: "800", color: colors.ink },
  billingCancelledText: { fontSize: 13, color: colors.muted, lineHeight: 19, marginTop: 4 },
  cancelButton: { marginTop: 12, alignSelf: "flex-start" },
  cancelButtonText: { color: colors.danger, fontWeight: "700", fontSize: 13.5 },
  noRefundText: { fontSize: 11, color: colors.muted, marginTop: 8 },
  perksCard: {
    marginTop: 12,
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 18,
    gap: 12,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
  perksTitle: { fontSize: 15, fontWeight: "800", color: colors.navy },
  perkRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  perkIconBubble: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
  },
  perkText: { flex: 1, fontSize: 13.5, color: colors.ink, fontWeight: "500" },
});
