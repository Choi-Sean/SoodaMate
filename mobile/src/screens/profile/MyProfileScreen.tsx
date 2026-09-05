import { Image, Linking, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../../api/profiles";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "MyProfile">;

export default function MyProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const accessToken = useAuthStore((s) => s.accessToken);

  const photo = profile?.photos[0];

  function openShop() {
    // The web shop has no login of its own — it reads the JWT straight out
    // of the URL (see web/shop.html), since the mobile app is the only place
    // a session exists. Stripe Checkout needs a real browser context anyway.
    Linking.openURL(`${env.marketingSiteUrl}/shop.html?token=${encodeURIComponent(accessToken ?? "")}`);
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {photo ? (
        <Image source={{ uri: photo.url }} style={styles.avatar} />
      ) : (
        <View style={[styles.avatar, styles.avatarPlaceholder]} />
      )}

      <View style={styles.nameRow}>
        <Text style={styles.name}>{profile?.display_name ?? "..."}</Text>
        {profile?.verified_badge && <Text style={styles.badge}>🏅</Text>}
      </View>
      {profile?.bio && <Text style={styles.bio}>{profile.bio}</Text>}

      {profile && (
        <View style={styles.creditsRow}>
          <View style={styles.creditChip}>
            <Text style={styles.creditChipText}>{t("profile.superlikeCredits", { count: profile.superlike_credits })}</Text>
          </View>
          <View style={styles.creditChip}>
            <Text style={styles.creditChipText}>{t("profile.boostCredits", { count: profile.boost_credits })}</Text>
          </View>
        </View>
      )}

      <Pressable style={styles.shopButton} onPress={openShop}>
        <Text style={styles.shopButtonText}>✨ {t("profile.shop")}</Text>
      </Pressable>

      <Pressable style={styles.button} onPress={() => navigation.navigate("EditProfile")}>
        <Text style={styles.buttonText}>{t("profile.editProfile")}</Text>
      </Pressable>
      <Pressable style={styles.button} onPress={() => navigation.navigate("PhotoManager")}>
        <Text style={styles.buttonText}>{t("profile.managePhotos")}</Text>
      </Pressable>
      <Pressable style={styles.button} onPress={() => navigation.navigate("Settings")}>
        <Text style={styles.buttonText}>{t("profile.settings")}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: "center", padding: 24, paddingTop: 48, gap: 12 },
  avatar: { width: 120, height: 120, borderRadius: 60, backgroundColor: colors.creamDeep },
  avatarPlaceholder: {},
  nameRow: { flexDirection: "row", alignItems: "center", gap: 6, marginTop: 12 },
  name: { fontSize: 22, fontWeight: "700", color: colors.navy },
  badge: { fontSize: 18 },
  bio: { color: colors.muted, textAlign: "center", marginBottom: 12 },
  creditsRow: { flexDirection: "row", gap: 8, marginBottom: 4 },
  creditChip: { backgroundColor: colors.creamDeep, borderRadius: 999, paddingVertical: 6, paddingHorizontal: 14 },
  creditChipText: { fontSize: 12.5, color: colors.accentDark, fontWeight: "700" },
  shopButton: {
    backgroundColor: colors.navy,
    borderRadius: 10,
    padding: 12,
    paddingHorizontal: 24,
    width: "100%",
    alignItems: "center",
    marginTop: 8,
  },
  shopButtonText: { color: "#fff", fontWeight: "700" },
  button: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    paddingHorizontal: 24,
    width: "100%",
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: colors.ink, fontWeight: "500" },
});
