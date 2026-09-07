import { Image, Linking, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../../api/profiles";
import VerifiedBadge from "../../components/VerifiedBadge";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import { calculateProfileCompleteness } from "../../utils/profileCompleteness";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "MyProfile">;

/** Bumble/Hinge-style profile home: a framed hero avatar (accent ring +
 * edit-pencil badge + completeness badge), name/bio, a 2-up grid of feature
 * cards, and a premium banner — all in the brand's cream/orange/navy look
 * rather than either app's literal colors. Every number and card state
 * comes from the real profile (credits, completeness %, premium status) —
 * nothing here is a static mock. */
export default function MyProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const accessToken = useAuthStore((s) => s.accessToken);

  const photo = profile?.photos[0];
  const completeness = profile ? calculateProfileCompleteness(profile) : null;
  const isPremium = profile?.is_premium_member ?? false;

  function openShop() {
    // The web shop has no login of its own — it reads the JWT straight out
    // of the URL (see web/shop.html), since the mobile app is the only place
    // a session exists. Stripe Checkout needs a real browser context anyway.
    Linking.openURL(`${env.marketingSiteUrl}/shop.html?token=${encodeURIComponent(accessToken ?? "")}`);
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.topBar}>
        <Text style={styles.topTitle}>{t("tabs.profile")}</Text>
        <Pressable style={styles.gearButton} onPress={() => navigation.navigate("Settings")} hitSlop={8}>
          <Ionicons name="settings-outline" size={22} color={colors.navy} />
        </Pressable>
      </View>

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

      <Pressable style={[styles.promoBanner, isPremium && styles.promoBannerActive]} onPress={openShop}>
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 8, gap: 4, backgroundColor: colors.cream, flexGrow: 1 },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 },
  topTitle: { fontSize: 28, fontWeight: "800", color: colors.navy },
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
});
